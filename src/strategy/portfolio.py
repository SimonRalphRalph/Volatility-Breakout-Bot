from __future__ import annotations
from typing import Iterable

def cap_positions(targets: dict[str,int], max_positions: int) -> dict[str,int]:
    if len(targets) <= max_positions:
        return targets
    # keep largest absolute sizes
    items = sorted(targets.items(), key=lambda kv: abs(kv[1]), reverse=True)[:max_positions]
    return dict(items)
