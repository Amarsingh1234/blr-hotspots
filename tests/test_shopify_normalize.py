from pipeline.normalize_shopify import (
    normalize_trove_product,
    normalize_whitebox_product,
)


def test_normalize_trove_product_with_date_tag():
    product = {
        "title": "The Espresso Lab",
        "vendor": "Trove Experiences",
        "tags": ["bangalore", "coffee", "Jun 13 – Jun 14", "upcoming"],
        "body_html": "<p>Coffee workshop in Bengaluru</p>",
        "images": [{"src": "https://example.com/img.jpg"}],
    }
    event = normalize_trove_product(product, source_url="https://troveexperiences.com/products/espresso")
    assert event is not None
    assert event["name"] == "The Espresso Lab"
    assert event["startDate"].startswith("2026-06-13")
    assert event["endDate"].startswith("2026-06-14")


def test_normalize_whitebox_bangalore_line():
    product = {
        "title": "Cupid's Soirée",
        "vendor": "The White Box",
        "body_html": (
            "<p><strong>Bangalore:</strong> June 28 | 12 PM | Brine<br>"
            "<strong>Mumbai -</strong> June 20 | 4 PM | Qey</p>"
        ),
    }
    events = normalize_whitebox_product(
        product,
        source_url="https://thewhiteboxco.in/products/cupids-soiree",
    )
    assert len(events) == 1
    assert events[0]["location"]["name"] == "Brine"
    assert "T12:00:00" in events[0]["startDate"]


def test_normalize_trove_skips_without_date_tag():
    product = {
        "title": "No Date",
        "tags": ["bangalore", "upcoming"],
    }
    assert normalize_trove_product(product, source_url="https://example.com/p") is None
