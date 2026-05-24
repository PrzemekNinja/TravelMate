from __future__ import annotations

import unittest

from travelmate.tools.markdown_contract import (
    parse_geo_markdown,
    parse_itinerary_markdown,
    parse_verification_markdown,
)


class MarkdownContractTests(unittest.TestCase):
    def test_parse_geo_markdown(self) -> None:
        markdown = """
# GEO PLAN
## Mobility Strategy
- Metro + walking

## Day 1: Historic Core
- Morning Zone: Louvre Museum
- Afternoon Zone: Tuileries Garden
- Evening Zone: Le Marais

## Day 2: Riverside
- Morning Zone: Musée d'Orsay
- Afternoon Zone: Saint-Germain-des-Prés
- Evening Zone: Seine River Cruise
""".strip()

        result = parse_geo_markdown(markdown, expected_days=2)
        self.assertEqual(result.mobility_strategy, "Metro + walking")
        self.assertEqual(len(result.days), 2)
        self.assertEqual(result.days[0].morning_zone, "Louvre Museum")

    def test_parse_itinerary_markdown(self) -> None:
        markdown = """
# ITINERARY DRAFT
## Estimated Ticket Cost
- Value: ~120 EUR

## Day 1: Historic Core
### Morning Activities
- ACTIVITY | start=09:00 | end=11:30 | name=Louvre Museum | why=Iconic collection | tip=Book online | description=Major highlights | logistics=Metro line 1

### Lunch
- MEAL | type=lunch | time=12:30 | name=Cafe Rivoli | cuisine=French | price=$$ | location=Near Louvre | note=Reservation advised | ambience=Casual

### Afternoon Activities
- ACTIVITY | start=14:00 | end=16:30 | name=Tuileries Garden | why=Relaxed walk | tip=Bring water | description=Open-air break | logistics=Walk 10 min

### Dinner
- MEAL | type=dinner | time=19:00 | name=Bistro Central | cuisine=French | price=$$ | location=Le Marais | note=Try set menu | ambience=Cozy

### Lodging
- LODGING | name=Hotel Marais | area=Le Marais | price=$$ | check_in=15:00 | check_out=11:00 | note=Close to metro
""".strip()

        result = parse_itinerary_markdown(markdown)
        self.assertEqual(result.estimated_ticket_cost, "~120 EUR")
        self.assertEqual(len(result.days), 1)
        self.assertEqual(result.days[0].lunch.name, "Cafe Rivoli")
        self.assertIsNotNone(result.days[0].lodging)

    def test_parse_verification_markdown(self) -> None:
        markdown = """
# VERIFICATION REPORT
## Opening Hours Warnings
- Museum closing time requires external verification

## Adjustments
- Move dinner 30 minutes later to avoid overlap
""".strip()

        result = parse_verification_markdown(markdown)
        self.assertEqual(len(result.opening_hours_warnings), 1)
        self.assertEqual(len(result.adjustments), 1)


if __name__ == "__main__":
    unittest.main()
