#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export BLR_HOST="${BLR_HOST:-0.0.0.0}"
export BLR_PORT="${PORT:-8001}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is required (Neon Postgres)." >&2
  exit 1
fi

if [[ "${BLR_RUN_INGEST_ON_START:-false}" == "true" ]]; then
  echo "Running ingestion into Neon Postgres ..."
  python -m pipeline.ingest
fi

echo "Starting API on ${BLR_HOST}:${BLR_PORT}"
exec python -m api.main
