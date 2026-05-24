from __future__ import annotations

import unittest

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
    VerificationOutput,
)
from travelmate.tools.markdown_formatter import build_geo_poi_section, build_markdown


class MarkdownFormatterGeoTests(unittest.TestCase):
    def test_geo_section_contains_required_address_format_and_fields(self) -> None:
        place = GeoPlace(
            name="Muzeum Testowe",
            coordinates=GeoCoordinates(lat=52.2297, lng=21.0122),
            address=GeoAddress(country="Polska", city="Warszawa", street="Krakowskie Przedmieście", building_number="15"),
            website="https://example.org",
            tripadvisor_url="https://www.tripadvisor.com/Attraction_Review-Example",
            tripadvisor_rating=4.6,
            tripadvisor_photo_url="https://dynamic-media-cdn.tripadvisor.com/media/photo-o/example.jpg",
        )
        geo_output = GeoOutput(
            mobility_strategy="Spacer",
            days=[
                GeoDay(
                    day=1,
                    title="Centrum",
                    morning_zone=place,
                    afternoon_zone=place,
                    evening_zone=place,
                )
            ],
        )

        section = build_geo_poi_section(geo_output)

        self.assertIn("### 📍 Metadane POI (geo)", section)
        self.assertIn("Współrzędne: 52.2297, 21.0122", section)
        self.assertIn("Strona WWW: https://example.org", section)
        self.assertIn("Adres: Polska, Warszawa, Krakowskie Przedmieście, 15", section)
        self.assertIn("TripAdvisor rating: 4.6/5", section)
        self.assertIn("TripAdvisor: https://www.tripadvisor.com/Attraction_Review-Example", section)
        self.assertIn("Foto (TripAdvisor): https://dynamic-media-cdn.tripadvisor.com/media/photo-o/example.jpg", section)

    def test_build_markdown_renders_lodging_block_when_present(self) -> None:
        place = GeoPlace(
            name="Muzeum Testowe",
            coordinates=GeoCoordinates(lat=52.2297, lng=21.0122),
            address=GeoAddress(country="Polska", city="Warszawa", street="Krakowskie Przedmieście", building_number="15"),
            website="https://example.org",
        )
        geo_output = GeoOutput(
            mobility_strategy="Spacer",
            days=[
                GeoDay(
                    day=1,
                    title="Centrum",
                    morning_zone=place,
                    afternoon_zone=place,
                    evening_zone=place,
                )
            ],
        )
        req = ItineraryInput(
            destination="Warszawa",
            days=1,
            budget=Budget.MID,
            pace=Pace.MODERATE,
        )
        draft = ItineraryDraft(
            days=[
                DayPlan(
                    day=1,
                    area_title="Centrum",
                    morning_activities=[ActivityEntry(start="09:00", end="11:00", name="Muzeum Testowe")],
                    lunch=MealEntry(
                        meal_type="lunch",
                        time="12:30",
                        name="Lunch Test",
                        cuisine="Polska",
                        price="$$",
                        address_or_location="Centrum",
                    ),
                    afternoon_activities=[ActivityEntry(start="14:00", end="16:00", name="Spacer po Starówce")],
                    dinner=MealEntry(
                        meal_type="dinner",
                        time="19:00",
                        name="Kolacja Test",
                        cuisine="Polska",
                        price="$$",
                        address_or_location="Centrum",
                    ),
                    lodging=LodgingEntry(
                        name="Hotel Test",
                        area="Śródmieście",
                        price="$$",
                        check_in="15:00",
                        check_out="11:00",
                        note="Blisko metra.",
                    ),
                )
            ],
            estimated_ticket_cost="100 PLN",
        )

        markdown = build_markdown(
            req=req,
            profile_summary="Profil testowy",
            transport_report="# RAPORT TRANSPORTOWY\n## Podsumowanie parametrów\n- Trasa: Dom -> Warszawa",
            mobility_strategy=geo_output.mobility_strategy,
            geo_output=geo_output,
            draft=draft,
            verification=VerificationOutput(),
        )

        self.assertIn("🏨 Nocleg: Hotel Test", markdown)
        self.assertIn("Obszar:** Śródmieście", markdown)
        self.assertIn("Check-in / Check-out:** 15:00 / 11:00", markdown)
        self.assertIn("Uwaga:** Blisko metra.", markdown)
        self.assertIn("### 🏨 Nocleg (quick view)", markdown)
        self.assertIn("| Hotel | Obszar | Cena | Dni | Check-in / Check-out |", markdown)
        self.assertIn("| Hotel Test | Śródmieście | $$ | 1 | 15:00 / 11:00 |", markdown)
        self.assertIn("### 🚐 Raport transportowy", markdown)
        self.assertIn("# RAPORT TRANSPORTOWY", markdown)
        self.assertIn("#### 🏨 Noclegi (POI)", markdown)
        self.assertIn("Dni planu: 1", markdown)

    def test_geo_poi_section_groups_same_hotel_once(self) -> None:
        place = GeoPlace(
            name="Muzeum Testowe",
            coordinates=GeoCoordinates(lat=52.2297, lng=21.0122),
            address=GeoAddress(country="Polska", city="Warszawa", street="Krakowskie Przedmieście", building_number="15"),
            website="https://example.org",
        )
        geo_output = GeoOutput(
            mobility_strategy="Spacer",
            days=[
                GeoDay(day=1, title="Centrum", morning_zone=place, afternoon_zone=place, evening_zone=place),
                GeoDay(day=2, title="Praga", morning_zone=place, afternoon_zone=place, evening_zone=place),
            ],
        )
        draft = ItineraryDraft(
            days=[
                DayPlan(
                    day=1,
                    area_title="Centrum",
                    morning_activities=[ActivityEntry(start="09:00", end="10:00", name="Muzeum Testowe")],
                    lunch=MealEntry(meal_type="lunch", time="12:00", name="Lunch", cuisine="PL", price="$$", address_or_location="Centrum"),
                    afternoon_activities=[ActivityEntry(start="14:00", end="15:00", name="Spacer")],
                    dinner=MealEntry(meal_type="dinner", time="19:00", name="Kolacja", cuisine="PL", price="$$", address_or_location="Centrum"),
                    lodging=LodgingEntry(name="Hotel Wspólny", area="Śródmieście", price="$$", check_in="15:00", check_out="11:00"),
                ),
                DayPlan(
                    day=2,
                    area_title="Praga",
                    morning_activities=[ActivityEntry(start="09:00", end="10:00", name="Muzeum Testowe")],
                    lunch=MealEntry(meal_type="lunch", time="12:00", name="Lunch", cuisine="PL", price="$$", address_or_location="Praga"),
                    afternoon_activities=[ActivityEntry(start="14:00", end="15:00", name="Spacer")],
                    dinner=MealEntry(meal_type="dinner", time="19:00", name="Kolacja", cuisine="PL", price="$$", address_or_location="Praga"),
                    lodging=LodgingEntry(name="Hotel Wspólny", area="Śródmieście", price="$$", check_in="15:00", check_out="11:00"),
                ),
            ],
            estimated_ticket_cost="100 PLN",
        )

        section = build_geo_poi_section(geo_output, draft=draft)

        self.assertIn("#### 🏨 Noclegi (POI)", section)
        self.assertEqual(section.count("**Hotel Wspólny**"), 1)
        self.assertIn("Dni planu: 1, 2", section)


if __name__ == "__main__":
    unittest.main()
