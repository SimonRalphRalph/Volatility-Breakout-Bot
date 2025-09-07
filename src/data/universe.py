from __future__ import annotations
import pandas as pd

# Placeholder universe; in practice, build from Polygon/IBKR scanners
DEFAULT_UNIVERSE = [
    "NVAX","GME","PLTR","MRNA","BYND","AMC","RIOT","CRSP","HOOD","DNA",
    "SOFI","COIN","AFRM","LCID","ROKU","CVNA","BILI","BMBL","UPST","RBLX"
]

def build_universe(min_price: float = 2.0, min_atr_pct: float = 0.03) -> list[str]:
    # TODO: pull ATR%, ADV from data source and filter; using placeholder list for now
    return DEFAULT_UNIVERSE
