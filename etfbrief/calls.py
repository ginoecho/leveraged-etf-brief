"""Prediction log: every premarket call is appended to calls.jsonl.

One JSON object per line:
{
  "date": "2026-10-15",          # call date (US/Eastern)
  "symbol": "TSLL",
  "ref_price": 9.35,             # premarket / latest quote at call time
  "prev_close": 9.58,
  "bias": "偏空",
  "support": 8.94,
  "resistance": 10.23,
  "invalidation": 10.23,
  "reason": "盘前 -2.3%，跌破昨收"
}
"""

from __future__ import annotations

import datetime as dt
import json
import os

try:
    from zoneinfo import ZoneInfo

    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    ET = None


def today_et() -> str:
    now = dt.datetime.now(ET) if ET else dt.datetime.utcnow()
    return now.date().isoformat()


def append_call(path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_calls(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
