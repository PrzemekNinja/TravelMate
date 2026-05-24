from __future__ import annotations

import unittest

from travelmate.agents.itinerary_agent import _build_lodging_preferences
from travelmate.models import Budget, ItineraryInput, Pace


class ItineraryAgentLodgingStrategyTests(unittest.TestCase):
    def test_lodging_preferences_prioritize_area_and_hard_constraints(self) -> None:
        request = ItineraryInput(
            destination="Paryż",
            days=3,
            budget=Budget.MID,
            pace=Pace.MODERATE,
            constraints=[
                "Musi być parking",
                "Śniadanie mile widziane",
                "quiet neighborhood",
            ],
            accommodation_area="Le Marais",
        )
        state = {
            "request": request,
            "profile_summary": "",
            "transport_report": "",
            "geo_output": None,
            "itinerary_draft": None,
            "verification": None,
            "final_markdown": "",
        }

        preferences = _build_lodging_preferences(state)  # type: ignore[arg-type]

        self.assertGreaterEqual(len(preferences["hard_requirements"]), 2)
        self.assertEqual(preferences["hard_requirements"][0], "Obszar noclegu: Le Marais")
        self.assertIn("Musi być parking", preferences["hard_requirements"])
        self.assertIn("quiet neighborhood", preferences["hard_requirements"])
        self.assertIn("Śniadanie mile widziane", preferences["soft_requirements"])
        self.assertTrue(preferences["priority_order"][0].startswith("1) hard_requirements"))

    def test_lodging_preferences_without_constraints(self) -> None:
        request = ItineraryInput(
            destination="Warszawa",
            days=2,
            budget=Budget.LOW,
            pace=Pace.RELAXED,
            constraints=[],
            accommodation_area=None,
        )
        state = {
            "request": request,
            "profile_summary": "",
            "transport_report": "",
            "geo_output": None,
            "itinerary_draft": None,
            "verification": None,
            "final_markdown": "",
        }

        preferences = _build_lodging_preferences(state)  # type: ignore[arg-type]

        self.assertEqual(preferences["hard_requirements"], [])
        self.assertEqual(preferences["soft_requirements"], [])
        self.assertIn("Najpierw odrzuć", preferences["selection_policy"])


if __name__ == "__main__":
    unittest.main()
