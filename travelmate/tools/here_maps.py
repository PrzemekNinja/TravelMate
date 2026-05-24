from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from travelmate.tools.config import load_model_config
from travelmate.tools.logging_utils import get_logger
from travelmate.tools.tripadvisor import get_tripadvisor_place_details


LOGGER = get_logger("here_maps")


def _is_valid_api_key(api_key: str | None) -> bool:
    return bool(api_key and api_key.strip() and not api_key.startswith("your_"))


class HereMapsClient:
    def __init__(self, api_key: str, geocode_base_url: str, search_base_url: str) -> None:
        self.api_key = api_key
        self.geocode_base_url = geocode_base_url.rstrip("/")
        self.search_base_url = search_base_url.rstrip("/")

    def _request_json(self, base_url: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        query_params = dict(params)
        query_params["apiKey"] = self.api_key
        url = f"{base_url}/{endpoint}?{urlencode(query_params)}"

        request = Request(url, headers={"User-Agent": "TravelMate/1.0"})
        with urlopen(request, timeout=5.0) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def geocode(self, query: str) -> dict[str, Any] | None:
        payload = self._request_json(
            self.geocode_base_url,
            "geocode",
            {
                "q": query,
                "lang": "pl-PL",
                "limit": 1,
            },
        )
        items = payload.get("items", [])
        if not items:
            return None
        return items[0]

    def discover(self, query: str, at: str, limit: int = 3) -> list[dict[str, Any]]:
        payload = self._request_json(
            self.search_base_url,
            "discover",
            {
                "q": query,
                "at": at,
                "lang": "pl-PL",
                "limit": limit,
            },
        )
        return payload.get("items", [])

    def lookup(self, item_id: str) -> dict[str, Any] | None:
        payload = self._request_json(
            self.search_base_url,
            "lookup",
            {
                "id": item_id,
                "lang": "pl-PL",
                "show": "details,contacts",
            },
        )
        if not isinstance(payload, dict):
            return None
        return payload


def _extract_website(item: dict[str, Any]) -> str:
    direct_candidates = [
        item.get("website"),
        item.get("homepage"),
        item.get("url"),
    ]
    for candidate in direct_candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    contacts = item.get("contacts")
    if isinstance(contacts, dict):
        contacts = [contacts]

    if isinstance(contacts, list):
        for contact in contacts:
            if not isinstance(contact, dict):
                continue

            for key in ("www", "website"):
                candidate = contact.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
                if isinstance(candidate, list):
                    for entry in candidate:
                        if isinstance(entry, dict):
                            value = entry.get("value")
                            if isinstance(value, str) and value.strip():
                                return value.strip()
                        elif isinstance(entry, str) and entry.strip():
                            return entry.strip()

    return ""


def _extract_position(item: dict[str, Any]) -> dict[str, Any]:
    position = item.get("position")
    if isinstance(position, dict) and (position.get("lat") is not None and position.get("lng") is not None):
        return position

    access = item.get("access")
    if isinstance(access, list):
        for entry in access:
            if isinstance(entry, dict) and (entry.get("lat") is not None and entry.get("lng") is not None):
                return entry

    return {}


def _build_fallback_web_link(place_name: str, country: str, city: str, lat: Any, lng: Any) -> str:
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

    query = quote_plus(" ".join(part for part in [place_name, city, country] if part))
    if query:
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    return ""


def _normalize_place_payload(place_name: str, item: dict[str, Any] | None, source: str = "here") -> dict[str, Any]:
    if not item:
        return {
            "name": place_name,
            "coordinates": {"lat": None, "lng": None},
            "address": {
                "country": "",
                "city": "",
                "postcode": "",
                "street": "",
                "building_number": "",
            },
            "website": "",
            "tripadvisor_url": "",
            "tripadvisor_rating": None,
            "tripadvisor_photo_url": "",
            "tripadvisor_location_id": "",
            "source": source,
        }

    address = item.get("address") or {}
    position = _extract_position(item)

    city = address.get("city") or address.get("district") or address.get("county") or ""
    country = address.get("countryName") or address.get("countryCode") or ""

    lat = position.get("lat")
    lng = position.get("lng")
    website = _extract_website(item) or _build_fallback_web_link(place_name, country, city, lat, lng)

    return {
        "name": (item.get("title") or place_name or "").strip(),
        "coordinates": {
            "lat": lat,
            "lng": lng,
        },
        "address": {
            "country": country,
            "city": city,
            "postcode": address.get("postalCode") or "",
            "street": address.get("street") or "",
            "building_number": address.get("houseNumber") or "",
        },
        "website": website,
        "tripadvisor_url": "",
        "tripadvisor_rating": None,
        "tripadvisor_photo_url": "",
        "tripadvisor_location_id": "",
        "source": source,
    }


def _pick_best_item(place_name: str, items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None

    target = place_name.strip().lower()

    for candidate in items:
        title = str(candidate.get("title") or "").strip().lower()
        if title and title == target:
            return candidate

    for candidate in items:
        title = str(candidate.get("title") or "").strip().lower()
        if title and (title.startswith(target) or target.startswith(title)):
            return candidate

    return items[0]


def get_here_destination_context(destination: str) -> dict[str, Any] | None:
    cfg = load_model_config()

    if not _is_valid_api_key(cfg.here_api_key):
        LOGGER.info("HERE API pominięte: brak poprawnego HERE_API_KEY.")
        return None

    try:
        client = HereMapsClient(
            api_key=cfg.here_api_key.strip(),
            geocode_base_url=cfg.here_geocode_base_url,
            search_base_url=cfg.here_search_base_url,
        )
        destination_item = client.geocode(destination)
        if not destination_item:
            LOGGER.warning("HERE API: brak geokodowania dla '%s'.", destination)
            return None

        position = destination_item.get("position") or {}
        lat = position.get("lat")
        lng = position.get("lng")
        if lat is None or lng is None:
            LOGGER.warning("HERE API: brak współrzędnych dla '%s'.", destination)
            return None

        at = f"{lat},{lng}"
        poi_queries = ["museum", "art gallery", "historic site", "restaurant"]

        collected_places: list[dict[str, Any]] = []
        seen: set[str] = set()

        for poi_query in poi_queries:
            for item in client.discover(query=poi_query, at=at, limit=3):
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)

                address = item.get("address") or {}
                place_pos = item.get("position") or {}

                collected_places.append(
                    {
                        "name": title,
                        "query_source": poi_query,
                        "address": address.get("label", ""),
                        "lat": place_pos.get("lat"),
                        "lng": place_pos.get("lng"),
                    }
                )

                if len(collected_places) >= 8:
                    break
            if len(collected_places) >= 8:
                break

        context: dict[str, Any] = {
            "provider": "here",
            "destination": destination,
            "destination_label": destination_item.get("title", destination),
            "center": {"lat": lat, "lng": lng},
            "sample_places": collected_places,
        }
        LOGGER.info(
            "HERE API: przygotowano kontekst mapowy dla '%s' (POI=%d).",
            destination,
            len(collected_places),
        )
        return context
    except Exception as exc:
        LOGGER.warning("HERE API: błąd podczas pobierania danych (%s).", exc)
        return None


def get_here_places_details(destination: str, place_names: list[str]) -> dict[str, dict[str, Any]]:
    cfg = load_model_config()

    cleaned_place_names = [name.strip() for name in place_names if name and name.strip()]
    if not cleaned_place_names:
        return {}

    if not _is_valid_api_key(cfg.here_api_key):
        LOGGER.info("HERE API pominięte dla szczegółów miejsc: brak poprawnego HERE_API_KEY.")
        return {name: _normalize_place_payload(name, None, source="unresolved") for name in cleaned_place_names}

    client = HereMapsClient(
        api_key=cfg.here_api_key.strip(),
        geocode_base_url=cfg.here_geocode_base_url,
        search_base_url=cfg.here_search_base_url,
    )

    center_at = ""
    try:
        destination_item = client.geocode(destination)
        if destination_item:
            pos = destination_item.get("position") or {}
            lat = pos.get("lat")
            lng = pos.get("lng")
            if lat is not None and lng is not None:
                center_at = f"{lat},{lng}"
    except Exception as exc:
        LOGGER.warning("HERE API: nie udało się wyznaczyć centrum destynacji '%s' (%s).", destination, exc)

    details: dict[str, dict[str, Any]] = {}

    for place_name in cleaned_place_names:
        item: dict[str, Any] | None = None
        try:
            query = f"{place_name}, {destination}"
            if center_at:
                discovered = client.discover(query=query, at=center_at, limit=5)
                if discovered:
                    item = _pick_best_item(place_name, discovered)

                if not item:
                    discovered_short = client.discover(query=place_name, at=center_at, limit=5)
                    if discovered_short:
                        item = _pick_best_item(place_name, discovered_short)

            if not item:
                item = client.geocode(query)

            if item and item.get("id"):
                try:
                    looked_up = client.lookup(str(item["id"]))
                    if looked_up:
                        item = looked_up
                except (HTTPError, URLError, ValueError, TimeoutError):
                    pass

            normalized_payload = _normalize_place_payload(place_name, item, source="here")
            coordinates = normalized_payload.get("coordinates", {})
            lat_raw = coordinates.get("lat") if isinstance(coordinates, dict) else None
            lng_raw = coordinates.get("lng") if isinstance(coordinates, dict) else None

            ta_details = get_tripadvisor_place_details(
                place_name=str(normalized_payload.get("name") or place_name),
                destination=destination,
                lat=float(lat_raw) if isinstance(lat_raw, (int, float)) else None,
                lng=float(lng_raw) if isinstance(lng_raw, (int, float)) else None,
            )
            normalized_payload.update(ta_details)
            details[place_name] = normalized_payload
        except Exception as exc:
            LOGGER.warning("HERE API: błąd rozwiązywania miejsca '%s' (%s).", place_name, exc)
            unresolved_payload = _normalize_place_payload(place_name, None, source="unresolved")
            unresolved_payload.update(
                get_tripadvisor_place_details(
                    place_name=place_name,
                    destination=destination,
                    lat=None,
                    lng=None,
                )
            )
            details[place_name] = unresolved_payload

    return details
