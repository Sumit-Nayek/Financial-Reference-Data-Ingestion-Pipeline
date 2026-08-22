# tests/test_business_day.py
from datetime import date
import pytest
from sec_keyterms.business_day import MarketCalendar


@pytest.fixture
def calendar():
    return MarketCalendar(exchange="NYSE")


def test_standard_trading_day(calendar):
    # Wednesday, July 8, 2026 is a standard business day
    test_date = date(2026, 7, 8)
    assert calendar.is_business_day(test_date) is True
    assert calendar.get_latest_business_day(test_date) == test_date


def test_weekend_rollback(calendar):
    # Sunday, July 12, 2026 should roll back to Friday, July 10, 2026
    sunday = date(2026, 7, 12)
    assert calendar.is_business_day(sunday) is False
    assert calendar.get_latest_business_day(sunday) == date(2026, 7, 10)


def test_holiday_rollback(calendar):
    # Friday, July 3, 2026 (Observed US Independence Day) is a market holiday
    holiday_observed = date(2026, 7, 3)
    assert calendar.is_business_day(holiday_observed) is False
    assert calendar.get_latest_business_day(holiday_observed) == date(2026, 7, 2)