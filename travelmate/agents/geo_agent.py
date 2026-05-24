from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from travelmate.models import GeoOutput, PlannerState
from travelmate.prompts.geo_prompt import SYSTEM_PROMPT, TASK_PROMPT
from travelmate.tools.here_maps import get_here_destination_context, get_here_places_details
from travelmate.tools.llm_content import message_to_text
from travelmate.tools.logging_utils import get_logger
from travelmate.tools.markdown_contract import parse_geo_markdown
from travelmate.tools.model_factory import get_chat_model
from travelmate.tools.token_tracker import get_tracker


LOGGER = get_logger("geo_agent")


def geo_agent(state: PlannerState) -> dict[str, Any]:
    LOGGER.info("Krok 3/6: analiza geograficzna — start.")
    llm = get_chat_model()
    request = state["request"]
    task_prompt = TASK_PROMPT.format(
        destination=request.destination,
        days=request.days,
        budget=request.budget.value,
        pace=request.pace.value,
    )
    payload = {
        "request": request.model_dump(mode="json"),
        "profile": state["profile_summary"],
    }
    here_context = get_here_destination_context(request.destination)
    if here_context:
        payload["here_map_context"] = here_context

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=task_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
        ]
    )
    get_tracker().record("geo_agent", response)
    geo_markdown = message_to_text(response)
    draft = parse_geo_markdown(geo_markdown, expected_days=request.days)

    all_places: list[str] = []
    for day in draft.days:
        all_places.extend([day.morning_zone, day.afternoon_zone, day.evening_zone])

    place_details = get_here_places_details(request.destination, all_places)

    enriched_days = []
    for day in draft.days:
        enriched_days.append(
            {
                "day": day.day,
                "title": day.title,
                "morning_zone": place_details.get(day.morning_zone) or {
                    "name": day.morning_zone,
                    "coordinates": {"lat": None, "lng": None},
                    "address": {
                        "country": "",
                        "city": "",
                        "postcode": "",
                        "street": "",
                        "building_number": "",
                    },
                    "website": "",
                    "source": "unresolved",
                },
                "afternoon_zone": place_details.get(day.afternoon_zone) or {
                    "name": day.afternoon_zone,
                    "coordinates": {"lat": None, "lng": None},
                    "address": {
                        "country": "",
                        "city": "",
                        "postcode": "",
                        "street": "",
                        "building_number": "",
                    },
                    "website": "",
                    "source": "unresolved",
                },
                "evening_zone": place_details.get(day.evening_zone) or {
                    "name": day.evening_zone,
                    "coordinates": {"lat": None, "lng": None},
                    "address": {
                        "country": "",
                        "city": "",
                        "postcode": "",
                        "street": "",
                        "building_number": "",
                    },
                    "website": "",
                    "source": "unresolved",
                },
            }
        )

    response = GeoOutput.model_validate(
        {
            "mobility_strategy": draft.mobility_strategy,
            "days": enriched_days,
        }
    )

    LOGGER.info(
        "Krok 3/6: geo gotowe: strategia='%s', dni=%d.",
        response.mobility_strategy,
        len(response.days),
    )
    return {
        "geo_markdown": geo_markdown,
        "geo_output": response,
    }
