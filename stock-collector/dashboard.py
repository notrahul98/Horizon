"""
Nifty 150 Terminal Dashboard v3
- Corporate data fetched live from Yahoo Finance
- Full interactive dashboard with 4 tabs
"""

import os
import sqlite3
import json
import logging
import threading
from datetime import datetime, timezone, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
from flask import Flask, render_template_string, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import get_watchlist
from src.database import init_db
from src.collector import collect_historical

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")
app = Flask(__name__)
logger = logging.getLogger(__name__)

from corporate_dashboard import corporate_bp
app.register_blueprint(corporate_bp)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ist_now():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%d %b %Y · %H:%M:%S IST")


def _no_bdata(df, *cols):
    """Cast numeric columns to object dtype before handing a DataFrame to
    plotly.express. Plotly compacts numeric numpy arrays into a
    {"dtype","bdata"} binary format at trace-construction time that the
    Plotly.js CDN build loaded client-side can't decode (silently renders
    garbage instead of the chart) — object-dtype columns aren't numeric
    arrays in Plotly's eyes, so they're serialized as plain JSON instead.
    See the same fix applied directly in api_chart() for go.Figure traces."""
    df = df.copy()
    for col in cols:
        df[col] = df[col].astype(object)
    return df


PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#9ca3af", size=11, family="monospace"),
    xaxis=dict(gridcolor="#1f2937", linecolor="#374151", tickfont=dict(color="#6b7280")),
    yaxis=dict(gridcolor="#1f2937", linecolor="#374151", tickfont=dict(color="#6b7280")),
    margin=dict(t=30, b=30, l=50, r=20),
)


def get_latest_df():
    # day_chg here must match get_stock_detail()'s definition (prev close -> today's
    # close), not today's open -> close — otherwise the table and the per-stock detail
    # page show two different numbers for the same "Chg%" label.
    q = """
        SELECT p.symbol, s.name, s.sector,
               p.date, p.close, p.open, p.high, p.low, p.volume,
               (SELECT p2.close FROM price_history p2
                WHERE p2.symbol = p.symbol AND p2.interval = 'day' AND p2.date < p.date
                ORDER BY p2.date DESC LIMIT 1) AS prev_close
        FROM price_history p
        JOIN stocks s ON s.symbol = p.symbol
        WHERE p.interval = 'day'
          AND p.date = (SELECT MAX(p2.date) FROM price_history p2
                        WHERE p2.symbol = p.symbol AND p2.interval = 'day')
        ORDER BY p.symbol
    """
    with get_conn() as c:
        df = pd.read_sql_query(q, c)
    base = df["prev_close"].fillna(df["open"])
    df["day_chg"] = ((df["close"] - base) / base * 100).round(2)
    return df


def get_all_daily_history():
    """Full daily OHLC history for every symbol, for breadth/rotation stats
    that need more than just the latest bar. One bulk query instead of N
    per-symbol ones — 139 symbols x ~250 days is small enough for pandas to
    just chew through in one pass."""
    q = """
        SELECT p.symbol, s.sector, p.date, p.close, p.high, p.low
        FROM price_history p
        JOIN stocks s ON s.symbol = p.symbol
        WHERE p.interval = 'day'
        ORDER BY p.symbol, p.date
    """
    with get_conn() as c:
        df = pd.read_sql_query(q, c, parse_dates=["date"])
    return df


def get_market_breadth(df_all):
    """Advance/decline plus two breadth reads that need historical context
    beyond a single day's snapshot: how many stocks are at a genuine new
    52-week high/low (not just up/down today), and how many are trading
    above their own 50-day average (a broad rally vs a narrow one)."""
    if df_all.empty:
        return {}

    latest = df_all.groupby("symbol").tail(1).set_index("symbol")
    grouped = df_all.groupby("symbol")

    sma50 = grouped["close"].transform(lambda s: s.rolling(50, min_periods=10).mean())
    df_all = df_all.assign(sma50=sma50)
    latest_sma = df_all.groupby("symbol").tail(1).set_index("symbol")["sma50"]

    high_all = grouped["high"].max()
    low_all = grouped["low"].min()

    at_high = (latest["close"] >= high_all).sum()
    at_low = (latest["close"] <= low_all).sum()
    above_sma50 = (latest["close"] > latest_sma).sum()
    total_with_sma = latest_sma.notna().sum()

    return {
        "new_highs": int(at_high),
        "new_lows": int(at_low),
        "pct_above_sma50": round(float(above_sma50) / float(total_with_sma) * 100, 1) if total_with_sma else None,
    }


def get_sector_rotation(df_all, top_n=8, min_stocks=3):
    """Which sectors have gained/lost relative strength recently: compute
    each stock's own % return over the last 5 and 20 trading days (against
    its own date series), then average those returns within each sector.
    Positive + accelerating = money rotating in; negative = rotating out.

    Deliberately averaging per-stock *returns*, not raw price levels across
    stocks: stocks don't always share an identical trading-day calendar
    (e.g. one extra/missing row from a data hiccup), and averaging price
    levels breaks badly on the day where only some stocks have reported —
    the sector "index" swings by whatever the mix of who's-in shifts to,
    which can look like a huge move that isn't real.

    `sector` here is actually yfinance's granular "industry" field (see
    config.py's get_watchlist), so most values have exactly one constituent
    stock — e.g. "Oil & Gas Refining & Marketing" is just RELIANCE. A lone
    stock's move isn't "sector rotation," it's noise wearing a sector's
    name, so anything under min_stocks constituents is dropped rather than
    reported as if it were a real sector signal.
    """
    if df_all.empty:
        return pd.DataFrame(columns=["sector", "chg_5d", "chg_20d"])

    def pct_change_n(series, n):
        if len(series) <= n:
            return None
        prior = series.iloc[-1 - n]
        return (series.iloc[-1] - prior) / prior * 100 if prior else None

    rows = []
    for symbol, group in df_all.sort_values("date").groupby("symbol"):
        closes = group["close"]
        rows.append({
            "symbol": symbol,
            "sector": group["sector"].iloc[-1],
            "chg_5d": pct_change_n(closes, 5),
            "chg_20d": pct_change_n(closes, 20),
        })
    per_stock = pd.DataFrame(rows).dropna(subset=["chg_20d"])

    counts = per_stock.groupby("sector")["symbol"].nunique()
    valid_sectors = counts[counts >= min_stocks].index
    per_stock = per_stock[per_stock["sector"].isin(valid_sectors)]
    if per_stock.empty:
        return pd.DataFrame(columns=["sector", "chg_5d", "chg_20d"])

    out = per_stock.groupby("sector")[["chg_5d", "chg_20d"]].mean().round(2).reset_index()
    return out.sort_values("chg_20d", ascending=False).head(top_n)


def get_history(symbol, days=90):
    q = """SELECT date, open, high, low, close, volume
           FROM price_history
           WHERE symbol=? AND interval='day'
           ORDER BY date DESC LIMIT ?"""
    with get_conn() as c:
        df = pd.read_sql_query(q, c, params=(symbol, days))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return (100 - 100 / (1 + rs)).round(2)


def calc_stochastic(high, low, close, period=14, smooth=3):
    lowest_low = low.rolling(period).min()
    highest_high = high.rolling(period).max()
    rng = (highest_high - lowest_low).replace(0, 1e-9)
    k = (close - lowest_low) / rng * 100
    d = k.rolling(smooth).mean()
    return k, d


