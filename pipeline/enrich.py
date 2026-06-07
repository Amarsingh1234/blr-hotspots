from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from pipeline.models import CanonicalEvent

IST = timezone(timedelta(hours=5, minutes=30))

# Rough Bangalore neighborhood centroids for tagging when reverse geocode isn't available.
NEIGHBORHOOD_ANCHORS: dict[str, tuple[float, float]] = {
    "indiranagar": (12.9784, 77.6408),
    "koramangala": (12.9352, 77.6245),
    "hsr": (12.9116, 77.6389),
    "whitefield": (12.9698, 77.7500),
    "jayanagar": (12.9250, 77.5938),
    "mg-road": (12.9750, 77.6063),
    "malleshwaram": (13.0035, 77.5647),
}


def _parse_start(start_at: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt
    except ValueError:
        return None


def tag_neighborhood(lat: float | None, lon: float | None) -> str | None:
    if lat is None or lon is None:
        return None
    best_name = None
    best_dist = float("inf")
    for name, (nlat, nlon) in NEIGHBORHOOD_ANCHORS.items():
        d = math.dist((lat, lon), (nlat, nlon))
        if d < best_dist:
            best_dist = d
            best_name = name
    if best_dist <= 0.035:  # ~3.5 km
        return best_name
    return None


def recency_boost(start_at: str, now: datetime | None = None) -> float:
    now = now or datetime.now(tz=IST)
    start = _parse_start(start_at)
    if not start:
        return 0.3
    hours = (start - now).total_seconds() / 3600
    if hours < 0:
        return 0.0
    if 2 <= hours <= 8:
        return 1.0
    if 0 <= hours < 2:
        return 0.85
    if 8 < hours <= 24:
        return 0.7
    if 24 < hours <= 72:
        return 0.5
    return 0.25


def category_demand_boost(category: str, start_at: str) -> float:
    start = _parse_start(start_at)
    if not start:
        return 0.5
    weekend = start.weekday() >= 4  # Fri/Sat/Sun
    if category in {"comedy", "music", "party"} and weekend:
        return 1.0
    if category in {"workshop", "tech", "art"} and not weekend:
        return 0.8
    return 0.55


def venue_popularity_boost(event_count_30d: int) -> float:
    if event_count_30d >= 20:
        return 1.0
    if event_count_30d >= 8:
        return 0.75
    if event_count_30d >= 3:
        return 0.55
    return 0.35


def cluster_density_boost(lat: float | None, lon: float | None, peers: list[tuple[float, float]]) -> float:
    if lat is None or lon is None:
        return 0.2
    count = 0
    for plat, plon in peers:
        # ~1 km box check using crude degree delta
        if abs(plat - lat) <= 0.009 and abs(plon - lon) <= 0.009:
            count += 1
    if count >= 6:
        return 1.0
    if count >= 3:
        return 0.7
    if count >= 1:
        return 0.45
    return 0.2


def compute_hotspot_score(
    event: CanonicalEvent,
    *,
    venue_event_count_30d: int = 0,
    peer_coords: list[tuple[float, float]] | None = None,
) -> float:
    peer_coords = peer_coords or []
    score = (
        0.35 * recency_boost(event.start_at)
        + 0.25 * venue_popularity_boost(venue_event_count_30d)
        + 0.20 * category_demand_boost(event.category, event.start_at)
        + 0.10 * min(1.0, event.confidence)
        + 0.10
        * cluster_density_boost(
            event.venue.lat if event.venue else None,
            event.venue.lon if event.venue else None,
            peer_coords,
        )
    )
    return round(min(1.0, max(0.0, score)), 4)


def enrich_events(events: list[CanonicalEvent]) -> list[CanonicalEvent]:
    coords = [
        (e.venue.lat, e.venue.lon)
        for e in events
        if e.venue and e.venue.lat is not None and e.venue.lon is not None
    ]

    venue_counts: dict[str, int] = defaultdict(int)
    for event in events:
        if event.venue_id:
            venue_counts[event.venue_id] += 1

    for event in events:
        if event.venue:
            hood = tag_neighborhood(event.venue.lat, event.venue.lon)
            if hood:
                event.venue.neighborhood = hood
        event.hotspot_score = compute_hotspot_score(
            event,
            venue_event_count_30d=venue_counts.get(event.venue_id or "", 0),
            peer_coords=coords,
        )
    return events
