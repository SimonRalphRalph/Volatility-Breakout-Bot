from __future__ import annotations
from pydantic import BaseModel
from typing import Literal, Dict
from datetime import datetime

Side = Literal["BUY", "SELL"]

class Target(BaseModel):
    symbol: str
    side: Side
    qty: int
    entry_limit: float | None = None
    stop_loss: float | None = None
    trail_start: float | None = None
    trail_pct: float | None = None
    tag: str = "VOBREAKOUT"

class Fill(BaseModel):
    order_id: str
    symbol: str
    qty: int
    avg_price: float
    ts: datetime

class RunMeta(BaseModel):
    run_id: str
    asof: datetime
    mode: Literal["paper", "live"]
