from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

from travelmate.models import GeoOutput, GeoPlace, ItineraryDraft, ItineraryInput


def _slugify(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    return value or "trip"


def _lodging_marker_offset(day: int) -> tuple[float, float]:
    offsets = [
        (0.00018, 0.00012),
        (-0.00016, 0.00014),
        (0.00012, -0.00018),
        (-0.00014, -0.00014),
    ]
    return offsets[(max(1, day) - 1) % len(offsets)]


def _lodging_key(name: str, area: str) -> str:
    return f"{name.strip().lower()}|{area.strip().lower()}"


def _collect_geo_points(
    geo_output: GeoOutput | None,
    itinerary_draft: ItineraryDraft | None = None,
) -> list[dict[str, object]]:
    if geo_output is None:
        return []

    lodging_by_day = {}
    if itinerary_draft is not None:
        lodging_by_day = {
            day_plan.day: day_plan.lodging
            for day_plan in itinerary_draft.days
            if day_plan.lodging is not None
        }

    points: list[dict[str, object]] = []
    lodging_groups: dict[str, dict[str, object]] = {}
    for day in geo_output.days:
        zones: list[tuple[str, GeoPlace]] = [
            ("Poranek", day.morning_zone),
            ("Popołudnie", day.afternoon_zone),
            ("Wieczór", day.evening_zone),
        ]
        for part_of_day, place in zones:
            lat = place.coordinates.lat
            lng = place.coordinates.lng
            if lat is None or lng is None:
                continue

            points.append(
                {
                    "day": day.day,
                    "title": day.title,
                    "part_of_day": part_of_day,
                    "name": place.name,
                    "point_type": "activity",
                    "lat": lat,
                    "lng": lng,
                    "website": place.website,
                    "tripadvisor_url": place.tripadvisor_url,
                    "tripadvisor_rating": place.tripadvisor_rating,
                    "tripadvisor_photo_url": place.tripadvisor_photo_url,
                    "tripadvisor_location_id": place.tripadvisor_location_id,
                    "address": ", ".join(
                        filter(
                            None,
                            [
                                place.address.street,
                                place.address.building_number,
                                place.address.city,
                                place.address.country,
                            ],
                        )
                    ),
                    "source": place.source,
                }
            )

        lodging = lodging_by_day.get(day.day)
        evening_lat = day.evening_zone.coordinates.lat
        evening_lng = day.evening_zone.coordinates.lng
        if lodging is not None and evening_lat is not None and evening_lng is not None:
            key = _lodging_key(lodging.name, lodging.area)
            group = lodging_groups.get(key)
            if group is None:
                lodging_groups[key] = {
                    "name": lodging.name,
                    "area": lodging.area,
                    "price": lodging.price,
                    "check_in": lodging.check_in or "",
                    "check_out": lodging.check_out or "",
                    "note": lodging.note or "",
                    "days": [day.day],
                    "samples": [(evening_lat, evening_lng)],
                }
            else:
                group_days = group.get("days", [])
                if isinstance(group_days, list):
                    group_days.append(day.day)
                group_samples = group.get("samples", [])
                if isinstance(group_samples, list):
                    group_samples.append((evening_lat, evening_lng))

    for idx, lodging in enumerate(lodging_groups.values(), start=1):
        samples = lodging.get("samples", [])
        if not isinstance(samples, list) or not samples:
            continue

        avg_lat = sum(float(sample[0]) for sample in samples) / len(samples)
        avg_lng = sum(float(sample[1]) for sample in samples) / len(samples)
        lat_off, lng_off = _lodging_marker_offset(idx)
        lodging_days = lodging.get("days", [])
        day_for_color = min(lodging_days) if isinstance(lodging_days, list) and lodging_days else 1

        points.append(
            {
                "day": day_for_color,
                "title": "Baza noclegowa",
                "part_of_day": "Nocleg",
                "name": str(lodging.get("name", "Nocleg")),
                "point_type": "lodging",
                "lat": avg_lat + lat_off,
                "lng": avg_lng + lng_off,
                "website": "",
                "address": str(lodging.get("area", "")),
                "source": "itinerary_lodging",
                "price": str(lodging.get("price", "")),
                "check_in": str(lodging.get("check_in", "")),
                "check_out": str(lodging.get("check_out", "")),
                "note": str(lodging.get("note", "")),
                "lodging_days": lodging_days,
                "lodging_key": _lodging_key(str(lodging.get("name", "")), str(lodging.get("area", ""))),
            }
        )

    return points


def _collect_transfer_segments(
    geo_output: GeoOutput | None,
    itinerary_draft: ItineraryDraft | None = None,
    points: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    if geo_output is None:
        return []

    segments: list[dict[str, object]] = []

    lodging_by_day = {}
    if itinerary_draft is not None:
        lodging_by_day = {
            day_plan.day: day_plan.lodging
            for day_plan in itinerary_draft.days
            if day_plan.lodging is not None
        }

    lodging_centers: dict[str, tuple[float, float]] = {}
    for point in points or []:
        if point.get("point_type") != "lodging":
            continue
        key = str(point.get("lodging_key", ""))
        lat = point.get("lat")
        lng = point.get("lng")
        if key and lat is not None and lng is not None:
            lodging_centers[key] = (float(lat), float(lng))

    for day in geo_output.days:
        morning = day.morning_zone.coordinates
        afternoon = day.afternoon_zone.coordinates
        evening = day.evening_zone.coordinates

        if morning.lat is not None and morning.lng is not None and afternoon.lat is not None and afternoon.lng is not None:
            segments.append(
                {
                    "day": day.day,
                    "from_lat": morning.lat,
                    "from_lng": morning.lng,
                    "to_lat": afternoon.lat,
                    "to_lng": afternoon.lng,
                    "kind": "day_flow",
                }
            )

        if afternoon.lat is not None and afternoon.lng is not None and evening.lat is not None and evening.lng is not None:
            segments.append(
                {
                    "day": day.day,
                    "from_lat": afternoon.lat,
                    "from_lng": afternoon.lng,
                    "to_lat": evening.lat,
                    "to_lng": evening.lng,
                    "kind": "day_flow",
                }
            )

        lodging = lodging_by_day.get(day.day)
        if lodging is None:
            continue

        key = _lodging_key(lodging.name, lodging.area)
        center = lodging_centers.get(key)
        if center is None:
            continue

        lodging_lat, lodging_lng = center
        if evening.lat is not None and evening.lng is not None:
            segments.append(
                {
                    "day": day.day,
                    "from_lat": evening.lat,
                    "from_lng": evening.lng,
                    "to_lat": lodging_lat,
                    "to_lng": lodging_lng,
                    "kind": "to_lodging",
                }
            )

        if morning.lat is not None and morning.lng is not None:
            segments.append(
                {
                    "day": day.day,
                    "from_lat": lodging_lat,
                    "from_lng": lodging_lng,
                    "to_lat": morning.lat,
                    "to_lng": morning.lng,
                    "kind": "from_lodging",
                }
            )

    return segments


def _build_combined_itinerary_html(
    destination: str,
    days: int,
    markdown_plan: str,
    points: list[dict[str, object]],
    transfer_segments: list[dict[str, object]],
    mobility_strategy: str,
    generated_at: str,
) -> str:
    points_json = json.dumps(points, ensure_ascii=False)
    transfer_segments_json = json.dumps(transfer_segments, ensure_ascii=False)
    mobility_json = json.dumps(mobility_strategy, ensure_ascii=False)
    escaped_markdown = html.escape(markdown_plan)
    lodging_count = sum(1 for point in points if point.get("point_type") == "lodging")
    mobility_text = (mobility_strategy or "wg planu").strip() or "wg planu"
    transport_preview = mobility_text.split(".", 1)[0].strip()
    if transport_preview and transport_preview != mobility_text:
      transport_preview = f"{transport_preview}."

    if points:
        center_lat = sum(float(point["lat"]) for point in points) / len(points)
        center_lng = sum(float(point["lng"]) for point in points) / len(points)
    else:
        center_lat = 52.2297
        center_lng = 21.0122

    return f"""<!doctype html>
<html lang="pl" data-theme="light">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>TravelMate - Plan + mapa - {html.escape(destination)} ({days} dni)</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
  <style>
    :root {{
      --bg: #f2f6f7;
      --card: #ffffff;
      --text: #22303a;
      --muted: #5d6b75;
      --line: #d7e2e8;
      --accent: #4b7f9c;
      --accent-soft: #e5eff5;
      --day-active-text: #1f4f67;
      --plan-bg: #f6fafb;
    }}
    [data-theme="dark"] {{
      --bg: #0f1720;
      --card: #17222d;
      --text: #d9e6ef;
      --muted: #9ab0c0;
      --line: #273847;
      --accent: #8fc0dc;
      --accent-soft: #23384a;
      --day-active-text: #d8ecf8;
      --plan-bg: #1a2b37;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Inter", "Segoe UI", Arial, sans-serif;
      margin: 0;
      color: var(--text);
      background: radial-gradient(circle at top left, #f7fbfc 0%, var(--bg) 60%, #eaf1f3 100%);
    }}
    [data-theme="dark"] body {{
      background: radial-gradient(circle at top left, #162430 0%, #0f1720 55%, #0b121a 100%);
    }}
    .layout {{ display: grid; grid-template-rows: auto 1fr; min-height: 100vh; }}
    .header {{
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(4px);
    }}
    [data-theme="dark"] .header {{
      background: rgba(20, 30, 40, 0.88);
    }}
    .header-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 650; letter-spacing: -0.15px; }}
    .meta {{ margin-top: 8px; }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 8px;
      margin-bottom: 8px;
    }}
    .meta-item {{
      border: 1px solid #d9e6ee;
      border-radius: 10px;
      background: #f8fcfe;
      padding: 7px 9px;
      line-height: 1.3;
    }}
    .meta-label {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 2px;
      letter-spacing: 0.1px;
    }}
    .meta-value {{
      display: block;
      color: #223a4a;
      font-size: 16px;
      font-weight: 700;
    }}
    .transport-card {{
      border: 1px solid #d9e6ee;
      border-radius: 10px;
      background: #f8fcfe;
      padding: 8px 10px;
    }}
    .transport-title {{
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 4px;
      letter-spacing: 0.1px;
    }}
    .transport-preview {{
      color: #264657;
      font-size: 14px;
      font-weight: 600;
      line-height: 1.42;
      margin-bottom: 4px;
    }}
    .transport-details {{
      margin-top: 2px;
      font-size: 12px;
      color: var(--muted);
    }}
    .transport-details summary {{
      cursor: pointer;
      user-select: none;
      color: #507086;
      font-weight: 600;
      list-style: none;
    }}
    .transport-details summary::-webkit-details-marker {{ display: none; }}
    .transport-details summary::before {{ content: "▸ "; }}
    .transport-details[open] summary::before {{ content: "▾ "; }}
    .transport-full {{
      margin-top: 6px;
      font-size: 13px;
      color: #3d5666;
      line-height: 1.5;
      white-space: normal;
    }}
    .generated-at {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .theme-toggle {{
      border: 1px solid #bfd1dd;
      background: #f4f9fc;
      color: #2c4a5d;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all .15s ease;
    }}
    .theme-toggle:hover {{
      background: #eaf4fa;
      border-color: #adc6d5;
    }}
    [data-theme="dark"] .theme-toggle {{
      border-color: #375165;
      background: #1d3140;
      color: #d3e6f2;
    }}
    [data-theme="dark"] .theme-toggle:hover {{
      background: #264052;
      border-color: #44657b;
    }}
    [data-theme="dark"] .meta-item,
    [data-theme="dark"] .transport-card {{
      border-color: #314656;
      background: #1a2a36;
    }}
    [data-theme="dark"] .meta-value {{ color: #d6e8f3; }}
    [data-theme="dark"] .transport-preview {{ color: #cfe4f1; }}
    [data-theme="dark"] .transport-details summary {{ color: #8eb6cd; }}
    [data-theme="dark"] .transport-full {{ color: #b7ccda; }}
    .content {{
      display: grid;
      grid-template-columns: minmax(420px, 1.2fr) minmax(320px, 1fr);
      gap: 14px;
      padding: 14px;
      min-height: calc(100vh - 96px);
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 10px 24px rgba(31, 51, 65, 0.08);
    }}
    [data-theme="dark"] .card {{
      box-shadow: 0 10px 24px rgba(5, 10, 15, 0.45);
    }}
    .card h2 {{
      margin: 0;
      font-size: 15px;
      padding: 11px 13px;
      border-bottom: 1px solid #e4edf1;
      background: #f7fbfd;
      color: #274252;
    }}
    [data-theme="dark"] .card h2 {{
      border-bottom-color: #2b3f4e;
      background: #1b2a36;
      color: #d3e4ef;
    }}
    .map-toolbar {{
      padding: 10px 12px;
      border-bottom: 1px solid #e6eef2;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      background: #fcfeff;
    }}
    [data-theme="dark"] .map-toolbar {{
      border-bottom-color: #2a3d4b;
      background: #1a2935;
    }}
    .filter-label {{ font-size: 12px; color: var(--muted); margin-right: 4px; }}
    .day-filter-btn {{
      border: 1px solid #c9d8e2;
      background: #ffffff;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      color: #345062;
      cursor: pointer;
      transition: all .16s ease;
    }}
    .day-filter-btn:hover {{ background: #f2f8fb; border-color: #b8ccd8; }}
    .day-filter-btn.active {{
      border-color: #b6cfdd;
      background: var(--accent-soft);
      color: var(--day-active-text);
      font-weight: 600;
    }}
    [data-theme="dark"] .day-filter-btn {{
      border-color: #3a5364;
      background: #1e3241;
      color: #c5d9e6;
    }}
    [data-theme="dark"] .day-filter-btn:hover {{
      background: #264155;
      border-color: #4a697e;
    }}
    .day-legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-left: auto; }}
    .legend-item {{ display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--muted); }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; }}
    .legend-icon {{ font-size: 12px; }}
    .poi-number-marker {{ background: transparent; border: none; }}
    .poi-number-marker .pin {{
      width: 25px;
      height: 25px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      box-shadow: 0 0 0 2px #ffffff, 0 2px 6px rgba(31, 51, 65, 0.25);
    }}
    .poi-number-marker .pin.lodging {{ border-radius: 8px; width: 28px; }}
    #map {{ width: 100%; height: calc(100vh - 240px); min-height: 340px; }}
    .panel {{ padding: 0; display: grid; grid-template-rows: auto 1fr; }}
    .panel-scroll {{ overflow: auto; padding: 12px; max-height: calc(100vh - 190px); }}
    .plan-shell {{
      border: 1px solid #dfebf1;
      border-radius: 12px;
      background: linear-gradient(180deg, #fcfeff 0%, #f7fbfc 100%);
      overflow: hidden;
      box-shadow: 0 8px 20px rgba(35, 66, 84, 0.08);
      margin-bottom: 10px;
    }}
    [data-theme="dark"] .plan-shell {{
      border-color: #2d4251;
      background: linear-gradient(180deg, #1a2d39 0%, #172833 100%);
      box-shadow: 0 10px 24px rgba(7, 12, 18, 0.45);
    }}
    .plan-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 12px;
      border-bottom: 1px solid #e1ecf2;
      background: #f2f8fb;
      color: #2f4f62;
      font-size: 12px;
      font-weight: 600;
    }}
    [data-theme="dark"] .plan-header {{
      border-bottom-color: #304656;
      background: #1e3342;
      color: #cbe0ed;
    }}
    .plan-header .pill {{
      border: 1px solid #c9dce8;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      background: #ffffff;
      color: #406077;
    }}
    [data-theme="dark"] .plan-header .pill {{
      border-color: #446173;
      background: #274253;
      color: #d6e8f3;
    }}
    .plan-rich {{
      padding: 14px;
      color: #2d4453;
      line-height: 1.62;
      font-size: 14px;
    }}
    .plan-rich h1,
    .plan-rich h2,
    .plan-rich h3,
    .plan-rich h4 {{
      margin: 1rem 0 .55rem;
      color: #21465a;
      letter-spacing: -0.2px;
    }}
    .plan-rich h1 {{
      font-size: 1.35rem;
      border-bottom: 1px solid #dbe8ef;
      padding-bottom: .35rem;
    }}
    .plan-rich h2 {{
      font-size: 1.15rem;
      border-left: 4px solid #7faac2;
      padding-left: .55rem;
    }}
    .plan-rich h3 {{ font-size: 1.02rem; }}
    .plan-rich p {{ margin: .45rem 0 .7rem; }}
    .plan-rich ul,
    .plan-rich ol {{ padding-left: 1.2rem; margin: .45rem 0 .8rem; }}
    .plan-rich li {{ margin: .2rem 0; }}
    .plan-rich blockquote {{
      margin: .8rem 0;
      border-left: 4px solid #9cc1d5;
      background: #f3f9fc;
      padding: .55rem .7rem;
      border-radius: 8px;
      color: #35576b;
    }}
    .plan-rich code {{
      background: #eef5f9;
      color: #2e4a5a;
      border: 1px solid #d9e7ef;
      border-radius: 6px;
      padding: 1px 5px;
      font-size: .92em;
    }}
    .plan-rich pre {{
      background: #f3f8fb;
      border: 1px solid #ddebf2;
      border-radius: 10px;
      padding: .7rem .8rem;
      overflow: auto;
    }}
    .plan-rich hr {{ border: 0; border-top: 1px dashed #c9dbe5; margin: 1rem 0; }}
    .plan-rich table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin: .8rem 0;
      border: 1px solid #d9e6ee;
      border-radius: 10px;
      overflow: hidden;
      background: #ffffff;
    }}
    .plan-rich th,
    .plan-rich td {{ padding: .52rem .6rem; border-bottom: 1px solid #e6eff4; text-align: left; }}
    .plan-rich th {{ background: #edf6fb; color: #2e5063; font-weight: 650; }}
    .plan-rich tr:last-child td {{ border-bottom: none; }}
    [data-theme="dark"] .plan-rich h1,
    [data-theme="dark"] .plan-rich h2,
    [data-theme="dark"] .plan-rich h3,
    [data-theme="dark"] .plan-rich h4 {{
      color: #d2e7f4;
    }}
    [data-theme="dark"] .plan-rich h1 {{ border-bottom-color: #2e4454; }}
    [data-theme="dark"] .plan-rich h2 {{ border-left-color: #7faec8; }}
    [data-theme="dark"] .plan-rich blockquote {{
      border-left-color: #6c9bb6;
      background: #1f3544;
      color: #c7dcea;
    }}
    [data-theme="dark"] .plan-rich code {{
      background: #203646;
      color: #d8e7f2;
      border-color: #355061;
    }}
    [data-theme="dark"] .plan-rich pre {{
      background: #1b2e3b;
      border-color: #314a5a;
    }}
    [data-theme="dark"] .plan-rich hr {{ border-top-color: #395466; }}
    [data-theme="dark"] .plan-rich table {{
      border-color: #324a5a;
      background: #182935;
    }}
    [data-theme="dark"] .plan-rich th,
    [data-theme="dark"] .plan-rich td {{ border-bottom-color: #2b4251; }}
    [data-theme="dark"] .plan-rich th {{ background: #203746; color: #d5e7f2; }}
    .plan-raw-wrap {{ margin-top: 8px; }}
    .plan-raw-wrap summary {{
      cursor: pointer;
      color: #4a6678;
      font-size: 12px;
      font-weight: 600;
      user-select: none;
    }}
    .plan-raw {{
      white-space: pre-wrap;
      word-wrap: break-word;
      background: var(--plan-bg);
      border: 1px solid #e4edf1;
      border-radius: 10px;
      padding: 10px;
      margin-top: 8px;
      font-size: 12px;
      line-height: 1.52;
      color: #3f5664;
    }}
    [data-theme="dark"] .plan-raw {{
      border-color: #324958;
      color: #b8ccda;
    }}
    .poi-list {{ margin: 10px 0 0; padding-left: 0; list-style: none; font-size: 13px; }}
    .poi-item {{
      margin-bottom: 6px;
      border: 1px solid #e3ebef;
      border-left: 4px solid #cbd5e1;
      border-radius: 10px;
      padding: 8px 10px;
      background: #ffffff;
      cursor: pointer;
      outline: none;
      transition: transform .14s ease, box-shadow .14s ease, background-color .14s ease;
    }}
    [data-theme="dark"] .poi-item {{
      border-color: #2f4553;
      background: #1a2b37;
    }}
    .poi-item:hover {{ transform: translateY(-1px); box-shadow: 0 6px 14px rgba(33, 58, 74, 0.08); }}
    .poi-item.active {{ box-shadow: 0 0 0 2px #b6d2e0 inset; background: #edf6fb; }}
    [data-theme="dark"] .poi-item:hover {{ box-shadow: 0 8px 16px rgba(5, 10, 15, 0.4); }}
    [data-theme="dark"] .poi-item.active {{ box-shadow: 0 0 0 2px #5f859c inset; background: #223a49; }}
    .poi-item.hidden {{ display: none; }}
    .poi-main {{ font-weight: 600; color: #223a49; }}
    .poi-sub {{ color: var(--muted); font-size: 12px; margin-top: 2px; }}
    .poi-tripadvisor-link {{
      display: inline-flex;
      margin-top: 4px;
      font-size: 12px;
      text-decoration: none;
      color: #2b6b8f;
      font-weight: 600;
    }}
    .poi-tripadvisor-link:hover {{ text-decoration: underline; }}
    .poi-tripadvisor-photo {{
      display: block;
      width: 100%;
      max-width: 220px;
      border-radius: 8px;
      margin-top: 6px;
      border: 1px solid #dce9f1;
    }}
    [data-theme="dark"] .poi-tripadvisor-link {{ color: #9ec9e4; }}
    [data-theme="dark"] .poi-tripadvisor-photo {{ border-color: #365062; }}
    .poi-transfer {{ color: var(--accent); font-size: 12px; margin-top: 2px; }}
    .poi-popup h3 {{ margin: 0 0 6px; font-size: 15px; }}
    .poi-popup .line {{ margin: 2px 0; font-size: 13px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #eaf3f8; color: #2e5b75; font-size: 12px; }}
    @media (max-width: 1100px) {{
      .content {{ grid-template-columns: 1fr; }}
      #map {{ height: 50vh; }}
      .panel-scroll {{ max-height: none; }}
      .day-legend {{ margin-left: 0; width: 100%; }}
      .meta-grid {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
    }}
    @media (max-width: 680px) {{
      .meta-grid {{ grid-template-columns: 1fr 1fr; }}
      .header h1 {{ font-size: 18px; }}
      .meta-value {{ font-size: 15px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <div class="header">
      <div class="header-top">
        <h1>🧭 Plan podróży + mapa POI — {html.escape(destination)}</h1>
        <button id="theme-toggle" class="theme-toggle" type="button">🌙 Luxury dark</button>
      </div>
      <div class="meta">
        <div class="meta-grid">
          <div class="meta-item">
            <span class="meta-label">Dni</span>
            <span class="meta-value">{days}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">POI</span>
            <span class="meta-value">{len(points)}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Noclegi:</span>
            <span class="meta-value">{lodging_count}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Tryb mapy</span>
            <span class="meta-value">Interaktywny</span>
          </div>
        </div>
        <div class="transport-card">
          <div class="transport-title">Transport</div>
          <div class="transport-preview">{html.escape(transport_preview or mobility_text)}</div>
          <details class="transport-details">
            <summary>Pokaż pełną rekomendację</summary>
            <div class="transport-full">{html.escape(mobility_text)}</div>
          </details>
        </div>
        <div class="generated-at">Wygenerowano: {generated_at}</div>
      </div>
    </div>
    <div class="content">
      <div class="card">
        <h2>Mapa wycieczki</h2>
        <div class="map-toolbar">
          <span class="filter-label">Pokaż markery:</span>
          <div id="day-filters"></div>
          <div id="day-legend" class="day-legend"></div>
        </div>
        <div id="map"></div>
      </div>
      <div class="card panel">
        <h2>Opis wycieczki</h2>
        <div class="panel-scroll" id="description-panel">
          <div class="plan-shell">
            <div class="plan-header">
              <span>✨ Plan podróży — widok premium</span>
              <span class="pill">Markdown Render</span>
            </div>
            <article id="plan-rendered" class="plan-rich"></article>
          </div>
          <details class="plan-raw-wrap">
            <summary>Pokaż oryginalny markdown</summary>
            <pre class="plan-raw" id="plan-raw">{escaped_markdown}</pre>
          </details>
          <h3>Punkty na mapie (w tym noclegi)</h3>
          <ul id="poi-list" class="poi-list"></ul>
        </div>
      </div>
    </div>
  </div>

  <script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""
  ></script>
  <script src="https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js"></script>
  <script>
    const points = {points_json};
    const transferSegments = {transfer_segments_json};
    const mobilityStrategy = {mobility_json};
    const dayPalette = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2", "#be123c", "#4f46e5"];
    const uniqueDays = [...new Set(points.map((p) => Number(p.day)).filter((d) => Number.isFinite(d)))].sort((a, b) => a - b);
    const dayColors = new Map(uniqueDays.map((day, idx) => [day, dayPalette[idx % dayPalette.length]]));

    const map = L.map("map").setView([{center_lat}, {center_lng}], points.length ? 13 : 5);

    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }}).addTo(map);

    const markerGroup = L.featureGroup().addTo(map);
    const routeGroup = L.layerGroup().addTo(map);
    const dayFiltersHost = document.getElementById("day-filters");
    const dayLegendHost = document.getElementById("day-legend");
    const poiList = document.getElementById("poi-list");
    const planRawHost = document.getElementById("plan-raw");
    const planRenderedHost = document.getElementById("plan-rendered");
    const themeToggleBtn = document.getElementById("theme-toggle");

    const applyTheme = (theme) => {{
      const normalized = theme === "dark" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", normalized);
      if (themeToggleBtn) {{
        themeToggleBtn.textContent = normalized === "dark" ? "☀️ Tryb jasny" : "🌙 Luxury dark";
      }}
      try {{
        localStorage.setItem("travelmate_theme", normalized);
      }} catch (_err) {{
        // ignore storage errors
      }}
    }};

    let initialTheme = "light";
    try {{
      const savedTheme = localStorage.getItem("travelmate_theme");
      if (savedTheme === "dark" || savedTheme === "light") {{
        initialTheme = savedTheme;
      }} else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {{
        initialTheme = "dark";
      }}
    }} catch (_err) {{
      initialTheme = "light";
    }}
    applyTheme(initialTheme);

    if (themeToggleBtn) {{
      themeToggleBtn.addEventListener("click", () => {{
        const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
        applyTheme(current === "dark" ? "light" : "dark");
      }});
    }}

    if (planRawHost && planRenderedHost && typeof window.markdownit === "function") {{
      const md = window.markdownit({{
        html: false,
        linkify: true,
        breaks: true,
        typographer: true,
      }});
      planRenderedHost.innerHTML = md.render(planRawHost.textContent || "");
    }}

    const allMarkers = [];
    const colorForDay = (day) => dayColors.get(Number(day)) || "#334155";
    const routeSegments = transferSegments.map((seg) => {{
      const dayColor = colorForDay(seg.day);
      const isHotelTransfer = seg.kind === "to_lodging" || seg.kind === "from_lodging";
      const kindLabel = seg.kind === "to_lodging"
        ? "Dojazd do noclegu"
        : seg.kind === "from_lodging"
          ? "Wyjazd z noclegu"
          : "Przejazd dzienny";
      const tooltip = `Dzień ${{seg.day}} · ${{kindLabel}}`;
      const polyline = L.polyline(
        [
          [Number(seg.from_lat), Number(seg.from_lng)],
          [Number(seg.to_lat), Number(seg.to_lng)],
        ],
        {{
          color: dayColor,
          weight: isHotelTransfer ? 5 : 4,
          opacity: 0.78,
          dashArray: isHotelTransfer ? "3 4" : "6 4",
        }},
      ).bindTooltip(tooltip, {{ sticky: true }});
      return {{ polyline, day: seg.day }};
    }});
    const poiItems = [];
    let activeFilter = "all";

    const inferTransportOptions = (strategy) => {{
      const text = String(strategy || "").toLowerCase();
      return {{
        metro: text.includes("metro"),
        tram: text.includes("tram"),
        bus: text.includes("bus") || text.includes("autobus"),
        walk: text.includes("spacer") || text.includes("pieszo") || text.includes("walk"),
        bike: text.includes("rower") || text.includes("bike"),
        car: text.includes("samoch") || text.includes("taxi") || text.includes("uber") || text.includes("car"),
      }};
    }};

    const transportOptions = inferTransportOptions(mobilityStrategy);

    const normalizeExternalUrl = (value) => {{
      const raw = String(value || "").trim();
      if (!raw) return "";

      if (/^[a-z][a-z0-9+.-]*:/i.test(raw)) {{
        return raw;
      }}

      if (raw.startsWith("//")) {{
        return `https:${{raw}}`;
      }}

      return `https://${{raw.replace(/^\\/+/, "")}}`;
    }};

    const estimateTravel = (distanceKm) => {{
      let mode = "pieszo";
      let speedKmh = 4.8;
      let overheadMin = 2;

      if (distanceKm >= 2 && transportOptions.metro) {{
        mode = "metro";
        speedKmh = 30;
        overheadMin = 6;
      }} else if (distanceKm >= 2 && transportOptions.tram) {{
        mode = "tramwaj";
        speedKmh = 22;
        overheadMin = 5;
      }} else if (distanceKm >= 1.5 && transportOptions.bus) {{
        mode = "autobus";
        speedKmh = 18;
        overheadMin = 5;
      }} else if (distanceKm >= 1.5 && transportOptions.car) {{
        mode = "samochód/taxi";
        speedKmh = 26;
        overheadMin = 4;
      }} else if (distanceKm >= 1.2 && transportOptions.bike) {{
        mode = "rower";
        speedKmh = 15;
        overheadMin = 2;
      }} else if (!transportOptions.walk && (transportOptions.bus || transportOptions.tram || transportOptions.metro)) {{
        mode = transportOptions.metro ? "metro" : transportOptions.tram ? "tramwaj" : "autobus";
        speedKmh = transportOptions.metro ? 30 : transportOptions.tram ? 22 : 18;
        overheadMin = 5;
      }}

      const minutes = Math.max(1, Math.ceil((distanceKm / speedKmh) * 60 + overheadMin));
      return {{ mode, minutes }};
    }};

    const focusPoint = (idx) => {{
      const item = poiItems[idx];
      if (!item) return;

      poiItems.forEach((entry) => entry.classList.remove("active"));
      item.classList.add("active");
      item.scrollIntoView({{ behavior: "smooth", block: "center" }});
      item.focus({{ preventScroll: true }});
    }};

    const renderLegend = () => {{
      if (!dayLegendHost || uniqueDays.length === 0) return;
      uniqueDays.forEach((day) => {{
        const item = document.createElement("span");
        item.className = "legend-item";
        item.innerHTML = `<span class="legend-dot" style="background:${{colorForDay(day)}}"></span> Dzień ${{day}}`;
        dayLegendHost.appendChild(item);
      }});
      const markerLegend = document.createElement("span");
      markerLegend.className = "legend-item";
      markerLegend.innerHTML = `<span class="legend-icon">●</span> Aktywność · <span class="legend-icon">🏨</span> Nocleg`;
      dayLegendHost.appendChild(markerLegend);
    }};

    const setActiveFilterButton = (filterValue) => {{
      if (!dayFiltersHost) return;
      dayFiltersHost.querySelectorAll(".day-filter-btn").forEach((btn) => {{
        if (btn.dataset.dayFilter === filterValue) {{
          btn.classList.add("active");
        }} else {{
          btn.classList.remove("active");
        }}
      }});
    }};

    const applyFilter = (filterValue) => {{
      activeFilter = filterValue;
      markerGroup.clearLayers();
      routeGroup.clearLayers();

      const visibleMarkers = allMarkers.filter((entry) =>
        filterValue === "all" ? true : (entry.markerDays || [String(entry.day)]).includes(filterValue)
      );
      visibleMarkers.forEach((entry) => entry.marker.addTo(markerGroup));

      const visibleSegments = routeSegments.filter((seg) =>
        filterValue === "all" ? true : String(seg.day) === filterValue
      );
      visibleSegments.forEach((seg) => seg.polyline.addTo(routeGroup));

      poiItems.forEach((item, idx) => {{
        const point = points[idx];
        const day = String(point.day);
        const lodgingDays = Array.isArray(point.lodging_days) ? point.lodging_days.map((d) => String(d)) : [];
        const visible =
          filterValue === "all"
          || day === filterValue
          || (point.point_type === "lodging" && lodgingDays.includes(filterValue));
        item.classList.toggle("hidden", !visible);
      }});

      if (visibleMarkers.length > 0) {{
        map.fitBounds(markerGroup.getBounds().pad(0.2));
      }}

      setActiveFilterButton(filterValue);
    }};

    const createFilterButtons = () => {{
      if (!dayFiltersHost) return;

      const createBtn = (label, filterValue) => {{
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "day-filter-btn";
        btn.dataset.dayFilter = filterValue;
        btn.textContent = label;
        btn.addEventListener("click", () => applyFilter(filterValue));
        dayFiltersHost.appendChild(btn);
      }};

      createBtn("Wszystkie", "all");
      uniqueDays.forEach((day) => createBtn(`Dzień ${{day}}`, String(day)));
      setActiveFilterButton("all");
    }};

    points.forEach((point, idx) => {{
      const isLodging = point.point_type === "lodging";
      const markerColor = colorForDay(point.day);
      const websiteUrl = normalizeExternalUrl(point.website);
      const tripadvisorUrl = normalizeExternalUrl(point.tripadvisor_url);
      const tripadvisorPhotoUrl = normalizeExternalUrl(point.tripadvisor_photo_url);
      const transferInfo = isLodging
        ? "Dojazd do i z noclegu pokazano liniami na mapie."
        : "Dojazdy między punktami pokazano liniami na mapie.";

      const popupAddress = point.address ? `<div class="line"><strong>Adres:</strong> ${{point.address}}</div>` : "";
      const popupWebsite = websiteUrl ? `<div class="line"><a href="${{websiteUrl}}" target="_blank" rel="noopener">Strona WWW</a></div>` : "";
      const popupTripadvisorRating = point.tripadvisor_rating !== null && point.tripadvisor_rating !== undefined
        ? `<div class="line"><strong>TripAdvisor rating:</strong> ${{Number(point.tripadvisor_rating).toFixed(1)}} / 5</div>`
        : "";
      const popupTripadvisorUrl = tripadvisorUrl
        ? `<div class="line"><a href="${{tripadvisorUrl}}" target="_blank" rel="noopener">TripAdvisor</a></div>`
        : "";
      const popupTripadvisorPhoto = tripadvisorPhotoUrl
        ? `<div class="line"><img src="${{tripadvisorPhotoUrl}}" alt="${{point.name}} - TripAdvisor" style="width:100%;max-width:220px;border-radius:8px;margin-top:6px;" /></div>`
        : "";
      const popupLodgingPrice = isLodging && point.price ? `<div class="line"><strong>Poziom cenowy:</strong> ${{point.price}}</div>` : "";
      const popupLodgingHours = isLodging && (point.check_in || point.check_out)
        ? `<div class="line"><strong>Check-in/out:</strong> ${{point.check_in || "brak"}} / ${{point.check_out || "brak"}}</div>`
        : "";
      const popupLodgingNote = isLodging && point.note ? `<div class="line"><strong>Uwaga:</strong> ${{point.note}}</div>` : "";
      const popup = `
        <div class="poi-popup">
          <h3>${{idx + 1}}. ${{point.name}}</h3>
          <div class="line"><span class="badge" style="background:${{markerColor}}22;color:${{markerColor}}">Dzień ${{point.day}} · ${{point.part_of_day}}</span></div>
          <div class="line"><strong>Plan:</strong> ${{point.title}}</div>
          <div class="line"><strong>Przemieszczenie:</strong> ${{transferInfo}}</div>
          <div class="line"><strong>Współrzędne:</strong> ${{point.lat}}, ${{point.lng}}</div>
          ${{popupLodgingPrice}}
          ${{popupLodgingHours}}
          ${{popupLodgingNote}}
          ${{popupAddress}}
          ${{popupWebsite}}
          ${{popupTripadvisorRating}}
          ${{popupTripadvisorUrl}}
          ${{popupTripadvisorPhoto}}
        </div>
      `;

      const marker = L.marker([point.lat, point.lng], {{
        icon: L.divIcon({{
          className: "poi-number-marker",
          html: isLodging
            ? `<span class="pin lodging" style="background:${{markerColor}}">🏨</span>`
            : `<span class="pin" style="background:${{markerColor}}">${{idx + 1}}</span>`,
          iconSize: isLodging ? [28, 26] : [26, 26],
          iconAnchor: isLodging ? [14, 13] : [13, 13],
        }}),
      }}).bindPopup(popup);

      marker.on("click", () => {{
        focusPoint(idx);
      }});

      const markerDays = isLodging && Array.isArray(point.lodging_days) && point.lodging_days.length > 0
        ? point.lodging_days.map((d) => String(d))
        : [String(point.day)];
      allMarkers.push({{ marker, day: point.day, markerDays }});

      if (poiList) {{
        const li = document.createElement("li");
        li.id = `poi-point-${{idx}}`;
        li.className = "poi-item";
        li.tabIndex = -1;
        li.style.borderLeftColor = markerColor;
        const poiPrefix = isLodging ? "🏨" : `${{idx + 1}}.`;
        const listTripadvisorPhoto = tripadvisorPhotoUrl
          ? `<img class="poi-tripadvisor-photo" src="${{tripadvisorPhotoUrl}}" alt="${{point.name}} - TripAdvisor" loading="lazy" />`
          : "";
        const listTripadvisorLink = tripadvisorUrl
          ? `<a class="poi-tripadvisor-link" href="${{tripadvisorUrl}}" target="_blank" rel="noopener">TripAdvisor ↗</a>`
          : "";
        li.innerHTML = `
          <div class="poi-main">${{poiPrefix}} Dzień ${{point.day}} (${{point.part_of_day}}): ${{point.name}}</div>
          <div class="poi-sub">${{point.title}}${{point.address ? ` · ${{point.address}}` : ""}}</div>
          <div class="poi-sub">${{point.tripadvisor_rating !== null && point.tripadvisor_rating !== undefined ? `TripAdvisor: ${{Number(point.tripadvisor_rating).toFixed(1)}}/5` : ""}}</div>
          ${{listTripadvisorLink}}
          ${{listTripadvisorPhoto}}
          <div class="poi-transfer">${{transferInfo}}</div>
        `;
        li.addEventListener("click", () => {{
          if (activeFilter !== "all" && String(point.day) !== activeFilter) {{
            const targetDay = isLodging && Array.isArray(point.lodging_days) && point.lodging_days.length > 0
              ? String(point.lodging_days[0])
              : String(point.day);
            applyFilter(targetDay);
          }}
          marker.openPopup();
          map.panTo(marker.getLatLng());
          focusPoint(idx);
        }});

        poiItems.push(li);
        poiList.appendChild(li);
      }}
    }});

    if (poiList && points.length === 0) {{
      const li = document.createElement("li");
      li.className = "poi-item";
      li.textContent = "Brak punktów z koordynatami do wyświetlenia na mapie.";
      poiList.appendChild(li);
    }}

    renderLegend();
    createFilterButtons();
    applyFilter("all");
  </script>
</body>
</html>
"""


def save_itinerary_output(
    request: ItineraryInput,
    markdown_plan: str,
    geo_output: GeoOutput | None = None,
    itinerary_draft: ItineraryDraft | None = None,
    output_root: Path | None = None,
) -> Path:
    root = output_root or Path.cwd() / "output"
    root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{_slugify(request.destination)}_{request.days}d"
    trip_dir = root / folder_name
    trip_dir.mkdir(parents=True, exist_ok=True)

    md_path = trip_dir / "itinerary.md"
    md_path.write_text(markdown_plan, encoding="utf-8")

    meta_path = trip_dir / "request.json"
    meta_path.write_text(
        json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    points = _collect_geo_points(geo_output, itinerary_draft=itinerary_draft)
    transfer_segments = _collect_transfer_segments(
      geo_output,
      itinerary_draft=itinerary_draft,
      points=points,
    )

    html_content = _build_combined_itinerary_html(
        destination=request.destination,
        days=request.days,
        markdown_plan=markdown_plan,
        points=points,
      transfer_segments=transfer_segments,
        mobility_strategy=geo_output.mobility_strategy if geo_output else "",
        generated_at=generated_at,
    )

    html_path = trip_dir / "itinerary.html"
    html_path.write_text(html_content, encoding="utf-8")

    return html_path
