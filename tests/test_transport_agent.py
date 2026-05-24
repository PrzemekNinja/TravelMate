from __future__ import annotations

import unittest
from unittest.mock import patch

from travelmate.agents.transport_agent import _build_baggage_summary, transport_agent
from travelmate.models import BaggageItem, Budget, ItineraryInput, Pace


class _RaisingModel:
    def invoke(self, _messages):
        raise RuntimeError("boom")


class TransportAgentTests(unittest.TestCase):
    def test_build_baggage_summary_aggregates_weight_and_pieces(self) -> None:
        request = ItineraryInput(
            destination="Lizbona",
            days=5,
            budget=Budget.MID,
            pace=Pace.MODERATE,
            participants=2,
            baggage=[
                BaggageItem(owner="A", pieces=1, height_cm=55, width_cm=40, depth_cm=20, weight_kg=8),
                BaggageItem(owner="B", pieces=2, height_cm=70, width_cm=45, depth_cm=30, weight_kg=18),
            ],
        )
        state = {
            "request": request,
            "profile_summary": "profil",
            "transport_report": "",
            "geo_output": None,
            "itinerary_draft": None,
            "verification": None,
            "final_markdown": "",
        }

        summary = _build_baggage_summary(state)  # type: ignore[arg-type]

        self.assertEqual(summary["pieces"], 3)
        self.assertEqual(summary["weight_kg"], 44)
        self.assertEqual(len(summary["details"]), 2)

    @patch("travelmate.agents.transport_agent.get_chat_model", return_value=_RaisingModel())
    def test_transport_agent_uses_fallback_on_model_error(self, _mock_model) -> None:
        request = ItineraryInput(
            destination="Paryż",
            days=3,
            budget=Budget.MID,
            pace=Pace.MODERATE,
            home_location="Warszawa",
            participants=2,
        )
        state = {
            "request": request,
            "profile_summary": "Rodzina z dziećmi",
            "transport_report": "",
            "geo_output": None,
            "itinerary_draft": None,
            "verification": None,
            "final_markdown": "",
        }

        result = transport_agent(state)  # type: ignore[arg-type]

        self.assertIn("RAPORT TRANSPORTOWY", result["transport_report"])
        self.assertIn("Propozycja 1: Loty", result["transport_report"])


if __name__ == "__main__":
    unittest.main()
