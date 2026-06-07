from __future__ import annotations

import json
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from db.store import EventStore

app = FastAPI(
    title="blr-hotspots API",
    description="Bangalore events and hotspot discovery",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = EventStore(os.getenv("BLR_DB_PATH", "data/blr_hotspots.db"))


def _serialize_event(row: dict[str, Any]) -> dict[str, Any]:
    vibe_tags = row.get("vibe_tags") or "[]"
    if isinstance(vibe_tags, str):
        vibe_tags = json.loads(vibe_tags)

    venue = None
    if row.get("venue_name"):
        venue = {
            "name": row["venue_name"],
            "address": row.get("venue_address"),
            "lat": row.get("venue_lat"),
            "lon": row.get("venue_lon"),
            "neighborhood": row.get("venue_neighborhood"),
        }

    return {
        "id": row["id"],
        "title": row["title"],
        "start_at": row["start_at"],
        "end_at": row.get("end_at"),
        "category": row["category"],
        "vibe_tags": vibe_tags,
        "description": row.get("description"),
        "image_url": row.get("image_url"),
        "price_min": row.get("price_min"),
        "price_max": row.get("price_max"),
        "is_free": bool(row.get("is_free")),
        "ticket_url": row.get("ticket_url"),
        "hotspot_score": row.get("hotspot_score"),
        "confidence": row.get("confidence"),
        "venue": venue,
        "distance_km": row.get("distance_km"),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/meta/categories")
def categories() -> dict[str, list[str]]:
    return {
        "categories": [
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
        ]
    }


def _top_category(categories_csv: str | None) -> str:
    if not categories_csv:
        return "other"
    counts: dict[str, int] = {}
    for category in categories_csv.split(","):
        key = category.strip()
        if key:
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return "other"
    return max(counts, key=counts.get)


def _serialize_hotspot(row: dict[str, Any]) -> dict[str, Any]:
    titles_blob = row.get("titles") or ""
    sample_titles = [t.strip() for t in titles_blob.split("|") if t.strip()][:3]
    neighborhoods = row.get("neighborhoods")
    neighborhood = None
    if isinstance(neighborhoods, str) and neighborhoods:
        neighborhood = neighborhoods.split(",")[0].strip() or None

    lat = float(row["lat"])
    lon = float(row["lon"])
    return {
        "id": f"cluster:{round(lat, 4)}:{round(lon, 4)}",
        "lat": lat,
        "lon": lon,
        "event_count": int(row["event_count"]),
        "score_sum": round(float(row["score_sum"] or 0), 4),
        "score_peak": round(float(row["score_peak"] or 0), 4),
        "top_category": _top_category(row.get("categories")),
        "neighborhood": neighborhood,
        "sample_titles": sample_titles,
    }


@app.get("/v1/hotspots")
def list_hotspots(
    from_at: str | None = Query(None, alias="from"),
    to_at: str | None = Query(None, alias="to"),
    category: str | None = Query(None, description="Comma-separated categories"),
    grid_km: float = Query(2.0, ge=0.5, le=20),
    limit: int = Query(80, ge=1, le=200),
) -> dict[str, Any]:
    categories = [c.strip() for c in category.split(",")] if category else None
    rows = store.list_hotspot_clusters(
        from_at=from_at,
        to_at=to_at,
        categories=categories,
        grid_km=grid_km,
        limit=limit,
    )
    hotspots = [_serialize_hotspot(r) for r in rows]
    return {"count": len(hotspots), "hotspots": hotspots}


@app.get("/v1/events")
def list_events(
    lat: float | None = Query(None, description="User latitude"),
    lon: float | None = Query(None, description="User longitude"),
    radius_km: float | None = Query(10.0, ge=0.5, le=100),
    from_at: str | None = Query(None, alias="from"),
    to_at: str | None = Query(None, alias="to"),
    category: str | None = Query(None, description="Comma-separated categories"),
    sort: str = Query("hotspot", pattern="^(hotspot|time|distance)$"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    categories = [c.strip() for c in category.split(",")] if category else None
    rows = store.list_events(
        from_at=from_at,
        to_at=to_at,
        categories=categories,
        lat=lat,
        lon=lon,
        radius_km=radius_km if lat is not None and lon is not None else None,
        sort=sort,
        limit=limit,
    )
    return {
        "count": len(rows),
        "events": [_serialize_event(r) for r in rows],
    }


@app.get("/v1/events/{event_id}")
def get_event(event_id: str) -> dict[str, Any]:
    row = store.get_event(event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    payload = _serialize_event(row)
    payload["sources"] = row.get("sources", [])
    return payload


def serve() -> None:
    # Default 8001 — port 8000 is commonly used by other local FastAPI apps.
    host = os.getenv("BLR_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", os.getenv("BLR_PORT", "8001")))
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    serve()
