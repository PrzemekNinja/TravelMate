from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from openai import BadRequestError

from travelmate.models import ActivityEntry, DayPlan, ItineraryDraft, LodgingEntry, MealEntry, PlannerState
from travelmate.prompts.itinerary_prompt import COMPACT_SYSTEM_PROMPT, COMPACT_TASK_PROMPT
from travelmate.tools.llm_content import message_to_text
from travelmate.tools.logging_utils import get_logger
from travelmate.tools.markdown_contract import parse_itinerary_markdown
from travelmate.tools.model_factory import get_chat_model
from travelmate.tools.token_tracker import get_tracker


LOGGER = get_logger("itinerary_agent")


def _truncate(text: str, limit: int = 320) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _price_for_budget(budget_value: str) -> str:
    mapping = {
        "Low": "$",
        "Mid": "$$",
        "Luxury": "$$$",
    }
    return mapping.get(budget_value, "$$")


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _build_lodging_preferences(state: PlannerState) -> dict[str, Any]:
    request = state["request"]
    constraints = [c.strip() for c in request.constraints if c and c.strip()]
    normalized = [c.lower() for c in constraints]

    hard_requirements: list[str] = []
    soft_requirements: list[str] = []

    hard_markers = (
        "must",
        "musi",
        "obowiązk",
        "konieczn",
        "bezwzgl",
    )
    hard_topic_markers = (
        "winda",
        "elevator",
        "wheelchair",
        "accessible",
        "bez schod",
        "niepełnosp",
        "parking",
        "pet",
        "zwier",
        "late check",
        "24h recepcj",
        "24/7",
        "cisz",
        "quiet",
        "safe",
        "bezpiecz",
    )

    for original, lowered in zip(constraints, normalized, strict=False):
        if _contains_any(lowered, hard_markers) or _contains_any(lowered, hard_topic_markers):
            hard_requirements.append(original)
        else:
            soft_requirements.append(original)

    if request.accommodation_area:
        hard_requirements.insert(0, f"Obszar noclegu: {request.accommodation_area}")

    return {
        "hard_requirements": hard_requirements[:8],
        "soft_requirements": soft_requirements[:8],
        "priority_order": [
            "1) hard_requirements (must-have)",
            "2) budget alignment",
            "3) proximity to evening activities / transit",
            "4) soft_requirements (nice-to-have)",
        ],
        "selection_policy": (
            "Najpierw odrzuć opcje niespełniające hard_requirements. "
            "Przy remisie wybierz nocleg najlepiej zgodny z budżetem i logistyką przejazdów."
        ),
    }


def _fallback_itinerary_from_geo(state: PlannerState, compact_geo: dict[str, Any]) -> ItineraryDraft:
    request = state["request"]
    price = _price_for_budget(request.budget.value)
    lodging_preferences = _build_lodging_preferences(state)
    preferred_area = (request.accommodation_area or "").strip()

    days: list[DayPlan] = []
    for day in compact_geo.get("days", []):
        morning_place = day.get("morning_place", "Poranna atrakcja")
        afternoon_place = day.get("afternoon_place", "Popołudniowa atrakcja")
        evening_place = day.get("evening_place", "Wieczorna atrakcja")
        lodging_area = preferred_area or str(day.get("title", "centrum"))
        hard_joined = ", ".join(lodging_preferences["hard_requirements"]) or "brak"
        soft_joined = ", ".join(lodging_preferences["soft_requirements"]) or "brak"
        lodging_note = (
            f"Priorytety (hard): {hard_joined}. Nice-to-have: {soft_joined}. "
            "Wybierz nocleg blisko wieczornych aktywności lub głównego węzła transportowego."
        )

        days.append(
            DayPlan(
                day=int(day.get("day", 1)),
                area_title=str(day.get("title", f"Dzień {day.get('day', 1)}")),
                morning_activities=[
                    ActivityEntry(
                        start="09:00",
                        end="11:30",
                        name=morning_place,
                        why="Miejsce rekomendowane przez geo-clustering.",
                        logistics="Dojazd zgodnie z mobility_strategy.",
                    )
                ],
                lunch=MealEntry(
                    meal_type="lunch",
                    time="12:30",
                    name=f"Lunch blisko {morning_place}",
                    cuisine="Local",
                    price=price,
                    address_or_location=morning_place,
                    note="Wybierz lokal do 10-15 min pieszo od porannej atrakcji.",
                ),
                afternoon_activities=[
                    ActivityEntry(
                        start="14:00",
                        end="16:30",
                        name=afternoon_place,
                        why="Kontynuacja dnia w tej samej strefie geograficznej.",
                        logistics="Przejście/krótki przejazd zgodnie z planem transportu.",
                    )
                ],
                dinner=MealEntry(
                    meal_type="dinner",
                    time="19:00",
                    name=f"Kolacja blisko {evening_place}",
                    cuisine="Local",
                    price=price,
                    address_or_location=evening_place,
                    ambience="Spokojna atmosfera na zakończenie dnia.",
                ),
                lodging=LodgingEntry(
                    name=f"Nocleg w rejonie {lodging_area}",
                    area=lodging_area,
                    price=price,
                    check_in="15:00",
                    check_out="11:00",
                    note=lodging_note,
                ),
            )
        )

    return ItineraryDraft(days=days, estimated_ticket_cost="Do potwierdzenia na miejscu")