def calc_williams_r(high, low, close, period=14):
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    rng = (highest_high - lowest_low).replace(0, 1e-9)
    return (highest_high - close) / rng * -100


def calc_cci(high, low, close, period=20):
    typical = (high + low + close) / 3
    sma = typical.rolling(period).mean()
    mean_dev = typical.rolling(period).apply(lambda x: (x - x.mean()).abs().mean(), raw=False)
    return (typical - sma) / (0.015 * mean_dev.replace(0, 1e-9))


def get_stock_detail(symbol):
    # 260 trading days (~1 calendar year) so 52W high/low are accurate and the
    # longer indicators (SMA50, CCI) have enough warm-up data — the 90-day
    # window used elsewhere is fine for the *chart display* but was silently
    # truncating "52W High/Low" to just the last 90 days here.
    hist = get_history(symbol, 260)
    if hist.empty:
        return {}

    close, high, low = hist["close"], hist["high"], hist["low"]
    latest = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]

    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    rsi = calc_rsi(close).iloc[-1]
    sma20 = close.rolling(20).mean().iloc[-1]
    std20 = close.rolling(20).std().iloc[-1]
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    high_52w = high.max()
    low_52w = low.min()
    avg_vol = hist["volume"].mean()
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = (ema12 - ema26).iloc[-1]
    signal_line = (ema12 - ema26).ewm(span=9).mean().iloc[-1]
    bb_pos = ((latest["close"] - bb_lower) / (bb_upper - bb_lower) * 100) if (bb_upper - bb_lower) > 0 else 50
    trend = "BULLISH" if ema20 > ema50 else "BEARISH"
    trend_color = "#34d399" if trend == "BULLISH" else "#f87171"

    stoch_k, stoch_d = calc_stochastic(high, low, close)
    williams_r = calc_williams_r(high, low, close).iloc[-1]
    cci = calc_cci(high, low, close).iloc[-1]
    stoch_k_val, stoch_d_val = stoch_k.iloc[-1], stoch_d.iloc[-1]

    if rsi < 30:
        rsi_signal = "OVERSOLD"
    elif rsi > 70:
        rsi_signal = "OVERBOUGHT"
    else:
        rsi_signal = "NEUTRAL"

    if stoch_k_val < 20:
        stoch_signal = "OVERSOLD"
    elif stoch_k_val > 80:
        stoch_signal = "OVERBOUGHT"
    else:
        stoch_signal = "NEUTRAL"

    if williams_r < -80:
        williams_signal = "OVERSOLD"
    elif williams_r > -20:
        williams_signal = "OVERBOUGHT"
    else:
        williams_signal = "NEUTRAL"

    if cci > 100:
        cci_signal = "OVERBOUGHT"
    elif cci < -100:
        cci_signal = "OVERSOLD"
    else:
        cci_signal = "NEUTRAL"

    return {
        "symbol": symbol,
        "close": round(float(latest["close"]), 2),
        "open": round(float(latest["open"]), 2),
        "high": round(float(latest["high"]), 2),
        "low": round(float(latest["low"]), 2),
        "volume": int(latest["volume"]),
        "prev_close": round(float(prev["close"]), 2),
        "day_chg": round((latest["close"] - prev["close"]) / prev["close"] * 100, 2),
        "high_52w": round(float(high_52w), 2),
        "low_52w": round(float(low_52w), 2),
        "avg_volume": round(float(avg_vol) / 1e6, 2),
        "ema20": round(float(ema20), 2),
        "ema50": round(float(ema50), 2),
        "rsi": round(float(rsi), 1),
        "rsi_signal": rsi_signal,
        "macd": round(float(macd), 3),
        "macd_signal": round(float(signal_line), 3),
        "bb_upper": round(float(bb_upper), 2),
        "bb_lower": round(float(bb_lower), 2),
        "bb_pos": round(float(bb_pos), 1),
        "trend": trend,
        "trend_color": trend_color,
        "sma20": round(float(sma20), 2),
        "stoch_k": round(float(stoch_k_val), 1) if pd.notna(stoch_k_val) else None,
        "stoch_d": round(float(stoch_d_val), 1) if pd.notna(stoch_d_val) else None,
        "stoch_signal": stoch_signal,
        "williams_r": round(float(williams_r), 1) if pd.notna(williams_r) else None,
        "williams_signal": williams_signal,
        "cci": round(float(cci), 1) if pd.notna(cci) else None,
        "cci_signal": cci_signal,
    }


# ── Daily auto-refresh ──────────────────────────────────────────
# Railway's filesystem is ephemeral (no persistent volume attached), so instead
# of relying on data accumulated over time, every boot pulls whatever session
# yfinance currently has available (today's close if it's past NSE market close,
# otherwise the previous session's), and a background job repeats that at 16:00
# IST daily for as long as this process keeps running. Only price_history needs
# refreshing here — fundamentals/corporate data are fetched live per-request via
# /api/corporate/<symbol> already, not read from the DB.
def _run_daily_refresh():
    try:
        init_db(DB_PATH)
        # Uses config.py's symbol list (not just whatever's already in the DB) so a
        # newly-added ticker gets seeded automatically on the next refresh instead
        # of needing a separate manual backfill step. Relies on the committed
        # nifty_150_cache.json being fresh (<24h old) so this stays a cache hit,
        # not a ~150-symbol live metadata fetch, on every boot.
        watchlist = get_watchlist(cache_ok=True)
        if not watchlist:
            logger.warning("[daily_refresh] empty watchlist, skipping")
            return
        logger.info("[daily_refresh] pulling latest session for %d symbols ...", len(watchlist))
        collect_historical(DB_PATH, watchlist, period="1y")
        logger.info("[daily_refresh] done")
    except Exception:
        logger.exception("[daily_refresh] failed")


def _start_scheduler():
    threading.Thread(target=_run_daily_refresh, daemon=True).start()

    sched = BackgroundScheduler(timezone="Asia/Kolkata")
    sched.add_job(
        _run_daily_refresh,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0),
        id="daily_refresh",
        max_instances=1,
        misfire_grace_time=3600,
    )
    sched.start()


_start_scheduler()


@app.route("/api/stock/<symbol>")
def api_stock(symbol):
    return jsonify(get_stock_detail(symbol))


@app.route("/api/chart/<symbol>")
def api_chart(symbol):
    hist = get_history(symbol, 90)
    if hist.empty:
        return jsonify({"error": "No data"})

    close = hist["close"]
    ema20 = close.ewm(span=20).mean()
    ema50 = close.ewm(span=50).mean()

    # Plotly compacts numpy-backed trace data into a {"dtype","bdata"} binary
    # array format at trace-construction time (not at JSON-dump time, so
    # fixing it after the fact doesn't work) — the Plotly.js CDN build we
    # load client-side is too old to decode that format and silently
    # renders garbage instead of the real chart. Passing plain Python lists
    # (and date strings, not Timestamps) avoids that code path entirely.
    dates = hist["date"].dt.strftime("%Y-%m-%d").tolist()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=dates, open=hist["open"].tolist(), high=hist["high"].tolist(),
        low=hist["low"].tolist(), close=hist["close"].tolist(), name="OHLC",
        increasing_line_color="#34d399", decreasing_line_color="#f87171",
        increasing_fillcolor="#34d399", decreasing_fillcolor="#f87171",
    ))
    fig.add_trace(go.Scatter(x=dates, y=ema20.tolist(), name="EMA20",
        line=dict(color="#38bdf8", width=1.2), opacity=0.8))
    fig.add_trace(go.Scatter(x=dates, y=ema50.tolist(), name="EMA50",
        line=dict(color="#fbbf24", width=1.2), opacity=0.8))
    fig.update_layout(height=280, xaxis_rangeslider_visible=False,
        title=dict(text=f"{symbol} — 90 Day Chart", font=dict(color="#d1d5db", size=12)),
        **PLOTLY_DARK)
    return jsonify({"chart": json.dumps(fig, cls=PlotlyJSONEncoder)})


