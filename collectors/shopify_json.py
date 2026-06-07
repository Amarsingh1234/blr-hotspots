from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from collectors.base import RawEvent

_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class ShopifyJsonCollector:
    """Fetch events from a Shopify `products.json` collection endpoint."""

    def __init__(self, *, name: str, url: str, page_size: int = 250) -> None:
        self.name = name
        self.url = url.rstrip("/")
        self.page_size = page_size
        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

    def collect(self) -> list[RawEvent]:
        fetched_at = datetime.now(timezone.utc).isoformat()
        raw_events: list[RawEvent] = []
        page = 1

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            while True:
                response = client.get(
                    self.url,
                    params={"limit": self.page_size, "page": page},
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                products = payload.get("products") or []
                if not products:
                    break

                for product in products:
                    if not isinstance(product, dict):
                        continue
                    product_id = str(product.get("id") or product.get("handle") or "")
                    if not product_id:
                        continue
                    handle = str(product.get("handle") or product_id)
                    source_url = urljoin(self.base_url, f"/products/{handle}")
                    raw_events.append(
                        RawEvent(
                            source_name=self.name,
                            source_event_id=product_id,
                            source_url=source_url,
                            fetched_at=fetched_at,
                            payload=product,
                        )
                    )

                next_url = _parse_next_link(response.headers.get("link", ""))
                if next_url:
                    self.url = next_url.split("?")[0]
                    page += 1
                    continue
                if len(products) < self.page_size:
                    break
                page += 1

        return raw_events


def _parse_next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        match = _LINK_NEXT_RE.search(part.strip())
        if match:
            return match.group(1)
    return None
