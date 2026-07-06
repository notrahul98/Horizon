"""
Console reporting helpers — prints latest prices, recent collection runs,
and per-symbol price history in a readable tabular format.
"""

import logging
from tabulate import tabulate

from src.database import get_latest_prices, get_recent_runs, get_price_history

logger = logging.getLogger(__name__)


def print_latest_prices(db_path: str) -> None:
    rows = get_latest_prices(db_path)
    if not rows:
        print("No price data found. Run a historical collection first.\n")
        return

    table = []
    for r in rows:
        close = r["close"]
        open_ = r["open"]
        change = ((close - open_) / open_ * 100) if open_ else 0.0
        direction = "▲" if change >= 0 else "▼"
        table.append([
            r["symbol"],
            r["name"],
            r["sector"],
            r["date"],
            f"${close:.2f}",
            f"{direction} {abs(change):.2f}%",
            f"{r['volume']:,}" if r["volume"] else "—",
        ])

    print("\n=== Latest Closing Prices ===")
    print(tabulate(table, headers=["Symbol", "Name", "Sector", "Date", "Close", "Day Chg", "Volume"]))
    print()


def print_recent_runs(db_path: str) -> None:
    runs = get_recent_runs(db_path, limit=10)
    if not runs:
        print("No collection runs recorded yet.\n")
        return

    table = [
        [
            r["id"],
            r["run_type"],
            r["started_at"],
            r["finished_at"] or "—",
            r["records_written"],
            r["errors"],
            r["status"],
        ]
        for r in runs
    ]
    print("\n=== Recent Collection Runs ===")
    print(tabulate(table,
                   headers=["ID", "Type", "Started", "Finished", "Records", "Errors", "Status"]))
    print()


def print_symbol_history(db_path: str, symbol: str, limit: int = 10) -> None:
    rows = get_price_history(db_path, symbol.upper(), limit=limit)
    if not rows:
        print(f"No history for {symbol}\n")
        return

    table = [
        [r["date"],
         f"${r['open']:.2f}" if r["open"] else "—",
         f"${r['high']:.2f}" if r["high"] else "—",
         f"${r['low']:.2f}" if r["low"] else "—",
         f"${r['close']:.2f}",
         f"{r['volume']:,}" if r["volume"] else "—"]
        for r in rows
    ]
    print(f"\n=== {symbol.upper()} — Last {limit} Daily Closes ===")
    print(tabulate(table, headers=["Date", "Open", "High", "Low", "Close", "Volume"]))
    print()


def print_status(db_path: str) -> None:
    from src.database import get_status
    s = get_status(db_path)
    print("\n=== Collector Status ===")
    print(f"  Stocks tracked:         {s['stocks']}")
    print(f"  Total price records:    {s['price_records']:,}  ({s['daily_records']:,} daily, {s['intraday_records']:,} intraday)")
    print(f"  Symbols with prices:    {s['priced_symbols']}")
    print(f"  Fundamentals snapshots: {s['fundamentals']}")
    print(f"  Latest daily data:      {s['latest_daily'] or '—'}")
    print(f"  Latest intraday data:   {s['latest_intraday'] or '—'}")
    print(f"  Last collection run:      {s['last_run_at'] or '—'}")
    print()