@app.route("/api/corporate/<symbol>")
def api_corporate(symbol):
    """Fetch corporate data using yfinance (Yahoo Finance works on Railway)"""
    try:
        import yfinance as yf

        if not symbol.endswith('.NS'):
            symbol = symbol + '.NS'

        ticker = yf.Ticker(symbol)
        result = {'symbol': symbol, 'timestamp': datetime.now().isoformat()}

        # EARNINGS
        try:
            info = ticker.info
            quarterly = ticker.quarterly_earnings
            result['earnings'] = {
                'pe_ratio': round(float(info.get('trailingPE', 0) or 0), 2),
                'pb_ratio': round(float(info.get('priceToBook', 0) or 0), 2),
                'market_cap': info.get('marketCap', None),
                'profit_margin': info.get('profitMargins', None),
                'revenue_growth': info.get('revenueGrowth', None),
                'earnings_growth': info.get('earningsGrowth', None),
                'next_earnings_date': None,
                'eps_surprise_pct': None,
                'history': []
            }
            try:
                cal = ticker.calendar
                if cal is not None and 'Earnings Date' in cal.index:
                    result['earnings']['next_earnings_date'] = str(cal.loc['Earnings Date'].iloc[0])
            except Exception:
                pass
            if quarterly is not None and not quarterly.empty:
                actual = float(quarterly.iloc[0].get('Actual', 0) or 0)
                estimate = float(quarterly.iloc[0].get('Estimate', 0) or 0)
                if estimate != 0:
                    result['earnings']['eps_surprise_pct'] = round(((actual - estimate) / abs(estimate)) * 100, 2)
                for date, row in quarterly.head(4).iterrows():
                    result['earnings']['history'].append({
                        'date': str(date)[:10],
                        'actual': round(float(row.get('Actual', 0) or 0), 2),
                        'estimate': round(float(row.get('Estimate', 0) or 0), 2),
                    })
        except Exception as e:
            result['earnings'] = {'error': str(e)}

        # DIVIDENDS
        try:
            info = ticker.info
            dividends = ticker.dividends
            result['dividends'] = {
                'yield': info.get('dividendYield', None),
                'rate': info.get('dividendRate', None),
                'ex_date': None,
                'last_amount': None,
                'history': []
            }
            ex = info.get('exDividendDate', None)
            if ex:
                result['dividends']['ex_date'] = datetime.fromtimestamp(ex).strftime('%Y-%m-%d')
            if dividends is not None and not dividends.empty:
                result['dividends']['last_amount'] = round(float(dividends.iloc[-1]), 2)
                for date, amt in dividends.tail(4).items():
                    result['dividends']['history'].append({
                        'date': str(date.date()), 'amount': round(float(amt), 2)
                    })
        except Exception as e:
            result['dividends'] = {'error': str(e)}

        # HOLDERS
        try:
            major = ticker.major_holders
            inst = ticker.institutional_holders
            result['holders'] = {
                'promoter_pct': None, 'institution_pct': None,
                'public_pct': None, 'top_institutions': []
            }
            if major is not None and not major.empty:
                for _, row in major.iterrows():
                    desc = str(row.iloc[1]).lower()
                    pct = str(row.iloc[0])
                    if 'insider' in desc or 'promoter' in desc:
                        result['holders']['promoter_pct'] = pct
                    elif 'institution' in desc:
                        result['holders']['institution_pct'] = pct
                    elif 'float' in desc or 'public' in desc:
                        result['holders']['public_pct'] = pct
            if inst is not None and not inst.empty:
                for _, row in inst.head(5).iterrows():
                    result['holders']['top_institutions'].append({
                        'name': str(row.get('Holder', '')),
                        'pct': round(float(row.get('% Out', 0) or 0), 2),
                    })
        except Exception as e:
            result['holders'] = {'error': str(e)}

        # COMPANY INFO
        try:
            info = ticker.info
            desc = info.get('longBusinessSummary', '') or ''
            result['company'] = {
                'employees': info.get('fullTimeEmployees', None),
                'industry': info.get('industry', None),
                'sector': info.get('sector', None),
                'description': desc[:300] + '...' if len(desc) > 300 else desc,
                'website': info.get('website', None),
                'beta': round(float(info.get('beta', 0) or 0), 2),
                'country': info.get('country', None),
            }
        except Exception as e:
            result['company'] = {'error': str(e)}

        # SIGNAL
        score = 0; flags = []; reasons = []
        surprise = (result.get('earnings') or {}).get('eps_surprise_pct')
        if surprise:
            if surprise > 10: score += 2; reasons.append(f"Strong earnings beat: +{surprise:.1f}%")
            elif surprise > 0: score += 1; reasons.append(f"Earnings beat: +{surprise:.1f}%")
            elif surprise < -10: score -= 2; flags.append(f"Major miss: {surprise:.1f}%")
            else: score -= 1; flags.append(f"Earnings miss: {surprise:.1f}%")

        dy = (result.get('dividends') or {}).get('yield')
        if dy and float(dy or 0) > 0.03:
            score += 1; reasons.append(f"High dividend: {float(dy)*100:.1f}%")

        pe = (result.get('earnings') or {}).get('pe_ratio', 0) or 0
        if 0 < pe < 15: score += 1; reasons.append(f"Low P/E: {pe:.1f}x")
        elif pe > 50: flags.append(f"High P/E: {pe:.1f}x")

        next_date = (result.get('earnings') or {}).get('next_earnings_date')
        if next_date and str(next_date) != 'None':
            try:
                days = (pd.Timestamp(str(next_date)) - pd.Timestamp.now()).days
                if 0 < days <= 7: flags.append(f"⚠️ Results in {days} days - HIGH RISK"); score -= 1
                elif 0 < days <= 14: flags.append(f"Results in {days} days - be cautious")
            except Exception: pass

        rg = (result.get('earnings') or {}).get('revenue_growth')
        if rg and rg > 0.15: score += 1; reasons.append(f"Revenue growth: +{rg*100:.1f}%")

        if score >= 2: signal = 'STRONG BUY'
        elif score == 1: signal = 'BUY'
        elif score == -1: signal = 'CAUTION'
        elif score <= -2: signal = 'AVOID'
        else: signal = 'NEUTRAL'

        result['signal'] = {'signal': signal, 'score': score, 'flags': flags, 'reasons': reasons}
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e), 'symbol': symbol}), 500


@app.route("/api/stocks")
def api_stocks():
    df = get_latest_df()
    return jsonify(df.to_dict("records"))


