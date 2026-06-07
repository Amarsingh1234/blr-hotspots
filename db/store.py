from __future__ import annotations

import json
from typing import Any

from db.connection import get_connection, init_database
from pipeline.models import CanonicalEvent, Organizer, SourceRef, Venue


class EventStore:
    def __init__(self) -> None:
        pass

    def init_schema(self) -> None:
        init_database()

    def ping(self) -> bool:
        with get_connection() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        return bool(row and row["ok"] == 1)

    def ensure_source(self, source: SourceRef) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sources (id, name, type, base_url, confidence_base)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    base_url = EXCLUDED.base_url,
                    confidence_base = EXCLUDED.confidence_base
                """,
                (source.id, source.name, source.type, source.base_url, source.confidence_base),
            )

    def upsert_venue(self, venue: Venue) -> str:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO venues (id, name, address, lat, lon, neighborhood, city, venue_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    address = COALESCE(EXCLUDED.address, venues.address),
                    lat = COALESCE(EXCLUDED.lat, venues.lat),
                    lon = COALESCE(EXCLUDED.lon, venues.lon),
                    neighborhood = COALESCE(EXCLUDED.neighborhood, venues.neighborhood),
                    venue_type = COALESCE(EXCLUDED.venue_type, venues.venue_type),
                    updated_at = NOW()
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
        return venue.id

    def upsert_organizer(self, organizer: Organizer | None) -> str | None:
        if organizer is None:
            return None
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO organizers (id, name, url)
                VALUES (%s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    name = EXCLUDED.name,
                    url = COALESCE(EXCLUDED.url, organizers.url)
                """,
                (organizer.id, organizer.name, organizer.url),
            )
        return organizer.id

    def upsert_event(self, event: CanonicalEvent, source: SourceRef) -> str:
        vibe_tags = json.dumps(event.vibe_tags)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    id, title, slug, start_at, end_at, timezone, description, image_url,
                    category, vibe_tags, price_min, price_max, is_free, ticket_url,
                    status, confidence, hotspot_score, schema_type,
                    venue_id, organizer_id, dedupe_key, updated_at
                ) VALUES (
                    %s, %s, %s, %s::timestamptz, %s::timestamptz, %s, %s, %s,
                    %s, %s::jsonb, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, NOW()
                )
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    title = EXCLUDED.title,
                    end_at = COALESCE(EXCLUDED.end_at, events.end_at),
                    description = CASE
                        WHEN length(COALESCE(EXCLUDED.description, '')) > length(COALESCE(events.description, ''))
                        THEN EXCLUDED.description ELSE events.description END,
                    image_url = COALESCE(EXCLUDED.image_url, events.image_url),
                    category = EXCLUDED.category,
                    vibe_tags = EXCLUDED.vibe_tags,
                    price_min = COALESCE(EXCLUDED.price_min, events.price_min),
                    price_max = COALESCE(EXCLUDED.price_max, events.price_max),
                    is_free = EXCLUDED.is_free,
                    ticket_url = COALESCE(EXCLUDED.ticket_url, events.ticket_url),
                    status = EXCLUDED.status,
                    confidence = GREATEST(events.confidence, EXCLUDED.confidence),
                    hotspot_score = EXCLUDED.hotspot_score,
                    schema_type = COALESCE(EXCLUDED.schema_type, events.schema_type),
                    venue_id = COALESCE(EXCLUDED.venue_id, events.venue_id),
                    organizer_id = COALESCE(EXCLUDED.organizer_id, events.organizer_id),
                    updated_at = NOW()
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
                    event.is_free,
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
                "SELECT id FROM events WHERE dedupe_key = %s", (event.dedupe_key,)
            ).fetchone()
            event_id = row["id"] if row else event.id

            raw_payload = json.dumps(source.raw_payload) if source.raw_payload else None
            conn.execute(
                """
                INSERT INTO event_source_map (
                    event_id, source_id, source_event_id, source_url, raw_payload, fetched_at
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::timestamptz)
                ON CONFLICT(source_id, source_event_id) DO UPDATE SET
                    event_id = EXCLUDED.event_id,
                    source_url = EXCLUDED.source_url,
                    raw_payload = EXCLUDED.raw_payload,
                    fetched_at = EXCLUDED.fetched_at
                """,
                (
                    event_id,
                    source.id,
                    source.source_event_id,
                    source.source_url,
                    raw_payload,
                    source.fetched_at,
                ),
            )
        return event_id

    def expire_past_events(self) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """
                UPDATE events
                SET status = 'expired', updated_at = NOW()
                WHERE status = 'scheduled'
                  AND start_at < NOW() - INTERVAL '6 hours'
                """
            )
            return cur.rowcount

    def recompute_venue_counts(self) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE venues SET event_count_30d = (
                    SELECT COUNT(*) FROM events e
                    WHERE e.venue_id = venues.id
                      AND e.status = 'scheduled'
                      AND e.start_at >= NOW() - INTERVAL '30 days'
                ), updated_at = NOW()
                """
            )

    def list_events(
        self,
        *,
        q: str | None = None,
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
        where_params: list[Any] = []
        select_params: list[Any] = []

        if q:
            pattern = f"%{q.strip()}%"
            clauses.append(
                """
                (
                    e.title ILIKE %s
                    OR COALESCE(e.description, '') ILIKE %s
                    OR COALESCE(v.name, '') ILIKE %s
                    OR COALESCE(v.neighborhood, '') ILIKE %s
                    OR e.category ILIKE %s
                )
                """
            )
            where_params.extend([pattern, pattern, pattern, pattern, pattern])

        if from_at:
            clauses.append("e.start_at >= %s::timestamptz")
            where_params.append(from_at)
        if to_at:
            clauses.append("e.start_at <= %s::timestamptz")
            where_params.append(to_at)
        if categories:
            placeholders = ",".join("%s" for _ in categories)
            clauses.append(f"e.category IN ({placeholders})")
            where_params.extend(categories)

        distance_sql = "NULL::double precision AS distance_km"
        if lat is not None and lon is not None:
            distance_sql = """
                (6371 * acos(
                    LEAST(1.0, GREATEST(-1.0,
                        cos(radians(%s)) * cos(radians(v.lat)) *
                        cos(radians(v.lon) - radians(%s)) +
                        sin(radians(%s)) * sin(radians(v.lat))
                    ))
                )) AS distance_km
            """
            select_params.extend([lat, lon, lat])
            if radius_km is not None:
                clauses.append(
                    """
                    (6371 * acos(
                        LEAST(1.0, GREATEST(-1.0,
                            cos(radians(%s)) * cos(radians(v.lat)) *
                            cos(radians(v.lon) - radians(%s)) +
                            sin(radians(%s)) * sin(radians(v.lat))
                        ))
                    )) <= %s
                    """
                )
                where_params.extend([lat, lon, lat, radius_km])

        order_by = {
            "hotspot": "e.hotspot_score DESC, e.start_at ASC",
            "time": "e.start_at ASC",
            "distance": "distance_km ASC NULLS LAST, e.start_at ASC",
        }.get(sort, "e.hotspot_score DESC, e.start_at ASC")

        order_params: list[Any] = []
        if q and sort == "hotspot":
            order_by = (
                "GREATEST(similarity(e.title, %s), similarity(COALESCE(v.name, ''), %s)) DESC, "
                + order_by
            )
            order_params.extend([q.strip(), q.strip()])

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
            LIMIT %s
        """
        params = select_params + where_params + order_params + [limit]

        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def list_hotspot_clusters(
        self,
        *,
        q: str | None = None,
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

        if q:
            pattern = f"%{q.strip()}%"
            clauses.append(
                """
                (
                    e.title ILIKE %s
                    OR COALESCE(e.description, '') ILIKE %s
                    OR COALESCE(v.name, '') ILIKE %s
                    OR COALESCE(v.neighborhood, '') ILIKE %s
                )
                """
            )
            params.extend([pattern, pattern, pattern, pattern])

        if from_at:
            clauses.append("e.start_at >= %s::timestamptz")
            params.append(from_at)
        if to_at:
            clauses.append("e.start_at <= %s::timestamptz")
            params.append(to_at)
        if categories:
            placeholders = ",".join("%s" for _ in categories)
            clauses.append(f"e.category IN ({placeholders})")
            params.extend(categories)

        sql = f"""
            SELECT
                AVG(v.lat) AS lat,
                AVG(v.lon) AS lon,
                COUNT(*) AS event_count,
                SUM(e.hotspot_score) AS score_sum,
                MAX(e.hotspot_score) AS score_peak,
                STRING_AGG(DISTINCT e.category, ',') AS categories,
                STRING_AGG(e.title, ' | ') AS titles,
                STRING_AGG(DISTINCT v.neighborhood, ',') AS neighborhoods
            FROM events e
            JOIN venues v ON v.id = e.venue_id
            WHERE {' AND '.join(clauses)}
            GROUP BY
                CAST(ROUND(v.lat / %s) AS INTEGER),
                CAST(ROUND(v.lon / %s) AS INTEGER)
            ORDER BY score_sum DESC, event_count DESC
            LIMIT %s
        """
        params.extend([grid_deg, grid_deg, limit])

        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT e.*, v.name AS venue_name, v.address AS venue_address,
                       v.lat AS venue_lat, v.lon AS venue_lon,
                       v.neighborhood AS venue_neighborhood
                FROM events e
                LEFT JOIN venues v ON v.id = e.venue_id
                WHERE e.id = %s
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
                WHERE m.event_id = %s
                """,
                (event_id,),
            ).fetchall()
            event["sources"] = [dict(s) for s in sources]
            return event
