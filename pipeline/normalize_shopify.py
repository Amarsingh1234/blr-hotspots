from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))


def plain_text_from_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

DATE_RANGE_TAG_RE = re.compile(
    r"^(?P<m1>[A-Za-z]{3,9})\s+(?P<d1>\d{1,2})\s*[–\-]\s*(?:(?P<m2>[A-Za-z]{3,9})\s+)?(?P<d2>\d{1,2})$"
)

OTHER_CITY_RE = re.compile(
    r"\s+(?:Mumbai|Gurgaon|Delhi|Chennai|Hyderabad|Pune)\s*[-:]",
    re.IGNORECASE,
)

WHITE_BOX_BLR_RE = re.compile(
    r"Bangalore\s*[:\-]\s*"
    r"(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2})\s*\|\s*"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>AM|PM)\s*\|\s*"
    r"(?P<venue>[^|]+)",
    re.IGNORECASE,
)


def _month_num(name: str) -> int | None:
    return MONTHS.get(name.strip().lower()[:3])


def _infer_year(month: int, day: int, *, now: datetime | None = None) -> int:
    now = now or datetime.now(IST)
    year = now.year
    candidate = datetime(year, month, day, tzinfo=IST)
    if candidate.date() < now.date() - timedelta(days=1):
        year += 1
    return year


def _to_iso(year: int, month: int, day: int, hour: int = 11, minute: int = 0) -> str:
    dt = datetime(year, month, day, hour, minute, tzinfo=IST)
    return dt.isoformat()


def _parse_time(hour: int, ampm: str) -> tuple[int, int]:
    ampm = ampm.upper()
    if ampm == "AM":
        return (0, 0) if hour == 12 else (hour, 0)
    return (12, 0) if hour == 12 else (hour + 12, 0)


def _find_date_tag(tags: list[Any]) -> str | None:
    for tag in tags:
        if not isinstance(tag, str):
            continue
        if DATE_RANGE_TAG_RE.match(tag.strip()):
            return tag.strip()
    return None


def _parse_date_range_tag(tag: str, *, default_hour: int = 11) -> tuple[str, str | None]:
    match = DATE_RANGE_TAG_RE.match(tag.strip())
    if not match:
        raise ValueError(f"Unparseable date tag: {tag}")

    m1 = _month_num(match.group("m1"))
    d1 = int(match.group("d1"))
    m2 = _month_num(match.group("m2") or match.group("m1"))
    d2 = int(match.group("d2"))
    if m1 is None or m2 is None:
        raise ValueError(f"Unparseable month in tag: {tag}")

    year = _infer_year(m1, d1)
    start_at = _to_iso(year, m1, d1, default_hour, 0)
    end_at = _to_iso(year, m2, d2, default_hour + 2, 0) if (m2, d2) != (m1, d1) else None
    return start_at, end_at


def _product_image(product: dict[str, Any]) -> str | None:
    images = product.get("images")
    if isinstance(images, list) and images:
        src = images[0].get("src") if isinstance(images[0], dict) else None
        if isinstance(src, str):
            return src
    return None


def _schema_base(
    *,
    title: str,
    start_at: str,
    end_at: str | None,
    description: str | None,
    image_url: str | None,
    venue_name: str | None,
    organizer_name: str | None,
    ticket_url: str,
    keywords: list[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "@type": "Event",
        "name": title,
        "startDate": start_at,
        "description": description,
        "url": ticket_url,
        "keywords": keywords,
    }
    if end_at:
        payload["endDate"] = end_at
    if image_url:
        payload["image"] = image_url
    if venue_name:
        payload["location"] = {"name": venue_name, "address": f"{venue_name}, Bengaluru"}
    if organizer_name:
        payload["organizer"] = {"name": organizer_name}
    return payload


def normalize_trove_product(product: dict[str, Any], *, source_url: str) -> dict[str, Any] | None:
    title = product.get("title")
    if not title:
        return None

    tags = product.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tag_blob = " ".join(str(t) for t in tags).lower()
    if "bangalore" not in tag_blob and "bengaluru" not in tag_blob:
        return None

    date_tag = _find_date_tag(tags)
    if not date_tag:
        return None

    try:
        start_at, end_at = _parse_date_range_tag(date_tag, default_hour=11)
    except ValueError:
        return None

    body = plain_text_from_html(str(product.get("body_html") or ""))
    description = body or None
    keywords = [str(t) for t in tags if isinstance(t, str)]
    organizer = str(product.get("vendor") or "Trove Experiences")

    return _schema_base(
        title=str(title).strip(),
        start_at=start_at,
        end_at=end_at,
        description=description,
        image_url=_product_image(product),
        venue_name="Bengaluru",
        organizer_name=organizer,
        ticket_url=source_url,
        keywords=keywords,
    )


def normalize_whitebox_product(product: dict[str, Any], *, source_url: str) -> list[dict[str, Any]]:
    title = product.get("title")
    if not title:
        return []

    body_html = str(product.get("body_html") or "")
    body_text = plain_text_from_html(body_html)
    events: list[dict[str, Any]] = []

    for match in WHITE_BOX_BLR_RE.finditer(body_text):
        month = _month_num(match.group("month"))
        if month is None:
            continue
        day = int(match.group("day"))
        hour, minute = _parse_time(int(match.group("hour")), match.group("ampm"))
        year = _infer_year(month, day)
        start_at = _to_iso(year, month, day, hour, minute)
        venue_name = OTHER_CITY_RE.split(match.group("venue").strip())[0].strip()

        description = plain_text_from_html(body_html)
        events.append(
            _schema_base(
                title=str(title).strip(),
                start_at=start_at,
                end_at=None,
                description=description,
                image_url=_product_image(product),
                venue_name=venue_name,
                organizer_name=str(product.get("vendor") or "The White Box"),
                ticket_url=source_url,
                keywords=["whitebox", "bangalore", venue_name.lower()],
            )
        )

    return events


def shopify_product_to_schema_events(
    product: dict[str, Any],
    *,
    source_name: str,
    source_url: str,
) -> list[dict[str, Any]]:
    if source_name == "trove":
        event = normalize_trove_product(product, source_url=source_url)
        return [event] if event else []
    if source_name == "whitebox":
        return normalize_whitebox_product(product, source_url=source_url)
    return []