@app.route("/")
def index():
    df = get_latest_df()
    if df.empty:
        return "<h1 style='color:#9ca3af;font-family:monospace;padding:40px'>No data yet.</h1>"

    with get_conn() as c:
        records = c.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]

    sec = df.groupby("sector").agg(count=("symbol", "count"), avg_close=("close", "mean")).reset_index()
    sec_fig = px.bar(_no_bdata(sec, "count", "avg_close"), x="sector", y="count", color="avg_close",
                     color_continuous_scale=["#1e3a5f", "#38bdf8"])
    sec_fig.update_layout(xaxis_tickangle=-35, xaxis_title="", yaxis_title="",
                          coloraxis_showscale=False, **PLOTLY_DARK)
    sector_chart = json.dumps(sec_fig, cls=PlotlyJSONEncoder)

    top_g = df.nlargest(8, "day_chg")[["symbol", "day_chg"]].assign(type="Gainer")
    top_l = df.nsmallest(8, "day_chg")[["symbol", "day_chg"]].assign(type="Loser")
    movers = pd.concat([top_g, top_l])
    mov_fig = px.bar(_no_bdata(movers, "day_chg"), y="symbol", x="day_chg", color="type", orientation="h",
                     color_discrete_map={"Gainer": "#34d399", "Loser": "#f87171"})
    mov_fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False,
                          margin=dict(t=10, b=10, l=80, r=20),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#9ca3af", size=11, family="monospace"),
                          xaxis=dict(gridcolor="#1f2937"), yaxis=dict(gridcolor="#1f2937"))
    movers_chart = json.dumps(mov_fig, cls=PlotlyJSONEncoder)

    df_all = get_all_daily_history()
    breadth = get_market_breadth(df_all)
    rotation = get_sector_rotation(df_all)

    rot_fig = px.bar(_no_bdata(rotation.sort_values("chg_20d"), "chg_20d"), y="sector", x="chg_20d", orientation="h",
                     color="chg_20d", color_continuous_scale=["#f87171", "#6b7280", "#34d399"],
                     color_continuous_midpoint=0)
    rot_fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False,
                          margin=dict(t=10, b=10, l=110, r=20), coloraxis_showscale=False,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#9ca3af", size=11, family="monospace"),
                          xaxis=dict(gridcolor="#1f2937"), yaxis=dict(gridcolor="#1f2937"))
    rotation_chart = json.dumps(rot_fig, cls=PlotlyJSONEncoder)

    stocks = df.to_dict("records")
    gainers = len(df[df["day_chg"] > 0])
    losers = len(df[df["day_chg"] < 0])

    return render_template_string(DASHBOARD_HTML,
        ist_time=ist_now(),
        stocks=stocks,
        total=len(df),
        gainers=gainers,
        losers=losers,
        records=f"{records:,}",
        avg_chg=round(df["day_chg"].mean(), 2),
        top_gainer=f"{df.loc[df['day_chg'].idxmax(),'symbol']} +{df['day_chg'].max():.2f}%",
        latest_date=df["date"].max(),
        sector_chart=sector_chart,
        movers_chart=movers_chart,
        rotation_chart=rotation_chart,
        breadth=breadth,
    )


@app.route("/stock/<symbol>")
def stock_page(symbol):
    with get_conn() as c:
        row = c.execute("SELECT symbol, name, sector FROM stocks WHERE symbol=?", (symbol,)).fetchone()
    if row is None:
        return f"<h1 style='color:#9ca3af;font-family:monospace;padding:40px'>Unknown symbol {symbol}</h1>", 404

    return render_template_string(DETAIL_HTML,
        ist_time=ist_now(),
        symbol=row["symbol"],
        name=row["name"],
        sector=row["sector"],
    )


