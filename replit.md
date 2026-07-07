# Nifty 150 Stock Data Collector

A Python service that collects, stores, and reports on **Indian stock market data**. It pulls daily OHLCV history, intraday 5-minute bars, fundamental metrics, and (Phase 2) corporate actions for the **Nifty 150** index into a local SQLite database, with a built-in scheduler that keeps everything up to date automatically.

**This is the canonical, working system.** A separate Node.js/Postgres rewrite was scaffolded under `lib/` and `artifacts/` but was never wired up (see "Node.js workspace" below) — don't assume it runs.

## Run & Operate

### Stock Collector (Python)
```bash
# Run all collectors once and print a report
python stock-collector/main.py --collect

# Fetch corporate actions (earnings/dividends/insider) once
python stock-collector/main.py --corporate

# Print latest prices and collection history
python stock-collector/main.py --report

# Print database summary
python stock-collector/main.py --status

# Print recent price history for a symbol
python stock-collector/main.py --history RELIANCE.NS

# Start the scheduler (runs forever, Ctrl-C to stop)
python stock-collector/main.py
```

### Dashboard (Flask)
```bash
python stock-collector/launcher.py   # serves dashboard.py on $PORT (default 20702)
```
Two pages: `/` is the overview (KPIs, sector/movers charts, sortable/searchable stock table); clicking a row goes to `/stock/<symbol>`, a full-width page with Technical / Fundamental / Corporate / Company tabs (previously all four were crammed into one 380px side panel alongside the table on a single page). `dashboard.py` also registers the Phase 2 `corporate_bp` blueprint from `corporate_dashboard.py`, though note the actual `/api/corporate/<symbol>` route the frontend calls is a separate live-yfinance implementation inside `dashboard.py` itself, not the blueprint's `/api/corporate/stock/<symbol>` — the blueprint's routes exist but nothing in the UI calls them.

**Daily auto-refresh, no persistent volume required**: Railway's filesystem is ephemeral (no volume attached), so instead of relying on `main.py`'s standalone scheduler, `dashboard.py` runs its own lightweight background job on import — via `APScheduler`'s `BackgroundScheduler` plus a `threading.Thread` for the immediate on-boot run. On every process start it immediately refreshes `price_history` from yfinance (whatever session Yahoo has most recently published), then repeats that at 16:00 IST on weekdays for as long as the process stays up. Only `price_history` is refreshed this way — `fundamentals` and corporate data are fetched live per-request already, so they don't need a stored copy. See `_start_scheduler()` in `dashboard.py`.

### Node.js workspace — scaffolding only, not runnable as-is
`lib/` (db, api-spec, api-zod, api-client-react) and `artifacts/` (api-server, nifty-dashboard, mockup-sandbox) contain an in-progress Node/Postgres/Drizzle rewrite. **It is not wired up**: there is no root `package.json` and no `pnpm-workspace.yaml`, so the `"catalog:"` dependency references in each package's `package.json` don't resolve and `pnpm install` at the repo root will fail. No `DATABASE_URL`/Postgres is actually provisioned or used anywhere yet. Treat this as an unfinished prototype, not a running service — finishing it requires adding the workspace/catalog config and deciding on a Postgres setup before any of the commands below will work:
- `pnpm --filter @workspace/api-server run dev` — intended to run the API server (port 5000)
- `pnpm run build` — intended to typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — intended to regenerate API hooks/Zod schemas from the OpenAPI spec

## Stack

- **Python**: 3.12, yfinance, APScheduler, pandas, tabulate, Flask, plotly
- **Database**: SQLite (at `stock-collector/data/stocks.db`, plus `stock-collector/data/swing_trader.db` for corporate actions)
- **Node.js stack (unfinished prototype, see above)**: pnpm workspaces, Node.js 24, TypeScript 5.9, Express 5, PostgreSQL + Drizzle ORM

## Where things live

