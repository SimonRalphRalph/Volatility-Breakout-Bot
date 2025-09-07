from src.core.types import Target

def plan_orders(targets: list[Target]) -> list[Target]:
    dedup: dict[str, Target] = {}
    for t in targets:
        if t.symbol not in dedup or abs(t.qty) > abs(dedup[t.symbol].qty):
            dedup[t.symbol] = t
    return list(dedup.values())