BASE_STYLE = r"""
:root{--bg:#0a0a0f;--card:#111118;--hover:#16161f;--border:#1e1e2a;--text:#9ca3af;--dim:#6b7280;--bright:#e5e7eb;--green:#34d399;--red:#f87171;--blue:#38bdf8;--amber:#fbbf24;--purple:#a78bfa;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:ui-monospace,'SFMono-Regular',Menlo,Monaco,Consolas,monospace;font-size:13px;}
.nav{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;border-bottom:1px solid var(--border);background:#0d0d14;flex-shrink:0;}
.nav-brand{display:flex;align-items:center;gap:10px;}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:blink 2s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.brand-name{color:var(--green);font-size:14px;font-weight:700;letter-spacing:.12em;text-decoration:none;}
.nav-links{display:flex;align-items:center;gap:16px;}
.nav-back{color:var(--dim);text-decoration:none;font-size:11px;}
.nav-back:hover{color:var(--bright);}
.nav-meta{color:var(--dim);font-size:11px;}
.section-title{font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:var(--blue);margin:14px 0 6px;border-bottom:1px solid var(--border);padding-bottom:4px;}
.stat-box{background:var(--card);padding:12px 14px;border-radius:0 8px 8px 0;border-left:3px solid var(--border);}
.stat-label{font-size:9px;color:var(--dim);text-transform:uppercase;margin-bottom:3px;}
.stat-val{font-size:15px;font-weight:700;color:var(--bright);}
.stat-val.g{color:var(--green)}.stat-val.r{color:var(--red)}.stat-val.a{color:var(--amber)}.stat-val.b{color:var(--blue)}.stat-val.p{color:var(--purple)}
.prog-bg{background:var(--border);border-radius:2px;height:5px;width:100%;margin-top:4px;}
.prog-fill{height:5px;border-radius:2px;transition:width .4s;}
.corp-signal{padding:10px 14px;border-radius:4px;text-align:center;font-size:14px;font-weight:700;margin-bottom:10px;}
.corp-flag{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);color:var(--amber);padding:6px 10px;border-radius:3px;margin:4px 0;font-size:12px;}
.corp-reason{background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.2);color:var(--green);padding:6px 10px;border-radius:3px;margin:4px 0;font-size:12px;}
.hist-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:11px;}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--blue);border-radius:50%;animation:spin .8s linear infinite;margin-right:6px;}
@keyframes spin{to{transform:rotate(360deg)}}
"""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nifty 150 Terminal</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
""" + BASE_STYLE + r"""
body{height:100vh;overflow:hidden;display:flex;flex-direction:column;font-size:13px;}
.body{display:grid;grid-template-columns:280px 1fr;flex:1;overflow:hidden;}
.sidebar{border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
.sidebar-kpis{padding:16px;display:flex;flex-direction:column;gap:10px;border-bottom:1px solid var(--border);}
.kpi{background:var(--card);border-left:3px solid;border-radius:0 8px 8px 0;padding:12px 14px;}
.kpi.g{border-color:var(--green)}.kpi.b{border-color:var(--blue)}.kpi.a{border-color:var(--amber)}.kpi.r{border-color:var(--red)}.kpi.p{border-color:var(--purple)}
.kpi-label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin-bottom:5px;}
.kpi-val{font-size:24px;font-weight:700;}
.kpi-val.g{color:var(--green)}.kpi-val.b{color:var(--blue)}.kpi-val.a{color:var(--amber)}.kpi-val.r{color:var(--red)}.kpi-val.p{color:var(--purple)}
.sidebar-charts{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:16px;}
.chart-label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin-bottom:6px;}
.chart-box{height:190px;}
.main{display:flex;flex-direction:column;overflow:hidden;}
.table-header{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:16px;flex-wrap:wrap;}
.tbl-title{font-size:11px;color:var(--dim);}
.search-box{background:var(--bg);border:1px solid var(--border);color:var(--bright);padding:7px 14px;border-radius:6px;font-family:inherit;font-size:13px;width:240px;}
.search-box:focus{outline:none;border-color:var(--blue);}
.table-wrap{flex:1;overflow:auto;}
table{width:100%;border-collapse:collapse;}
thead th{position:sticky;top:0;background:#0d0d14;padding:11px 16px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);border-bottom:1px solid var(--border);cursor:pointer;user-select:none;white-space:nowrap;z-index:2;}
thead th:hover{color:var(--bright);}
thead th.r{text-align:right;}
thead th.sym-col{position:sticky;left:0;z-index:3;}
tbody td{padding:12px 16px;border-bottom:1px solid rgba(30,30,42,.8);white-space:nowrap;}
tbody tr{cursor:pointer;transition:background .1s;}
tbody tr:hover{background:var(--hover);}
tbody tr:hover .sym-col{background:var(--hover);}
.sym-col{position:sticky;left:0;background:var(--bg);border-left:3px solid transparent;}
.sym-col.up{border-left-color:var(--green);}
.sym-col.dn{border-left-color:var(--red);}
.sym{font-weight:700;color:var(--bright);font-size:14px;display:block;}
.name-sub{color:var(--dim);font-size:11px;margin-top:2px;max-width:170px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.tag{font-size:10px;padding:3px 7px;border-radius:4px;background:#1f2937;color:var(--dim);}
.num{text-align:right;}
.up{color:var(--green);font-weight:700;}
.dn{color:var(--red);font-weight:700;}
.dim{color:var(--dim);}
@media(max-width:1000px){
  .body{grid-template-columns:1fr}
  .sidebar{flex-direction:row;flex-wrap:wrap;border-right:none;border-bottom:1px solid var(--border);}
  .sidebar-kpis{flex-direction:row;flex-wrap:wrap;border-bottom:none;flex:1;}
  .kpi{flex:1;min-width:120px;}
  .sidebar-charts{display:none;}
}
@media(max-width:760px){.hide-narrow{display:none;}}
@media(max-width:560px){.hide-mobile{display:none;}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="dot"></div>
    <span class="brand-name">NIFTY 150 TERMINAL</span>
  </div>
  <div class="nav-meta" id="navTime">{{ ist_time }}</div>
</nav>
<div class="body">
  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="sidebar-kpis">
      <div class="kpi g"><div class="kpi-label">Stocks</div><div class="kpi-val g">{{ total }}</div></div>
      <div class="kpi b"><div class="kpi-label">Price Records</div><div class="kpi-val b">{{ records }}</div></div>
      <div class="kpi {% if avg_chg >= 0 %}g{% else %}r{% endif %}">
        <div class="kpi-label">Avg Change</div>
        <div class="kpi-val {% if avg_chg >= 0 %}g{% else %}r{% endif %}">{% if avg_chg >= 0 %}+{% endif %}{{ avg_chg }}%</div>
      </div>
      <div class="kpi g"><div class="kpi-label">Gainers</div><div class="kpi-val g">{{ gainers }}</div></div>
      <div class="kpi r"><div class="kpi-label">Losers</div><div class="kpi-val r">{{ losers }}</div></div>
      <div class="kpi a"><div class="kpi-label">Top Gainer</div><div class="kpi-val a" style="font-size:13px">{{ top_gainer }}</div></div>
      <div class="kpi g"><div class="kpi-label">New 52W Highs</div><div class="kpi-val g">{{ breadth.new_highs }}</div></div>
      <div class="kpi r"><div class="kpi-label">New 52W Lows</div><div class="kpi-val r">{{ breadth.new_lows }}</div></div>
      {% if breadth.pct_above_sma50 is not none %}
      <div class="kpi {% if breadth.pct_above_sma50 >= 50 %}g{% else %}r{% endif %}">
        <div class="kpi-label">Above 50D Avg</div>
        <div class="kpi-val {% if breadth.pct_above_sma50 >= 50 %}g{% else %}r{% endif %}">{{ breadth.pct_above_sma50 }}%</div>
      </div>
      {% endif %}
    </div>
    <div class="sidebar-charts">
      <div><div class="chart-label">Sector Rotation · 20D</div><div class="chart-box" id="rot-chart"></div></div>
      <div><div class="chart-label">Sector Distribution</div><div class="chart-box" id="sec-chart"></div></div>
      <div><div class="chart-label">Top Movers</div><div class="chart-box" id="mov-chart"></div></div>
    </div>
  </div>
  <!-- MAIN TABLE -->
  <div class="main">
    <div class="table-header">
      <span class="tbl-title">{{ latest_date }} · {{ total }} stocks · click a row for full details</span>
      <input class="search-box" id="searchBox" placeholder="Search symbol, name, sector..." oninput="filterTable()">
    </div>
    <div class="table-wrap">
      <table id="stockTable">
        <thead>
          <tr>
            <th class="sym-col" onclick="sortTable('sym')">Symbol</th>
            <th class="hide-narrow">Sector</th>
            <th class="r" onclick="sortTable('close')">Close ₹</th>
            <th class="r" onclick="sortTable('chg')">Chg%</th>
            <th class="r hide-narrow" onclick="sortTable('high')">High</th>
            <th class="r hide-narrow" onclick="sortTable('low')">Low</th>
            <th class="r hide-mobile" onclick="sortTable('vol')">Volume</th>
          </tr>
        </thead>
        <tbody id="stockBody">
          {% for s in stocks %}
          <tr onclick="location.href='/stock/{{ s.symbol }}'"
              data-sym="{{ s.symbol }}" data-name="{{ s.name }}" data-sector="{{ s.sector }}"
              data-close="{{ s.close }}" data-chg="{{ s.day_chg }}"
              data-high="{{ s.high }}" data-low="{{ s.low }}" data-vol="{{ s.volume }}">
            <td class="sym-col {% if s.day_chg >= 0 %}up{% else %}dn{% endif %}">
              <span class="sym">{{ s.symbol.replace('.NS','') }}</span>
              <span class="name-sub">{{ s.name }}</span>
            </td>
            <td class="hide-narrow"><span class="tag">{{ s.sector[:16] }}</span></td>
            <td class="num">₹{{ "%.2f"|format(s.close) }}</td>
            <td class="num {% if s.day_chg >= 0 %}up{% else %}dn{% endif %}">{% if s.day_chg >= 0 %}+{% endif %}{{ "%.2f"|format(s.day_chg) }}%</td>
            <td class="num hide-narrow">{{ "%.2f"|format(s.high) }}</td>
            <td class="num hide-narrow">{{ "%.2f"|format(s.low) }}</td>
            <td class="num dim hide-mobile">{{ "{:.1f}M".format(s.volume/1000000) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
<script>
var secChart={{ sector_chart|safe }};
var movChart={{ movers_chart|safe }};
var rotChart={{ rotation_chart|safe }};
Plotly.newPlot('sec-chart',secChart.data,secChart.layout,{displayModeBar:false,responsive:true});
Plotly.newPlot('mov-chart',movChart.data,movChart.layout,{displayModeBar:false,responsive:true});
Plotly.newPlot('rot-chart',rotChart.data,rotChart.layout,{displayModeBar:false,responsive:true});

// Live clock — must format in Asia/Kolkata explicitly, otherwise the browser's
// own local timezone gets applied on top and the displayed time drifts.
setInterval(()=>{
  document.getElementById('navTime').textContent=new Date().toLocaleString('en-IN',{
    day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',
    hour12:false,timeZone:'Asia/Kolkata'
  })+' IST';
},1000);

// Search
function filterTable(){
  const q=document.getElementById('searchBox').value.toLowerCase();
  document.querySelectorAll('#stockBody tr').forEach(row=>{
    const match=row.dataset.sym.toLowerCase().includes(q)||row.dataset.name.toLowerCase().includes(q)||row.dataset.sector.toLowerCase().includes(q);
    row.style.display=match?'':'none';
  });
}

// Sort
let sortDir={};
function sortTable(col){
  const rows=Array.from(document.querySelectorAll('#stockBody tr'));
  const dir=sortDir[col]===1?-1:1;
  sortDir[col]=dir;
  rows.sort((a,b)=>{
    const av=a.dataset[col]||'';
    const bv=b.dataset[col]||'';
    if(!isNaN(av)&&!isNaN(bv)) return dir*(parseFloat(av)-parseFloat(bv));
    return dir*av.localeCompare(bv);
  });
  const tbody=document.getElementById('stockBody');
  rows.forEach(r=>tbody.appendChild(r));
}
</script>
</body>
</html>"""

DETAIL_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ symbol.replace('.NS','') }} — Nifty 150 Terminal</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
""" + BASE_STYLE + r"""
body{min-height:100vh;}
.page{max-width:1100px;margin:0 auto;padding:20px 24px 60px;}
.detail-header{padding:16px 0;border-bottom:1px solid var(--border);margin-bottom:16px;}
.detail-sym{font-size:24px;font-weight:700;color:var(--bright);}
.detail-name{color:var(--dim);font-size:12px;margin-top:3px;}
.detail-price{display:flex;align-items:baseline;gap:12px;margin-top:10px;}
.price{font-size:32px;font-weight:700;color:var(--bright);}
.chg{font-size:16px;font-weight:700;}
.detail-tabs{display:flex;gap:4px;border-bottom:1px solid var(--border);margin-bottom:16px;}
.tab{padding:10px 18px;cursor:pointer;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);border-bottom:2px solid transparent;transition:all .2s;}
.tab:hover{color:var(--bright);}
.tab.active{color:var(--blue);border-bottom-color:var(--blue);}
.tab-content{display:none;}
.tab-content.active{display:block;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;}
.grid4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:10px;}
@media(max-width:800px){.grid3,.grid4{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.grid2,.grid3,.grid4{grid-template-columns:1fr}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <a href="/" class="brand-name"><div class="dot" style="display:inline-block;vertical-align:middle;margin-right:8px"></div>NIFTY 150 TERMINAL</a>
  </div>
  <div class="nav-links">
    <a href="/" class="nav-back">← Dashboard</a>
    <div class="nav-meta" id="navTime">{{ ist_time }}</div>
  </div>
</nav>
<div class="page">
  <div class="detail-header">
    <div class="detail-sym">{{ symbol.replace('.NS','') }}</div>
    <div class="detail-name">{{ name }} · {{ sector }}</div>
    <div class="detail-price">
      <span class="price" id="detailPrice">-</span>
      <span class="chg" id="detailChg">-</span>
    </div>
  </div>
  <div class="detail-tabs">
    <div class="tab active" onclick="switchTab('technical')">Technical</div>
    <div class="tab" onclick="switchTab('fundamental')">Fundamental</div>
    <div class="tab" onclick="switchTab('corporate')">Corporate</div>
    <div class="tab" onclick="switchTab('company')">Company</div>
  </div>

  <!-- TECHNICAL TAB -->
  <div class="tab-content active" id="tab-technical">
    <div id="detailChart" style="height:380px"></div>
    <div class="section-title">Today's Trading</div>
    <div class="grid4">
      <div class="stat-box"><div class="stat-label">Open</div><div class="stat-val" id="d-open">-</div></div>
      <div class="stat-box"><div class="stat-label">High</div><div class="stat-val g" id="d-high">-</div></div>
      <div class="stat-box"><div class="stat-label">Low</div><div class="stat-val r" id="d-low">-</div></div>
      <div class="stat-box"><div class="stat-label">Prev Close</div><div class="stat-val" id="d-prev">-</div></div>
      <div class="stat-box"><div class="stat-label">52W High</div><div class="stat-val g" id="d-52h">-</div></div>
      <div class="stat-box"><div class="stat-label">52W Low</div><div class="stat-val r" id="d-52l">-</div></div>
      <div class="stat-box"><div class="stat-label">Today Vol</div><div class="stat-val b" id="d-vol">-</div></div>
      <div class="stat-box"><div class="stat-label">90D Avg Vol</div><div class="stat-val" id="d-avgvol">-</div></div>
    </div>
    <div class="section-title">Indicators</div>
    <div class="grid4">
      <div class="stat-box">
        <div class="stat-label">Trend (EMA20 vs EMA50)</div>
        <div class="stat-val" id="d-trend">-</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">RSI (14)</div>
        <div class="stat-val" id="d-rsi">-</div>
        <div class="prog-bg"><div class="prog-fill" id="d-rsi-bar" style="width:50%;background:#38bdf8"></div></div>
      </div>
      <div class="stat-box"><div class="stat-label">EMA 20</div><div class="stat-val b" id="d-ema20">-</div></div>
      <div class="stat-box"><div class="stat-label">EMA 50</div><div class="stat-val a" id="d-ema50">-</div></div>
      <div class="stat-box"><div class="stat-label">MACD</div><div class="stat-val" id="d-macd">-</div></div>
      <div class="stat-box"><div class="stat-label">Signal Line</div><div class="stat-val" id="d-macd-sig">-</div></div>
      <div class="stat-box">
        <div class="stat-label">Stochastic %K/%D</div>
        <div class="stat-val" id="d-stoch">-</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Williams %R (14)</div>
        <div class="stat-val" id="d-williams">-</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">CCI (20)</div>
        <div class="stat-val" id="d-cci">-</div>
      </div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Bollinger Band Position</div>
      <div class="stat-val" id="d-bb-pos">-</div>
      <div class="prog-bg"><div class="prog-fill" id="d-bb-bar" style="width:50%;background:#a78bfa"></div></div>
      <div style="display:flex;justify-content:space-between;margin-top:4px;color:var(--dim);font-size:10px">
        <span id="d-bb-low">Lower</span><span id="d-bb-up">Upper</span>
      </div>
    </div>
  </div>

  <!-- FUNDAMENTAL TAB -->
  <div class="tab-content" id="tab-fundamental">
    <div id="fund-loading" style="color:var(--dim);padding:20px;text-align:center">
      <span class="spinner"></span> Loading fundamentals...
    </div>
    <div id="fund-content" style="display:none">
      <div class="section-title">Valuation</div>
      <div class="grid3">
        <div class="stat-box"><div class="stat-label">P/E Ratio</div><div class="stat-val" id="f-pe">-</div></div>
        <div class="stat-box"><div class="stat-label">P/B Ratio</div><div class="stat-val b" id="f-pb">-</div></div>
        <div class="stat-box"><div class="stat-label">Market Cap</div><div class="stat-val p" id="f-mcap">-</div></div>
      </div>
      <div class="section-title">Growth</div>
      <div class="grid4">
        <div class="stat-box"><div class="stat-label">Revenue Growth</div><div class="stat-val" id="f-revg">-</div></div>
        <div class="stat-box"><div class="stat-label">Earnings Growth</div><div class="stat-val" id="f-earng">-</div></div>
        <div class="stat-box"><div class="stat-label">Profit Margin</div><div class="stat-val" id="f-margin">-</div></div>
        <div class="stat-box"><div class="stat-label">Beta</div><div class="stat-val a" id="f-beta">-</div></div>
      </div>
      <div class="section-title">Dividends</div>
      <div class="grid4">
        <div class="stat-box"><div class="stat-label">Yield</div><div class="stat-val g" id="f-yield">-</div></div>
        <div class="stat-box"><div class="stat-label">Annual Rate</div><div class="stat-val" id="f-rate">-</div></div>
        <div class="stat-box"><div class="stat-label">Ex-Date</div><div class="stat-val a" id="f-exdate">-</div></div>
        <div class="stat-box"><div class="stat-label">Last Dividend</div><div class="stat-val" id="f-lastdiv">-</div></div>
      </div>
      <div class="section-title">Dividend History</div>
      <div id="f-divhist"></div>
    </div>
  </div>

  <!-- CORPORATE TAB -->
  <div class="tab-content" id="tab-corporate">
    <div id="corp-loading" style="color:var(--dim);padding:20px;text-align:center">
      <span class="spinner"></span> Loading corporate data...
    </div>
    <div id="corp-content" style="display:none">
      <div class="section-title">Corporate Signal</div>
      <div class="corp-signal" id="c-signal">-</div>
      <div id="c-flags"></div>
      <div id="c-reasons"></div>
      <div class="section-title">Earnings Calendar</div>
      <div class="grid2">
        <div class="stat-box"><div class="stat-label">Next Results</div><div class="stat-val a" id="c-nextdate" style="font-size:12px">-</div></div>
        <div class="stat-box"><div class="stat-label">EPS Surprise</div><div class="stat-val" id="c-surprise">-</div></div>
      </div>
      <div class="section-title">EPS History (Last 4 Quarters)</div>
      <div id="c-epshist"></div>
      <div class="section-title">Shareholding</div>
      <div class="grid3">
        <div class="stat-box"><div class="stat-label">Promoter</div><div class="stat-val g" id="c-promoter">-</div></div>
        <div class="stat-box"><div class="stat-label">Institution</div><div class="stat-val b" id="c-inst">-</div></div>
        <div class="stat-box"><div class="stat-label">Public</div><div class="stat-val" id="c-public">-</div></div>
      </div>
      <div class="section-title">Top Institutional Holders</div>
      <div id="c-institutions"></div>
    </div>
  </div>

  <!-- COMPANY TAB -->
  <div class="tab-content" id="tab-company">
    <div id="comp-loading" style="color:var(--dim);padding:20px;text-align:center">
      <span class="spinner"></span> Loading company info...
    </div>
    <div id="comp-content" style="display:none">
      <div class="section-title">Company Profile</div>
      <div class="grid4">
        <div class="stat-box"><div class="stat-label">Industry</div><div class="stat-val" id="co-industry" style="font-size:12px">-</div></div>
        <div class="stat-box"><div class="stat-label">Country</div><div class="stat-val" id="co-country">-</div></div>
        <div class="stat-box"><div class="stat-label">Employees</div><div class="stat-val b" id="co-emp">-</div></div>
        <div class="stat-box"><div class="stat-label">Website</div><div class="stat-val" id="co-web" style="font-size:11px">-</div></div>
      </div>
      <div class="section-title">About</div>
      <div id="co-desc" style="font-size:12px;color:var(--text);line-height:1.7;background:var(--bg);padding:12px;border-radius:3px;border:1px solid var(--border)">-</div>
    </div>
  </div>
</div>
<script>
const sym="{{ symbol }}";

// Live clock — see comment in dashboard template re: explicit timeZone.
setInterval(()=>{
  document.getElementById('navTime').textContent=new Date().toLocaleString('en-IN',{
    day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',
    hour12:false,timeZone:'Asia/Kolkata'
  })+' IST';
},1000);

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelector(`.tab[onclick="switchTab('${name}')"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
}

async function loadChart(){
  try{
    const r=await fetch(`/api/chart/${sym}`);
    const data=await r.json();
    if(data.chart){
      const fig=JSON.parse(data.chart);
      Plotly.newPlot('detailChart',fig.data,fig.layout,{displayModeBar:false,responsive:true});
    }
  }catch(e){}
}

async function loadTechnical(){
  try{
    const r=await fetch(`/api/stock/${sym}`);
    const d=await r.json();
    document.getElementById('detailPrice').textContent=`₹${d.close}`;
    const chgEl=document.getElementById('detailChg');
    chgEl.textContent=`${d.day_chg>=0?'+':''}${d.day_chg}%`;
    chgEl.style.color=d.day_chg>=0?'#34d399':'#f87171';
    document.getElementById('d-open').textContent=`₹${d.open}`;
    document.getElementById('d-high').textContent=`₹${d.high}`;
    document.getElementById('d-low').textContent=`₹${d.low}`;
    document.getElementById('d-prev').textContent=`₹${d.prev_close}`;
    document.getElementById('d-52h').textContent=`₹${d.high_52w}`;
    document.getElementById('d-52l').textContent=`₹${d.low_52w}`;
    const trendEl=document.getElementById('d-trend');
    trendEl.textContent=d.trend;
    trendEl.style.color=d.trend_color;
    const rsiEl=document.getElementById('d-rsi');
    rsiEl.textContent=`${d.rsi} — ${d.rsi_signal}`;
    rsiEl.style.color=d.rsi<30?'#34d399':d.rsi>70?'#f87171':'#9ca3af';
    document.getElementById('d-rsi-bar').style.width=`${Math.min(d.rsi,100)}%`;
    document.getElementById('d-rsi-bar').style.background=d.rsi<30?'#34d399':d.rsi>70?'#f87171':'#38bdf8';
    document.getElementById('d-ema20').textContent=`₹${d.ema20}`;
    document.getElementById('d-ema50').textContent=`₹${d.ema50}`;
    const macdEl=document.getElementById('d-macd');
    macdEl.textContent=d.macd;
    macdEl.style.color=d.macd>0?'#34d399':'#f87171';
    const sigEl=document.getElementById('d-macd-sig');
    sigEl.textContent=d.macd_signal;
    sigEl.style.color=d.macd_signal>0?'#34d399':'#f87171';
    document.getElementById('d-bb-pos').textContent=`${d.bb_pos}% between bands`;
    document.getElementById('d-bb-bar').style.width=`${Math.min(Math.max(d.bb_pos,0),100)}%`;
    document.getElementById('d-bb-low').textContent=`₹${d.bb_lower}`;
    document.getElementById('d-bb-up').textContent=`₹${d.bb_upper}`;
    document.getElementById('d-vol').textContent=`${(d.volume/1e6).toFixed(1)}M`;
    document.getElementById('d-avgvol').textContent=`${d.avg_volume}M`;

    const stochEl=document.getElementById('d-stoch');
    if(d.stoch_k!=null){
      stochEl.textContent=`${d.stoch_k} / ${d.stoch_d ?? '-'} — ${d.stoch_signal}`;
      stochEl.style.color=d.stoch_signal==='OVERSOLD'?'#34d399':d.stoch_signal==='OVERBOUGHT'?'#f87171':'#9ca3af';
    } else { stochEl.textContent='N/A'; }

    const willEl=document.getElementById('d-williams');
    if(d.williams_r!=null){
      willEl.textContent=`${d.williams_r} — ${d.williams_signal}`;
      willEl.style.color=d.williams_signal==='OVERSOLD'?'#34d399':d.williams_signal==='OVERBOUGHT'?'#f87171':'#9ca3af';
    } else { willEl.textContent='N/A'; }

    const cciEl=document.getElementById('d-cci');
    if(d.cci!=null){
      cciEl.textContent=`${d.cci} — ${d.cci_signal}`;
      cciEl.style.color=d.cci_signal==='OVERSOLD'?'#34d399':d.cci_signal==='OVERBOUGHT'?'#f87171':'#9ca3af';
    } else { cciEl.textContent='N/A'; }
  }catch(e){console.error(e);}
}

async function loadCorporate(){
  try{
    const r=await fetch(`/api/corporate/${sym}`);
    const d=await r.json();
    if(d.error){
      document.getElementById('fund-loading').textContent='⚠️ '+d.error;
      document.getElementById('corp-loading').textContent='⚠️ '+d.error;
      document.getElementById('comp-loading').textContent='⚠️ '+d.error;
      return;
    }

    // ---- FUNDAMENTALS TAB ----
    const e=d.earnings||{};
    const dv=d.dividends||{};
    const co=d.company||{};

    document.getElementById('f-pe').textContent=e.pe_ratio||'N/A';
    document.getElementById('f-pe').style.color=e.pe_ratio>0&&e.pe_ratio<15?'#34d399':e.pe_ratio>50?'#f87171':'#e5e7eb';
    document.getElementById('f-pb').textContent=e.pb_ratio||'N/A';
    document.getElementById('f-mcap').textContent=e.market_cap?`₹${(e.market_cap/1e9).toFixed(0)}B`:'N/A';
    const revg=e.revenue_growth;
    document.getElementById('f-revg').textContent=revg!=null?`${(revg*100).toFixed(1)}%`:'N/A';
    document.getElementById('f-revg').style.color=revg>0?'#34d399':'#f87171';
    const eg=e.earnings_growth;
    document.getElementById('f-earng').textContent=eg!=null?`${(eg*100).toFixed(1)}%`:'N/A';
    document.getElementById('f-earng').style.color=eg>0?'#34d399':'#f87171';
    const pm=e.profit_margin;
    document.getElementById('f-margin').textContent=pm!=null?`${(pm*100).toFixed(1)}%`:'N/A';
    document.getElementById('f-margin').style.color=pm>0?'#34d399':'#f87171';
    document.getElementById('f-beta').textContent=co.beta||'N/A';
    document.getElementById('f-yield').textContent=dv.yield!=null?`${(dv.yield*100).toFixed(2)}%`:'N/A';
    document.getElementById('f-rate').textContent=dv.rate?`₹${dv.rate}`:'N/A';
    document.getElementById('f-exdate').textContent=dv.ex_date||'N/A';
    document.getElementById('f-lastdiv').textContent=dv.last_amount?`₹${dv.last_amount}`:'N/A';

    const divH=document.getElementById('f-divhist');
    if(dv.history&&dv.history.length>0){
      divH.innerHTML=dv.history.map(h=>`<div class="hist-row"><span style="color:var(--dim)">${h.date}</span><span style="color:#34d399">₹${h.amount}</span></div>`).join('');
    } else {
      divH.innerHTML='<div style="color:var(--dim);font-size:11px">No dividend history</div>';
    }

    document.getElementById('fund-loading').style.display='none';
    document.getElementById('fund-content').style.display='block';

    // ---- CORPORATE TAB ----
    const sig=d.signal||{};
    let sigColor='#9ca3af';
    if(sig.signal==='STRONG BUY'||sig.signal==='BUY') sigColor='#34d399';
    else if(sig.signal==='CAUTION') sigColor='#fbbf24';
    else if(sig.signal==='AVOID') sigColor='#f87171';

    const sigEl=document.getElementById('c-signal');
    sigEl.textContent=`${sig.signal||'NEUTRAL'}  ·  Score: ${sig.score||0}`;
    sigEl.style.background=sigColor+'18';
    sigEl.style.border=`1px solid ${sigColor}44`;
    sigEl.style.color=sigColor;

    document.getElementById('c-flags').innerHTML=(sig.flags||[]).map(f=>`<div class="corp-flag">${f}</div>`).join('');
    document.getElementById('c-reasons').innerHTML=(sig.reasons||[]).map(r=>`<div class="corp-reason">✅ ${r}</div>`).join('');

    document.getElementById('c-nextdate').textContent=(e.next_earnings_date||'Unknown').split('T')[0];
    const surpriseEl=document.getElementById('c-surprise');
    surpriseEl.textContent=e.eps_surprise_pct!=null?`${e.eps_surprise_pct.toFixed(1)}%`:'N/A';
    surpriseEl.style.color=(e.eps_surprise_pct||0)>0?'#34d399':'#f87171';

    const epsH=document.getElementById('c-epshist');
    if(e.history&&e.history.length>0){
      epsH.innerHTML=`<div style="background:var(--bg);border:1px solid var(--border);border-radius:3px;padding:10px">
        <div class="hist-row" style="color:var(--dim)"><span>Date</span><span>Estimate</span><span>Actual</span><span>Beat?</span></div>
        ${e.history.map(h=>{const beat=h.actual>=h.estimate;return`<div class="hist-row"><span>${h.date}</span><span>${h.estimate.toFixed(2)}</span><span style="color:${beat?'#34d399':'#f87171'}">${h.actual.toFixed(2)}</span><span>${beat?'✅':'❌'}</span></div>`;}).join('')}
      </div>`;
    } else {
      epsH.innerHTML='<div style="color:var(--dim);font-size:11px">No earnings history</div>';
    }

    const h=d.holders||{};
    document.getElementById('c-promoter').textContent=h.promoter_pct||'N/A';
    document.getElementById('c-inst').textContent=h.institution_pct||'N/A';
    document.getElementById('c-public').textContent=h.public_pct||'N/A';
    const instEl=document.getElementById('c-institutions');
    if(h.top_institutions&&h.top_institutions.length>0){
      instEl.innerHTML=`<div style="background:var(--bg);border:1px solid var(--border);border-radius:3px;padding:10px">
        ${h.top_institutions.map(i=>`<div class="hist-row"><span style="color:var(--text);max-width:70%;overflow:hidden;text-overflow:ellipsis">${i.name}</span><span style="color:#38bdf8">${i.pct}%</span></div>`).join('')}
      </div>`;
    } else {
      instEl.innerHTML='<div style="color:var(--dim);font-size:11px">No institutional data</div>';
    }

    document.getElementById('corp-loading').style.display='none';
    document.getElementById('corp-content').style.display='block';

    // ---- COMPANY TAB ----
    document.getElementById('co-industry').textContent=co.industry||'N/A';
    document.getElementById('co-country').textContent=co.country||'N/A';
    document.getElementById('co-emp').textContent=co.employees?co.employees.toLocaleString():'N/A';
    const webEl=document.getElementById('co-web');
    if(co.website){
      webEl.innerHTML=`<a href="${co.website}" target="_blank" style="color:#38bdf8">${co.website}</a>`;
    } else {
      webEl.textContent='N/A';
    }
    document.getElementById('co-desc').textContent=co.description||'No description available';
    document.getElementById('comp-loading').style.display='none';
    document.getElementById('comp-content').style.display='block';

  }catch(err){
    document.getElementById('fund-loading').textContent='Failed to load: '+err.message;
    document.getElementById('corp-loading').textContent='Failed to load: '+err.message;
    document.getElementById('comp-loading').textContent='Failed to load: '+err.message;
  }
}

loadChart();
loadTechnical();
loadCorporate();
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
