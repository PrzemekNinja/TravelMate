"""TravelMate runs scanner — reads output/ folder from the main project."""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/runs", tags=["runs"])

# Path to TravelMate output directory — relative to this file's location
_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"

# In-memory store for live-pushed runs (auto-push from TravelMate)
_live_runs: list[dict] = []
_MAX_LIVE = 50


class NotifyPayload(BaseModel):
    run_id: str
    request_json: str
    itinerary_md: str
    token_usage: dict | None = None


def _scan_runs() -> list[dict]:
    if not _OUTPUT_DIR.exists():
        return []

    runs = []
    for folder in sorted(_OUTPUT_DIR.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        request_file = folder / "request.json"
        itinerary_file = folder / "itinerary.md"
        if not request_file.exists() or not itinerary_file.exists():
            continue
        try:
            request_data = json.loads(request_file.read_text(encoding="utf-8"))
            itinerary_text = itinerary_file.read_text(encoding="utf-8")
            runs.append({
                "id": folder.name,
                "destination": request_data.get("destination", "Unknown"),
                "days": request_data.get("days", "?"),
                "budget": request_data.get("budget", "?"),
                "pace": request_data.get("pace", "?"),
                "participants": request_data.get("participants", 1),
                "interests": request_data.get("interests", []),
                "request_json": json.dumps(request_data, ensure_ascii=False, indent=2),
                "itinerary_md": itinerary_text,
                "itinerary_preview": itinerary_text[:200].replace("\n", " ") + "...",
            })
        except Exception:
            continue
    return runs


@router.get("")
def list_runs():
    # Merge file-system runs + live-pushed runs (live ones first, deduped by id)
    fs_runs = _scan_runs()
    live_ids = {r["id"] for r in _live_runs}
    # Mark live runs
    for r in _live_runs:
        r["live"] = True
    # Mark fs runs, skip ones already in live
    fs_unique = [dict(r, live=False) for r in fs_runs if r["id"] not in live_ids]
    return {"runs": _live_runs + fs_unique}


@router.post("/notify")
def notify_run(payload: NotifyPayload):
    """Receive a live push from TravelMate after a trip is generated."""
    global _live_runs
    try:
        request_data = json.loads(payload.request_json)
    except Exception:
        request_data = {}

    run = {
        "id": payload.run_id,
        "destination": request_data.get("destination", "Unknown"),
        "days": request_data.get("days", "?"),
        "budget": request_data.get("budget", "?"),
        "pace": request_data.get("pace", "?"),
        "participants": request_data.get("participants", 1),
        "interests": request_data.get("interests", []),
        "request_json": json.dumps(request_data, ensure_ascii=False, indent=2),
        "itinerary_md": payload.itinerary_md,
        "itinerary_preview": payload.itinerary_md[:200].replace("\n", " ") + "...",
        "live": True,
        "pushed_at": datetime.utcnow().isoformat(),
        "token_usage": payload.token_usage,
    }

    # Deduplicate — replace if same id already exists
    _live_runs = [r for r in _live_runs if r["id"] != payload.run_id]
    _live_runs.insert(0, run)
    _live_runs = _live_runs[:_MAX_LIVE]

    return {"status": "ok", "run_id": payload.run_id}


@router.get("/live")
def get_live_runs():
    """Return only the live-pushed runs (most recent first)."""
    return {"runs": _live_runs}


@router.get("/{run_id}")
def get_run(run_id: str):
    # Sanitize — only allow folder names that look like our timestamp pattern
    safe_id = "".join(c for c in run_id if c.isalnum() or c in "_-")
    folder = _OUTPUT_DIR / safe_id
    request_file = folder / "request.json"
    itinerary_file = folder / "itinerary.md"

    if not folder.exists() or not request_file.exists() or not itinerary_file.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{safe_id}' not found")

    request_data = json.loads(request_file.read_text(encoding="utf-8"))
    itinerary_text = itinerary_file.read_text(encoding="utf-8")
    return {
        "id": safe_id,
        "destination": request_data.get("destination", "Unknown"),
        "days": request_data.get("days", "?"),
        "request_json": json.dumps(request_data, ensure_ascii=False, indent=2),
        "itinerary_md": itinerary_text,
    }


@router.get("/{run_id}/tokens")
def get_run_tokens(run_id: str):
    """Return real token usage for a run — from file or live push store."""
    from fastapi import HTTPException

    safe_id = "".join(c for c in run_id if c.isalnum() or c in "_-")

    # Check live store first
    for run in _live_runs:
        if run["id"] == safe_id and run.get("token_usage"):
            return run["token_usage"]

    # Fall back to file
    token_file = _OUTPUT_DIR / safe_id / "token_usage.json"
    if token_file.exists():
        return json.loads(token_file.read_text(encoding="utf-8"))

    raise HTTPException(status_code=404, detail=f"No token usage data for run '{safe_id}'")
