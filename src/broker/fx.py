from __future__ import annotations
import os
from src.core.log import logger

def gbp_per_usd() -> float:
    """
    Return GBP per USD (GBPUSD spot). Used to convert NAV in GBP -> USD notionals.
    Priority:
      1) ENV override FX_GBP_PER_USD
      2) Safe default 0.78 (≈ $1 = £0.78)
    """
    env = os.getenv("FX_GBP_PER_USD")
    if env:
        try:
            v = float(env)
            if v > 0:
                return v
        except ValueError:
            pass
        logger.warning(f"Invalid FX_GBP_PER_USD={env}; falling back to 0.78")
    return 0.78