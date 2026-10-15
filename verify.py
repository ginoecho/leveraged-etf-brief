#!/usr/bin/env python3
"""Verify past premarket calls against what actually happened.

Usage:
    python verify.py [--date 2026-10-15] [--scoreboard]

For each call on the given date (default: most recent call date in
calls.jsonl), fetch the *next trading day's* daily candle and score:

- 方向 (direction): did the day close in the direction of the bias?
  偏多 → close > open = 命中, close < open = 落空
  偏空 → close < open = 命中, close > open = 落空
  中性/未知 → 只记录，不打分
- 支撑/阻力: did the day's low/high respect the recorded levels?
- 证伪: was the invalidation level breached intraday?

--scoreboard prints the running hit-rate across all verified calls.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etfbrief import data, calls  # noqa: E402

CALLS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calls.jsonl")


def next_session(candles: list[dict], after: str) -> dict | None:
    for c in candles:
        if c["date"] > after:
            return c
    return None


def score_call(call: dict) -> dict:
    candles = data.get_daily(call["symbol"], months=3)
    session = next_session(candles, call["date"])
    if session is None:
        return {"symbol": call["symbol"], "status": "pending", "note": "下一交易日行情尚未产生"}
    o, h, l, c = session["open"], session["high"], session["low"], session["close"]
    bias = call["bias"]
    direction = "平" if c == o else ("涨" if c > o else "跌")
    if bias == "偏多":
        hit = c > o
    elif bias == "偏空":
        hit = c < o
    else:
        hit = None  # 中性/未知不打分
    support_held = l >= call["support"]
    resistance_capped = h <= call["resistance"]
    invalidated = False
    if call.get("invalidation") is not None:
        if bias == "偏多":
            invalidated = l < call["invalidation"]
        elif bias == "偏空":
            invalidated = h > call["invalidation"]
    return {
        "symbol": call["symbol"],
        "status": "done",
        "session_date": session["date"],
        "ohlc": (o, h, l, c),
        "bias": bias,
        "direction": direction,
        "hit": hit,
        "support_held": support_held,
        "resistance_capped": resistance_capped,
        "invalidated": invalidated,
    }


def render(result: dict, call: dict) -> str:
    if result["status"] == "pending":
        return f"## {call['symbol']}\n\n> {result['note']}\n"
    o, h, l, c = result["ohlc"]
    verdict = "—（中性观点不打分）"
    if result["hit"] is True:
        verdict = "✅ 命中"
    elif result["hit"] is False:
        verdict = "❌ 落空"
    inv = "证伪位被击穿" if result["invalidated"] else "证伪位守住"
    return (
        f"## {call['symbol']}（{call['date']} 的观点 → {result['session_date']} 验证）\n\n"
        f"- 当时观点：**{call['bias']}**（{call['reason']}），参考价 {call['ref_price']}\n"
        f"- 次日实际：开 {o} / 高 {h} / 低 {l} / 收 {c}（{result['direction']}）\n"
        f"- 方向：{verdict}\n"
        f"- 支撑 {call['support']}：{'守住' if result['support_held'] else '跌破'}\n"
        f"- 阻力 {call['resistance']}：{'压住' if result['resistance_capped'] else '突破'}\n"
        f"- {inv}\n"
    )


def scoreboard(all_calls: list[dict]) -> str:
    scored = verified = hits = 0
    per_symbol: dict[str, list[int]] = {}
    for call in all_calls:
        if call["bias"] not in ("偏多", "偏空"):
            continue
        try:
            r = score_call(call)
        except Exception:  # noqa: BLE001
            continue
        if r["status"] != "done":
            continue
        scored += 1
        per_symbol.setdefault(call["symbol"], []).append(1 if r["hit"] else 0)
        if r["hit"]:
            hits += 1
    lines = ["# 观点记分牌", ""]
    if not scored:
        return "\n".join(lines + ["> 暂无可打分的已验证观点。"])
    lines.append(f"- 已验证观点：{scored} 条，命中 {hits} 条，**命中率 {hits / scored:.0%}**")
    for sym, arr in sorted(per_symbol.items()):
        lines.append(f"- {sym}：{sum(arr)}/{len(arr)}（{sum(arr) / len(arr):.0%}）")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="要验证的观点日期，默认最近一次")
    ap.add_argument("--scoreboard", action="store_true")
    args = ap.parse_args()

    all_calls = calls.read_calls(CALLS_PATH)
    if not all_calls:
        print("calls.jsonl 为空，先运行 brief.py 生成并记录观点。")
        return
    if args.scoreboard:
        print(scoreboard(all_calls))
        return

    target = args.date or max(c["date"] for c in all_calls)
    print(f"# 验证 {target} 的盘前观点\n")
    for call in [c for c in all_calls if c["date"] == target]:
        try:
            print(render(score_call(call), call))
        except Exception as e:  # noqa: BLE001
            print(f"## {call['symbol']}\n\n> 验证失败：{e}\n")


if __name__ == "__main__":
    main()
