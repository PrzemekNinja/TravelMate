from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from travelmate.models import PlannerState
from travelmate.prompts.transport_prompt import SYSTEM_PROMPT, TASK_PROMPT
from travelmate.tools.llm_content import message_to_text
from travelmate.tools.logging_utils import compact_text, get_logger
from travelmate.tools.model_factory import get_chat_model


LOGGER = get_logger("transport_agent")


def _format_travel_dates(state: PlannerState) -> str:
    req = state["request"]
    if req.travel_start_date and req.travel_end_date:
        return f"{req.travel_start_date.isoformat()} -> {req.travel_end_date.isoformat()}"
    if req.travel_start_date:
        return f"od {req.travel_start_date.isoformat()}"
    if req.travel_end_date:
        return f"do {req.travel_end_date.isoformat()}"
    return "Wymaga doprecyzowania"


def _build_baggage_summary(state: PlannerState) -> dict[str, Any]:
    baggage = state["request"].baggage
    if not baggage:
        return {
            "pieces": 0,
            "weight_kg": 0.0,
            "details": ["Brak danych o bagażu (Wymaga doprecyzowania)."],
        }

    total_pieces = sum(item.pieces for item in baggage)
    total_weight = round(sum(item.weight_kg * item.pieces for item in baggage), 2)
    details = [
        (
            f"{item.owner or 'uczestnik'}: {item.pieces} szt., "
            f"{item.height_cm}x{item.width_cm}x{item.depth_cm} cm, "
            f"{item.weight_kg} kg/szt."
        )
        for item in baggage
    ]
    return {
        "pieces": total_pieces,
        "weight_kg": total_weight,
        "details": details,
    }


def transport_agent(state: PlannerState) -> dict[str, Any]:
    LOGGER.info("Krok 2/6: planowanie transportu — start.")
    req = state["request"]
    llm = get_chat_model()

    task_prompt = TASK_PROMPT.format(
        home_location=req.home_location or "Wymaga doprecyzowania",
        destination=req.destination,
        travel_dates=_format_travel_dates(state),
        participants=req.participants,
        budget=req.budget.value,
        pace=req.pace.value,
    )

    payload = {
        "request": req.model_dump(mode="json"),
        "profile_summary": state["profile_summary"],
        "baggage_summary": _build_baggage_summary(state),
    }

    try:
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=task_prompt),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
            ]
        )
        transport_report = message_to_text(response)
    except Exception as exc:
        LOGGER.warning("Krok 2/6: błąd transport_agent (%s). Używam fallbacku.", exc)
        transport_report = (
            "# RAPORT TRANSPORTOWY\n"
            "## Podsumowanie parametrów\n"
            f"- Trasa: {req.home_location or 'Wymaga doprecyzowania'} -> {req.destination}\n"
            f"- Liczba osób: {req.participants}\n"
            "- Łączny Bagaż: Wymaga doprecyzowania\n"
            f"- Budżet: {req.budget.value}\n"
            "\n"
            "## Propozycja 1: Loty\n"
            "Wymaga doprecyzowania.\n"
            "\n"
            "## Propozycja 2: Kolej\n"
            "Wymaga doprecyzowania.\n"
            "\n"
            "## Propozycja 3: Wynajem auta\n"
            "Wymaga doprecyzowania.\n"
            "\n"
            "## Propozycja 4: Auto własne\n"
            "Wymaga doprecyzowania."
        )

    LOGGER.info("Krok 2/6: raport transportowy gotowy: %s", compact_text(transport_report))
    return {
        "transport_markdown": transport_report,
        "transport_report": transport_report,
    }
