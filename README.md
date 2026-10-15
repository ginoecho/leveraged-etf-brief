# leveraged-etf-brief

盘前简报生成器 + **次日自我验证**，给 2 倍杠杆单股 ETF 用的（默认 TSLL / NVDL / SPCH，可配置）。

A premarket brief generator with **next-day self-verification** for 2x leveraged
single-stock ETFs (defaults: TSLL / NVDL / SPCH, configurable).

## 它解决什么问题 / What problem it solves

每天盘前看一堆观点，第二天没人记得昨天说了啥。这个工具把每天的观点
**记下来**，第二天用真实行情**打分**，攒出一张记分牌——观点准不准，
用数字说话。

Every premarket call is recorded; the next trading day it's scored against
actual price action. Over time you get a scoreboard instead of vibes.

## 快速开始 / Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. 生成今日简报（自动记入 calls.jsonl）
.venv/bin/python brief.py

# 换标的
.venv/bin/python brief.py --symbols TSLL,NVDL,SPCH,TSLA

# 2. 次日验证昨天的观点（默认验证最近一次）
.venv/bin/python verify.py

# 验证指定日期
.venv/bin/python verify.py --date 2026-10-14

# 3. 看累计记分牌
.venv/bin/python verify.py --scoreboard
```

## 观点是怎么生成的 / How calls are made

机械规则，透明可审计（`etfbrief/levels.py`）：

1. **关键位**：近 5 个已收盘交易日的最高/最低 → 阻力/支撑。
2. **方向**：参考价（盘前价，没有则用最新价）相对昨收的缺口
   - ≥ +1% → 偏多，证伪位 = 支撑
   - ≤ −1% → 偏空，证伪位 = 阻力
   - 之间 → 中性（不打分）
3. 盘中运行时会自动剔除今日未收盘的 K 线，只用已收盘数据。

Mechanical and auditable: support/resistance from the last 5 completed
daily candles; bias from the pre-market gap vs previous close (±1%
threshold); today's forming candle is excluded intraday.

## 验证打什么分 / How verification scores

- **方向**：次日收盘相对开盘的涨跌 vs 观点方向 → ✅ 命中 / ❌ 落空
- **支撑/阻力**：次日最低/最高是否守住记录的关键位
- **证伪**：证伪位盘中是否被击穿
- 中性观点只记录、不打分。

## 数据来源 / Data source

Yahoo Finance 公开行情接口（`query1.finance.yahoo.com`），无需 API key。
使用浏览器 UA 以避免部分共享出口 IP 被限流（HTTP 429）。

## 免责声明 / Disclaimer

本工具生成的观点由机械规则产生，仅供学习和复盘研究，
**不构成任何投资建议**。杠杆 ETF 有日内复利损耗，不适合长期持有。

Calls are rule-based and for research/backtesting only — **not investment
advice**. Leveraged ETFs suffer volatility decay; not for buy-and-hold.

## License

MIT
