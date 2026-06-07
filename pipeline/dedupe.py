from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def round_coord(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "na"
    return f"{round(value, digits):.{digits}f}"


def event_date_key(iso_start: str) -> str:
    return iso_start[:10] if iso_start else "unknown"


def make_dedupe_key(
    title: str,
    start_at: str,
    lat: float | None,
    lon: float | None,
    venue_name: str | None = None,
) -> str:
    parts = [
        normalize_title(title),
        event_date_key(start_at),
        round_coord(lat),
        round_coord(lon),
        normalize_title(venue_name or ""),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def title_similarity(a: str, b: str) -> float:
    """Simple token overlap ratio — good enough for MVP fuzzy dedupe hints."""
    ta = set(normalize_title(a).split())
    tb = set(normalize_title(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
