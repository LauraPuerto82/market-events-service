from datetime import date

from app.integrations.normalizers import normalize_provider_a, normalize_provider_b


def test_normalize_provider_a_earnings() -> None:
    raw = {
        "event_id": "pa-AAPL-earnings-202603",
        "ticker": "AAPL",
        "type": "earnings",
        "date": "2026-03-20",
        "title": "AAPL Earnings - Mar 2026",
        "details": {"eps_estimate": 3.45},
    }

    result = normalize_provider_a(raw)

    assert result.symbol == "AAPL"
    assert result.event_type == "earnings"
    assert result.event_date == date(2026, 3, 20)
    assert result.source == "provider_a"
    assert result.source_event_id == "pa-AAPL-earnings-202603"


def test_normalize_provider_a_preserves_details() -> None:
    raw = {
        "event_id": "pa-AAPL-earnings-202603",
        "ticker": "AAPL",
        "type": "earnings",
        "date": "2026-03-20",
        "title": "AAPL Earnings",
        "details": {"eps_estimate": 3.45, "revenue_estimate": 90_000_000_000},
    }

    result = normalize_provider_a(raw)
    assert result.details == {"eps_estimate": 3.45, "revenue_estimate": 90_000_000_000}


def test_normalize_provider_a_no_details() -> None:
    raw = {
        "event_id": "pa-AAPL-split-202603",
        "ticker": "AAPL",
        "type": "split",
        "date": "2026-03-20",
        "title": "AAPL Stock Split",
    }
    result = normalize_provider_a(raw)

    assert result.details is None


def test_normalize_provider_b_maps_category() -> None:
    raw = {
        "id": "pb-123",
        "instrument": {"symbol": "AAPL", "exchange": "NASDAQ"},
        "event": {
            "category": "earnings_release",  # Provider B name
            "scheduled_at": "2026-03-20T09:00:00Z",
            "title": "AAPL Earnings",
            "earnings_data": {"eps_consensus": 3.45},
        },
        "provider_metadata": {},
    }
    result = normalize_provider_b(raw)
    assert result.event_type == "earnings"  # mapped from "earnings_release"
    assert result.event_date == date(2026, 3, 20)
    assert result.symbol == "AAPL"
    assert result.source == "provider_b"
    assert result.source_event_id == "pb-123"


def test_normalize_provider_b_all_type_mappings() -> None:
    """Every Provider B category maps to the correct internal type."""
    mappings = {
        "earnings_release": "earnings",
        "dividend_payment": "dividend",
        "stock_split": "split",
        "economic_indicator": "economic",
    }

    for provider_b_type, expected_type in mappings.items():
        raw = {
            "id": "pb-test",
            "instrument": {"symbol": "AAPL", "exchange": "NYSE"},
            "event": {
                "category": provider_b_type,
                "scheduled_at": "2026-03-20T09:00:00Z",
                "title": "Test Event",
            },
            "provider_metadata": {},
        }
        result = normalize_provider_b(raw)
        assert result.event_type == expected_type, (
            f"Expected '{expected_type}' for category '{provider_b_type}', got '{result.event_type}'"
        )


def test_normalize_provider_b_extracts_date_from_datetime() -> None:
    """The date part is correctly extracted from Provider B's datetime string."""
    raw = {
        "id": "pb-date-test",
        "instrument": {"symbol": "MSFT", "exchange": "NASDAQ"},
        "event": {
            "category": "earnings_release",
            "scheduled_at": "2026-12-31T23:59:59Z",  # end of year, end of day
            "title": "Test",
        },
        "provider_metadata": {},
    }
    result = normalize_provider_b(raw)
    assert result.event_date == date(2026, 12, 31)


def test_normalize_provider_b_unknown_category_passthrough() -> None:
    """An unknown Provider B category passes through unchanged."""
    raw = {
        "id": "pb-unknown",
        "instrument": {"symbol": "AAPL", "exchange": "NYSE"},
        "event": {
            "category": "special_event",  # not in the mapping dict
            "scheduled_at": "2026-03-20T09:00:00Z",
            "title": "Special Event",
        },
        "provider_metadata": {},
    }
    result = normalize_provider_b(raw)
    assert result.event_type == "special_event"  # passed through unchanged
