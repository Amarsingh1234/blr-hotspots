CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    base_url TEXT,
    confidence_base DOUBLE PRECISION NOT NULL DEFAULT 0.8,
    last_sync_at TIMESTAMPTZ,
    sync_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS venues (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    neighborhood TEXT,
    city TEXT NOT NULL DEFAULT 'Bengaluru',
    venue_type TEXT,
    event_count_30d INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_venues_geo ON venues(lat, lon);
CREATE INDEX IF NOT EXISTS idx_venues_name ON venues(name);
CREATE INDEX IF NOT EXISTS idx_venues_neighborhood ON venues(neighborhood);

CREATE TABLE IF NOT EXISTS organizers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    description TEXT,
    image_url TEXT,
    category TEXT NOT NULL DEFAULT 'other',
    vibe_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    price_min INTEGER,
    price_max INTEGER,
    is_free BOOLEAN NOT NULL DEFAULT FALSE,
    ticket_url TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.8,
    hotspot_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    schema_type TEXT,
    venue_id TEXT REFERENCES venues(id),
    organizer_id TEXT REFERENCES organizers(id),
    dedupe_key TEXT NOT NULL UNIQUE,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_at);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_hotspot ON events(hotspot_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id);
CREATE INDEX IF NOT EXISTS idx_events_title_trgm ON events USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_events_description_trgm ON events USING gin (description gin_trgm_ops);

CREATE TABLE IF NOT EXISTS event_source_map (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id),
    source_event_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_payload JSONB,
    fetched_at TIMESTAMPTZ NOT NULL,
    UNIQUE(source_id, source_event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_source_event ON event_source_map(event_id);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    events_fetched INTEGER NOT NULL DEFAULT 0,
    events_upserted INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT
);