```
stock-collector/
  config.py          — Nifty 150 watchlist, DB path, schedule settings
  main.py            — CLI entry point (--collect / --report / --status / --history / --corporate / scheduler)
  launcher.py         — runs the Flask dashboard
  dashboard.py        — main Flask dashboard (price charts, registers corporate_bp)
  corporate_actions.py — Phase 2: earnings/dividends/insider/bulk-block-deal fetch + scoring, writes swing_trader.db
  corporate_dashboard.py — Phase 2: Flask blueprint exposing /api/corporate/* routes
  requirements.txt
  data/stocks.db      — SQLite database (auto-created)
  data/swing_trader.db — Phase 2 corporate_actions table (auto-created)
  data/nifty_150_cache.json — watchlist cache (auto-refreshed every 24h)
  src/
    database.py      — all DB init and CRUD helpers
    collector.py     — yfinance fetch logic (historical, intraday, fundamentals)
    scheduler.py     — APScheduler job definitions (IST timezone)
    reporter.py      — tabular console output

experiments/          — parked prototype: multi-agent (Claude/DeepSeek/Gemini) swing-trading
                        consensus + technical-analysis engine (core/, learning/, agents/, reports/).
                        Not imported by anything else in the repo — revive deliberately or delete.
```

## Database Schema

- `stocks` — symbol, name, sector, currency, exchange
- `price_history` — daily and intraday OHLCV bars (unique on symbol + date + interval)
- `fundamentals` — market cap, P/E, beta, 52-week range (snapshot per run)
- `collection_runs` — audit log of every scheduler run
- `corporate_actions` (in `swing_trader.db`) — earnings/dividend/insider snapshot + generated signal per symbol, one row per fetch (Phase 2)

## Schedule (default, all times Asia/Kolkata)

| Job | Trigger |
|-----|---------|
| Intraday (5-min bars) | Every 15 minutes |
| Daily OHLCV sync | Mon–Fri at 18:00 IST (post market close) |
| Fundamentals snapshot | Sunday at 08:00 IST |
| Corporate actions (Phase 2) | Manual only — run `--corporate`; not on the auto-scheduler yet |

## Architecture decisions

- **Nifty 150 watchlist** — automatically fetched from yfinance with sector/name metadata. Cached for 24 hours so CLI starts instantly; use `--refresh` to force a fresh fetch.
- **IST timezone** — scheduler and all job triggers use `Asia/Kolkata` to align with NSE market hours.
- SQLite chosen for zero-config portability; single WAL-mode file handles concurrent reads.
- `UNIQUE(symbol, date, interval)` constraint with `INSERT OR REPLACE` keeps price_history idempotent — safe to re-run any collector at any time.
- APScheduler `BlockingScheduler` keeps the process alive; `max_instances=1` prevents overlapping jobs.
- Data collected at start-up (historical) before the scheduler fires, so the database is never empty on first run.
- Corporate actions (Phase 2) intentionally left off the auto-scheduler — the deployment doc marks it "optional," and adding 150 automatic weekly yfinance lookups is a call worth making deliberately rather than silently. Wire it into `src/scheduler.py` (see `stock-collector/PHASE2_FINAL_DEPLOYMENT.md` for the originally-suggested cron) once you're ready for it to run unattended.

## Product

Tracks ~140–150 Indian stocks from the Nifty 50, Nifty Next 50, and Nifty Midcap 50 indices. Edit `config.py` → `_NIFTY_150_SYMBOLS` to change the ticker list, or adjust `SCHEDULES` for different collection frequency.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- yfinance `auto_adjust=False` is intentional — stores both `close` and `adj_close` so consumers can choose.
- Indian tickers use `.NS` suffix (e.g., `RELIANCE.NS`, `TCS.NS`).
- `TATAMOTORS.NS` may not be available via yfinance; check the console output for 404 warnings.
- The intraday job stores bars for the current trading day only; historical bars cover 1 year of daily closes.
- Corporate actions data lives in a separate `swing_trader.db` file, not `stocks.db` — a former path bug (`corporate_actions.py` resolving `..` one directory too high) has been fixed; if you see a `data/` folder appear outside `stock-collector/`, that's the old bug re-surfacing from a stale cached `.pyc`.
