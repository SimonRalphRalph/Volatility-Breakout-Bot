from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass


ANN_DAYS = 252


def cum_returns(returns: pd.Series) -> pd.Series:
    return (1.0 + returns.fillna(0.0)).cumprod()


def drawdown(cum: pd.Series) -> pd.Series:
    peak = cum.cummax()
    return cum / peak - 1.0


@dataclass
class Perf:
    ann_ret: float
    ann_vol: float
    sharpe: float
    sortino: float
    max_dd: float
    calmar: float
    win_rate: float
    avg_win: float
    avg_loss: float
    n_trades: int


def performance(returns: pd.Series) -> Perf:
    r = returns.dropna().astype(float)
    if r.empty:
        return Perf(0, 0, np.nan, np.nan, 0, np.nan, 0, 0, 0, 0)

    mu = r.mean() * ANN_DAYS
    vol = r.std(ddof=1) * np.sqrt(ANN_DAYS)
    sharpe = mu / vol if vol > 0 else np.nan

    neg = r[r < 0]
    downside = neg.std(ddof=1) * np.sqrt(ANN_DAYS) if len(neg) > 1 else np.nan
    sortino = mu / downside if downside and downside > 0 else np.nan

    cum = cum_returns(r)
    dd = drawdown(cum)
    mdd = float(dd.min())
    calmar = mu / abs(mdd) if mdd < 0 else np.nan

    # Trade stats proxy: count non-zero days as "trades" (approx)
    nz = r[r != 0.0]
    wins = nz[nz > 0]
    losses = nz[nz < 0]
    win_rate = len(wins) / len(nz) if len(nz) > 0 else 0.0
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 0.0

    return Perf(
        ann_ret=float(mu),
        ann_vol=float(vol),
        sharpe=float(sharpe),
        sortino=float(sortino),
        max_dd=float(mdd),
        calmar=float(calmar),
        win_rate=float(win_rate),
        avg_win=float(avg_win),
        avg_loss=float(avg_loss),
        n_trades=int(len(nz)),
    )
