from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from collectors.blr_today import BlrTodayCollector
from collectors.shopify_json import ShopifyJsonCollector
from db.store import EventStore
from pipeline.enrich import enrich_events
from pipeline.models import CanonicalEvent, SourceRef
from pipeline.normalize import is_future_event, normalize_schema_event
from pipeline.normalize_shopify import shopify_product_to_schema_events

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.yaml"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def _source_ref(source_id: str, config: dict[str, Any], *, fetched_at: str) -> SourceRef:
    return SourceRef(
        id=source_id,
        name=str(config.get("name") or source_id),
        type=str(config.get("type") or "unknown"),
        base_url=str(config.get("base_url") or config.get("url") or ""),
        confidence_base=float(config.get("confidence", 0.75)),
        source_event_id="bootstrap",
        source_url=str(config.get("base_url") or config.get("url") or ""),
        fetched_at=fetched_at,
    )


def upsert_canonical_events(
    store: EventStore,
    source: SourceRef,
    events: list[CanonicalEvent],
) -> int:
    upserted = 0
    for event in events:
        if event.venue:
            store.upsert_venue(event.venue)
        if event.organizer:
            store.upsert_organizer(event.organizer)

        src = SourceRef(
            id=source.id,
            name=source.name,
            type=source.type,
            base_url=source.base_url,
            confidence_base=source.confidence_base,
            source_event_id=event.ticket_url or event.id,
            source_url=event.ticket_url or source.base_url or "",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            raw_payload=None,
        )
        store.upsert_event(event, src)
        upserted += 1
    return upserted


def ingest_blr_today(store: EventStore, config: dict[str, Any]) -> dict[str, int]:
    confidence = float(config.get("confidence", 0.85))
    collector = BlrTodayCollector(dataset_url=str(config.get("url", "")) if config.get("url") else None)
    raw_events = collector.collect(cache_path=ROOT / "data" / "blr_today_cache.db")

    source = _source_ref("blr.today", config, fetched_at=datetime.now(timezone.utc).isoformat())
    store.ensure_source(source)

    canonical: list[CanonicalEvent] = []
    for raw in raw_events:
        if not is_future_event(str(raw.payload.get("startDate", ""))):
            continue
        event = normalize_schema_event(
            raw.payload,
            source_url=raw.source_url,
            source_confidence=confidence,
            fetched_at=raw.fetched_at,
        )
        if event:
            canonical.append(event)

    canonical = enrich_events(canonical)
    upserted = upsert_canonical_events(store, source, canonical)

    return {
        "fetched": len(raw_events),
        "normalized": len(canonical),
        "upserted": upserted,
    }


def ingest_shopify_json(store: EventStore, config: dict[str, Any]) -> dict[str, int]:
    source_id = str(config.get("name") or "shopify")
    confidence = float(config.get("confidence", 0.72))
    collector = ShopifyJsonCollector(name=source_id, url=str(config["url"]))
    raw_events = collector.collect()

    source = _source_ref(source_id, config, fetched_at=datetime.now(timezone.utc).isoformat())
    store.ensure_source(source)

    canonical: list[CanonicalEvent] = []
    for raw in raw_events:
        schema_events = shopify_product_to_schema_events(
            raw.payload,
            source_name=source_id,
            source_url=raw.source_url,
        )
        for schema in schema_events:
            if not is_future_event(str(schema.get("startDate", ""))):
                continue
            event = normalize_schema_event(
                schema,
                source_url=raw.source_url,
                source_confidence=confidence,
                fetched_at=raw.fetched_at,
            )
            if event:
                canonical.append(event)

    canonical = enrich_events(canonical)
    upserted = upsert_canonical_events(store, source, canonical)

    return {
        "fetched": len(raw_events),
        "normalized": len(canonical),
        "upserted": upserted,
    }


def run_ingest(store: EventStore | None = None) -> dict[str, Any]:
    config = load_config()
    store = store or EventStore()
    store.init_schema()

    stats: dict[str, Any] = {"sources": {}}

    for source_config in config.get("bootstrap", []):
        name = str(source_config.get("name") or "bootstrap")
        stats["sources"][name] = ingest_blr_today(store, source_config)

    for source_config in config.get("phase_1", []):
        if not source_config.get("enabled"):
            continue
        name = str(source_config.get("name") or "phase_1")
        if source_config.get("type") == "json":
            stats["sources"][name] = ingest_shopify_json(store, source_config)

    stats["expired"] = store.expire_past_events()
    store.recompute_venue_counts()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blr-hotspots ingestion pipeline")
    parser.add_argument(
        "--db",
        default=str(EventStore().db_path),
        help="SQLite database path (default: data/blr_hotspots.db)",
    )
    args = parser.parse_args()

    store = EventStore(args.db)
    stats = run_ingest(store)

    print("Ingestion complete:")
    for name, source_stats in stats.get("sources", {}).items():
        print(f"  [{name}]")
        for key, value in source_stats.items():
            print(f"    {key}: {value}")
    if "expired" in stats:
        print(f"  expired: {stats['expired']}")


if __name__ == "__main__":
    main()
