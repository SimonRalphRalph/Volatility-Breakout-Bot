from __future__ import annotations
import pandas as pd
import pandas_market_calendars as mcal
from datetime import datetime

nyse = mcal.get_calendar("XNYS")

def last_trading_day(ts: pd.Timestamp | None = None) -> pd.Timestamp:
    ts = pd.Timestamp.utcnow().normalize() if ts is None else pd.Timestamp(ts)
    sched = nyse.schedule(start_date=ts - pd.Timedelta(days=10), end_date=ts)
    return sched.index[-1]
