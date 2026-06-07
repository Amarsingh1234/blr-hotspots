from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class RawEvent:
    source_name: str
    source_event_id: str
    source_url: str
    fetched_at: str
    payload: dict[str, Any]


class Collector(Protocol):
    name: str

    def collect(self) -> list[RawEvent]:
        ...
