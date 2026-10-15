"""Market data fetcher.

Uses Yahoo Finance's public chart API directly (no API key needed).
A browser User-Agent is used because some shared egress IPs get
rate-limited (HTTP 429) with library default headers.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.request

try:
    from zoneinfo import ZoneInfo

    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    ET = None


def today_et() -> str:
    now = dt.datetime.now(ET) if ET else dt.datetime.utcnow()
    return now.date().isoformat()

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)
BASE = "https://query1.finance.yahoo.com/v8/finance/chart"


def _get(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_daily(symbol: str, months: int = 3) -> list[dict]:
    """Return daily OHLCV candles, oldest first.

    Each item: {"date": "YYYY-MM-DD", "open", "high", "low", "close", "volume"}.
    """
    url = f"{BASE}/{symbol}?interval=1d&range={months}mo"
    payload = _get(url)
    result = payload["chart"]["result"][0]
    stamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    # 盘中时 Yahoo 会返回今日未收盘的 K 线，剔除，保证只用已收盘的数据
    cutoff = today_et()
    out = []
    for i, ts in enumerate(stamps):
        if quote["close"][i] is None:
            continue
        day = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        if ET is not None:
            day = day.astimezone(ET)
        day = day.date()
        if day.isoformat() >= cutoff:
            continue
        out.append(
            {
                "date": day.isoformat(),
                "open": round(quote["open"][i], 4),
                "high": round(quote["high"][i], 4),
                "low": round(quote["low"][i], 4),
                "close": round(quote["close"][i], 4),
                "volume": quote["volume"][i] or 0,
            }
        )
    return out


def get_quote(symbol: str) -> dict:
    """Return the latest quote snapshot.

    Includes pre-market price when the market is in pre-market hours,
    plus previous close and day range. Times are US/Eastern.
    """
    url = f"{BASE}/{symbol}?interval=1m&range=1d"
    payload = _get(url)
    meta = payload["chart"]["result"][0]["meta"]
    state = (meta.get("marketState") or "").upper()
    session = {"PRE": "盘前", "REGULAR": "盘中", "POST": "盘后"}.get(state, "盘中")
    if state in ("PRE", "POST"):
        ref = meta.get("preMarketPrice") or meta.get("postMarketPrice") or meta.get("regularMarketPrice")
    else:
        ref = meta.get("regularMarketPrice")
    quote = {
        "symbol": symbol,
        "session": session,
        "regular_price": meta.get("regularMarketPrice"),
        "previous_close": meta.get("previousClose") or meta.get("chartPreviousClose"),
        "open": meta.get("regularMarketDayOpen"),
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "premarket_price": meta.get("preMarketPrice"),
        "postmarket_price": meta.get("postMarketPrice"),
        "market_time": dt.datetime.fromtimestamp(
            meta["regularMarketTime"], tz=dt.timezone.utc
        ).isoformat(),
    }
    prev = quote["previous_close"]
    if ref and prev:
        quote["change_pct"] = round((ref - prev) / prev * 100, 2)
    else:
        quote["change_pct"] = None
    quote["ref_price"] = ref
    return quote
