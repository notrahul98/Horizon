"""
Stock data collection using yfinance.
Three collection modes:
  - historical   : full 1-year daily OHLCV history
  - intraday     : today's 5-minute bars
  - fundamentals : key valuation and info fields
"""

import logging
from typing import Optional

import yfinance as yf

from src.database import (
    upsert_stock,
    insert_prices,
    insert_fundamentals,
    start_run,
    finish_run,
)

logger = logging.getLogger(__name__)


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return None if (v != v) else v
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def collect_historical(db_path: str, watchlist: list, period: str = "1y") -> None:
    run_id = start_run(db_path, "historical")
    total_records = 0
    total_errors = 0

    for stock in watchlist:
        symbol = stock["symbol"]
        try:
            logger.info("[historical] fetching %s ...", symbol)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, auto_adjust=False)

            if hist.empty:
                logger.warning("[historical] no data for %s", symbol)
                total_errors += 1
                continue

            info = ticker.fast_info
            upsert_stock(
                db_path,
                symbol=symbol,
                name=stock["name"],
                sector=stock.get("sector"),
                currency=getattr(info, "currency", None),
                exchange=getattr(info, "exchange", None),
            )

            rows = []
            for ts, row in hist.iterrows():
                date_str = ts.strftime("%Y-%m-%d")
                rows.append({
                    "symbol": symbol,
                    "date": date_str,
                    "interval": "day",
                    "open": _safe_float(row.get("Open")),
                    "high": _safe_float(row.get("High")),
                    "low": _safe_float(row.get("Low")),
                    "close": _safe_float(row.get("Close")),
                    "adj_close": _safe_float(row.get("Adj Close")),
                    "volume": _safe_int(row.get("Volume")),
                })

            written = insert_prices(db_path, rows)
            total_records += written
            logger.info("[historical] %s: inserted/replaced %d rows", symbol, written)

        except Exception as exc:
            logger.error("[historical] error for %s: %s", symbol, exc, exc_info=True)
            total_errors += 1

    finish_run(db_path, run_id, records=total_records, errors=total_errors)
    logger.info("[historical] done — %d records, %d errors", total_records, total_errors)


def collect_intraday(db_path: str, watchlist: list,
                     period: str = "1d", interval: str = "5m") -> None:
    run_id = start_run(db_path, "intraday")
    total_records = 0
    total_errors = 0

    for stock in watchlist:
        symbol = stock["symbol"]
        try:
            logger.info("[intraday] fetching %s ...", symbol)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval, auto_adjust=False)

            if hist.empty:
                logger.warning("[intraday] no data for %s", symbol)
                continue

            rows = []
            for ts, row in hist.iterrows():
                date_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                rows.append({
                    "symbol": symbol,
                    "date": date_str,
                    "interval": interval,
                    "open": _safe_float(row.get("Open")),
                    "high": _safe_float(row.get("High")),
                    "low": _safe_float(row.get("Low")),
                    "close": _safe_float(row.get("Close")),
                    "adj_close": _safe_float(row.get("Adj Close")),
                    "volume": _safe_int(row.get("Volume")),
                })

            written = insert_prices(db_path, rows)
            total_records += written
            logger.info("[intraday] %s: inserted/replaced %d bars", symbol, written)

        except Exception as exc:
            logger.error("[intraday] error for %s: %s", symbol, exc, exc_info=True)
            total_errors += 1

    finish_run(db_path, run_id, records=total_records, errors=total_errors)
    logger.info("[intraday] done — %d records, %d errors", total_records, total_errors)


def collect_fundamentals(db_path: str, watchlist: list) -> None:
    run_id = start_run(db_path, "fundamentals")
    total_records = 0
    total_errors = 0

    for stock in watchlist:
        symbol = stock["symbol"]
        try:
            logger.info("[fundamentals] fetching %s ...", symbol)
            ticker = yf.Ticker(symbol)
            info = ticker.info

            insert_fundamentals(db_path, {
                "symbol": symbol,
                "market_cap": _safe_int(info.get("marketCap")),
                "pe_ratio": _safe_float(info.get("trailingPE")),
                "forward_pe": _safe_float(info.get("forwardPE")),
                "dividend_yield": _safe_float(info.get("dividendYield")),
                "beta": _safe_float(info.get("beta")),
                "fifty_two_week_high": _safe_float(info.get("fiftyTwoWeekHigh")),
                "fifty_two_week_low": _safe_float(info.get("fiftyTwoWeekLow")),
                "avg_volume": _safe_int(info.get("averageVolume")),
            })
            total_records += 1
            logger.info("[fundamentals] %s: saved", symbol)

        except Exception as exc:
            logger.error("[fundamentals] error for %s: %s", symbol, exc, exc_info=True)
            total_errors += 1

    finish_run(db_path, run_id, records=total_records, errors=total_errors)
    logger.info("[fundamentals] done — %d records, %d errors", total_records, total_errors)
