"""
Fire-and-forget push to the AI Cost & Cache Dashboard after a TravelMate run.
If the dashboard is not running, the error is silently swallowed — TravelMate
continues normally regardless.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from travelmate.tools.logging_utils import get_logger

LOGGER = get_logger("dashboard_push")

_DASHBOARD_URL = "http://localhost:8001/api/runs/notify"


def push_run_async(run_folder: Path) -> None:
    """Push a completed run to the dashboard in a background thread."""
    thread = threading.Thread(
        target=_push_run,
        args=(run_folder,),
        daemon=True,
        name="dashboard-push",
    )
    thread.start()


def _push_run(run_folder: Path) -> None:
    try:
        import urllib.request

        request_file = run_folder / "request.json"
        itinerary_file = run_folder / "itinerary.md"

        if not request_file.exists() or not itinerary_file.exists():
            LOGGER.debug("Dashboard push skipped — files not ready yet: %s", run_folder)
            return

        payload = json.dumps({
            "run_id": run_folder.name,
            "request_json": request_file.read_text(encoding="utf-8"),
            "itinerary_md": itinerary_file.read_text(encoding="utf-8"),
        }).encode("utf-8")

        req = urllib.request.Request(
            _DASHBOARD_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            LOGGER.info(
                "Dashboard push OK: run_id=%s status=%s",
                run_folder.name,
                resp.status,
            )
    except Exception as exc:
        # Dashboard not running — that's fine, just log at debug level
        LOGGER.debug("Dashboard push skipped (dashboard not running?): %s", exc)
