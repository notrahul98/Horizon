# Nifty 150 Stock Data Collector

A Python service that collects, stores, and reports on **Indian stock market data**. It pulls daily OHLCV history, intraday 5-minute bars, and fundamental metrics for the **Nifty 150** index into a local SQLite database, with a built-in scheduler that keeps everything up to date automatically.

## Run & Operate

### Stock Collector (Python)
```bash
# Run all collectors once and print a report
python stock-collector/main.py --collect

# Print latest prices and collection history
python stock-collector/main.py --report

# Print database summary
python stock-collector/main.py --status

# Print recent price history for a symbol
python stock-collector/main.py --history RELIANCE.NS

# Start the scheduler (runs forever, Ctrl-C to stop)
python stock-collector/main.py
```

### Node.js API Server
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- **Python**: 3.12, yfinance, APScheduler, pandas, tabulate
- **Database**: SQLite (at `stock-collector/data/stocks.db`)
- **Node.js stack**: pnpm workspaces, Node.js 24, TypeScript 5.9, Express 5, PostgreSQL + Drizzle ORM

## Where things live

```
stock-collector/
  config.py          — Nifty 150 watchlist, DB path, schedule settings
  main.py            — CLI entry point (--collect / --report / --status / --history / scheduler)
  requirements.txt
  data/stocks.db     — SQLite database (auto-created)
  data/nifty_150_cache.json — watchlist cache (auto-refreshed every 24h)
  src/
    database.py      — all DB init and CRUD helpers
    collector.py     — yfinance fetch logic (historical, intraday, fundamentals)
    scheduler.py     — APScheduler job definitions (IST timezone)
    reporter.py      — tabular console output
```

## Database Schema

- `stocks` — symbol, name, sector, currency, exchange
- `price_history` — daily and intraday OHLCV bars (unique on symbol + date + interval)
- `fundamentals` — market cap, P/E, beta, 52-week range (snapshot per run)
- `collection_runs` — audit log of every scheduler run

## Schedule (default, all times Asia/Kolkata)

| Job | Trigger |
|-----|---------|
| Intraday (5-min bars) | Every 15 minutes |
| Daily OHLCV sync | Mon–Fri at 18:00 IST (post market close) |
| Fundamentals snapshot | Sunday at 08:00 IST |

## Architecture decisions

- **Nifty 150 watchlist** — automatically fetched from yfinance with sector/name metadata. Cached for 24 hours so CLI starts instantly; use `--refresh` to force a fresh fetch.
- **IST timezone** — scheduler and all job triggers use `Asia/Kolkata` to align with NSE market hours.
- SQLite chosen for zero-config portability; single WAL-mode file handles concurrent reads.
- `UNIQUE(symbol, date, interval)` constraint with `INSERT OR REPLACE` keeps price_history idempotent — safe to re-run any collector at any time.
- APScheduler `BlockingScheduler` keeps the process alive; `max_instances=1` prevents overlapping jobs.
- Data collected at start-up (historical) before the scheduler fires, so the database is never empty on first run.

## Product

Tracks ~140–150 Indian stocks from the Nifty 50, Nifty Next 50, and Nifty Midcap 50 indices. Edit `config.py` → `_NIFTY_150_SYMBOLS` to change the ticker list, or adjust `SCHEDULES` for different collection frequency.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- yfinance `auto_adjust=False` is intentional — stores both `close` and `adj_close` so consumers can choose.
- Indian tickers use `.NS` suffix (e.g., `RELIANCE.NS`, `TCS.NS`).
- `TATAMOTORS.NS` may not be available via yfinance; check the console output for 404 warnings.
- The intraday job stores bars for the current trading day only; historical bars cover 1 year of daily closes.
