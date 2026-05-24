from __future__ import annotations

import re

from travelmate.models import (
    ActivityEntry,
    DayPlan,
    GeoDayDraft,
    GeoOutputDraft,
    ItineraryDraft,
    LodgingEntry,
    MealEntry,
    VerificationOutput,
)


_DAY_HEADER_RE = re.compile(r"^##\s*Day\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def _extract_section(markdown: str, title: str) -> str:
    pattern = re.compile(
        rf"^##\s*{re.escape(title)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(markdown)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_bullets(section_text: str) -> list[str]:
    return [
        line.strip()[2:].strip()
        for line in section_text.splitlines()
        if line.strip().startswith("- ")
    ]


def parse_geo_markdown(markdown: str, expected_days: int) -> GeoOutputDraft:
    mobility_section = _extract_section(markdown, "Mobility Strategy")
    mobility_items = _extract_bullets(mobility_section)
    mobility_strategy = mobility_items[0] if mobility_items else "Requires clarification"

    days: list[GeoDayDraft] = []
    for match in _DAY_HEADER_RE.finditer(markdown):
        day_number = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        next_match = _DAY_HEADER_RE.search(markdown, start)
        chunk = markdown[start : next_match.start() if next_match else len(markdown)]

        morning = "Requires clarification"
        afternoon = "Requires clarification"
        evening = "Requires clarification"
        for raw in chunk.splitlines():
            line = raw.strip()
            if line.lower().startswith("- morning zone:"):
                morning = line.split(":", 1)[1].strip() or morning
            elif line.lower().startswith("- afternoon zone:"):
                afternoon = line.split(":", 1)[1].strip() or afternoon
            elif line.lower().startswith("- evening zone:"):
                evening = line.split(":", 1)[1].strip() or evening

        days.append(
            GeoDayDraft(
                day=day_number,
                title=title,
                morning_zone=morning,
                afternoon_zone=afternoon,
                evening_zone=evening,
            )
        )

    if not days:
        for idx in range(1, expected_days + 1):
            days.append(
                GeoDayDraft(
                    day=idx,
                    title=f"Day {idx}",
                    morning_zone="Requires clarification",
                    afternoon_zone="Requires clarification",
                    evening_zone="Requires clarification",
                )
            )

    days = sorted(days, key=lambda item: item.day)
    if expected_days > 0 and len(days) > expected_days:
        days = days[:expected_days]
    if expected_days > 0 and len(days) < expected_days:
        existing_days = {day.day for day in days}
        for idx in range(1, expected_days + 1):
            if idx in existing_days:
                continue
            days.append(
                GeoDayDraft(
                    day=idx,
                    title=f"Day {idx}",
                    morning_zone="Requires clarification",
                    afternoon_zone="Requires clarification",
                    evening_zone="Requires clarification",
                )
            )
        days = sorted(days, key=lambda item: item.day)

    return GeoOutputDraft(mobility_strategy=mobility_strategy, days=days)


def _parse_pipe_fields(line: str) -> dict[str, str]:
    result: dict[str, str] = {}
    parts = [part.strip() for part in line.split("|")]
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key.strip().lower()] = value.strip()
    return result


def parse_itinerary_markdown(markdown: str) -> ItineraryDraft:
    cost_section = _extract_section(markdown, "Estimated Ticket Cost")
    cost_items = _extract_bullets(cost_section)
    estimated_ticket_cost = "Requires clarification"
    for item in cost_items:
        if item.lower().startswith("value:"):
            estimated_ticket_cost = item.split(":", 1)[1].strip() or estimated_ticket_cost
            break

    day_matches = list(_DAY_HEADER_RE.finditer(markdown))
    plans: list[DayPlan] = []

    for index, match in enumerate(day_matches):
        day_number = int(match.group(1))
        area_title = match.group(2).strip()
        start = match.end()
        end = day_matches[index + 1].start() if index + 1 < len(day_matches) else len(markdown)
        chunk = markdown[start:end]

        morning_activities: list[ActivityEntry] = []
        afternoon_activities: list[ActivityEntry] = []
        lunch: MealEntry | None = None
        dinner: MealEntry | None = None
        lodging: LodgingEntry | None = None

        mode = ""
        for raw in chunk.splitlines():
            line = raw.strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("### morning activities"):
                mode = "morning"
                continue
            if lowered.startswith("### lunch"):
                mode = "lunch"
                continue
            if lowered.startswith("### afternoon activities"):
                mode = "afternoon"
                continue
            if lowered.startswith("### dinner"):
                mode = "dinner"
                continue
            if lowered.startswith("### lodging"):
                mode = "lodging"
                continue

            if not line.startswith("- "):
                continue

            content = line[2:].strip()
            if content.startswith("ACTIVITY") and mode in {"morning", "afternoon"}:
                fields = _parse_pipe_fields(content)
                item = ActivityEntry(
                    start=fields.get("start", "09:00"),
                    end=fields.get("end", "11:00"),
                    name=fields.get("name", "Requires clarification"),
                    why=fields.get("why") or None,
                    tip=fields.get("tip") or None,
                    description=fields.get("description") or None,
                    logistics=fields.get("logistics") or None,
                )
                if mode == "morning":
                    morning_activities.append(item)
                else:
                    afternoon_activities.append(item)
                continue

            if content.startswith("MEAL") and mode in {"lunch", "dinner"}:
                fields = _parse_pipe_fields(content)
                meal = MealEntry(
                    meal_type="lunch" if mode == "lunch" else "dinner",
                    time=fields.get("time", "12:30" if mode == "lunch" else "19:00"),
                    name=fields.get("name", "Requires clarification"),
                    cuisine=fields.get("cuisine", "Local"),
                    price=fields.get("price", "$$") if fields.get("price", "$$") in {"$", "$$", "$$$"} else "$$",
                    address_or_location=fields.get("location", "Requires clarification"),
                    note=fields.get("note") or None,
                    ambience=fields.get("ambience") or None,
                )
                if mode == "lunch":
                    lunch = meal
                else:
                    dinner = meal
                continue

            if content.startswith("LODGING") and mode == "lodging":
                fields = _parse_pipe_fields(content)
                price = fields.get("price", "$$")
                lodging = LodgingEntry(
                    name=fields.get("name", "Requires clarification"),
                    area=fields.get("area", "Requires clarification"),
                    price=price if price in {"$", "$$", "$$$"} else "$$",
                    check_in=fields.get("check_in") or None,
                    check_out=fields.get("check_out") or None,
                    note=fields.get("note") or None,
                )

        if not morning_activities:
            morning_activities.append(
                ActivityEntry(
                    start="09:00",
                    end="11:00",
                    name="Requires clarification",
                    logistics="Requires clarification",
                )
            )
        if not afternoon_activities:
            afternoon_activities.append(
                ActivityEntry(
                    start="14:00",
                    end="16:00",
                    name="Requires clarification",
                    logistics="Requires clarification",
                )
            )
        if lunch is None:
            lunch = MealEntry(
                meal_type="lunch",
                time="12:30",
                name="Requires clarification",
                cuisine="Local",
                price="$$",
                address_or_location="Requires clarification",
            )
        if dinner is None:
            dinner = MealEntry(
                meal_type="dinner",
                time="19:00",
                name="Requires clarification",
                cuisine="Local",
                price="$$",
                address_or_location="Requires clarification",
            )

        plans.append(
            DayPlan(
                day=day_number,
                area_title=area_title,
                morning_activities=morning_activities,
                lunch=lunch,
                afternoon_activities=afternoon_activities,
                dinner=dinner,
                lodging=lodging,
            )
        )

    if not plans:
        plans.append(
            DayPlan(
                day=1,
                area_title="Day 1",
                morning_activities=[
                    ActivityEntry(start="09:00", end="11:00", name="Requires clarification")
                ],
                lunch=MealEntry(
                    meal_type="lunch",
                    time="12:30",
                    name="Requires clarification",
                    cuisine="Local",
                    price="$$",
                    address_or_location="Requires clarification",
                ),
                afternoon_activities=[
                    ActivityEntry(start="14:00", end="16:00", name="Requires clarification")
                ],
                dinner=MealEntry(
                    meal_type="dinner",
                    time="19:00",
                    name="Requires clarification",
                    cuisine="Local",
                    price="$$",
                    address_or_location="Requires clarification",
                ),
                lodging=None,
            )
        )

    plans = sorted(plans, key=lambda item: item.day)
    return ItineraryDraft(days=plans, estimated_ticket_cost=estimated_ticket_cost)


def parse_verification_markdown(markdown: str) -> VerificationOutput:
    warnings = _extract_bullets(_extract_section(markdown, "Opening Hours Warnings"))
    adjustments = _extract_bullets(_extract_section(markdown, "Adjustments"))

    warnings = [item for item in warnings if item and item.lower() != "none"]
    adjustments = [item for item in adjustments if item and item.lower() != "none"]

    return VerificationOutput(opening_hours_warnings=warnings, adjustments=adjustments)
