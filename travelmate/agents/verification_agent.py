from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from openai import BadRequestError

from travelmate.models import PlannerState, VerificationOutput
from travelmate.prompts.verification_prompt import SYSTEM_PROMPT, TASK_PROMPT
from travelmate.tools.llm_content import message_to_text
from travelmate.tools.logging_utils import compact_text, get_logger
from travelmate.tools.markdown_contract import parse_verification_markdown
from travelmate.tools.model_factory import get_chat_model
from travelmate.tools.token_tracker import get_tracker


LOGGER = get_logger("verification_agent")


def _truncate(text: str, limit: int = 1200) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _compact_geo_for_verification(state: PlannerState) -> dict[str, Any]:
    geo = state["geo_output"]
    return {
        "mobility_strategy": geo.mobility_strategy,
        "days": [
            {
                "day": day.day,
                "title": day.title,
                "morning_place": day.morning_zone.name,
                "afternoon_place": day.afternoon_zone.name,
                "evening_place": day.evening_zone.name,
            }
            for day in geo.days
        ],
    }

def _compact_itinerary_for_verification(state: PlannerState) -> dict[str, Any]:
    draft = state["itinerary_draft"]
    return {
        "estimated_ticket_cost": draft.estimated_ticket_cost,
        "days": [
            {
                "day": day.day,
                "area_title": day.area_title,
                "morning": [f"{item.start}-{item.end} {item.name}" for item in day.morning_activities],
                "lunch": f"{day.lunch.time} {day.lunch.name}",
                "afternoon": [f"{item.start}-{item.end} {item.name}" for item in day.afternoon_activities],
                "dinner": f"{day.dinner.time} {day.dinner.name}",
                "lodging": (
                    f"{day.lodging.name} ({day.lodging.area}, {day.lodging.price})"
                    if day.lodging
                    else "brak"
                ),
            }
            for day in draft.days
        ],
    }


def verification_agent(state: PlannerState) -> dict[str, Any]:
    LOGGER.info("Krok 5/6: weryfikacja planu — start.")
    llm = get_chat_model()
    compact_itinerary = _compact_itinerary_for_verification(state)
    compact_request = {
        "destination": state["request"].destination,
        "days": state["request"].days,
        "budget": state["request"].budget.value,
        "pace": state["request"].pace.value,
        "constraints": state["request"].constraints[:8],
        "interests": state["request"].interests[:8],
    }
    payload = {
        "request": compact_request,
        "itinerary_draft": compact_itinerary,
        "itinerary_markdown": _truncate(state.get("itinerary_markdown", ""), limit=2800),
    }
    flow_history = {
        "profile_summary": _truncate(state["profile_summary"], limit=600),
        "geo_output": _compact_geo_for_verification(state),
        "geo_markdown": _truncate(state.get("geo_markdown", ""), limit=1200),
    }
    task_prompt = TASK_PROMPT.format(
        user_info=json.dumps(payload["request"], ensure_ascii=False, separators=(",", ":")),
        plan_content=json.dumps(
            {
                "itinerary_draft": payload["itinerary_draft"],
                "itinerary_markdown": payload["itinerary_markdown"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        flow_history=json.dumps(flow_history, ensure_ascii=False, separators=(",", ":")),
    )

    try:
        llm_response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=task_prompt),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            ]
        )
        get_tracker().record("verification_agent", llm_response)
        verification_markdown = message_to_text(llm_response)
        response = parse_verification_markdown(verification_markdown)
    except BadRequestError as exc:
        if "Context size has been exceeded" in str(exc) or "n_ctx" in str(exc):
            LOGGER.warning(
                "Krok 5/6: przekroczony kontekst modelu (%s). Używam fallbacku weryfikacji.",
                exc,
            )
            verification_markdown = ""
            response = VerificationOutput(
                opening_hours_warnings=[
                    "Weryfikacja skrócona: przekroczony kontekst modelu. Sprawdź godziny otwarcia ręcznie."
                ],
                adjustments=[],
            )
        else:
            raise
    except Exception as exc:
        LOGGER.warning("Krok 5/6: awaria weryfikacji (%s). Używam fallbacku.", exc)
        verification_markdown = ""
        response = VerificationOutput(
            opening_hours_warnings=[
                "Weryfikacja częściowo niedostępna (fallback). Sprawdź krytyczne punkty ręcznie."
            ],
            adjustments=[],
        )
    first_warning = (
        compact_text(response.opening_hours_warnings[0])
        if response.opening_hours_warnings
        else "brak"
    )
    LOGGER.info(
        "Krok 5/6: weryfikacja gotowa: ostrzeżenia=%d, poprawki=%d, pierwsze_ostrzeżenie='%s'.",
        len(response.opening_hours_warnings),
        len(response.adjustments),
        first_warning,
    )
    return {
        "verification_markdown": verification_markdown,
        "verification": response,
    }
