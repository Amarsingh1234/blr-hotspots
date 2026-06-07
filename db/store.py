from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pipeline.models import CanonicalEvent, Organizer, SourceRef, Venue

DEFAULT_DB_PATH = Path("data/blr_hotspots.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class EventStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        sql = SCHEMA_PATH.read_text()
        with self.connect() as conn:
            conn.executescript(sql)
            conn.commit()

    def ensure_source(self, source: SourceRef) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sources (id, name, type, base_url, confidence_base)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    type = excluded.type,
                    base_url = excluded.base_url,
                    confidence_base = excluded.confidence_base
                """,
                (source.id, source.name, source.type, source.base_url, source.confidence_base),
            )
            conn.commit()

    def upsert_venue(self, venue: Venue) -> str:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO venues (id, name, address, lat, lon, neighborhood, city, venue_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    address = COALESCE(excluded.address, venues.address),
                    lat = COALESCE(excluded.lat, venues.lat),
                    lon = COALESCE(excluded.lon, venues.lon),
                    neighborhood = COALESCE(excluded.neighborhood, venues.neighborhood),
                    venue_type = COALESCE(excluded.venue_type, venues.venue_type),
                    updated_at = datetime('now')
                """,
                (
                    venue.id,
                    venue.name,
                    venue.address,
                    venue.lat,
                    venue.lon,
                    venue.neighborhood,
                    venue.city,
                    venue.venue_type,
                ),
            )
            conn.commit()
        return venue.id

    def upsert_organizer(self, organizer: Organizer | None) -> str | None:
        if organizer is None:
            return None
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO organizers (id, name, url)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    url = COALESCE(excluded.url, organizers.url)
                """,
                (organizer.id, organizer.name, organizer.url),
            )
            conn.commit()
        return organizer.id

    def upsert_event(self, event: CanonicalEvent, source: SourceRef) -> str:
        vibe_tags = json.dumps(event.vibe_tags)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    id, title, slug, start_at, end_at, timezone, description, image_url,
                    category, vibe_tags, price_min, price_max, is_free, ticket_url,
                    status, confidence, hotspot_score, schema_type,
                    venue_id, organizer_id, dedupe_key, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    title = excluded.title,
                    end_at = COALESCE(excluded.end_at, events.end_at),
                    description = CASE
                        WHEN length(COALESCE(excluded.description, '')) > length(COALESCE(events.description, ''))
                        THEN excluded.description ELSE events.description END,
                    image_url = COALESCE(excluded.image_url, events.image_url),
                    category = excluded.category,
                    vibe_tags = excluded.vibe_tags,
                    price_min = COALESCE(excluded.price_min, events.price_min),
                    price_max = COALESCE(excluded.price_max, events.price_max),
                    is_free = excluded.is_free,
                    ticket_url = COALESCE(excluded.ticket_url, events.ticket_url),
                    status = excluded.status,
                    confidence = MAX(events.confidence, excluded.confidence),
                    hotspot_score = excluded.hotspot_score,
                    schema_type = COALESCE(excluded.schema_type, events.schema_type),
                    venue_id = COALESCE(excluded.venue_id, events.venue_id),
                    organizer_id = COALESCE(excluded.organizer_id, events.organizer_id),
                    updated_at = datetime('now')
                """,
                (
                    event.id,
                    event.title,
                    event.slug,
                    event.start_at,
                    event.end_at,
                    event.timezone,
                    event.description,
                    event.image_url,
                    event.category,
                    vibe_tags,
                    event.price_min,
                    event.price_max,
                    int(event.is_free),
                    event.ticket_url,
                    event.status,
                    event.confidence,
                    event.hotspot_score,
                    event.schema_type,
                    event.venue_id,
                    event.organizer_id,
                    event.dedupe_key,
                ),
            )
            row = conn.execute(
                "SELECT id FROM events WHERE dedupe_key = ?", (event.dedupe_key,)
            ).fetchone()
            event_id = row["id"] if row else event.id

            conn.execute(
                """
                INSERT INTO event_source_map (
                    event_id, source_id, source_event_id, source_url, raw_payload, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, source_event_id) DO UPDATE SET
                    event_id = excluded.event_id,
                    source_url = excluded.source_url,
                    raw_payload = excluded.raw_payload,
                    fetched_at = excluded.fetched_at
                """,
                (
                    event_id,
                    source.id,
                    source.source_event_id,
                    source.source_url,
                    json.dumps(source.raw_payload) if source.raw_payload else None,
                    source.fetched_at,
                ),
            )
            conn.commit()
        return event_id

    def expire_past_events(self) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE events
                SET status = 'expired', updated_at = datetime('now')
                WHERE status = 'scheduled'
                  AND datetime(replace(substr(start_at, 1, 19), 'T', ' ')) < datetime('now', '-6 hours')
                """
            )
            conn.commit()
            return cur.rowcount

    def recompute_venue_counts(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE venues SET event_count_30d = (
                    SELECT COUNT(*) FROM events e
                    WHERE e.venue_id = venues.id
                      AND e.status = 'scheduled'
                      AND datetime(replace(substr(e.start_at, 1, 19), 'T', ' '))
                          >= datetime('now', '-30 days')
                ), updated_at = datetime('now')
                """
            )
            conn.commit()

    def list_events(
        self,
        *,
        from_at: str | None = None,
        to_at: str | None = None,
        categories: list[str] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_km: float | None = None,
        sort: str = "hotspot",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = ["e.status = 'scheduled'"]
        params: list[Any] = []

        if from_at:
            clauses.append("e.start_at >= ?")
            params.append(from_at)
        if to_at:
            clauses.append("e.start_at <= ?")
            params.append(to_at)
        if categories:
            placeholders = ",".join("?" for _ in categories)
            clauses.append(f"e.category IN ({placeholders})")
            params.extend(categories)

        distance_sql = "NULL AS distance_km"
        if lat is not None and lon is not None:
            # Haversine approximation in km (good enough for city-scale filtering).
            distance_sql = """
                (6371 * acos(
                    cos(radians(?)) * cos(radians(v.lat)) *
                    cos(radians(v.lon) - radians(?)) +
                    sin(radians(?)) * sin(radians(v.lat))
                )) AS distance_km
            """
            params.extend([lat, lon, lat])
            if radius_km is not None:
                clauses.append(
                    """
                    (6371 * acos(
                        cos(radians(?)) * cos(radians(v.lat)) *
                        cos(radians(v.lon) - radians(?)) +
                        sin(radians(?)) * sin(radians(v.lat))
                    )) <= ?
                    """
                )
                params.extend([lat, lon, lat, radius_km])

        order_by = {
            "hotspot": "e.hotspot_score DESC, e.start_at ASC",
            "time": "e.start_at ASC",
            "distance": "distance_km ASC NULLS LAST, e.start_at ASC",
        }.get(sort, "e.hotspot_score DESC, e.start_at ASC")

        sql = f"""
            SELECT
                e.*,
                v.name AS venue_name,
                v.address AS venue_address,
                v.lat AS venue_lat,
                v.lon AS venue_lon,
                v.neighborhood AS venue_neighborhood,
                {distance_sql}
            FROM events e
            LEFT JOIN venues v ON v.id = e.venue_id
            WHERE {' AND '.join(clauses)}
            ORDER BY {order_by}
            LIMIT ?
        """
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def list_hotspot_clusters(
        self,
        *,
        from_at: str | None = None,
        to_at: str | None = None,
        categories: list[str] | None = None,
        grid_km: float = 2.0,
        limit: int = 80,
    ) -> list[dict[str, Any]]:
        grid_deg = max(0.003, grid_km * 0.009)
        clauses = [
            "e.status = 'scheduled'",
            "v.lat IS NOT NULL",
            "v.lon IS NOT NULL",
        ]
        params: list[Any] = []

        if from_at:
            clauses.append("e.start_at >= ?")
            params.append(from_at)
        if to_at:
            clauses.append("e.start_at <= ?")
            params.append(to_at)
        if categories:
            placeholders = ",".join("?" for _ in categories)
            clauses.append(f"e.category IN ({placeholders})")
            params.extend(categories)

        sql = f"""
            SELECT
                AVG(v.lat) AS lat,
                AVG(v.lon) AS lon,
                COUNT(*) AS event_count,
                SUM(e.hotspot_score) AS score_sum,
                MAX(e.hotspot_score) AS score_peak,
                GROUP_CONCAT(DISTINCT e.category) AS categories,
                GROUP_CONCAT(e.title, ' | ') AS titles,
                GROUP_CONCAT(DISTINCT v.neighborhood) AS neighborhoods
            FROM events e
            JOIN venues v ON v.id = e.venue_id
            WHERE {' AND '.join(clauses)}
            GROUP BY
                CAST(ROUND(v.lat / ?) AS INTEGER),
                CAST(ROUND(v.lon / ?) AS INTEGER)
            ORDER BY score_sum DESC, event_count DESC
            LIMIT ?
        """
        params.extend([grid_deg, grid_deg, limit])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT e.*, v.name AS venue_name, v.address AS venue_address,
                       v.lat AS venue_lat, v.lon AS venue_lon,
                       v.neighborhood AS venue_neighborhood
                FROM events e
                LEFT JOIN venues v ON v.id = e.venue_id
                WHERE e.id = ?
                """,
                (event_id,),
            ).fetchone()
            if not row:
                return None
            event = dict(row)
            sources = conn.execute(
                """
                SELECT s.name, m.source_url, m.fetched_at
                FROM event_source_map m
                JOIN sources s ON s.id = m.source_id
                WHERE m.event_id = ?
                """,
                (event_id,),
            ).fetchall()
            event["sources"] = [dict(s) for s in sources]
            return event
