from __future__ import annotations
import pandas as pd
import numpy as np

# --- Signals ---

def atr_pct(df: pd.DataFrame, n: int = 20) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    return (atr / df["close"]).fillna(0.0)


def breakout_long(df: pd.DataFrame, theta: float, vol_mult: float) -> pd.Series:
    """
    Breakout if today's HIGH exceeds (yesterday's high * (1 + theta)).
    If vol_mult <= 0, skip the volume confirmation. Otherwise require
    today's volume > vol_mult * 20-day average volume.
    """
    prev_high = df["high"].shift(1)
    level = prev_high * (1 + float(theta))
    broke = df["high"] > level

    if vol_mult is None or float(vol_mult) <= 0:
        return broke.fillna(False)

    vol_ok = df["volume"] > float(vol_mult) * df["volume"].rolling(20).mean()
    return (broke & vol_ok).fillna(False)

# --- Sizing ---

def risk_sized_qty(nav: float, price: float, per_trade_risk: float, stop_pct: float) -> int:
    # risk per trade in £ divided by risk per share
    risk_gbp = nav * per_trade_risk
    risk_per_share = price * stop_pct
    if risk_per_share <= 0:
        return 0
    qty = int(max(0, risk_gbp // risk_per_share))
    return qty
