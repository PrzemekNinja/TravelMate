from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from travelmate.models import PlannerState
from travelmate.prompts.profile_prompt import SYSTEM_PROMPT, TASK_PROMPT
from travelmate.tools.llm_content import message_to_text
from travelmate.tools.logging_utils import compact_text, get_logger
from travelmate.tools.model_factory import get_chat_model
from travelmate.tools.payload import request_to_json_payload
from travelmate.tools.token_tracker import get_tracker


LOGGER = get_logger("profile_agent")


def profile_agent(state: PlannerState) -> dict[str, Any]:
    LOGGER.info("Krok 1/6: profil podróżnika — start.")
    llm = get_chat_model()
    request = state["request"]
    task_prompt = TASK_PROMPT.format(
        destination=request.destination,
        days=request.days,
        budget=request.budget.value,
        pace=request.pace.value,
    )
    payload = request_to_json_payload(request)

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=task_prompt),
            HumanMessage(content=payload),
        ]
    )
    get_tracker().record("profile_agent", response)
    profile_summary = message_to_text(response)
    LOGGER.info("Krok 1/6: profil gotowy: %s", compact_text(profile_summary))
    return {
        "profile_markdown": profile_summary,
        "profile_summary": profile_summary,
    }
