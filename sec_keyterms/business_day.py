from datetime import date, timedelta
from typing import Optional
import pandas_market_calendars as mcal
from sec_keyterms.config import DEFAULT_EXCHANGE


class MarketCalendar:
    """Manages Indian market trading calendars (NSE/BSE) and settlement dates."""

    def __init__(self, exchange: str = DEFAULT_EXCHANGE):
        self.exchange_name = exchange
        self.calendar = mcal.get_calendar(exchange)

    def is_business_day(self, target_date: date) -> bool:
        """Checks if target_date was an active trading session on the NSE/BSE."""
        date_str = target_date.isoformat()
        schedule = self.calendar.schedule(start_date=date_str, end_date=date_str)
        return not schedule.empty

    def get_latest_business_day(self, target_date: Optional[date] = None) -> date:
        """Returns target_date if active, or rolls backward across weekends/Indian holidays."""
        if target_date is None:
            target_date = date.today()

        start_lookup = target_date - timedelta(days=10)
        valid_days = self.calendar.valid_days(
            start_date=start_lookup.isoformat(),
            end_date=target_date.isoformat()
        )

        if len(valid_days) == 0:
            raise ValueError(f"No valid {self.exchange_name} trading sessions found before {target_date}.")

        return valid_days[-1].date()