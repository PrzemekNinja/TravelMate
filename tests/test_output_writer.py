from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from travelmate.models import (
    ActivityEntry,
    Budget,
    DayPlan,
    GeoAddress,
    GeoCoordinates,
    GeoDay,
    GeoOutput,
    GeoPlace,
    ItineraryDraft,
    ItineraryInput,
    LodgingEntry,
    MealEntry,
    Pace,
)
from travelmate.tools.output_writer import save_itinerary_output


class OutputWriterMapTests(unittest.TestCase):
    def test_save_output_creates_single_html_with_map_and_description(self) -> None:
        request = ItineraryInput(
            destination="Paryż",
            days=2,
            budget=Budget.MID,
            pace=Pace.MODERATE,
        )

        place_a = GeoPlace(
            name="Louvre Museum",
            coordinates=GeoCoordinates(lat=48.8606, lng=2.3376),
            address=GeoAddress(country="France", city="Paris", street="Rue de Rivoli", building_number="99"),
            website="https://www.louvre.fr",
            tripadvisor_url="https://www.tripadvisor.com/Attraction_Review-g187147-d188150-Reviews-Louvre_Museum-Paris_Ile_de_France.html",
            tripadvisor_rating=4.7,
            tripadvisor_photo_url="https://dynamic-media-cdn.tripadvisor.com/media/photo-o/example-louvre.jpg",
            source="here",
        )
        place_b = GeoPlace(
            name="Eiffel Tower",
            coordinates=GeoCoordinates(lat=48.8584, lng=2.2945),
            address=GeoAddress(country="France", city="Paris", street="Champ de Mars", building_number="5"),
            website="www.toureiffel.paris",
            source="here",
        )

        geo_output = GeoOutput(
            mobility_strategy="Spacer + metro",
            days=[
                GeoDay(
                    day=1,
                    title="Centrum",
                    morning_zone=place_a,
                    afternoon_zone=place_b,
                    evening_zone=place_a,
                ),
                GeoDay(
                    day=2,
                    title="Prawy brzeg",
                    morning_zone=place_b,
                    afternoon_zone=place_a,
                    evening_zone=place_b,
                ),
            ],
        )

        itinerary_draft = ItineraryDraft(
            days=[
                DayPlan(
                    day=1,
                    area_title="Centrum",
                    morning_activities=[ActivityEntry(start="09:00", end="11:30", name="Louvre Museum")],
                    lunch=MealEntry(
                        meal_type="lunch",
                        time="12:30",
                        name="Lunch test",
                        cuisine="French",
                        price="$$",
                        address_or_location="Paris",
                    ),
                    afternoon_activities=[ActivityEntry(start="14:00", end="16:00", name="Eiffel Tower")],
                    dinner=MealEntry(
                        meal_type="dinner",
                        time="19:00",
                        name="Dinner test",
                        cuisine="French",
                        price="$$",
                        address_or_location="Paris",
                    ),
                    lodging=LodgingEntry(
                        name="Hotel Lumiere",
                        area="Le Marais",
                        price="$$",
                        check_in="15:00",
                        check_out="11:00",
                        note="Cichy hotel w centrum.",
                    ),
                )
                ,
                DayPlan(
                    day=2,
                    area_title="Prawy brzeg",
                    morning_activities=[ActivityEntry(start="09:30", end="11:00", name="Eiffel Tower")],
                    lunch=MealEntry(
                        meal_type="lunch",
                        time="12:30",
                        name="Lunch test 2",
                        cuisine="French",
                        price="$$",
                        address_or_location="Paris",
                    ),
                    afternoon_activities=[ActivityEntry(start="14:00", end="16:00", name="Louvre Museum")],
                    dinner=MealEntry(
                        meal_type="dinner",
                        time="19:00",
                        name="Dinner test 2",
                        cuisine="French",
                        price="$$",
                        address_or_location="Paris",
                    ),
                    lodging=LodgingEntry(
                        name="Hotel Lumiere",
                        area="Le Marais",
                        price="$$",
                        check_in="15:00",
                        check_out="11:00",
                        note="Cichy hotel w centrum.",
                    ),
                )
            ],
            estimated_ticket_cost="n/a",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            html_path = save_itinerary_output(
                request=request,
                markdown_plan="## Test plan",
                geo_output=geo_output,
                itinerary_draft=itinerary_draft,
                output_root=Path(tmp_dir),
            )

            self.assertTrue(html_path.exists())

            map_path = html_path.parent / "map.html"
            self.assertFalse(map_path.exists())

            merged_html = html_path.read_text(encoding="utf-8")
            self.assertIn("Plan podróży + mapa POI", merged_html)
            self.assertIn("Noclegi:", merged_html)
            self.assertIn("id=\"map\"", merged_html)
            self.assertIn("Opis wycieczki", merged_html)
            self.assertIn("## Test plan", merged_html)
            self.assertIn("Louvre Museum", merged_html)
            self.assertIn("Eiffel Tower", merged_html)
            self.assertIn("tripadvisor_url", merged_html)
            self.assertIn("tripadvisor_rating", merged_html)
            self.assertIn("tripadvisor_photo_url", merged_html)
            self.assertIn("TripAdvisor rating:", merged_html)
            self.assertIn("example-louvre.jpg", merged_html)
            self.assertIn("poi-tripadvisor-link", merged_html)
            self.assertIn("poi-tripadvisor-photo", merged_html)
            self.assertIn("TripAdvisor ↗", merged_html)
            self.assertIn("Hotel Lumiere", merged_html)
            self.assertIn("Le Marais", merged_html)
            self.assertIn("point_type\": \"lodging\"", merged_html)
            self.assertEqual(merged_html.count("point_type\": \"lodging\""), 1)
            self.assertIn("to_lodging", merged_html)
            self.assertIn("from_lodging", merged_html)
            self.assertIn("Dojazd do noclegu", merged_html)
            self.assertIn("Wyjazd z noclegu", merged_html)
            self.assertIn("🏨", merged_html)
            self.assertIn("48.8606", merged_html)
            self.assertIn("2.2945", merged_html)
            self.assertIn("id=\"day-filters\"", merged_html)
            self.assertIn("day-filter-btn", merged_html)
            self.assertIn("L.marker", merged_html)
            self.assertIn("colorForDay", merged_html)
            self.assertIn("focusPoint", merged_html)
            self.assertIn("poi-point-", merged_html)
            self.assertIn("routeSegments", merged_html)
            self.assertIn("L.polyline", merged_html)
            self.assertIn("inferTransportOptions", merged_html)
            self.assertIn("estimateTravel", merged_html)
            self.assertIn("const normalizeExternalUrl = (value) =>", merged_html)
            self.assertIn("const websiteUrl = normalizeExternalUrl(point.website);", merged_html)
            self.assertIn("const popupWebsite = websiteUrl ?", merged_html)
            self.assertNotIn("href=\"${point.website}\"", merged_html)


if __name__ == "__main__":
    unittest.main()
