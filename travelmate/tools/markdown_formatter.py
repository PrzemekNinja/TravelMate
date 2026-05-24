from __future__ import annotations

from travelmate.models import GeoAddress, GeoOutput, GeoPlace, ItineraryDraft, ItineraryInput, VerificationOutput


def _display_or_fallback(value: str | None, fallback: str = "brak") -> str:
    text = (value or "").strip()
    return text if text else fallback


def _format_geo_address(address: GeoAddress) -> str:
    return ", ".join(
        [
            _display_or_fallback(address.country),
            _display_or_fallback(address.city),
            _display_or_fallback(address.street),
            _display_or_fallback(address.building_number),
        ]
    )


def _format_geo_place(place: GeoPlace) -> list[str]:
    lat = "brak" if place.coordinates.lat is None else str(place.coordinates.lat)
    lng = "brak" if place.coordinates.lng is None else str(place.coordinates.lng)
    rating = "brak" if place.tripadvisor_rating is None else f"{place.tripadvisor_rating:.1f}/5"
    tripadvisor_url = _display_or_fallback(place.tripadvisor_url)
    photo_url = _display_or_fallback(place.tripadvisor_photo_url)

    return [
        f"- **{place.name}**",
        f"  - Współrzędne: {lat}, {lng}",
        f"  - Strona WWW: {_display_or_fallback(place.website)}",
        f"  - Adres: {_format_geo_address(place.address)}",
        f"  - TripAdvisor rating: {rating}",
        f"  - TripAdvisor: {tripadvisor_url}",
        f"  - Foto (TripAdvisor): {photo_url}",
    ]


def _build_lodging_poi_lines(draft: ItineraryDraft | None) -> list[str]:
    if draft is None:
        return []

    grouped: dict[str, dict[str, str | list[int]]] = {}
    for day in draft.days:
        if day.lodging is None:
            continue

        key = f"{day.lodging.name.strip().lower()}|{day.lodging.area.strip().lower()}"
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "name": day.lodging.name,
                "area": day.lodging.area,
                "price": day.lodging.price,
                "check_in": day.lodging.check_in or "",
                "check_out": day.lodging.check_out or "",
                "note": day.lodging.note or "",
                "days": [day.day],
            }
        else:
            days = existing.get("days", [])
            if isinstance(days, list):
                days.append(day.day)

    if not grouped:
        return []

    lines: list[str] = []
    lines.append("#### 🏨 Noclegi (POI)")
    for item in grouped.values():
        days = item.get("days", [])
        day_label = ", ".join(str(day) for day in sorted(set(days))) if isinstance(days, list) else "-"
        name = str(item.get("name", "Nocleg"))
        area = _display_or_fallback(str(item.get("area", "")))
        price = _display_or_fallback(str(item.get("price", "")))
        check_in = _display_or_fallback(str(item.get("check_in", "")))
        check_out = _display_or_fallback(str(item.get("check_out", "")))
        note = _display_or_fallback(str(item.get("note", "")))

        lines.append(f"- **{name}**")
        lines.append(f"  - Dni planu: {day_label}")
        lines.append(f"  - Obszar: {area}")
        lines.append(f"  - Cena: {price}")
        lines.append(f"  - Check-in / Check-out: {check_in} / {check_out}")
        lines.append(f"  - Notatka: {note}")

    return lines


def build_lodging_poi_section(draft: ItineraryDraft | None) -> str:
    lines = _build_lodging_poi_lines(draft)
    return "\n".join(lines).strip()


def _build_lodging_quick_view_lines(draft: ItineraryDraft | None) -> list[str]:
    if draft is None:
        return []

    grouped: dict[str, dict[str, str | list[int]]] = {}
    for day in draft.days:
        if day.lodging is None:
            continue

        key = f"{day.lodging.name.strip().lower()}|{day.lodging.area.strip().lower()}"
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "name": day.lodging.name,
                "area": day.lodging.area,
                "price": day.lodging.price,
                "check_in": day.lodging.check_in or "",
                "check_out": day.lodging.check_out or "",
                "days": [day.day],
            }
        else:
            days = existing.get("days", [])
            if isinstance(days, list):
                days.append(day.day)

    if not grouped:
        return []

    def _table_safe(value: str) -> str:
        return value.replace("|", "\\|")

    lines: list[str] = []
    lines.append("### 🏨 Nocleg (quick view)")
    lines.append("")
    lines.append("| Hotel | Obszar | Cena | Dni | Check-in / Check-out |")
    lines.append("|---|---|---|---|---|")
    for item in grouped.values():
        days = item.get("days", [])
        day_label = ", ".join(str(day) for day in sorted(set(days))) if isinstance(days, list) else "-"
        name = _table_safe(str(item.get("name", "Nocleg")))
        area = _table_safe(_display_or_fallback(str(item.get("area", ""))))
        price = _table_safe(_display_or_fallback(str(item.get("price", ""))))
        check_in = _table_safe(_display_or_fallback(str(item.get("check_in", ""))))
        check_out = _table_safe(_display_or_fallback(str(item.get("check_out", ""))))

        lines.append(f"| {name} | {area} | {price} | {day_label} | {check_in} / {check_out} |")

    return lines


