from db.store import EventStore
from pipeline.enrich import enrich_events
from pipeline.models import CanonicalEvent, SourceRef
from pipeline.normalize import normalize_schema_event


def _sample_event(title: str, lat: float, lon: float, category: str = "comedy") -> CanonicalEvent:
    payload = {
        "@type": "Event",
        "name": title,
        "startDate": "2026-12-01T20:00:00+05:30",
        "location": {
            "name": "Test Venue",
            "geo": {"latitude": str(lat), "longitude": str(lon)},
        },
    }
    event = normalize_schema_event(
        payload,
        source_url="https://example.com/event",
        source_confidence=0.85,
        fetched_at="2026-06-07T00:00:00Z",
    )
    assert event is not None
    event.category = category
    return event


def test_list_hotspot_clusters_groups_nearby_events(tmp_path):
    db_path = tmp_path / "test.db"
    store = EventStore(db_path)
    store.init_schema()

    events = enrich_events(
        [
            _sample_event("Show A", 12.9784, 77.6408),
            _sample_event("Show B", 12.9786, 77.6410),
            _sample_event("Far Away", 12.8500, 77.5000),
        ]
    )

    src = SourceRef(
        id="test",
        name="test",
        type="test",
        base_url="https://example.com",
        confidence_base=0.8,
        source_event_id="bootstrap",
        source_url="https://example.com",
        fetched_at="2026-06-07T00:00:00Z",
    )
    store.ensure_source(src)

    for event in events:
        if event.venue:
            store.upsert_venue(event.venue)
        store.upsert_event(event, src)

    clusters = store.list_hotspot_clusters(grid_km=2.0, limit=10)
    assert len(clusters) == 2
    top = clusters[0]
    assert top["event_count"] >= 2
