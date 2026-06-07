#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export BLR_HOST="${BLR_HOST:-0.0.0.0}"
export BLR_PORT="${PORT:-8001}"
export BLR_DB_PATH="${BLR_DB_PATH:-data/blr_hotspots.db}"

mkdir -p "$(dirname "$BLR_DB_PATH")"

if [[ "${BLR_RUN_INGEST_ON_START:-false}" == "true" ]] || [[ ! -f "$BLR_DB_PATH" ]]; then
  echo "Running ingestion into $BLR_DB_PATH ..."
  python -m pipeline.ingest --db "$BLR_DB_PATH"
fi

echo "Starting API on ${BLR_HOST}:${BLR_PORT}"
exec python -m api.main
