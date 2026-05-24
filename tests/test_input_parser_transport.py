from __future__ import annotations

import unittest

from travelmate.tools.input_parser import parse_user_input_to_request_with_metadata


class InputParserTransportFieldsTests(unittest.TestCase):
    def test_parses_transport_fields_from_json(self) -> None:
        parsed = parse_user_input_to_request_with_metadata(
            """
{
  "destination": "Rzym",
  "days": 4,
  "budget": "Mid",
  "pace": "Moderate",
  "home_location": "Kraków",
  "travel_start_date": "2026-07-10",
  "travel_end_date": "2026-07-14",
  "participants": 2,
  "baggage": [
    {"owner": "A", "pieces": 1, "height_cm": 55, "width_cm": 40, "depth_cm": 20, "weight_kg": 8}
  ]
}
""".strip()
        )

        self.assertEqual(parsed.request.home_location, "Kraków")
        self.assertEqual(parsed.request.participants, 2)
        self.assertEqual(len(parsed.request.baggage), 1)
        self.assertEqual(parsed.request.baggage[0].weight_kg, 8)

    def test_parses_transport_fields_from_key_value(self) -> None:
        parsed = parse_user_input_to_request_with_metadata(
            "\n".join(
                [
                    "destination: Barcelona",
                    "days: 3",
                    "budget: Mid",
                    "pace: Moderate",
                    "home_location: Łódź",
                    "participants: 3",
                    "travel_start_date: 2026-08-01",
                    "travel_end_date: 2026-08-04",
                    "baggage: [{\"owner\":\"A\",\"pieces\":2,\"height_cm\":55,\"width_cm\":40,\"depth_cm\":20,\"weight_kg\":10}]",
                ]
            )
        )

        self.assertEqual(parsed.request.destination, "Barcelona")
        self.assertEqual(parsed.request.home_location, "Łódź")
        self.assertEqual(parsed.request.participants, 3)
        self.assertEqual(parsed.request.baggage[0].pieces, 2)


if __name__ == "__main__":
    unittest.main()
