from pipeline.dedupe import make_dedupe_key, title_similarity
from pipeline.normalize import infer_category, normalize_schema_event


def test_dedupe_key_stable():
    key_a = make_dedupe_key("Standup Night!", "2026-06-07T20:00:00+05:30", 12.97, 77.59, "The Comedy Theatre")
    key_b = make_dedupe_key("standup night", "2026-06-07T20:00:00+05:30", 12.97, 77.59, "The Comedy Theatre")
    assert key_a == key_b


def test_title_similarity():
    assert title_similarity("Standup Showcase", "Standup Showcase Night") > 0.4


def test_normalize_schema_event_comedy():
    payload = {
        "@type": "Event",
        "name": "Open Mic Standup Night",
        "startDate": "2026-12-01T20:00:00+05:30",
        "description": "A comedy open mic in Indiranagar",
        "location": {
            "name": "The Comedy Theatre",
            "geo": {"latitude": "12.9784", "longitude": "77.6408"},
        },
    }
    event = normalize_schema_event(
        payload,
        source_url="https://insider.in/example",
        source_confidence=0.85,
        fetched_at="2026-06-07T00:00:00Z",
    )
    assert event is not None
    assert event.category == "comedy"
    assert event.venue is not None
    assert event.dedupe_key


def test_infer_category_music_event_type():
    payload = {"@type": "MusicEvent", "name": "Gig", "startDate": "2026-12-01T20:00:00+05:30"}
    assert infer_category(payload) == "music"
