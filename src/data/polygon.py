# src/data/polygon.py
from __future__ import annotations

import os
import asyncio
from typing import Dict, List, Optional

import httpx
import pandas as pd


API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"


def _empty_df(symbol: Optional[str] = None) -> pd.DataFrame:
    cols = ["timestamp", "open", "high", "low", "close", "volume", "symbol"]
    df = pd.DataFrame(columns=cols)
    if symbol is not None:
        df["symbol"] = symbol
    return df


def _normalize(js: dict, symbol: str) -> pd.DataFrame:
    rows = js.get("results", [])
    if not rows:
        return _empty_df(symbol)
    df = pd.DataFrame(rows)
    # polygon keys: t (ms), o,h,l,c,v
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.rename(
        columns={
            "t": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        }
    )
    df["symbol"] = symbol
    return df[["timestamp", "open", "high", "low", "close", "volume", "symbol"]]


async def _get_with_retries(
    client: httpx.AsyncClient, url: str, *, retries: int = 3, backoff: float = 0.8
) -> Optional[dict]:
    """
    Small retry helper. Returns parsed JSON dict or None on failure.
    Backoff is exponential: backoff * (2 ** attempt).
    """
    for i in range(retries + 1):
        try:
            resp = await client.get(url)
            # Handle 429 (rate limit) and 5xx with retries
            if resp.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError(
                    f"status={resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError):
            if i == retries:
                return None
            await asyncio.sleep(backoff * (2**i))
    return None


async def agg_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch daily OHLCV bars for one symbol.
    start/end format: 'YYYY-MM-DD'
    """
    if not API_KEY:
        # No key configured: return empty to let the pipeline skip data work
        return _empty_df(symbol)

    url = (
        f"{BASE}/v2/aggs/ticker/{symbol}/range/1/day/"
        f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        js = await _get_with_retries(client, url)
    if js is None:
        return _empty_df(symbol)
    return _normalize(js, symbol)


async def agg_daily_many(
    symbols: List[str],
    start: str,
    end: str,
    *,
    concurrency: int = 8,
) -> Dict[str, pd.DataFrame]:
    """
    Concurrently fetch daily OHLCV bars for many symbols.
    Returns: {symbol: DataFrame}. Missing/failed lookups map to empty DataFrames.
    """
    if not API_KEY:
        # Produce empty frames for all; upstream will handle as "no data"
        return {s: _empty_df(s) for s in symbols}

    sem = asyncio.Semaphore(max(1, concurrency))

    async with httpx.AsyncClient(timeout=30) as client:

        async def _one(sym: str) -> tuple[str, pd.DataFrame]:
            url = (
                f"{BASE}/v2/aggs/ticker/{sym}/range/1/day/"
                f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}"
            )
            async with sem:
                js = await _get_with_retries(client, url)
            if js is None:
                return sym, _empty_df(sym)
            try:
                return sym, _normalize(js, sym)
            except Exception:
                # If JSON format changed or unexpected, fail safe
                return sym, _empty_df(sym)

        pairs = await asyncio.gather(*[_one(s) for s in symbols])
        return {sym: df for sym, df in pairs}