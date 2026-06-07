# blr-hotspots

Bangalore events aggregator — ingest public feeds, dedupe, rank hotspots, serve a map-ready API.

**MVP status:** Phase 0 complete — bootstraps from the open [blr.today](https://blr.today) dataset.

## Free-tier stack (₹0 / $0)

| Layer | Choice | Free tier |
|---|---|---|
| **Database** | Neon Postgres (`DATABASE_URL`) | Free tier |
| **Ingestion** | Python + GitHub Actions cron | Free on public repos |
| **API** | FastAPI | Deploy on Render free / run locally |
| **Frontend** | Next.js on Vercel (phase 1) | Hobby tier free |
| **Maps** | MapLibre GL + Carto vector tiles | Free (no API key) |
| **Geocoding** | Rule-based neighborhoods for now | Free |
| **Cache** | Skip Redis in MVP | — |

### Why this stack?

- **Neon Postgres** — persistent, shared by API + GitHub Actions ingest; server-side search.
- **Python** matches the blr.today ingest ecosystem — easy to add collectors later.
- **GitHub Actions** replaces a paid cron scheduler (ingest every 4 hours).
- **No ML, no Redis, no paid APIs** in phase 0.

### Deploy path (still $0)

1. **Public GitHub repo** → Actions ingests on schedule, uploads DB artifact.
2. **Render free web service** → `render.yaml` included; runs ingest on start, persists SQLite on a 1GB disk.
3. **Vercel** → import `web/`, set `NEXT_PUBLIC_API_URL` to your Render API URL.

```bash
# Render (after pushing repo)
# Dashboard → New → Blueprint → point at render.yaml

# Vercel
cd web && vercel
# Set NEXT_PUBLIC_API_URL=https://blr-hotspots-api.onrender.com
```

> Note: Render free tier spins down after inactivity (cold starts). Fine for MVP.

## Quick start

```bash
cd ~/Projects/blr-hotspots
cp .env.example .env   # add Neon DATABASE_URL — see NEON_SETUP.md
export $(grep -v '^#' .env | xargs)
make install
make ingest       # creates schema + ingests blr.today, Trove, White Box
make serve        # API at http://localhost:8001

# Map UI (separate terminal)
cd web && cp .env.local.example .env.local
make web-dev      # http://localhost:3000
```

### API examples

```bash
# Health
curl http://localhost:8001/health

# Tonight's hotspots
curl "http://localhost:8001/v1/events?sort=hotspot&limit=10"

# Comedy near Indiranagar
curl "http://localhost:8001/v1/events?lat=12.9784&lon=77.6408&radius_km=5&category=comedy"

# Hotspot clusters (for map bubbles at city zoom)
curl "http://localhost:8001/v1/hotspots?grid_km=2&limit=20"

# Search (server-side, Postgres)
curl "http://localhost:8001/v1/events?q=standup%20koramangala&limit=10"
```

## Architecture

```
collectors/     → fetch raw events (blr.today dataset today)
pipeline/       → normalize, dedupe, enrich, hotspot score
db/             → SQLite schema + store
api/            → FastAPI read endpoints
config/         → source registry (sources.yaml)
```

## Data attribution

blr.today data is [ODbL-1.0](https://opendatacommons.org/licenses/odbl/1.0/). Attribute **blr.today** in the UI when showing events sourced from that dataset.

## Web app (`web/`)

Map-first UI built with Next.js 14 + MapLibre GL + Carto dark vector tiles (free, gap-free zoom).

- Sidebar: time presets (Tonight / Weekend), category chips, ranked event list
- Map: category-colored markers sized by hotspot score
- Click list ↔ fly to marker on map

Deploy frontend free on Vercel; set `NEXT_PUBLIC_API_URL` to your Render API URL.

## Roadmap

- [x] Phase 0: blr.today ingest + API
- [x] Phase 0.5: Map UI
- [x] Phase 1: JSON feeds (Trove, White Box)
- [x] Phase 3: Deploy on Render
- [x] Postgres migration (Neon) + server-side search (`?q=`)
- [x] Phase 4: Hotspot cluster endpoint (`GET /v1/hotspots`) + map bubbles at city zoom
- [x] Deploy live on Render (see `DEPLOY.md`)
- [ ] Phase 2: BookMyShow — blocked by Cloudflare (deferred)

## License

Code: MIT (add license file when ready). Event data from blr.today: ODbL.
