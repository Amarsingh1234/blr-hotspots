# Deploy blr-hotspots ($0 stack)

## 1. Push to GitHub

```bash
git init   # if not already
git add .
git commit -m "blr-hotspots MVP"
git remote add origin git@github.com:YOUR_USER/blr-hotspots.git
git push -u origin main
```

GitHub Actions will ingest every 4 hours and upload `data/blr_hotspots.db` as an artifact.

## 2. API on Render (free)

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
2. Connect the repo — Render reads `render.yaml`
3. Wait for first deploy (runs ingest on start, ~1–2 min)
4. Copy the service URL, e.g. `https://blr-hotspots-api.onrender.com`
5. Test: `curl https://blr-hotspots-api.onrender.com/health`

**Notes:**
- Free tier sleeps after ~15 min idle — first request may take 30–60s
- SQLite lives on a 1GB persistent disk at `/var/data/blr_hotspots.db`
- Set `BLR_RUN_INGEST_ON_START=false` after first deploy if you only want GitHub Actions to refresh data

## 3. Frontend on Vercel (free)

```bash
cd web
npx vercel
```

In the Vercel project settings, add:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://blr-hotspots-api.onrender.com` |

Redeploy after setting the env var.

## 4. Optional: refresh API data from Actions artifact

Render does not auto-pull GitHub artifacts. Options:

- **Default:** ingest runs on each Render deploy / restart (`BLR_RUN_INGEST_ON_START=true`)
- **Manual:** download artifact from Actions → upload to Render disk (advanced)
- **Later:** publish DB to a GitHub Release and download in `render_start.sh`

## Skipped sources

| Source | Reason |
|---|---|
| Meetup | Paid API |
| BookMyShow | Cloudflare blocks server-side access |
