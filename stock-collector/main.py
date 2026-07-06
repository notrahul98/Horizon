"""
Entry point for the stock data collector.

Usage:
  python stock-collector/main.py               # start scheduler (runs forever)
  python stock-collector/main.py --collect     # run all collectors once and exit
  python stock-collector/main.py --report      # print latest prices and run history
  python stock-collector/main.py --history TCS.NS  # print recent history for a symbol
  python stock-collector/main.py --status      # print database summary
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    get_watchlist, DB_PATH, SCHEDULES,
    HISTORICAL_PERIOD, INTRADAY_PERIOD, INTRADAY_INTERVAL,
)
from src.database import init_db
from src.collector import collect_historical, collect_intraday, collect_fundamentals
from src.scheduler import build_scheduler
from src.reporter import print_latest_prices, print_recent_runs, print_symbol_history, print_status


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Nifty 150 Stock Data Collector")
    parser.add_argument("--collect",  action="store_true",
                        help="Run all collectors once and exit")
    parser.add_argument("--report",   action="store_true",
                        help="Print latest prices and recent run history, then exit")
    parser.add_argument("--history",  metavar="SYMBOL",
                        help="Print daily price history for SYMBOL, then exit")
    parser.add_argument("--status",   action="store_true",
                        help="Print database summary and exit")
    parser.add_argument("--refresh",  action="store_true",
                        help="Force a fresh watchlist fetch (ignore cache)")
    args = parser.parse_args()

    logger.info("Loading watchlist ...")
    watchlist = get_watchlist(cache_ok=not args.refresh)

    logger.info("Initialising database at %s ...", DB_PATH)
    init_db(DB_PATH)

    symbols_str = ", ".join(s["symbol"] for s in watchlist[:5])
    logger.info("Watchlist (%d): %s ...", len(watchlist), symbols_str)

    if args.report:
        print_latest_prices(DB_PATH)
        print_recent_runs(DB_PATH)
        return

    if args.status:
        print_status(DB_PATH)
        return

    if args.history:
        print_symbol_history(DB_PATH, args.history, limit=30)
        return

    if args.collect:
        logger.info("--- Running one-off collection ---")
        collect_historical(DB_PATH, watchlist, period=HISTORICAL_PERIOD)
        collect_intraday(DB_PATH, watchlist,
                         period=INTRADAY_PERIOD, interval=INTRADAY_INTERVAL)
        collect_fundamentals(DB_PATH, watchlist)
        logger.info("--- One-off collection complete ---")
        print_latest_prices(DB_PATH)
        print_recent_runs(DB_PATH)
        return

    logger.info("Starting scheduler (Ctrl-C to stop) ...")
    logger.info("  Intraday  : every %d min", SCHEDULES["intraday_minutes"])
    logger.info("  Daily     : Mon-Fri at %02d:%02d IST",
                SCHEDULES["daily_hour"], SCHEDULES["daily_minute"])
    logger.info("  Fundamentals: %s at %02d:%02d IST",
                SCHEDULES["weekly_day"].capitalize(),
                SCHEDULES["weekly_hour"], SCHEDULES["weekly_minute"])

    logger.info("Running initial historical collection before starting scheduler ...")
    collect_historical(DB_PATH, watchlist, period=HISTORICAL_PERIOD)

    scheduler = build_scheduler(
        db_path=DB_PATH,
        watchlist=watchlist,
        schedules=SCHEDULES,
        historical_period=HISTORICAL_PERIOD,
        intraday_period=INTRADAY_PERIOD,
        intraday_interval=INTRADAY_INTERVAL,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
