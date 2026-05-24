from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"Pydantic serializer warnings:.*",
    category=UserWarning,
)

from .graph import build_graph
from .models import ItineraryInput


def _load_input(path: Path) -> ItineraryInput:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ItineraryInput.model_validate(raw)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TravelMate AI - generator planu podróży (LangGraph)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Ścieżka do pliku JSON z wymaganiami użytkownika.",
    )
    args = parser.parse_args()

    request = _load_input(args.input)

    app = build_graph()
    result = app.invoke(
        {
            "request": request,
            "profile_summary": "",
            "geo_output": None,
            "itinerary_draft": None,
            "verification": None,
            "final_markdown": "",
        }
    )

    print(result["final_markdown"])


if __name__ == "__main__":
    main()
