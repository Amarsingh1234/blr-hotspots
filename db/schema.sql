PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    base_url TEXT,
    confidence_base REAL NOT NULL DEFAULT 0.8,
    last_sync_at TEXT,
    sync_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS venues (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    lat REAL,
    lon REAL,
    neighborhood TEXT,
    city TEXT NOT NULL DEFAULT 'Bengaluru',
    venue_type TEXT,
    event_count_30d INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_venues_geo ON venues(lat, lon);
CREATE INDEX IF NOT EXISTS idx_venues_name ON venues(name);

CREATE TABLE IF NOT EXISTS organizers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    description TEXT,
    image_url TEXT,
    category TEXT NOT NULL DEFAULT 'other',
    vibe_tags TEXT NOT NULL DEFAULT '[]',
    price_min INTEGER,
    price_max INTEGER,
    is_free INTEGER NOT NULL DEFAULT 0,
    ticket_url TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    confidence REAL NOT NULL DEFAULT 0.8,
    hotspot_score REAL NOT NULL DEFAULT 0.0,
    schema_type TEXT,
    venue_id TEXT REFERENCES venues(id),
    organizer_id TEXT REFERENCES organizers(id),
    dedupe_key TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_at);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_hotspot ON events(hotspot_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id);

CREATE TABLE IF NOT EXISTS event_source_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id),
    source_event_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_payload TEXT,
    fetched_at TEXT NOT NULL,
    UNIQUE(source_id, source_event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_source_event ON event_source_map(event_id);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES sources(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    events_fetched INTEGER NOT NULL DEFAULT 0,
    events_upserted INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT
);
