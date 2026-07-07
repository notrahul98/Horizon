"""
Phase 5: swing-trade candidate scanner.

A repeatable rule-based screen, same style as agents/*_agent.py's offline
heuristics — not a prediction engine, just a fixed formula applied to
whatever is in price_history right now:

  1. Phase 4's AI consensus says BUY, with HIGH or MEDIUM conviction and
     >= min_confidence.
  2. Trend alignment: close > EMA20 > EMA50 (short/medium-term uptrend).
  3. RSI < 70 (not already overbought — room to run over 5-15 days).

For anything that clears all three, stop-loss and target are derived from
ATR(14), a standard volatility-based swing-trading risk placement — not a
guess: stop = entry - 1.5*ATR, target = entry + reward_risk*(entry-stop).
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def calc_atr(high, low, close, period=14):
    prev_close = close.shift(1)
    true_range = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def scan_for_candidates(symbols, get_stock_detail_fn, get_history_fn, get_ai_consensus_fn,
                         reward_risk=2.5, min_confidence=55, atr_multiple=1.5):
    candidates = []
    for symbol in symbols:
        try:
            detail = get_stock_detail_fn(symbol)
            if not detail:
                continue

            consensus = get_ai_consensus_fn(detail)
            if not consensus or consensus.get("consensus_signal") != "BUY":
                continue
            if consensus.get("conviction") not in ("HIGH", "MEDIUM"):
                continue
            if consensus.get("confidence", 0) < min_confidence:
                continue
            if detail["rsi"] >= 70:
                continue
            if not (detail["close"] > detail["ema20"] > detail["ema50"]):
                continue

            hist = get_history_fn(symbol, 30)
            if hist.empty or len(hist) < 15:
                continue
            atr = calc_atr(hist["high"], hist["low"], hist["close"]).iloc[-1]
            if pd.isna(atr) or atr <= 0:
                continue

            entry = detail["close"]
            stop = round(entry - atr_multiple * atr, 2)
            if stop <= 0 or stop >= entry:
                continue
            target = round(entry + reward_risk * (entry - stop), 2)

            candidates.append({
                "symbol": symbol,
                "entry": entry,
                "stop_loss": stop,
                "target": target,
                "risk_pct": round((entry - stop) / entry * 100, 2),
                "reward_pct": round((target - entry) / entry * 100, 2),
                "confidence": consensus["confidence"],
                "conviction": consensus["conviction"],
                "rsi": detail["rsi"],
                "trend": detail["trend"],
            })
        except Exception:
            logger.exception("[scanner] failed for %s", symbol)
            continue

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return candidates


def format_daily_report(candidates, breadth, total_stocks, gainers, losers, latest_date, top_n=10):
    lines = [
        "*Nifty 150 Terminal — Daily Report*",
        f"_{latest_date}_",
        "",
        f"Tracked: {total_stocks} | Gainers: {gainers} | Losers: {losers}",
    ]
    if breadth:
        lines.append(
            f"Near 52W High: {breadth.get('near_high_count', 0)} | "
            f"Near 52W Low: {breadth.get('near_low_count', 0)} | "
            f"Above 50D Avg: {breadth.get('pct_above_sma50', '—')}%"
        )
    lines.append("")
    lines.append(f"*Swing Candidates — 5-15 day momentum ({len(candidates)} found)*")
    if not candidates:
        lines.append("No candidates cleared the screen today.")
    else:
        for c in candidates[:top_n]:
            sym = c["symbol"].replace(".NS", "")
            lines.append(
                f"• *{sym}* — Entry ₹{c['entry']} | SL ₹{c['stop_loss']} "
                f"(-{c['risk_pct']}%) | Target ₹{c['target']} (+{c['reward_pct']}%) | "
                f"{c['confidence']}% conf ({c['conviction']})"
            )
    lines.append("")
    lines.append(
        "_Rule-based technical screen only — not financial advice. "
        "Verify independently before trading; past setups don't guarantee outcomes._"
    )
    return "\n".join(lines)
