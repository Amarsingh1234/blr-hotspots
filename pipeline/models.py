from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CATEGORIES = {
    "music",
    "comedy",
    "games",
    "workshop",
    "sports",
    "food",
    "art",
    "party",
    "tech",
    "theater",
    "other",
}

SCHEMA_TYPE_TO_CATEGORY = {
    "MusicEvent": "music",
    "ComedyEvent": "comedy",
    "SportsEvent": "sports",
    "FoodEvent": "food",
    "EducationEvent": "workshop",
    "LiteraryEvent": "art",
    "TheaterEvent": "theater",
    "ScreeningEvent": "art",
    "SocialEvent": "party",
    "Event": "other",
}


@dataclass
class Venue:
    id: str
    name: str
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    neighborhood: str | None = None
    city: str = "Bengaluru"
    venue_type: str | None = None


@dataclass
class Organizer:
    id: str
    name: str
    url: str | None = None


@dataclass
class SourceRef:
    id: str
    name: str
    type: str
    base_url: str | None
    confidence_base: float
    source_event_id: str
    source_url: str
    fetched_at: str
    raw_payload: dict[str, Any] | None = None


@dataclass
class CanonicalEvent:
    id: str
    title: str
    slug: str
    start_at: str
    end_at: str | None
    timezone: str
    description: str | None
    image_url: str | None
    category: str
    vibe_tags: list[str] = field(default_factory=list)
    price_min: int | None = None
    price_max: int | None = None
    is_free: bool = False
    ticket_url: str | None = None
    status: str = "scheduled"
    confidence: float = 0.8
    hotspot_score: float = 0.0
    schema_type: str | None = None
    venue_id: str | None = None
    organizer_id: str | None = None
    dedupe_key: str = ""
    venue: Venue | None = None
    organizer: Organizer | None = None
