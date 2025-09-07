from __future__ import annotations
import pandas as pd
from typing import Iterable
from .vobreakout import breakout_long, risk_sized_qty

from src.core.types import Target


def build_targets(
    symbol: str,
    df: pd.DataFrame,
    nav_gbp: float,
    fx_gbp_per_usd: float,
    *,
    breakout_threshold: float,
    vol_multiplier: float,
    per_trade_risk: float,
    stop_loss_pct: float,
    trail_start_pct: float,
    trail_pct: float,
    entry_limit_pct: float,
) -> list[Target]:
    # Assume df is daily bars; use the last row for decision
    if df.empty or len(df) < 25:
        return []
    last = df.iloc[-1]
    sig = breakout_long(df, breakout_threshold, vol_multiplier).iloc[-1]
    if not sig:
        return []
    px = float(last["close"])  # USD
    nav_usd = nav_gbp / fx_gbp_per_usd
    qty = risk_sized_qty(nav_usd, px, per_trade_risk, stop_loss_pct)
    if qty <= 0:
        return []
    entry_limit = px * (1
