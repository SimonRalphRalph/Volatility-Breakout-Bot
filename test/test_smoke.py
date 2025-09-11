# tests/test_smoke.py
from __future__ import annotations
import os
import pandas as pd
import numpy as np

from src.core.config import load_settings
from src.broker.fx import gbp_per_usd
from src.strategy.vobreakout import breakout_long
from src.strategy.pipeline import build_targets
from src.core.types import Target
from src.broker.reconciliation import plan_from_targets


def test_config_loads():
    cfg = load_settings()
    # Core sections present
    assert cfg.default.base_ccy in ("GBP", "USD", "EUR")
    assert "max_gross_exposure" in cfg.default.risk
    assert 0 < cfg.strat.signal["breakout_threshold"] < 0.05
    assert cfg.ibkr.host and isinstance(cfg.ibkr.port, int)


def test_fx_env_and_default(monkeypatch):
    # Default path (no env)
    monkeypatch.delenv("FX_GBP_PER_USD", raising=False)
    v = gbp_per_usd()
    assert v > 0

    # Env override valid
    monkeypatch.setenv("FX_GBP_PER_USD", "0.81")
    v2 = gbp_per_usd()
    assert abs(v2 - 0.81) < 1e-9

    # Env override invalid -> fallback
    monkeypatch.setenv("FX_GBP_PER_USD", "not_a_number")
    v3 = gbp_per_usd()
    assert v3 > 0


def _make_df(no_signal: bool, n: int = 40):
    """
    Build a tiny OHLCV frame:
    - if no_signal=True, closes never exceed prior highs
    - else, last bar breaks out above prior high with a volume spike
    """
    rng = np.random.default_rng(123)
    base = np.cumsum(rng.normal(0, 0.2, size=n)) + 10.0
    high = base + 0.5
    low = base - 0.5
    close = base.copy()
    vol = np.full(n, 1_000_000.0)

    if not no_signal:
        # Force breakout on last bar: close above prior high by ~2% and volume spike
        close[-1] = high[-2] * 1.02
        vol[-1] = vol[-1] * 2.0  # 200% of avg

    df = pd.DataFrame(
        {"open": close - 0.2, "high": high, "low": low, "close": close, "volume": vol},
        index=pd.date_range("2024-01-01", periods=n, freq="B"),
    )
    return df


def test_breakout_long_signal_and_pipeline_no_signal():
    df = _make_df(no_signal=True)
    sig = breakout_long(df, theta=0.012, vol_mult=1.5)
    # No breakout expected anywhere
    assert not sig.any()

    # Pipeline also produces no targets
    targets = build_targets(
        symbol="TEST",
        df=df,
        nav_gbp=500.0,
        fx_gbp_per_usd=0.80,
        breakout_threshold=0.012,
        vol_multiplier=1.5,
        per_trade_risk=0.015,
        stop_loss_pct=0.03,
        trail_start_pct=0.05,
        trail_pct=0.04,
        entry_limit_pct=0.005,
    )
    assert targets == []


def test_breakout_long_signal_and_pipeline_with_signal():
    df = _make_df(no_signal=False)
    sig = breakout_long(df, theta=0.012, vol_mult=1.5)
    assert sig.iloc[-1] is True  # last bar breaks out

    targets = build_targets(
        symbol="TEST",
        df=df,
        nav_gbp=500.0,
        fx_gbp_per_usd=0.80,  # $1 = £0.80
        breakout_threshold=0.012,
        vol_multiplier=1.5,
        per_trade_risk=0.015,
        stop_loss_pct=0.03,
        trail_start_pct=0.05,
        trail_pct=0.04,
        entry_limit_pct=0.005,
    )
    assert len(targets) == 1
    t = targets[0]
    assert isinstance(t, Target)
    assert t.symbol == "TEST"
    assert t.qty > 0
    assert t.entry_limit and t.stop_loss and t.trail_start


def test_reconciliation_basic_caps():
    # Two planned targets with different sizes
    planned = [
        Target(symbol="AAA", side="BUY", qty=50, entry_limit=10.5, stop_loss=10.0, trail_start=11.0, trail_pct=0.04),
        Target(symbol="BBB", side="BUY", qty=200, entry_limit=5.25, stop_loss=5.10, trail_start=5.5, trail_pct=0.04),
    ]
    positions = {}  # no existing holdings
    last_prices = {"AAA": 10.6, "BBB": 5.30}

    # NAV ~$1,000 (USD); cap positions to 1, and gross exposure to 70% (so only the bigger intent survives)
    child = plan_from_targets(
        targets=planned,
        cur_positions=positions,
        last_prices=last_prices,
        max_positions=1,
        max_gross_exposure=0.70,
        nav_usd=1000.0,
        per_name_cap=0.50,  # per name cap = 50% of NAV
    )

    # Only one order should remain (the highest dollar one), and qty should be scaled if needed
    assert len(child) == 1
    chosen = child[0]
    assert chosen.symbol in ("AAA", "BBB")
    # Dollar exposure should not exceed caps
    dollars = abs(chosen.qty) * last_prices[chosen.symbol]
    assert dollars <= 0.70 * 1000.0 + 1e-6  # gross cap
    assert dollars <= 0.50 * 1000.0 + 1e-6  # per-name cap
