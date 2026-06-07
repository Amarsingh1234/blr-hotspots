# Neon Postgres setup

## What you need to provide

1. **A Neon project** — https://neon.tech (free tier is fine)
2. **`DATABASE_URL`** — the Postgres connection string

## Steps

### 1. Create Neon database

1. Sign in to Neon → **New Project**
2. Name: `blr-hotspots` (region: **AWS ap-southeast-1** is closest to Bangalore)
3. Copy the connection string — use the **direct** URL for migrations/ingest, or **pooled** for Render API

Example shape:

```
postgresql://neondb_owner:PASSWORD@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

### 2. Local dev

```bash
cp .env.example .env
# paste DATABASE_URL into .env
export $(grep -v '^#' .env | xargs)

make install
python -m pipeline.ingest    # creates tables + ingests events
make serve
```

### 3. GitHub Actions secret

Repo → **Settings → Secrets → Actions** → add:

| Name | Value |
|---|---|
| `DATABASE_URL` | your Neon connection string |

### 4. Render env vars

Update both services in the [Render dashboard](https://dashboard.render.com):

| Service | Variable | Value |
|---|---|---|
| `blr-hotspots-api` | `DATABASE_URL` | Neon connection string |
| `blr-hotspots-web` | `NEXT_PUBLIC_API_URL` | `https://blr-hotspots-api.onrender.com` |

Redeploy API after setting `DATABASE_URL`.

### 5. Verify

```bash
curl https://blr-hotspots-api.onrender.com/health
# {"status":"ok","database":"postgres"}

curl "https://blr-hotspots-api.onrender.com/v1/events?q=koramangala&limit=3"
```

## Notes

- **pg_trgm** extension is enabled automatically on first ingest (`CREATE EXTENSION IF NOT EXISTS pg_trgm`) — supported on Neon free tier.
- SQLite (`data/blr_hotspots.db`) is no longer used — safe to delete locally.
- Re-running ingest is idempotent (upserts by `dedupe_key`).
