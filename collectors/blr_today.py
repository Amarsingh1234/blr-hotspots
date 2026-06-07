from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from collectors.base import RawEvent

BLR_TODAY_DATASET_URL = (
    "https://github.com/blr-today/dataset/releases/latest/download/events.db"
)


class BlrTodayCollector:
    name = "blr.today"

    def __init__(self, dataset_url: str | None = None) -> None:
        self.dataset_url = dataset_url or BLR_TODAY_DATASET_URL

    def download_dataset(self, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(self.dataset_url)
            response.raise_for_status()
            dest.write_bytes(response.content)
        return dest

    def collect(self, *, cache_path: Path | None = None) -> list[RawEvent]:
        fetched_at = datetime.now(timezone.utc).isoformat()
        db_path = cache_path
        if db_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            db_path = Path(tmp.name)
            tmp.close()

        self.download_dataset(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT url, event_json FROM events").fetchall()
        conn.close()

        raw_events: list[RawEvent] = []
        for row in rows:
            url = row["url"]
            try:
                payload: dict[str, Any] = json.loads(row["event_json"])
            except json.JSONDecodeError:
                continue
            raw_events.append(
                RawEvent(
                    source_name=self.name,
                    source_event_id=url,
                    source_url=url,
                    fetched_at=fetched_at,
                    payload=payload,
                )
            )
        return raw_events
