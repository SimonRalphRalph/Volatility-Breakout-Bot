from __future__ import annotations
import os, httpx, pandas as pd

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

async def agg_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    # Simplified; replace with proper pagination and rate-limit handling
    url = f"{BASE}/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        js = r.json()
    rows = js.get("results", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.rename(columns={"t":"timestamp","o":"open","h":"high","l":"low","c":"close","v":"volume"})
    return df[["timestamp","open","high","low","close","volume"]]
