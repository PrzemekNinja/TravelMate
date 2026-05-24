from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from travelmate.models import PlannerState
from travelmate.prompts.formatter_prompt import SYSTEM_PROMPT, TASK_PROMPT
from travelmate.tools.llm_content import message_to_text
from travelmate.tools.logging_utils import get_logger
from travelmate.tools.markdown_formatter import build_geo_poi_section, build_lodging_poi_section, build_markdown
from travelmate.tools.model_factory import get_chat_model


LOGGER = get_logger("formatter_agent")


def _truncate(text: str, limit: int = 1200) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _build_compact_generated_plan(state: PlannerState) -> dict[str, Any]:
    draft = state["itinerary_draft"]
    return {
        "estimated_ticket_cost": draft.estimated_ticket_cost,
        "days": [
            {
                "day": day.day,
                "title": day.area_title,
                "morning": [activity.name for activity in day.morning_activities[:3]],
                "lunch": day.lunch.name,
                "afternoon": [activity.name for activity in day.afternoon_activities[:3]],
                "dinner": day.dinner.name,
                "lodging": day.lodging.name if day.lodging else "none",
            }
            for day in draft.days
        ],
    }


def _build_compact_verification(state: PlannerState) -> dict[str, Any]:
    verification = state["verification"]
    return {
        "warnings": verification.opening_hours_warnings[:12],
        "adjustments": verification.adjustments[:12],
    }


def _normalize_for_match(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _count_day_headers(markdown: str) -> int:
    return len(
        re.findall(
            r"^#{2,4}\s+[^\n]*(?:dzień|day)\s+\d+",
            markdown,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def _is_formatter_output_consistent(final_markdown: str, destination: str, expected_days: int) -> tuple[bool, str]:
    normalized_destination = _normalize_for_match(destination)
    normalized_markdown = _normalize_for_match(final_markdown)

    if normalized_destination and normalized_destination not in normalized_markdown:
        return False, "destination_mismatch"

    detected_days = _count_day_headers(final_markdown)
    if detected_days > 0 and detected_days != expected_days:
        return False, f"days_mismatch:{detected_days}!={expected_days}"

    return True, "ok"


def formatter_agent(state: PlannerState) -> dict[str, Any]:
    LOGGER.info("Krok 6/6: formatowanie końcowe — start.")
    req = state["request"]
    draft = state["itinerary_draft"]
    verification = state["verification"]

    baseline_markdown = build_markdown(
        req=req,
        profile_summary=state["profile_summary"],
        transport_report=state["transport_report"],
        mobility_strategy=state["geo_output"].mobility_strategy,
        geo_output=state["geo_output"],
        draft=draft,
        verification=verification,
    )

    llm = get_chat_model()
    compact_plan = _build_compact_generated_plan(state)
    compact_verification = _build_compact_verification(state)
    compact_user_info = {
        "destination": req.destination,
        "days": req.days,
        "budget": req.budget.value,
        "pace": req.pace.value,
        "constraints": req.constraints[:8],
        "interests": req.interests[:8],
    }

    payload = {
        "generated_plan": compact_plan,
        "verification_results": compact_verification,
        "user_info": compact_user_info,
        "profile_summary": state["profile_markdown"],
        "profile_markdown": _truncate(state["profile_markdown"], limit=1000),
        "transport_markdown": _truncate(state["transport_markdown"], limit=1400),
        "geo_markdown": _truncate(state["geo_markdown"], limit=1200),
        "itinerary_markdown": _truncate(state["itinerary_markdown"], limit=2200),
        "verification_markdown": _truncate(state["verification_markdown"], limit=1200),
        "mobility_strategy": state["geo_output"].mobility_strategy,
        "baseline_markdown": baseline_markdown,
    }
    task_prompt = TASK_PROMPT.format(
        generated_plan=json.dumps(payload["generated_plan"], ensure_ascii=False, separators=(",", ":")),
        verification_results=json.dumps(payload["verification_results"], ensure_ascii=False, separators=(",", ":")),
        user_info=json.dumps(payload["user_info"], ensure_ascii=False, separators=(",", ":")),
        profile_markdown=payload["profile_markdown"],
        transport_markdown=payload["transport_markdown"],
        geo_markdown=payload["geo_markdown"],
        itinerary_markdown=payload["itinerary_markdown"],
        verification_markdown=payload["verification_markdown"],
    )

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=task_prompt),
            HumanMessage(content=payload["baseline_markdown"]),
        ]
    )
    final_markdown = message_to_text(response) or baseline_markdown

    is_consistent, reason = _is_formatter_output_consistent(
        final_markdown=final_markdown,
        destination=req.destination,
        expected_days=req.days,
    )
    if not is_consistent:
        LOGGER.warning(
            "Krok 6/6: wykryto niespójność outputu formattera (%s). Wracam do baseline markdown.",
            reason,
        )
        final_markdown = baseline_markdown

    poi_section = build_geo_poi_section(state["geo_output"], draft=draft)
    if "### 📍 Metadane POI (geo)" not in final_markdown:
        final_markdown = f"{final_markdown}\n\n{poi_section}".strip()
    elif "#### 🏨 Noclegi (POI)" not in final_markdown:
        lodging_section = build_lodging_poi_section(draft)
        if lodging_section:
            final_markdown = f"{final_markdown}\n\n{lodging_section}".strip()

    LOGGER.info("Krok 6/6: formatowanie gotowe: długość_markdown=%d znaków.", len(final_markdown))
    return {"final_markdown": final_markdown}
