"""Key-level calculation and a transparent, rule-based bias.

The bias here is a *mechanical heuristic*, not investment advice:
it only describes where price sits inside its recent range and how
the pre-market quote gaps versus the previous close. The point of the
tool is that every call is recorded and scored the next day, so the
heuristic's actual hit-rate is visible instead of assumed.
"""

from __future__ import annotations


def key_levels(candles: list[dict], window: int = 5) -> dict:
    """Support/resistance from the last `window` completed daily candles."""
    recent = candles[-window:]
    support = min(c["low"] for c in recent)
    resistance = max(c["high"] for c in recent)
    prev_close = candles[-1]["close"]
    chg_5d = (candles[-1]["close"] - candles[-window]["close"]) / candles[-window]["close"] * 100
    return {
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "prev_close": round(prev_close, 2),
        "chg_5d_pct": round(chg_5d, 2),
        "window": window,
    }


def bias(ref_price: float | None, levels: dict, session: str = "盘前",
         gap_threshold: float = 1.0) -> dict:
    """Mechanical bias from the pre-market (or latest) quote.

    - ref_price > prev_close * (1 + t%) -> 偏多 (bullish)
    - ref_price < prev_close * (1 - t%) -> 偏空 (bearish)
    - otherwise -> 中性 (neutral)

    `invalidation` is the level that proves the call wrong intraday:
    for 偏多 it is the support, for 偏空 the resistance.
    """
    if ref_price is None:
        return {"bias": "未知", "invalidation": None, "reason": "无实时报价"}
    prev = levels["prev_close"]
    gap = (ref_price - prev) / prev * 100
    if gap >= gap_threshold:
        return {
            "bias": "偏多",
            "invalidation": levels["support"],
            "reason": f"{session} +{gap:.1f}%，站上昨收",
        }
    if gap <= -gap_threshold:
        return {
            "bias": "偏空",
            "invalidation": levels["resistance"],
            "reason": f"{session} {gap:.1f}%，跌破昨收",
        }
    pos = ""
    if ref_price <= levels["support"] * 1.01:
        pos = "，贴近 5 日支撑"
    elif ref_price >= levels["resistance"] * 0.99:
        pos = "，贴近 5 日阻力"
    return {
        "bias": "中性",
        "invalidation": None,
        "reason": f"{session} {gap:+.1f}%，无明显缺口{pos}",
    }
