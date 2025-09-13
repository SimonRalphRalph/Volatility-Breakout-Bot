from __future__ import annotations
import pandas as pd

from src.strategy.vobreakout import breakout_long, risk_sized_qty
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
    """
    Build a list of trade Targets for a single symbol based on the breakout rule.
    Expects daily OHLCV in df with columns: open, high, low, close, volume.
    """
    # Need enough history for rolling averages (e.g., 20-day volume)
    if df is None or df.empty or len(df) < 25:
        return []

    # Signal: breakout above yesterday's high with volume confirmation
    sig_series = breakout_long(df, breakout_threshold, vol_multiplier)
    sig = bool(sig_series.iloc[-1])
    if not sig:
        return []

    last = df.iloc[-1]
    px = float(last["close"])  # USD

    # FX: GBP per USD (GBPUSD). Fallback if unset/invalid.
    fx = fx_gbp_per_usd if fx_gbp_per_usd and fx_gbp_per_usd > 0 else 0.78
    nav_usd = float(nav_gbp) / fx

    # Risk-based sizing: shares so that loss at stop ≈ per_trade_risk * NAV
    qty = risk_sized_qty(nav_usd, px, per_trade_risk, stop_loss_pct)
    if qty <= 0:
        return []

    # Bracket parameters
    entry_limit = px * (1 + entry_limit_pct)
    stop_loss = px * (1 - stop_loss_pct)
    trail_start = px * (1 + trail_start_pct)

    return [
        Target(
            symbol=symbol,
            side="BUY",
            qty=qty,
            entry_limit=entry_limit,
            stop_loss=stop_loss,
            trail_start=trail_start,
            trail_pct=trail_pct,
            tag="VOBREAKOUT",
        )
    ]
