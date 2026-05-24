from __future__ import annotations

import json

from travelmate.models import ItineraryInput


def request_to_json_payload(request: ItineraryInput) -> str:
    return json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2)
