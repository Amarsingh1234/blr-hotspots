from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pipeline.dedupe import make_dedupe_key
from pipeline.models import (
    CATEGORIES,
    SCHEMA_TYPE_TO_CATEGORY,
    CanonicalEvent,
    Organizer,
    Venue,
)

KEYWORD_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("comedy", ["standup", "stand-up", "stand up", "comedy", "open mic", "open-mic"]),
    ("music", ["concert", "gig", "dj", "live music", "acoustic", "band", "festival"]),
    ("games", ["board game", "chess", "esports", "gaming", "quiz"]),
    ("workshop", ["workshop", "masterclass", "training", "class", "bootcamp"]),
    ("sports", ["run", "marathon", "cycling", "trek", "hike", "fitness", "yoga"]),
    ("food", ["brunch", "food", "tasting", "brew", "coffee"]),
    ("art", ["exhibition", "gallery", "screening", "film", "poetry", "literary"]),
    ("party", ["party", "night", "carnival", "club", "pub crawl"]),
    ("tech", ["meetup", "hackathon", "developer", "startup", "tech talk"]),
    ("theater", ["play", "theatre", "theater", "drama"]),
]

FREE_KEYWORDS = ["free", "rsvp", "no ticket", "open to all"]
PAID_PLATFORM_HOSTS = {
    "insider.in",
    "district.in",
    "highape.com",
    "skillboxes.com",
    "bookmyshow.com",
    "townscript.com",
    "allevents.in",
}


def slugify(title: str, start_at: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    date_part = start_at[:10] if start_at else "undated"
    return f"{base}-{date_part}"[:120]


def stable_id_from_url(url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


def _text_blob(event: dict[str, Any]) -> str:
    parts = [
        str(event.get("name") or event.get("title") or ""),
        str(event.get("description") or ""),
        " ".join(event.get("keywords") or []),
    ]
    return " ".join(parts).lower()


def infer_category(event: dict[str, Any]) -> str:
    schema_type = str(event.get("@type") or "Event")
    if schema_type in SCHEMA_TYPE_TO_CATEGORY:
        category = SCHEMA_TYPE_TO_CATEGORY[schema_type]
        if category != "other":
            return category

    blob = _text_blob(event)
    for category, keywords in KEYWORD_CATEGORY_RULES:
        if any(kw in blob for kw in keywords):
            return category
    return "other"


def infer_vibe_tags(event: dict[str, Any], category: str) -> list[str]:
    blob = _text_blob(event)
    tags: list[str] = []
    if any(kw in blob for kw in FREE_KEYWORDS):
        tags.append("free")
    if category in {"party", "music", "comedy"}:
        tags.append("nightlife")
    if category == "workshop":
        tags.append("learning")
    if "outdoor" in blob or "park" in blob or "trek" in blob:
        tags.append("outdoors")
    if "family" in blob or "kids" in blob:
        tags.append("family")
    return sorted(set(tags))


def parse_location(event: dict[str, Any]) -> Venue | None:
    location = event.get("location")
    if not isinstance(location, dict):
        return None

    name = location.get("name") or location.get("address") or "Venue TBD"
    address = location.get("address")
    if isinstance(address, dict):
        parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
        ]
        address = ", ".join(p for p in parts if p)

    lat = lon = None
    geo = location.get("geo")
    if isinstance(geo, dict):
        lat = _to_float(geo.get("latitude"))
        lon = _to_float(geo.get("longitude"))

    venue_id = stable_id_from_url(f"venue:{name}:{lat}:{lon}")
    return Venue(
        id=venue_id,
        name=str(name),
        address=str(address) if address else None,
        lat=lat,
        lon=lon,
        city="Bengaluru",
    )


def parse_organizer(event: dict[str, Any]) -> Organizer | None:
    organizer = event.get("organizer")
    if not isinstance(organizer, dict):
        return None
    name = organizer.get("name")
    if not name:
        return None
    url = organizer.get("url") or organizer.get("sameAs")
    org_id = stable_id_from_url(f"organizer:{name}:{url or ''}")
    return Organizer(id=org_id, name=str(name), url=url)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pick_ticket_url(event: dict[str, Any], fallback_url: str) -> str:
    for key in ("url", "sameAs"):
        val = event.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    offers = event.get("offers")
    if isinstance(offers, dict):
        offer_url = offers.get("url")
        if isinstance(offer_url, str):
            return offer_url
    if isinstance(offers, list):
        for offer in offers:
            if isinstance(offer, dict) and isinstance(offer.get("url"), str):
                return offer["url"]
    return fallback_url


def source_confidence_boost(source_url: str, base: float) -> float:
    host = urlparse(source_url).netloc.removeprefix("www.")
    if host in PAID_PLATFORM_HOSTS:
        return min(0.98, base + 0.08)
    return base


def normalize_schema_event(
    payload: dict[str, Any],
    *,
    source_url: str,
    source_confidence: float,
    fetched_at: str,
) -> CanonicalEvent | None:
    title = payload.get("name") or payload.get("title")
    start_at = payload.get("startDate") or payload.get("start_at")
    if not title or not start_at:
        return None

    end_at = payload.get("endDate") or payload.get("end_at")
    venue = parse_location(payload)
    organizer = parse_organizer(payload)
    category = infer_category(payload)
    vibe_tags = infer_vibe_tags(payload, category)

    ticket_url = pick_ticket_url(payload, source_url)
    is_free = "free" in vibe_tags

    confidence = source_confidence_boost(source_url, source_confidence)
    if venue and venue.lat is not None and venue.lon is not None:
        confidence = min(0.99, confidence + 0.03)
    else:
        confidence = max(0.4, confidence - 0.15)

    dedupe_key = make_dedupe_key(
        str(title),
        str(start_at),
        venue.lat if venue else None,
        venue.lon if venue else None,
        venue.name if venue else None,
    )

    # Canonical ID derived from dedupe key so cross-source merges stay stable.
    event_id = stable_id_from_url(f"event:{dedupe_key}")
    return CanonicalEvent(
        id=event_id,
        title=str(title).strip(),
        slug=slugify(str(title), str(start_at)),
        start_at=str(start_at),
        end_at=str(end_at) if end_at else None,
        timezone="Asia/Kolkata",
        description=(str(payload.get("description")).strip() if payload.get("description") else None),
        image_url=payload.get("image") if isinstance(payload.get("image"), str) else None,
        category=category if category in CATEGORIES else "other",
        vibe_tags=vibe_tags,
        is_free=is_free,
        ticket_url=ticket_url,
        status="scheduled",
        confidence=confidence,
        schema_type=str(payload.get("@type") or "Event"),
        dedupe_key=dedupe_key,
        venue=venue,
        organizer=organizer,
        venue_id=venue.id if venue else None,
        organizer_id=organizer.id if organizer else None,
    )


def is_future_event(start_at: str, *, now: datetime | None = None) -> bool:
    now = now or datetime.now().astimezone()
    try:
        dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return True
        return dt >= now.replace(hour=0, minute=0, second=0, microsecond=0) - __import__(
            "datetime"
        ).timedelta(hours=6)
    except ValueError:
        return True
