from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
from ib_insync import IB, Contract, Stock
import math
from src.core.types import Target
from src.core.config import load_settings
from src.core.log import logger


@dataclass
class PositionSnapshot:
    symbol: str
    qty: int
    avg_price: float
    currency: str


def _contract(symbol: str, currency: str = "USD", primary: str = "SMART") -> Contract:
    return Stock(symbol, "SMART", currency, primaryExchange=primary)


def fetch_positions(ib: IB) -> Dict[str, PositionSnapshot]:
    """
    Returns {symbol -> PositionSnapshot}. Works for both paper and live.
    """
    pos = ib.positions()
    snap: Dict[str, PositionSnapshot] = {}
    for p in pos:
        sym = p.contract.symbol
        snap[sym] = PositionSnapshot(
            symbol=sym,
            qty=int(p.position),
            avg_price=float(p.avgCost or 0.0),
            currency=p.contract.currency or "USD",
        )
    return snap


def fetch_last_prices(ib: IB, symbols: List[str]) -> Dict[str, float]:
    """
    Lightweight price fetch via reqMktData snapshot (no streaming).
    """
    prices: Dict[str, float] = {}
    cfg = load_settings().ibkr
    contracts = [_contract(s, currency=cfg.currency, primary=cfg.primaryExchange) for s in symbols]
    tickers = ib.reqTickers(*contracts)
    for t in tickers:
        mid = None
        if t.marketPrice() and not math.isnan(t.marketPrice()):
            mid = float(t.marketPrice())
        elif t.last and t.last > 0:
            mid = float(t.last)
        elif t.close and t.close > 0:
            mid = float(t.close)
        if mid is not None:
            prices[t.contract.symbol] = mid
    return prices


def fetch_nav_gbp(ib: IB) -> float | None:
    """
    Try to get NetLiquidation in GBP. Returns None if unavailable.
    """
    vals = ib.accountValues()
    # Prefer BASE=GBP NetLiquidation if available
    for v in vals:
        if v.tag == "NetLiquidation" and (v.currency == "GBP" or v.currency == ""):
            try:
                return float(v.value)
            except Exception:
                pass
    # Fallback: None (caller may override via CLI flag)
    return None


def plan_from_targets(
    targets: List[Target],
    cur_positions: Dict[str, PositionSnapshot],
    last_prices: Dict[str, float],
    max_positions: int,
    max_gross_exposure: float,
    nav_usd: float,
    per_name_cap: float | None = None,
) -> List[Target]:
    """
    Convert target objects into deduped child orders with risk caps applied.

    - Dedup per symbol (keep largest abs qty).
    - Enforce max positions (keep largest dollar intents).
    - Enforce gross exposure cap vs NAV.
    - Optional per-name dollar cap.
    """
    if not targets:
        return []

    # Dedup largest qty per symbol
    dedup: Dict[str, Target] = {}
    for t in targets:
        if t.symbol not in dedup or abs(t.qty) > abs(dedup[t.symbol].qty):
            dedup[t.symbol] = t

    # Rank by intended dollar size
    def _dollars(t: Target) -> float:
        px = last_prices.get(t.symbol, 0.0)
        return abs(t.qty) * px

    ranked = sorted(dedup.values(), key=_dollars, reverse=True)

    # Enforce max_positions
    trimmed = ranked[:max_positions]

    # Apply per-name cap (if any)
    if per_name_cap:
        capped: List[Target] = []
        for t in trimmed:
            px = last_prices.get(t.symbol, 0.0)
            if px <= 0:
                continue
            max_dollars = per_name_cap * nav_usd
            if abs(t.qty) * px > max_dollars:
                qty_cap = int(max_dollars // px)
                if qty_cap <= 0:
                    continue
                t = t.copy(update={"qty": qty_cap if t.qty > 0 else -qty_cap})
            capped.append(t)
        trimmed = capped

    # Enforce gross exposure cap
    # Compute total intended dollars including existing holdings drift to target (simplified: use only new orders)
    intended = sum(_dollars(t) for t in trimmed)
    max_dollars_total = max_gross_exposure * nav_usd
    if intended > max_dollars_total and intended > 0:
        scale = max_dollars_total / intended
        scaled: List[Target] = []
        for t in trimmed:
            new_qty = int(max(0, math.floor(abs(t.qty) * scale)))
            if new_qty == 0:
                continue
            new_qty = new_qty if t.qty > 0 else -new_qty
            scaled.append(t.copy(update={"qty": new_qty}))
        trimmed = scaled

    # Convert to *child* orders (difference to current)
    child: List[Target] = []
    for t in trimmed:
        cur = cur_positions.get(t.symbol)
        cur_qty = cur.qty if cur else 0
        diff = t.qty - cur_qty  # we aim for qty (notional target); if you prefer delta, comment this
        if diff == 0:
            continue
        child.append(t.copy(update={"qty": diff}))

    logger.info(f"Reconciliation planned child orders: {len(child)}")
    return child