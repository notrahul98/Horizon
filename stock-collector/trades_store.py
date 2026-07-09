"""
Mock-trade storage (Phase 6: mock trading view).

Backed by Turso (hosted libSQL/SQLite, free tier) so trades survive
Railway's ephemeral filesystem — unlike price data, trades can't be
re-fetched after a redeploy wipes the disk.

Talks to Turso via its Hrana-over-HTTP pipeline API using plain `requests`
instead of the libsql client package: no native wheel to build, identical
behavior on the Railway builder and local Windows dev.

Graceful fallback (same pattern as notifications.py / the agents): if
TURSO_DATABASE_URL / TURSO_AUTH_TOKEN aren't set, falls back to a local
SQLite file — fully functional for local dev, but on Railway that file is
wiped on every redeploy, so a warning is logged.
"""

import os
import sqlite3
import logging
import threading

import requests

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_TRADES_DB = os.path.join(_HERE, "data", "trades.db")

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

_schema_ready = False
_schema_lock = threading.Lock()


def turso_enabled() -> bool:
    return bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


def _http_url() -> str:
    # Turso hands out a libsql:// URL; the HTTP pipeline endpoint is the
    # same host over https.
    url = TURSO_DATABASE_URL.replace("libsql://", "https://").rstrip("/")
    return f"{url}/v2/pipeline"


def _encode_arg(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}


def _decode_cell(cell):
    t = cell.get("type")
    v = cell.get("value")
    if t == "null":
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    return v


def _execute(sql: str, args=()) -> list[dict]:
    """Run one statement; returns rows as dicts (empty list for writes)."""
    if turso_enabled():
        resp = requests.post(
            _http_url(),
            headers={"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"},
            json={"requests": [
                {"type": "execute",
                 "stmt": {"sql": sql, "args": [_encode_arg(a) for a in args]}},
                {"type": "close"},
            ]},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()["results"][0]
        if result.get("type") != "ok":
            raise RuntimeError(f"Turso error: {result.get('error', result)}")
        res = result["response"]["result"]
        cols = [c["name"] for c in res.get("cols", [])]
        return [dict(zip(cols, (_decode_cell(c) for c in row)))
                for row in res.get("rows", [])]

    conn = sqlite3.connect(LOCAL_TRADES_DB)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, tuple(args))
        rows = [dict(r) for r in cur.fetchall()]
        conn.commit()
        return rows
    finally:
        conn.close()


def _ensure_schema():
    """Lazy, memoized schema init — deliberately not done at import time so a
    slow/unreachable Turso can never stall app boot; the first trades API
    call pays the one-time round trip instead."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        if not turso_enabled():
            logger.warning(
                "[trades] TURSO_DATABASE_URL/TURSO_AUTH_TOKEN not set — using local "
                "SQLite at %s. On Railway this file is WIPED on every redeploy; "
                "set the Turso env vars for trades to actually persist.",
                LOCAL_TRADES_DB,
            )
        _execute("""
            CREATE TABLE IF NOT EXISTS mock_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 1,
                entry_price REAL NOT NULL,
                entry_date TEXT NOT NULL,
                stop_loss REAL,
                target REAL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                exit_price REAL,
                exit_date TEXT,
                exit_reason TEXT,
                source TEXT NOT NULL DEFAULT 'MANUAL',
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        _schema_ready = True


def add_trade(symbol, quantity, entry_price, entry_date,
              stop_loss=None, target=None, source="MANUAL", notes=None) -> None:
    _ensure_schema()
    _execute(
        """INSERT INTO mock_trades
               (symbol, quantity, entry_price, entry_date, stop_loss, target, source, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [symbol, float(quantity), float(entry_price), str(entry_date),
         float(stop_loss) if stop_loss is not None else None,
         float(target) if target is not None else None,
         source, notes],
    )


def list_trades() -> list[dict]:
    _ensure_schema()
    return _execute("SELECT * FROM mock_trades ORDER BY id DESC")


def open_trades(source=None) -> list[dict]:
    _ensure_schema()
    if source:
        return _execute(
            "SELECT * FROM mock_trades WHERE status='OPEN' AND source=? ORDER BY id",
            [source])
    return _execute("SELECT * FROM mock_trades WHERE status='OPEN' ORDER BY id")


def close_trade(trade_id, exit_price, exit_date, exit_reason="MANUAL") -> None:
    _ensure_schema()
    _execute(
        """UPDATE mock_trades
           SET status='CLOSED', exit_price=?, exit_date=?, exit_reason=?
           WHERE id=? AND status='OPEN'""",
        [float(exit_price), str(exit_date), exit_reason, int(trade_id)],
    )


def delete_trade(trade_id) -> None:
    _ensure_schema()
    _execute("DELETE FROM mock_trades WHERE id=?", [int(trade_id)])
