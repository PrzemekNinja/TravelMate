from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from travelmate.graph import build_graph
from travelmate.models import ItineraryInput
from travelmate.tools.logging_utils import get_logger
from travelmate.tools.input_parser import ParsedRequest, parse_user_input_to_request_with_metadata
from travelmate.tools.output_writer import save_itinerary_output
from travelmate.tools.dashboard_push import push_run_async


@dataclass
class PlannerRunResult:
    parsed: ParsedRequest
    markdown_plan: str
    html_output_path: Path
    map_output_path: Path | None


LOGGER = get_logger("planner_service")

PlannerEventCallback = Callable[[dict[str, Any]], None]


def _serialize_debug_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_debug_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_debug_value(item) for item in value]
    return value


def _emit_event(callback: PlannerEventCallback | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    callback(event)


class PlannerService:
    def __init__(self) -> None:
        self._app = build_graph()

    def run(
        self,
        user_text: str,
        output_root: Path,
        event_callback: PlannerEventCallback | None = None,
    ) -> PlannerRunResult:
        LOGGER.info("Start pipeline: parsowanie wejścia użytkownika.")
        parsed = parse_user_input_to_request_with_metadata(user_text)
        LOGGER.info(
            "Parsowanie OK: destynacja='%s', dni=%d, źródło='%s'.",
            parsed.request.destination,
            parsed.request.days,
            parsed.source,
        )
        _emit_event(
            event_callback,
            {
                "type": "debug_json",
                "label": "parsed_request",
                "data": {
                    "source": parsed.source,
                    "assumptions": list(parsed.assumptions),
                    "request": parsed.request.model_dump(mode="json"),
                },
            },
        )

        LOGGER.info("Start pipeline agentów (6 kroków).")
        result = self._app.invoke(
            {
                "request": parsed.request,
                "profile_markdown": "",
                "profile_summary": "",
                "transport_markdown": "",
                "transport_report": "",
                "geo_markdown": "",
                "geo_output": None,
                "itinerary_markdown": "",
                "itinerary_draft": None,
                "verification_markdown": "",
                "verification": None,
                "final_markdown": "",
            }
        )
        markdown_plan = result["final_markdown"]
        LOGGER.info("Pipeline agentów zakończony.")
        _emit_event(
            event_callback,
            {
                "type": "debug_json",
                "label": "pipeline_result",
                "data": {
                    "geo_output": _serialize_debug_value(result.get("geo_output")),
                    "itinerary_draft": _serialize_debug_value(result.get("itinerary_draft")),
                    "verification": _serialize_debug_value(result.get("verification")),
                    "final_markdown_preview": markdown_plan[:2000],
                },
            },
        )

        html_output_path = save_itinerary_output(
            request=parsed.request,
            markdown_plan=markdown_plan,
            geo_output=result.get("geo_output"),
            itinerary_draft=result.get("itinerary_draft"),
            output_root=output_root,
        )
        map_output_path = html_output_path
        LOGGER.info("Zapis wyników OK: %s", html_output_path)
        _emit_event(
            event_callback,
            {
                "type": "debug_json",
                "label": "saved_output",
                "data": {
                    "html_output_path": str(html_output_path),
                    "map_output_path": str(map_output_path),
                },
            },
        )

        # Fire-and-forget push to the AI Cost & Cache Dashboard (if running)
        push_run_async(html_output_path.parent)

        return PlannerRunResult(
            parsed=parsed,
            markdown_plan=markdown_plan,
            html_output_path=html_output_path,
            map_output_path=map_output_path,
        )

    def save_current(self, request: ItineraryInput, markdown_plan: str, output_root: Path) -> Path:
        return save_itinerary_output(request=request, markdown_plan=markdown_plan, output_root=output_root)
