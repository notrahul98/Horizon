"""
SQLite database setup and all data access operations.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stocks (
                symbol      TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                sector      TEXT,
                currency    TEXT DEFAULT 'USD',
                exchange    TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT NOT NULL REFERENCES stocks(symbol),
                date        TEXT NOT NULL,
                interval    TEXT NOT NULL DEFAULT 'day',
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL NOT NULL,
                adj_close   REAL,
                volume      INTEGER,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(symbol, date, interval)
            );

            CREATE INDEX IF NOT EXISTS idx_price_symbol_date
                ON price_history(symbol, date DESC);

            CREATE TABLE IF NOT EXISTS fundamentals (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol              TEXT NOT NULL REFERENCES stocks(symbol),
                market_cap          INTEGER,
                pe_ratio            REAL,
                forward_pe          REAL,
                dividend_yield      REAL,
                beta                REAL,
                fifty_two_week_high REAL,
                fifty_two_week_low  REAL,
                avg_volume          INTEGER,
                recorded_at         TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_fundamentals_symbol
                ON fundamentals(symbol, recorded_at DESC);

            CREATE TABLE IF NOT EXISTS collection_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type        TEXT NOT NULL,
                started_at      TEXT NOT NULL,
                finished_at     TEXT,
                records_written INTEGER DEFAULT 0,
                errors          INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'running',
                notes           TEXT
            );
        """)
        conn.commit()
    logger.info("Database initialised at %s", db_path)


def upsert_stock(db_path: str, symbol: str, name: str, sector: Optional[str],
                 currency: Optional[str] = None, exchange: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO stocks(symbol, name, sector, currency, exchange, updated_at)
            VALUES(?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name,
                sector=excluded.sector,
                currency=COALESCE(excluded.currency, stocks.currency),
                exchange=COALESCE(excluded.exchange, stocks.exchange),
                updated_at=excluded.updated_at
        """, (symbol, name, sector, currency, exchange))
        conn.commit()


def insert_prices(db_path: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    with get_connection(db_path) as conn:
        cursor = conn.executemany("""
            INSERT OR REPLACE INTO price_history
                (symbol, date, interval, open, high, low, close, adj_close, volume)
            VALUES(:symbol, :date, :interval, :open, :high, :low, :close, :adj_close, :volume)
        """, rows)
        conn.commit()
        return cursor.rowcount


def insert_fundamentals(db_path: str, data: dict) -> None:
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO fundamentals
                (symbol, market_cap, pe_ratio, forward_pe, dividend_yield,
                 beta, fifty_two_week_high, fifty_two_week_low, avg_volume)
            VALUES(:symbol, :market_cap, :pe_ratio, :forward_pe, :dividend_yield,
                   :beta, :fifty_two_week_high, :fifty_two_week_low, :avg_volume)
        """, data)
        conn.commit()


def start_run(db_path: str, run_type: str) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute("""
            INSERT INTO collection_runs(run_type, started_at)
            VALUES(?, datetime('now'))
        """, (run_type,))
        conn.commit()
        return cur.lastrowid


def finish_run(db_path: str, run_id: int, records: int, errors: int,
               status: str = "ok", notes: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("""
            UPDATE collection_runs
            SET finished_at=datetime('now'), records_written=?, errors=?, status=?, notes=?
            WHERE id=?
        """, (records, errors, status, notes, run_id))
        conn.commit()


def get_latest_prices(db_path: str) -> list[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute("""
            SELECT p.symbol, s.name, s.sector,
                   p.date, p.close, p.open, p.high, p.low, p.volume
            FROM price_history p
            JOIN stocks s ON s.symbol = p.symbol
            WHERE p.interval = 'day'
              AND p.date = (
                  SELECT MAX(p2.date)
                  FROM price_history p2
                  WHERE p2.symbol = p.symbol AND p2.interval = 'day'
              )
            ORDER BY s.sector, p.symbol
        """).fetchall()


def get_recent_runs(db_path: str, limit: int = 10) -> list[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute("""
            SELECT * FROM collection_runs
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,)).fetchall()


def get_price_history(db_path: str, symbol: str, limit: int = 30) -> list[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute("""
            SELECT date, open, high, low, close, volume
            FROM price_history
            WHERE symbol=? AND interval='day'
            ORDER BY date DESC
            LIMIT ?
        """, (symbol, limit)).fetchall()


def get_status(db_path: str) -> dict:
    with get_connection(db_path) as conn:
        row = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM stocks)              AS stocks,
                (SELECT COUNT(*) FROM price_history)         AS price_records,
                (SELECT COUNT(DISTINCT symbol) FROM price_history WHERE interval='day') AS priced_symbols,
                (SELECT COUNT(*) FROM price_history WHERE interval='day') AS daily_records,
                (SELECT COUNT(*) FROM price_history WHERE interval!='day') AS intraday_records,
                (SELECT COUNT(*) FROM fundamentals)          AS fundamentals,
                (SELECT MAX(date) FROM price_history WHERE interval='day') AS latest_daily,
                (SELECT MAX(date) FROM price_history WHERE interval!='day') AS latest_intraday,
                (SELECT MAX(started_at) FROM collection_runs) AS last_run_at
        """).fetchone()
    return {
        "stocks": row["stocks"],
        "price_records": row["price_records"],
        "priced_symbols": row["priced_symbols"],
        "daily_records": row["daily_records"],
        "intraday_records": row["intraday_records"],
        "fundamentals": row["fundamentals"],
        "latest_daily": row["latest_daily"],
        "latest_intraday": row["latest_intraday"],
        "last_run_at": row["last_run_at"],
    }