def build_geo_poi_section(geo_output: GeoOutput, draft: ItineraryDraft | None = None) -> str:
    lines: list[str] = []
    lines.append("### 📍 Metadane POI (geo)")
    lines.append("")

    for day in geo_output.days:
        lines.append(f"#### Dzień {day.day}: {day.title}")
        lines.extend(_format_geo_place(day.morning_zone))
        lines.extend(_format_geo_place(day.afternoon_zone))
        lines.extend(_format_geo_place(day.evening_zone))
        lines.append("")

    lodging_lines = _build_lodging_poi_lines(draft)
    if lodging_lines:
        lines.extend(lodging_lines)
        lines.append("")

    return "\n".join(lines).strip()


def build_markdown(
    req: ItineraryInput,
    profile_summary: str,
    transport_report: str,
    mobility_strategy: str,
    geo_output: GeoOutput,
    draft: ItineraryDraft,
    verification: VerificationOutput,
) -> str:
    lines: list[str] = []
    lines.append(f"## 🗺️ {req.destination} - Plan Podróży ({req.days} Dni)")
    lines.append("")
    lines.append(f"**Profil:** {profile_summary}")
    lines.append("")

    quick_view_lines = _build_lodging_quick_view_lines(draft)
    if quick_view_lines:
        lines.extend(quick_view_lines)
        lines.append("")

    lines.append("---")
    lines.append("")

    for day in draft.days:
        lines.append(f"### 📅 Dzień {day.day}: {day.area_title}")
        lines.append("")

        for act in day.morning_activities:
            lines.append(f"**{act.start} – {act.end} | {act.name}**")
            if act.why:
                lines.append(f"* **Dlaczego:** {act.why}")
            if act.tip:
                lines.append(f"* **Wskazówka:** {act.tip}")
            lines.append("")

        lines.append(f"**{day.lunch.time} | Lunch: {day.lunch.name}**")
        lines.append(f"* **Kuchnia:** {day.lunch.cuisine} | **Cena:** {day.lunch.price}")
        lines.append(f"* **Adres/Lokalizacja:** {day.lunch.address_or_location}")
        if day.lunch.note:
            lines.append(f"* **Uwaga:** {day.lunch.note}")
        lines.append("")

        for act in day.afternoon_activities:
            lines.append(f"**{act.start} – {act.end} | {act.name}**")
            if act.description:
                lines.append(f"* **Opis:** {act.description}")
            if act.logistics:
                lines.append(f"* **Logistyka:** {act.logistics}")
            lines.append("")

        lines.append(f"**{day.dinner.time} | Kolacja: {day.dinner.name}**")
        if day.dinner.ambience:
            lines.append(f"* **Klimat:** {day.dinner.ambience}")
        lines.append("")

        if day.lodging:
            lines.append(f"**🏨 Nocleg: {day.lodging.name}**")
            lines.append(f"* **Obszar:** {day.lodging.area} | **Cena:** {day.lodging.price}")
            if day.lodging.check_in or day.lodging.check_out:
                check_in = _display_or_fallback(day.lodging.check_in)
                check_out = _display_or_fallback(day.lodging.check_out)
                lines.append(f"* **Check-in / Check-out:** {check_in} / {check_out}")
            if day.lodging.note:
                lines.append(f"* **Uwaga:** {day.lodging.note}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("### 💡 Podsumowanie i Transport")
    lines.append("")
    lines.append(f"* **Poruszanie się:** {mobility_strategy}")
    lines.append(f"* **Estymowany koszt biletów wstępu:** {draft.estimated_ticket_cost}")

    lines.append("")
    lines.append("### 🚐 Raport transportowy")
    lines.append("")
    lines.append((transport_report or "Brak danych transportowych.").strip())

    if verification.opening_hours_warnings or verification.adjustments:
        lines.append("")
        lines.append("### ⚠️ Weryfikacja")
        lines.append("")
        for warn in verification.opening_hours_warnings:
            lines.append(f"* {warn}")
        for adj in verification.adjustments:
            lines.append(f"* {adj}")

    lines.append("")
    lines.append(build_geo_poi_section(geo_output, draft=draft))

    return "\n".join(lines).strip()
