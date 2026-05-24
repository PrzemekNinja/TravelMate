from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, model_validator


class Budget(str, Enum):
    LOW = "Low"
    MID = "Mid"
    LUXURY = "Luxury"


class Pace(str, Enum):
    RELAXED = "Relaxed"
    MODERATE = "Moderate"
    INTENSE = "Intense"


class BaggageItem(BaseModel):
    owner: str | None = None
    pieces: int = Field(1, ge=1, le=10)
    height_cm: float = Field(..., gt=0)
    width_cm: float = Field(..., gt=0)
    depth_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)


class ItineraryInput(BaseModel):
    destination: str = Field(..., min_length=2)
    days: int = Field(..., ge=1, le=14)
    budget: Budget
    pace: Pace
    home_location: str | None = None
    travel_start_date: date | None = None
    travel_end_date: date | None = None
    participants: int = Field(1, ge=1, le=30)
    baggage: list[BaggageItem] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    accommodation_area: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "ItineraryInput":
        if self.travel_start_date and self.travel_end_date and self.travel_end_date < self.travel_start_date:
            raise ValueError("travel_end_date nie może być wcześniejsza niż travel_start_date")
        return self


class GeoCoordinates(BaseModel):
    lat: float | None = None
    lng: float | None = None


class GeoAddress(BaseModel):
    country: str = ""
    city: str = ""
    postcode: str = ""
    street: str = ""
    building_number: str = ""


class GeoPlace(BaseModel):
    name: str
    coordinates: GeoCoordinates
    address: GeoAddress
    website: str = ""
    tripadvisor_url: str = ""
    tripadvisor_rating: float | None = None
    tripadvisor_photo_url: str = ""
    tripadvisor_location_id: str = ""
    source: str = "here"


class GeoDayDraft(BaseModel):
    day: int
    title: str
    morning_zone: str
    afternoon_zone: str
    evening_zone: str


class GeoOutputDraft(BaseModel):
    mobility_strategy: str
    days: list[GeoDayDraft]


class GeoDay(BaseModel):
    day: int
    title: str
    morning_zone: GeoPlace
    afternoon_zone: GeoPlace
    evening_zone: GeoPlace


class GeoOutput(BaseModel):
    mobility_strategy: str
    days: list[GeoDay]


class ActivityEntry(BaseModel):
    start: str
    end: str
    name: str
    why: str | None = None
    tip: str | None = None
    description: str | None = None
    logistics: str | None = None


class MealEntry(BaseModel):
    meal_type: Literal["lunch", "dinner"]
    time: str
    name: str
    cuisine: str
    price: Literal["$", "$$", "$$$"]
    address_or_location: str
    note: str | None = None
    ambience: str | None = None


class LodgingEntry(BaseModel):
    name: str
    area: str
    price: Literal["$", "$$", "$$$"]
    check_in: str | None = None
    check_out: str | None = None
    note: str | None = None


class DayPlan(BaseModel):
    day: int
    area_title: str
    morning_activities: list[ActivityEntry]
    lunch: MealEntry
    afternoon_activities: list[ActivityEntry]
    dinner: MealEntry
    lodging: LodgingEntry | None = None


class ItineraryDraft(BaseModel):
    days: list[DayPlan]
    estimated_ticket_cost: str


class VerificationOutput(BaseModel):
    opening_hours_warnings: list[str] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)


class PlannerState(TypedDict):
    request: ItineraryInput
    profile_markdown: str
    profile_summary: str
    transport_markdown: str
    transport_report: str
    geo_markdown: str
    geo_output: GeoOutput
    itinerary_markdown: str
    itinerary_draft: ItineraryDraft
    verification_markdown: str
    verification: VerificationOutput
    final_markdown: str
