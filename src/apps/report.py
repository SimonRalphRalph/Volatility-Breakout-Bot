from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd
from src.research.metrics import performance, cum_returns
from src.core.config import load_settings
from src.core.log import logger


def render_markdown(asof: str, daily_returns: pd.Series) -> str:
    perf = performance(daily_returns)
    cum = cum_returns(daily_returns)
    start = daily_returns.index.min()
    end = daily_returns.index.max()
    body = f"""# Aggressive Volatility Breakout — Daily Report
**As of:** {asof}

## Summary
- Period: {start.date()} → {end.date()}
- Annualized Return: {perf.ann_ret:.2%}
- Annualized Vol: {perf.ann_vol:.2%}
- Sharpe: {perf.sharpe:.2f}
- Sortino: {perf.sortino:.2f}
- Max Drawdown: {perf.max_dd:.2%}
- Calmar: {perf.calmar:.2f}
- Win Rate: {perf.win_rate:.1%}  (n={perf.n_trades})
- Avg Win / Avg Loss: {perf.avg_win:.2%} / {perf.avg_loss:.2%}

## Last 10 Daily Returns
{daily_returns.tail(10).to_string(float_format=lambda x: f"{x:.2%}")}

## Cumulative Return (table, last 10)
{cum.tail(10).to_string(float_format=lambda x: f"{x:.2f}x")}
"""
    return body


def save_report(content: str, asof: str | None = None) -> Path:
    cfg = load_settings().default
    asof = asof or datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = Path(cfg.report_dir) / asof
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "report.md"
    out_path.write_text(content)
    return out_path


def main():
    """
    Example usage: load a CSV of returns and write a report.
    In production you’d call this from your nightly job passing the real daily PnL series.
    """
    # Example synthetic series for demo purposes:
    idx = pd.date_range("2025-08-01", periods=22, freq="B")
    import numpy as np
    rng = np.random.default_rng(42)
    daily = pd.Series(rng.normal(0.001, 0.01, size=len(idx)), index=idx, name="ret")

    md = render_markdown(datetime.utcnow().strftime("%Y-%m-%d"), daily)
    path = save_report(md)
    logger.info(f"Report written to {path}")


if __name__ == "__main__":
    main()