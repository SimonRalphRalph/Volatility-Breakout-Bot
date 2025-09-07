from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from src.strategy.vobreakout import breakout_long


@dataclass
class BTConfig:
    breakout_threshold: float = 0.012
    vol_multiplier: float = 1.5
    stop_loss_pct: float = 0.03
    trail_start_pct: float = 0.05
    trail_pct: float = 0.04
    cost_bps: float = 10.0  # round-trip cost assumption per trade


def simulate_day(entry: float, next_high: float, next_low: float, next_close: float, cfg: BTConfig) -> float:
    """
    One-position, one-day outcome given entry price and next-day OHLC.
    Priority: hit stop -> hit trail target -> close-to-close.
    Returns simple return (not log).
    """
    # Hard stop first
    if (entry - next_low) / entry >= cfg.stop_loss_pct:
        return -cfg.stop_loss_pct
    # If move exceeds trail start, book trail lock-in
    if (next_high - entry) / entry >= cfg.trail_start_pct:
        # lock-in (trail_start - trail_pct) as conservative assumption
        return max(cfg.trail_start_pct - cfg.trail_pct, (next_close / entry) - 1.0)
    # Otherwise close-to-close
    return (next_close / entry) - 1.0


def backtest_breakout(df: pd.DataFrame, cfg: BTConfig) -> pd.Series:
    """
    Vectorized-ish daily loop: when breakout triggers on day T, assume entry at close(T),
    outcome materializes on day T+1 using next-day OHLC.
    Returns daily return series (net of modeled costs).
    """
    assert {"open", "high", "low", "close", "volume"}.issubset(df.columns), "OHLCV columns missing"
    sig = breakout_long(df, cfg.breakout_threshold, cfg.vol_multiplier).astype(bool)
    c = df["close"]

    # Precompute next-day OHLC
    nh = df["high"].shift(-1)
    nl = df["low"].shift(-1)
    nc = df["close"].shift(-1)

    rets = []
    idx = []
    for i in range(len(df) - 1):
        if not sig.iloc[i]:
            rets.append(0.0)
            idx.append(df.index[i])
            continue
        entry = c.iloc[i]
        r = simulate_day(entry, nh.iloc[i], nl.iloc[i], nc.iloc[i], cfg)
        # subtract simple cost per trade
        r -= (cfg.cost_bps / 1e4)
        rets.append(r)
        idx.append(df.index[i])
    return pd.Series(rets, index=pd.Index(idx, name="date")).fillna(0.0)