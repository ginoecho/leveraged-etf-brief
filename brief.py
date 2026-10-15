#!/usr/bin/env python3
"""Generate a premarket brief for leveraged ETFs and record the day's calls.

Usage:
    python brief.py [--symbols TSLL,NVDL,SPCH] [--out briefs/] [--no-record]

The brief is printed as Markdown and saved to briefs/<date>.md.
Each symbol's call is appended to calls.jsonl for next-day verification
(see verify.py).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etfbrief import data, levels, calls  # noqa: E402

DEFAULT_SYMBOLS = ["TSLL", "NVDL", "SPCH"]


def build_brief(symbols: list[str]) -> tuple[str, list[dict]]:
    lines: list[str] = []
    records = []
    session_title = None
    for sym in symbols:
        try:
            candles = data.get_daily(sym)
            quote = data.get_quote(sym)
        except Exception as e:  # noqa: BLE001
            lines += [f"## {sym}", "", f"> 数据抓取失败：{e}", ""]
            continue
        if session_title is None:
            kind = {"盘前": "盘前简报", "盘中": "盘中快照", "盘后": "盘后复盘"}.get(
                quote.get("session", "盘前"), "盘前简报"
            )
            session_title = f"# {kind} {calls.today_et()}（美东）"
            lines += [session_title, ""]
        lv = levels.key_levels(candles)
        b = levels.bias(quote["ref_price"], lv, session=quote.get("session", "盘前"))
        ref = quote["ref_price"]
        chg = quote["change_pct"]
        chg_str = f"{chg:+.2f}%" if chg is not None else "—"

        lines += [
            f"## {sym}",
            "",
            f"- 参考价：**{ref}**（{chg_str}，前收 {lv['prev_close']}）",
            f"- 关键位：支撑 **{lv['support']}** / 阻力 **{lv['resistance']}**（近 {lv['window']} 日）",
            f"- 5 日涨跌：{lv['chg_5d_pct']:+.2f}%",
            f"- 今日观点：**{b['bias']}**——{b['reason']}",
        ]
        if b["invalidation"] is not None:
            direction_word = "升破" if b["bias"] == "偏空" else "跌破"
            lines.append(f"- 证伪位：{direction_word} **{b['invalidation']}** 则观点失效")
        lines.append("")
        records.append(
            {
                "date": calls.today_et(),
                "symbol": sym,
                "ref_price": ref,
                "prev_close": lv["prev_close"],
                "bias": b["bias"],
                "support": lv["support"],
                "resistance": lv["resistance"],
                "invalidation": b["invalidation"],
                "reason": b["reason"],
            }
        )
    lines += [
        "> 本简报由机械规则生成，仅供复盘研究，不构成投资建议。",
        "> 每条观点已记入 calls.jsonl，次日可用 verify.py 验证打分。",
    ]
    return "\n".join(lines), records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--out", default="briefs")
    ap.add_argument("--no-record", action="store_true", help="只生成简报，不记录预测")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    md, records = build_brief(symbols)
    print(md)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"premarket-{calls.today_et()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(f"\n[brief saved to {path}]", file=sys.stderr)

    if not args.no_record:
        for r in records:
            calls.append_call("calls.jsonl", r)
        print(f"[{len(records)} calls recorded to calls.jsonl]", file=sys.stderr)


if __name__ == "__main__":
    main()
