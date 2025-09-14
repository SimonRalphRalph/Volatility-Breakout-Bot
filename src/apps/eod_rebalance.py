from __future__ import annotations
import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List

import typer
from rich import print

from src.core.config import load_settings
from src.core.log import logger
from src.core.types import Target
from src.data.universe import build_universe
from src.data import polygon as poly
from src.strategy.pipeline import build_targets
from src.broker.ibkr_client import IbClient
from src.broker.ibkr_exec import Executor
from src.broker.reconciliation import fetch_positions, fetch_last_prices, plan_from_targets
from src.broker.fx import gbp_per_usd


app = typer.Typer(add_completion=False)


def _date_strs(days_back: int = 60) -> tuple[str, str]:
    """Helper: get ISO start/end dates for Polygon fetch."""
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days_back)
    return start.isoformat(), end.isoformat()


async def _fetch_bars(symbols: List[str], start: str, end: str):
    """Concurrent daily OHLCV fetch for many symbols via Polygon."""
    return await poly.agg_daily_many(symbols, start, end)


@app.command()
def main(
    mode: str = typer.Option("paper", help="paper|live"),
    run_id: str = typer.Option(datetime.now(UTC).strftime("%Y%m%d")),
    dry_run: bool = typer.Option(False, help="Compute targets but do not submit orders"),
    nav_gbp: float = typer.Option(500.0, help="Override NAV in GBP (temporary until wired to IBKR)"),
    days_back: int = typer.Option(60, help="Bars lookback window for signal calc"),
):
    """
    EOD pipeline:
      1) Connect to IBKR
      2) Build volatile universe
      3) Pull recent daily bars (Polygon)
      4) Generate risk-sized breakout targets
      5) Reconcile vs positions and apply risk caps
      6) (Optional) Submit bracket orders to IBKR
    """
    cfg = load_settings()
    print(f"[bold cyan]Volatility Breakout Bot[/bold cyan]  run_id={run_id}  mode={mode}")

    # 1) Connect to IBKR
    ibc = IbClient()
    asyncio.get_event_loop().run_until_complete(ibc.connect())
    ex = Executor(ibc.ib)

    # NAV handling: for now we use CLI arg; later we’ll pull NetLiquidation directly from IBKR
    nav_gbp_eff = float(nav_gbp)
    fx_gbp_per_usd = gbp_per_usd()
    nav_usd_eff = nav_gbp_eff / fx_gbp_per_usd

    logger.info(f"NAV (GBP)={nav_gbp_eff:.2f} | FX GBP/USD={fx_gbp_per_usd:.4f} | NAV (USD)={nav_usd_eff:.2f}")

    # 2) Universe
    symbols = build_universe(
        min_price=cfg.strat.universe["min_price"],
        min_atr_pct=cfg.strat.universe["min_atr_pct"],
    )
    if not symbols:
        print("[red]Universe is empty. Aborting.[/red]")
        raise typer.Exit(code=1)
    logger.info(f"Universe size={len(symbols)}")

    # 3) Fetch bars (daily)
    start, end = _date_strs(days_back)
    logger.info(f"Fetching bars {start} → {end}")
    bars_map = asyncio.get_event_loop().run_until_complete(_fetch_bars(symbols, start, end))

    # 4) Generate targets
    targets: List[Target] = []
    for sym, df in bars_map.items():
        ts = build_targets(
            sym,
            df,
            nav_gbp=nav_gbp_eff,
            fx_gbp_per_usd=fx_gbp_per_usd,
            breakout_threshold=cfg.strat.signal["breakout_threshold"],
            vol_multiplier=cfg.strat.signal["vol_multiplier"],
            per_trade_risk=cfg.default.risk["per_trade_risk"],
            stop_loss_pct=cfg.strat.execution["stop_loss_pct"],
            trail_start_pct=cfg.strat.execution["trail_start_pct"],
            trail_pct=cfg.strat.execution["trail_pct"],
            entry_limit_pct=cfg.strat.execution["entry_limit_pct"],
        )
        if ts:
            targets.extend(ts)

    if not targets:
        print("[yellow]No signals today. Nothing to do.[/yellow]")
        return

    # 5) Reconciliation & risk caps
    positions = fetch_positions(ibc.ib)                              # current holdings
    last_prices = fetch_last_prices(ibc.ib, [t.symbol for t in targets])  # for dollar sizing
    child_orders = plan_from_targets(
        targets=targets,
        cur_positions=positions,
        last_prices=last_prices,
        max_positions=cfg.default.risk["max_positions"],
        max_gross_exposure=cfg.default.risk["max_gross_exposure"],
        nav_usd=nav_usd_eff,
        per_name_cap=cfg.default.risk.get("per_name_cap", None),
    )

    print(f"[yellow]Planned orders: {len(child_orders)}[/yellow]")
    for t in child_orders:
        px = last_prices.get(t.symbol, float("nan"))
        logger.info(f"PLAN {t.symbol} qty={t.qty} limit={t.entry_limit:.2f} stop={t.stop_loss:.2f} px≈{px:.2f}")

    if dry_run or not child_orders:
        print("[green]Dry run or no orders; nothing submitted[/green]")
        return

    # 6) Submit orders (entry + stop as bracket)
    submitted = 0
    for t in child_orders:
        try:
            ex.place_bracket(t)
            submitted += 1
        except Exception as e:
            logger.error(f"Submit failed {t.symbol}: {e}")

    print(f"[green]Run {run_id} completed. Submitted orders: {submitted}[/green]")


if __name__ == "__main__":
    app()