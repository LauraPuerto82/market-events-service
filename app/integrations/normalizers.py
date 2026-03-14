from datetime import date
from typing import Any


class NormalizedEvent:
    def __init__(
        self,
        symbol: str,
        event_type: str,
        event_date: date,
        title: str,
        details: dict[str, Any] | None,
        source: str,
        source_event_id: str,
    ) -> None:
        self.symbol = symbol
        self.event_type = event_type
        self.event_date = event_date
        self.title = title
        self.details = details
        self.source = source
        self.source_event_id = source_event_id


PROVIDER_B_TYPE_MAP = {
    "earnings_release": "earnings",
    "dividend_payment": "dividend",
    "stock_split": "split",
    "economic_indicator": "economic",
}


def normalize_provider_a(raw: dict[str, Any]) -> NormalizedEvent:
    return NormalizedEvent(
        symbol=raw["ticker"],
        event_type=raw["type"],
        event_date=date.fromisoformat(raw["date"]),
        title=raw["title"],
        details=raw.get("details"),
        source="provider_a",
        source_event_id=raw["event_id"],
    )


def normalize_provider_b(raw: dict[str, Any]) -> NormalizedEvent:
    event = raw["event"]
    scheduled_at = event["scheduled_at"]
    event_date = date.fromisoformat(scheduled_at[:10])
    raw_category = event["category"]
    event_type = PROVIDER_B_TYPE_MAP.get(raw_category) or raw_category
    details = (
        event.get("earnings_data")
        or event.get("dividend_data")
        or event.get("split_data")
        or event.get("economic_data")
    )
    return NormalizedEvent(
        symbol=raw["instrument"]["symbol"],
        event_type=event_type,
        event_date=event_date,
        title=event["title"],
        details=details,
        source="provider_b",
        source_event_id=raw["id"],
    )
