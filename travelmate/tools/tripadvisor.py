from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from travelmate.tools.config import load_model_config
from travelmate.tools.logging_utils import get_logger


LOGGER = get_logger("tripadvisor")


def _is_valid_api_key(api_key: str | None) -> bool:
    return bool(api_key and api_key.strip() and not api_key.startswith("your_"))


class TripAdvisorClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        language: str,
        currency: str,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.language = language
        self.currency = currency

    def _request_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        query_params = dict(params)
        query_params["key"] = self.api_key
        url = f"{self.base_url}/{endpoint}?{urlencode(query_params)}"

        request = Request(url, headers={"User-Agent": "TravelMate/1.0"})
        with urlopen(request, timeout=5.0) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def search(self, query: str, lat: float | None = None, lng: float | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "searchQuery": query,
            "language": self.language,
        }
        if lat is not None and lng is not None:
            params["latLong"] = f"{lat},{lng}"

        payload = self._request_json("location/search", params)
        return payload.get("data", []) if isinstance(payload, dict) else []

    def details(self, location_id: str) -> dict[str, Any] | None:
        payload = self._request_json(
            f"location/{location_id}/details",
            {
                "language": self.language,
                "currency": self.currency,
            },
        )
        return payload if isinstance(payload, dict) else None

    def photos(self, location_id: str, limit: int = 1) -> list[dict[str, Any]]:
        payload = self._request_json(
            f"location/{location_id}/photos",
            {
                "language": self.language,
                "limit": max(1, limit),
            },
        )
        return payload.get("data", []) if isinstance(payload, dict) else []


def _pick_best_location(query: str, items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None

    target = query.strip().lower()

    for item in items:
        name = str(item.get("name") or "").strip().lower()
        if name and name == target:
            return item

    for item in items:
        name = str(item.get("name") or "").strip().lower()
        if name and (name.startswith(target) or target.startswith(name)):
            return item

    return items[0]


def _extract_photo_url(photo: dict[str, Any]) -> str:
    images = photo.get("images")
    if not isinstance(images, dict):
        return ""

    for key in ("large", "original", "medium", "small", "thumbnail"):
        value = images.get(key)
        if isinstance(value, dict):
            url = value.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()

    return ""


def get_tripadvisor_place_details(
    place_name: str,
    destination: str,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    cfg = load_model_config()

    fallback = {
        "tripadvisor_url": "",
        "tripadvisor_rating": None,
        "tripadvisor_photo_url": "",
        "tripadvisor_location_id": "",
    }

    if not _is_valid_api_key(cfg.tripadvisor_api_key):
        return fallback

    try:
        client = TripAdvisorClient(
            api_key=cfg.tripadvisor_api_key.strip(),
            base_url=cfg.tripadvisor_base_url,
            language=cfg.tripadvisor_language,
            currency=cfg.tripadvisor_currency,
        )

        search_query = ", ".join(part for part in [place_name, destination] if part)
        search_results = client.search(search_query, lat=lat, lng=lng)
        best = _pick_best_location(place_name, search_results)

        if not best and (lat is not None and lng is not None):
            search_results = client.search(place_name)
            best = _pick_best_location(place_name, search_results)

        if not best:
            return fallback

        location_id = str(best.get("location_id") or "").strip()
        if not location_id:
            return fallback

        details = client.details(location_id) or {}
        photos = client.photos(location_id, limit=1)

        rating_raw = details.get("rating")
        rating: float | None = None
        try:
            if rating_raw is not None:
                rating = float(rating_raw)
        except (TypeError, ValueError):
            rating = None

        photo_url = ""
        if photos:
            photo_url = _extract_photo_url(photos[0])

        web_url = details.get("web_url")
        if not isinstance(web_url, str):
            web_url = ""

        return {
            "tripadvisor_url": web_url.strip(),
            "tripadvisor_rating": rating,
            "tripadvisor_photo_url": photo_url,
            "tripadvisor_location_id": location_id,
        }
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        LOGGER.warning("TripAdvisor API: błąd dla miejsca '%s' (%s).", place_name, exc)
        return fallback
    except Exception as exc:
        LOGGER.warning("TripAdvisor API: nieoczekiwany błąd dla '%s' (%s).", place_name, exc)
        return fallback