def _compact_geo_for_planning(state: PlannerState) -> dict[str, Any]:
    geo = state["geo_output"]
    compact_days: list[dict[str, Any]] = []

    for day in geo.days:
        compact_days.append(
            {
                "day": day.day,
                "title": day.title,
                "morning_place": day.morning_zone.name,
                "afternoon_place": day.afternoon_zone.name,
                "evening_place": day.evening_zone.name,
            }
        )

    return {
        "mobility_strategy": geo.mobility_strategy,
        "days": compact_days,
    }


def itinerary_agent(state: PlannerState) -> dict[str, Any]:
    LOGGER.info("Krok 4/6: budowa szkicu planu — start.")
    llm = get_chat_model()
    compact_geo = _compact_geo_for_planning(state)
    lodging_preferences = _build_lodging_preferences(state)
    request = state["request"]

    compact_request = {
        "destination": request.destination,
        "days": request.days,
        "budget": request.budget.value,
        "pace": request.pace.value,
        "interests": request.interests[:6],
        "constraints": request.constraints[:6],
        "accommodation_area": request.accommodation_area,
        "lodging_preferences": lodging_preferences,
    }

    payload = {
        "request": compact_request,
        "profile": _truncate(state["profile_summary"]),
        "geo": compact_geo,
    }
    task_compact = COMPACT_TASK_PROMPT

    try:
        llm_response = llm.invoke(
            [
                SystemMessage(content=COMPACT_SYSTEM_PROMPT),
                SystemMessage(content=task_compact),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            ]
        )
        get_tracker().record("itinerary_agent", llm_response)
        itinerary_markdown = message_to_text(llm_response)
        response = parse_itinerary_markdown(itinerary_markdown)
    except BadRequestError as exc:
        if "Context size has been exceeded" in str(exc) or "n_ctx" in str(exc):
            LOGGER.warning(
                "Krok 4/6: przekroczony kontekst modelu (%s). Używam fallbacku itinerary bez LLM.",
                exc,
            )
            itinerary_markdown = ""
            response = _fallback_itinerary_from_geo(state, compact_geo)
        else:
            raise
    except Exception as exc:
        LOGGER.warning(
            "Krok 4/6: awaria wywołania modelu (%s). Używam fallbacku itinerary bez LLM.",
            exc,
        )
        itinerary_markdown = ""
        response = _fallback_itinerary_from_geo(state, compact_geo)
    LOGGER.info(
        "Krok 4/6: szkic gotowy: dni=%d, koszt_biletów='%s'.",
        len(response.days),
        response.estimated_ticket_cost,
    )
    return {
        "itinerary_markdown": itinerary_markdown,
        "itinerary_draft": response,
    }
