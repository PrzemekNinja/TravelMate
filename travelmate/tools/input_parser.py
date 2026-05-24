from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from travelmate.models import ItineraryInput
from travelmate.tools.model_factory import get_chat_model


class _NaturalLanguageExtraction(BaseModel):
    destination: str | None = None
    days: int | None = None
    budget: Literal["Low", "Mid", "Luxury"] | None = None
    pace: Literal["Relaxed", "Moderate", "Intense"] | None = None
    home_location: str | None = None
    travel_start_date: date | None = None
    travel_end_date: date | None = None
    participants: int | None = None
    baggage: list[dict[str, Any]] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    accommodation_area: str | None = None
    assumptions: list[str] = Field(default_factory=list)


class ParsedRequest(BaseModel):
    request: ItineraryInput
    source: Literal["json", "key_value", "natural_language"]
    assumptions: list[str] = Field(default_factory=list)


def _looks_like_key_value(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    key_value_lines = [
        line
        for line in lines
        if re.match(r"^[A-Za-z_][A-Za-z0-9_\- ]*:\s*.+$", line)
    ]
    if len(key_value_lines) < 4:
        return False

    ratio = len(key_value_lines) / len(lines)
    if ratio < 0.8:
        return False

    known_keys = {
        "destination",
        "days",
        "budget",
        "pace",
        "home_location",
        "travel_start_date",
        "travel_end_date",
        "participants",
        "baggage",
        "interests",
        "constraints",
        "accommodation_area",
    }
    normalized_keys = {
        line.split(":", 1)[0].strip().lower().replace(" ", "_")
        for line in key_value_lines
    }
    return len(known_keys.intersection(normalized_keys)) >= 3


def _normalize_budget(value: str) -> str:
    mapping = {
        "low": "Low",
        "mid": "Mid",
        "medium": "Mid",
        "luxury": "Luxury",
        "niski": "Low",
        "średni": "Mid",
        "sredni": "Mid",
        "luksus": "Luxury",
        "luksusowy": "Luxury",
    }
    key = value.strip().lower()
    return mapping.get(key, value.strip())


def _normalize_pace(value: str) -> str:
    mapping = {
        "relaxed": "Relaxed",
        "moderate": "Moderate",
        "intense": "Intense",
        "spokojne": "Relaxed",
        "spokojny": "Relaxed",
        "umiarkowane": "Moderate",
        "umiarkowany": "Moderate",
        "intensywne": "Intense",
        "intensywny": "Intense",
    }
    key = value.strip().lower()
    return mapping.get(key, value.strip())


def _parse_key_value_message(message: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in message.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(
                "Niepoprawny format. Użyj JSON lub linii typu klucz: wartość."
            )
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()

    required = {"destination", "days", "budget", "pace"}
    missing = required.difference(data.keys())
    if missing:
        raise ValueError(
            f"Brakuje wymaganych pól: {', '.join(sorted(missing))}."
        )

    interests = data.get("interests", "")
    constraints = data.get("constraints", "")
    baggage_raw = data.get("baggage", "")
    baggage: list[dict[str, Any]] = []
    if baggage_raw:
        try:
            decoded = json.loads(baggage_raw)
            if isinstance(decoded, list):
                baggage = [item for item in decoded if isinstance(item, dict)]
        except json.JSONDecodeError:
            baggage = []

    return {
        "destination": data.get("destination", ""),
        "days": int(data.get("days", "0")),
        "budget": _normalize_budget(data.get("budget", "")),
        "pace": _normalize_pace(data.get("pace", "")),
        "home_location": data.get("home_location") or None,
        "travel_start_date": data.get("travel_start_date") or None,
        "travel_end_date": data.get("travel_end_date") or None,
        "participants": int(data.get("participants", "1")),
        "baggage": baggage,
        "interests": [x.strip() for x in interests.split(",") if x.strip()],
        "constraints": [x.strip() for x in constraints.split(",") if x.strip()],
        "accommodation_area": data.get("accommodation_area") or None,
    }


def _build_request_with_defaults(extracted: _NaturalLanguageExtraction) -> ParsedRequest:
    if not extracted.destination:
        raise ValueError(
            "Nie udało się wykryć destynacji. Dopisz proszę miasto/kraj wycieczki."
        )

    assumptions = list(extracted.assumptions)

    days = extracted.days if extracted.days is not None else 3
    if extracted.days is None:
        assumptions.append("Brak liczby dni w opisie — ustawiono domyślnie 3 dni.")

    budget = extracted.budget or "Mid"
    if extracted.budget is None:
        assumptions.append("Brak poziomu budżetu — ustawiono domyślnie Mid.")

    pace = extracted.pace or "Moderate"
    if extracted.pace is None:
        assumptions.append("Brak tempa zwiedzania — ustawiono domyślnie Moderate.")

    participants = extracted.participants if extracted.participants is not None else 1
    if extracted.participants is None:
        assumptions.append("Brak liczby uczestników — ustawiono domyślnie 1.")

    if extracted.home_location is None:
        assumptions.append("Brak miejsca zamieszkania/startu — plan transportu oznaczy to jako wymagające doprecyzowania.")

    request = ItineraryInput.model_validate(
        {
            "destination": extracted.destination,
            "days": days,
            "budget": budget,
            "pace": pace,
            "home_location": extracted.home_location,
            "travel_start_date": extracted.travel_start_date,
            "travel_end_date": extracted.travel_end_date,
            "participants": participants,
            "baggage": extracted.baggage,
            "interests": extracted.interests,
            "constraints": extracted.constraints,
            "accommodation_area": extracted.accommodation_area,
        }
    )

    return ParsedRequest(
        request=request,
        source="natural_language",
        assumptions=assumptions,
    )


def _parse_natural_language_message(message: str) -> ParsedRequest:
    llm = get_chat_model().with_structured_output(_NaturalLanguageExtraction)

    system_prompt = (
        "Jesteś parserem wymagań podróży. "
        "Z wypowiedzi użytkownika w języku naturalnym wyciągnij parametry planu podróży. "
        "Uzupełnij interests i constraints konkretnymi tagami, jeśli wynikają z opisu. "
        "Nie wymyślaj destynacji; jeśli jej brak, zostaw null."
    )
    task_prompt = (
        "Zwróć strukturę z polami: destination, days, budget, pace, home_location, travel_start_date, travel_end_date, participants, baggage, interests, constraints, accommodation_area, assumptions. "
        "Budget mapuj do: Low/Mid/Luxury. Pace mapuj do: Relaxed/Moderate/Intense."
    )

    extracted = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            SystemMessage(content=task_prompt),
            HumanMessage(content=message),
        ]
    )

    normalized: _NaturalLanguageExtraction
    if isinstance(extracted, _NaturalLanguageExtraction):
        normalized = extracted
    elif hasattr(extracted, "parsed") and isinstance(getattr(extracted, "parsed"), _NaturalLanguageExtraction):
        normalized = getattr(extracted, "parsed")
    elif isinstance(extracted, dict):
        normalized = _NaturalLanguageExtraction.model_validate(extracted)
    elif hasattr(extracted, "model_dump"):
        normalized = _NaturalLanguageExtraction.model_validate(extracted.model_dump(mode="json"))
    else:
        raise ValueError("Nie udało się znormalizować odpowiedzi parsera języka naturalnego.")

    return _build_request_with_defaults(normalized)


def parse_user_input_to_request_with_metadata(message: str) -> ParsedRequest:
    text = message.strip()
    if not text:
        raise ValueError("Wiadomość jest pusta.")

    if text.startswith("{"):
        raw = json.loads(text)
        request = ItineraryInput.model_validate(raw)
        return ParsedRequest(request=request, source="json")
    if _looks_like_key_value(text):
        try:
            raw = _parse_key_value_message(text)
            request = ItineraryInput.model_validate(raw)
            return ParsedRequest(request=request, source="key_value")
        except ValueError:
            # Gdy tekst przypomina key-value, ale zawiera sekcje/bullety,
            # traktujemy go jak natural language zamiast przerywać działanie.
            pass

    return _parse_natural_language_message(text)


def parse_user_input_to_request(message: str) -> ItineraryInput:
    parsed = parse_user_input_to_request_with_metadata(message)
    return parsed.request
