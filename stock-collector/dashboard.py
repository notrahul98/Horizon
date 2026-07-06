"""
Nifty 150 Terminal Dashboard v3
- Auto-installs yfinance if missing
- Corporate data fetched live from Yahoo Finance
- Full interactive dashboard with 4 tabs
"""

import sys
import os
import subprocess
import glob

def ensure_yfinance():
    """Find yfinance in any location, or install it"""
    try:
        import yfinance
        return True
    except ImportError:
        pass

    # Search all possible site-packages locations
    patterns = [
        '/app/*/site-packages',
        '/app/.venv/lib/*/site-packages',
        '/usr/local/lib/*/site-packages',
        '/usr/lib/*/site-packages',
        '/mise/installs/python/*/lib/*/site-packages',
        '/root/.local/lib/*/site-packages',
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            if path not in sys.path:
                sys.path.insert(0, path)
            try:
                import yfinance
                return True
            except ImportError:
                continue

    # Auto-install as last resort
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'yfinance', 'requests', '--quiet', '--target=/app/pkgs'
        ])
        sys.path.insert(0, '/app/pkgs')
        import yfinance
        return True
    except Exception as e:
        print(f"yfinance install failed: {e}")
        return False

YFINANCE_AVAILABLE = ensure_yfinance()

for p in ['/app', '/app/pkgs',
          '/app/.venv/lib/python3.13/site-packages',
          '/mise/installs/python/3.13.14/lib/python3.13/site-packages']:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

_venv_site = os.path.join(os.path.dirname(__file__), "..", ".pythonlibs", "lib", "python3.11", "site-packages")
if os.path.isdir(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)


import sqlite3
import json
from datetime import datetime, timezone, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
from flask import Flask, render_template_string, request, jsonify

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")
app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ist_now():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%d %b %Y · %H:%M:%S IST")


PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#9ca3af", size=11, family="monospace"),
    xaxis=dict(gridcolor="#1f2937", linecolor="#374151", tickfont=dict(color="#6b7280")),
    yaxis=dict(gridcolor="#1f2937", linecolor="#374151", tickfont=dict(color="#6b7280")),
    margin=dict(t=30, b=30, l=50, r=20),
)


def get_latest_df():
    q = """
        SELECT p.symbol, s.name, s.sector,
               p.date, p.close, p.open, p.high, p.low, p.volume
        FROM price_history p
        JOIN stocks s ON s.symbol = p.symbol
        WHERE p.interval = 'day'
          AND p.date = (SELECT MAX(p2.date) FROM price_history p2
                        WHERE p2.symbol = p.symbol AND p2.interval = 'day')
        ORDER BY p.symbol
    """
    with get_conn() as c:
        df = pd.read_sql_query(q, c)
    df["day_chg"] = ((df["close"] - df["open"]) / df["open"] * 100).round(2)
    return df


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


def get_stock_detail(symbol):
    hist = get_history(symbol, 90)
    if hist.empty:
        return {}

    close = hist["close"]
    latest = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]

    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    rsi = calc_rsi(close).iloc[-1]
    sma20 = close.rolling(20).mean().iloc[-1]
    std20 = close.rolling(20).std().iloc[-1]
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    high_52w = hist["high"].max()
    low_52w = hist["low"].min()
    avg_vol = hist["volume"].mean()
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = (ema12 - ema26).iloc[-1]
    signal_line = (ema12 - ema26).ewm(span=9).mean().iloc[-1]
    bb_pos = ((latest["close"] - bb_lower) / (bb_upper - bb_lower) * 100) if (bb_upper - bb_lower) > 0 else 50
    trend = "BULLISH" if ema20 > ema50 else "BEARISH"
    trend_color = "#34d399" if trend == "BULLISH" else "#f87171"

    if rsi < 30:
        rsi_signal = "OVERSOLD"
    elif rsi > 70:
        rsi_signal = "OVERBOUGHT"
    else:
        rsi_signal = "NEUTRAL"

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
    }


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

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist["date"], open=hist["open"], high=hist["high"],
        low=hist["low"], close=hist["close"], name="OHLC",
        increasing_line_color="#34d399", decreasing_line_color="#f87171",
        increasing_fillcolor="#34d399", decreasing_fillcolor="#f87171",
    ))
    fig.add_trace(go.Scatter(x=hist["date"], y=ema20, name="EMA20",
        line=dict(color="#38bdf8", width=1.2), opacity=0.8))
    fig.add_trace(go.Scatter(x=hist["date"], y=ema50, name="EMA50",
        line=dict(color="#fbbf24", width=1.2), opacity=0.8))
    fig.update_layout(height=280, xaxis_rangeslider_visible=False,
        title=dict(text=f"{symbol} — 90 Day Chart", font=dict(color="#d1d5db", size=12)),
        **PLOTLY_DARK)
    return jsonify({"chart": json.dumps(fig, cls=PlotlyJSONEncoder)})


@app.route("/api/corporate/<symbol>")
def api_corporate(symbol):
    """Fetch corporate data using yfinance (Yahoo Finance works on Railway)"""
    try:
        # Use sys.path trick that worked in console
        import sys
        for p in ['/app', '/mise/installs/python/3.13.14/lib/python3.13/site-packages']:
            if p not in sys.path:
                sys.path.insert(0, p)

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
    sec_fig = px.bar(sec, x="sector", y="count", color="avg_close",
                     color_continuous_scale=["#1e3a5f", "#38bdf8"])
    sec_fig.update_layout(xaxis_tickangle=-35, xaxis_title="", yaxis_title="",
                          coloraxis_showscale=False, **PLOTLY_DARK)
    sector_chart = json.dumps(sec_fig, cls=PlotlyJSONEncoder)

    top_g = df.nlargest(8, "day_chg")[["symbol", "day_chg"]].assign(type="Gainer")
    top_l = df.nsmallest(8, "day_chg")[["symbol", "day_chg"]].assign(type="Loser")
    movers = pd.concat([top_g, top_l])
    mov_fig = px.bar(movers, y="symbol", x="day_chg", color="type", orientation="h",
                     color_discrete_map={"Gainer": "#34d399", "Loser": "#f87171"})
    mov_fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False,
                          margin=dict(t=10, b=10, l=80, r=20),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#9ca3af", size=11, family="monospace"),
                          xaxis=dict(gridcolor="#1f2937"), yaxis=dict(gridcolor="#1f2937"))
    movers_chart = json.dumps(mov_fig, cls=PlotlyJSONEncoder)

    stocks = df.to_dict("records")
    gainers = len(df[df["day_chg"] > 0])
    losers = len(df[df["day_chg"] < 0])

    return render_template_string(HTML,
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
    )


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nifty 150 Terminal</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
:root{--bg:#0a0a0f;--card:#111118;--hover:#16161f;--border:#1e1e2a;--text:#9ca3af;--dim:#6b7280;--bright:#e5e7eb;--green:#34d399;--red:#f87171;--blue:#38bdf8;--amber:#fbbf24;--purple:#a78bfa;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:ui-monospace,'SFMono-Regular',Menlo,Monaco,Consolas,monospace;font-size:12px;height:100vh;overflow:hidden;display:flex;flex-direction:column;}
.nav{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;border-bottom:1px solid var(--border);background:#0d0d14;flex-shrink:0;}
.nav-brand{display:flex;align-items:center;gap:10px;}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:blink 2s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.brand-name{color:var(--green);font-size:14px;font-weight:700;letter-spacing:.12em;}
.nav-meta{color:var(--dim);font-size:11px;}
.body{display:grid;grid-template-columns:220px 1fr 380px;flex:1;overflow:hidden;}
.sidebar{border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
.sidebar-kpis{padding:12px;display:flex;flex-direction:column;gap:7px;border-bottom:1px solid var(--border);}
.kpi{background:var(--card);border-left:2px solid;padding:8px 10px;border-radius:3px;}
.kpi.g{border-color:var(--green)}.kpi.b{border-color:var(--blue)}.kpi.a{border-color:var(--amber)}.kpi.r{border-color:var(--red)}.kpi.p{border-color:var(--purple)}
.kpi-label{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin-bottom:3px;}
.kpi-val{font-size:17px;font-weight:700;}
.kpi-val.g{color:var(--green)}.kpi-val.b{color:var(--blue)}.kpi-val.a{color:var(--amber)}.kpi-val.r{color:var(--red)}.kpi-val.p{color:var(--purple)}
.sidebar-charts{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:10px;}
.chart-label{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin-bottom:5px;}
.chart-box{height:140px;}
.main{display:flex;flex-direction:column;overflow:hidden;border-right:1px solid var(--border);}
.table-header{padding:8px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.tbl-title{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);}
.search-box{background:var(--bg);border:1px solid var(--border);color:var(--bright);padding:4px 10px;border-radius:3px;font-family:inherit;font-size:11px;width:180px;}
.search-box:focus{outline:none;border-color:var(--blue);}
.table-wrap{flex:1;overflow-y:auto;}
table{width:100%;border-collapse:collapse;}
thead th{position:sticky;top:0;background:#0d0d14;padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);border-bottom:1px solid var(--border);cursor:pointer;user-select:none;white-space:nowrap;}
thead th:hover{color:var(--bright);}
thead th.r{text-align:right;}
tbody td{padding:6px 10px;border-bottom:1px solid rgba(30,30,42,.8);white-space:nowrap;}
tbody tr{cursor:pointer;transition:background .1s;}
tbody tr:hover{background:var(--hover);}
tbody tr.active{background:#1a1a2e;border-left:2px solid var(--blue);}
.sym{font-weight:700;color:var(--bright);font-size:12px;}
.name-cell{color:var(--text);max-width:150px;overflow:hidden;text-overflow:ellipsis;}
.tag{font-size:9px;padding:2px 5px;border-radius:2px;background:#1f2937;color:var(--dim);}
.num{text-align:right;}
.up{color:var(--green);font-weight:700;}
.dn{color:var(--red);font-weight:700;}
.dim{color:var(--dim);}
.detail{display:flex;flex-direction:column;overflow:hidden;background:var(--card);}
.detail-header{padding:12px 16px;border-bottom:1px solid var(--border);flex-shrink:0;}
.detail-sym{font-size:18px;font-weight:700;color:var(--bright);}
.detail-name{color:var(--dim);font-size:11px;margin-top:2px;}
.detail-price{display:flex;align-items:baseline;gap:10px;margin-top:8px;}
.price{font-size:26px;font-weight:700;color:var(--bright);}
.chg{font-size:14px;font-weight:700;}
.detail-tabs{display:flex;gap:0;border-bottom:1px solid var(--border);flex-shrink:0;}
.tab{padding:8px 16px;cursor:pointer;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);border-bottom:2px solid transparent;transition:all .2s;}
.tab:hover{color:var(--bright);}
.tab.active{color:var(--blue);border-bottom-color:var(--blue);}
.detail-body{flex:1;overflow-y:auto;padding:12px 16px;}
.tab-content{display:none;}
.tab-content.active{display:block;}
.section-title{font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:var(--blue);margin:10px 0 6px;border-bottom:1px solid var(--border);padding-bottom:4px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:8px;}
.stat-box{background:var(--bg);padding:8px 10px;border-radius:3px;border:1px solid var(--border);}
.stat-label{font-size:9px;color:var(--dim);text-transform:uppercase;margin-bottom:3px;}
.stat-val{font-size:13px;font-weight:700;color:var(--bright);}
.stat-val.g{color:var(--green)}.stat-val.r{color:var(--red)}.stat-val.a{color:var(--amber)}.stat-val.b{color:var(--blue)}.stat-val.p{color:var(--purple)}
.prog-bg{background:var(--border);border-radius:2px;height:5px;width:100%;margin-top:4px;}
.prog-fill{height:5px;border-radius:2px;transition:width .4s;}
.corp-signal{padding:8px 12px;border-radius:4px;text-align:center;font-size:13px;font-weight:700;margin-bottom:8px;}
.corp-flag{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);color:var(--amber);padding:5px 8px;border-radius:3px;margin:3px 0;font-size:11px;}
.corp-reason{background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.2);color:var(--green);padding:5px 8px;border-radius:3px;margin:3px 0;font-size:11px;}
.hist-row{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);font-size:10px;}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--blue);border-radius:50%;animation:spin .8s linear infinite;margin-right:6px;}
@keyframes spin{to{transform:rotate(360deg)}}
.empty-detail{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--dim);gap:10px;}
@media(max-width:1100px){.body{grid-template-columns:200px 1fr}.detail{display:none}}
@media(max-width:700px){.body{grid-template-columns:1fr}.sidebar{display:none}}
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
      <div class="kpi a"><div class="kpi-label">Top Gainer</div><div class="kpi-val a" style="font-size:11px">{{ top_gainer }}</div></div>
    </div>
    <div class="sidebar-charts">
      <div><div class="chart-label">Sector Distribution</div><div class="chart-box" id="sec-chart"></div></div>
      <div><div class="chart-label">Top Movers</div><div class="chart-box" id="mov-chart"></div></div>
    </div>
  </div>
  <!-- MAIN TABLE -->
  <div class="main">
    <div class="table-header">
      <span class="tbl-title">Live Quote Feed · {{ latest_date }} · {{ total }} stocks</span>
      <input class="search-box" id="searchBox" placeholder="Search symbol, name, sector..." oninput="filterTable()">
    </div>
    <div class="table-wrap">
      <table id="stockTable">
        <thead>
          <tr>
            <th onclick="sortTable('sym')">Symbol</th>
            <th>Name</th>
            <th>Sector</th>
            <th class="r" onclick="sortTable('close')">Close ₹</th>
            <th class="r" onclick="sortTable('chg')">Chg%</th>
            <th class="r" onclick="sortTable('high')">High</th>
            <th class="r" onclick="sortTable('low')">Low</th>
            <th class="r" onclick="sortTable('vol')">Volume</th>
          </tr>
        </thead>
        <tbody id="stockBody">
          {% for s in stocks %}
          <tr onclick="selectStock('{{ s.symbol }}','{{ s.name }}')"
              data-sym="{{ s.symbol }}" data-name="{{ s.name }}" data-sector="{{ s.sector }}"
              data-close="{{ s.close }}" data-chg="{{ s.day_chg }}"
              data-high="{{ s.high }}" data-low="{{ s.low }}" data-vol="{{ s.volume }}">
            <td class="sym">{{ s.symbol.replace('.NS','') }}</td>
            <td class="name-cell">{{ s.name }}</td>
            <td><span class="tag">{{ s.sector[:16] }}</span></td>
            <td class="num">₹{{ "%.2f"|format(s.close) }}</td>
            <td class="num {% if s.day_chg >= 0 %}up{% else %}dn{% endif %}">{% if s.day_chg >= 0 %}+{% endif %}{{ "%.2f"|format(s.day_chg) }}%</td>
            <td class="num">{{ "%.2f"|format(s.high) }}</td>
            <td class="num">{{ "%.2f"|format(s.low) }}</td>
            <td class="num dim">{{ "{:.1f}M".format(s.volume/1000000) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <!-- DETAIL PANEL -->
  <div class="detail" id="detailPanel">
    <div class="empty-detail" id="emptyDetail">
      <div style="font-size:28px;color:var(--border)">←</div>
      <p>Click any stock to see details</p>
      <p style="font-size:10px;color:#374151">Technicals · Fundamentals · Corporate Actions</p>
    </div>
    <div id="stockDetail" style="display:none;flex-direction:column;height:100%;overflow:hidden;">
      <div class="detail-header">
        <div class="detail-sym" id="detailSym">-</div>
        <div class="detail-name" id="detailName">-</div>
        <div class="detail-price">
          <span class="price" id="detailPrice">-</span>
          <span class="chg" id="detailChg">-</span>
        </div>
      </div>
      <!-- TABS -->
      <div class="detail-tabs">
        <div class="tab active" onclick="switchTab('technical')">Technical</div>
        <div class="tab" onclick="switchTab('fundamental')">Fundamental</div>
        <div class="tab" onclick="switchTab('corporate')">Corporate</div>
        <div class="tab" onclick="switchTab('company')">Company</div>
      </div>
      <div class="detail-body">
        <!-- TECHNICAL TAB -->
        <div class="tab-content active" id="tab-technical">
          <div id="detailChart" style="height:220px"></div>
          <div class="section-title">Today's Trading</div>
          <div class="grid3">
            <div class="stat-box"><div class="stat-label">Open</div><div class="stat-val" id="d-open">-</div></div>
            <div class="stat-box"><div class="stat-label">High</div><div class="stat-val g" id="d-high">-</div></div>
            <div class="stat-box"><div class="stat-label">Low</div><div class="stat-val r" id="d-low">-</div></div>
            <div class="stat-box"><div class="stat-label">Prev Close</div><div class="stat-val" id="d-prev">-</div></div>
            <div class="stat-box"><div class="stat-label">52W High</div><div class="stat-val g" id="d-52h">-</div></div>
            <div class="stat-box"><div class="stat-label">52W Low</div><div class="stat-val r" id="d-52l">-</div></div>
          </div>
          <div class="section-title">Indicators</div>
          <div class="grid2">
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
          </div>
          <div class="stat-box">
            <div class="stat-label">Bollinger Band Position</div>
            <div class="stat-val" id="d-bb-pos">-</div>
            <div class="prog-bg"><div class="prog-fill" id="d-bb-bar" style="width:50%;background:#a78bfa"></div></div>
            <div style="display:flex;justify-content:space-between;margin-top:4px;color:var(--dim);font-size:9px">
              <span id="d-bb-low">Lower</span><span id="d-bb-up">Upper</span>
            </div>
          </div>
          <div class="section-title">Volume</div>
          <div class="grid2">
            <div class="stat-box"><div class="stat-label">Today Vol</div><div class="stat-val b" id="d-vol">-</div></div>
            <div class="stat-box"><div class="stat-label">90D Avg Vol</div><div class="stat-val" id="d-avgvol">-</div></div>
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
            <div class="grid2">
              <div class="stat-box"><div class="stat-label">Revenue Growth</div><div class="stat-val" id="f-revg">-</div></div>
              <div class="stat-box"><div class="stat-label">Earnings Growth</div><div class="stat-val" id="f-earng">-</div></div>
              <div class="stat-box"><div class="stat-label">Profit Margin</div><div class="stat-val" id="f-margin">-</div></div>
              <div class="stat-box"><div class="stat-label">Beta</div><div class="stat-val a" id="f-beta">-</div></div>
            </div>
            <div class="section-title">Dividends</div>
            <div class="grid2">
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
              <div class="stat-box"><div class="stat-label">Next Results</div><div class="stat-val a" id="c-nextdate" style="font-size:11px">-</div></div>
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
            <div class="grid2">
              <div class="stat-box"><div class="stat-label">Industry</div><div class="stat-val" id="co-industry" style="font-size:11px">-</div></div>
              <div class="stat-box"><div class="stat-label">Country</div><div class="stat-val" id="co-country">-</div></div>
              <div class="stat-box"><div class="stat-label">Employees</div><div class="stat-val b" id="co-emp">-</div></div>
              <div class="stat-box"><div class="stat-label">Website</div><div class="stat-val" id="co-web" style="font-size:10px">-</div></div>
            </div>
            <div class="section-title">About</div>
            <div id="co-desc" style="font-size:11px;color:var(--text);line-height:1.7;background:var(--bg);padding:10px;border-radius:3px;border:1px solid var(--border)">-</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
var secChart={{ sector_chart|safe }};
var movChart={{ movers_chart|safe }};
Plotly.newPlot('sec-chart',secChart.data,secChart.layout,{displayModeBar:false,responsive:true});
Plotly.newPlot('mov-chart',movChart.data,movChart.layout,{displayModeBar:false,responsive:true});

var currentSym=null, corpData=null;

// Live clock
setInterval(()=>{
  const now=new Date();
  const ist=new Date(now.getTime()+(5.5*60*60*1000));
  document.getElementById('navTime').textContent=ist.toLocaleString('en-IN',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})+' IST';
},1000);

// Tab switching
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelector(`.tab[onclick="switchTab('${name}')"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
}

// Select stock
async function selectStock(sym, name){
  currentSym=sym;
  document.querySelectorAll('tbody tr').forEach(r=>r.classList.remove('active'));
  const row=document.querySelector(`tr[data-sym="${sym}"]`);
  if(row) row.classList.add('active');
  document.getElementById('emptyDetail').style.display='none';
  const det=document.getElementById('stockDetail');
  det.style.display='flex';
  document.getElementById('detailSym').textContent=sym.replace('.NS','');
  document.getElementById('detailName').textContent=name;
  document.getElementById('detailPrice').textContent='...';

  // Reset loading states
  document.getElementById('fund-loading').style.display='block';
  document.getElementById('fund-content').style.display='none';
  document.getElementById('corp-loading').style.display='block';
  document.getElementById('corp-content').style.display='none';
  document.getElementById('comp-loading').style.display='block';
  document.getElementById('comp-content').style.display='none';

  // Switch to technical tab
  switchTab('technical');

  // Load chart
  loadChart(sym);

  // Load technical data
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
  }catch(e){console.error(e);}

  // Load corporate data (for all tabs)
  loadCorporate(sym);
}

async function loadChart(sym){
  try{
    const r=await fetch(`/api/chart/${sym}`);
    const data=await r.json();
    if(data.chart){
      const fig=JSON.parse(data.chart);
      Plotly.newPlot('detailChart',fig.data,fig.layout,{displayModeBar:false,responsive:true});
    }
  }catch(e){}
}

async function loadCorporate(sym){
  try{
    const r=await fetch(`/api/corporate/${sym}`);
    const d=await r.json();
    corpData=d;
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

    // Dividend history
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

    // EPS history
    const epsH=document.getElementById('c-epshist');
    if(e.history&&e.history.length>0){
      epsH.innerHTML=`<div style="background:var(--bg);border:1px solid var(--border);border-radius:3px;padding:8px">
        <div class="hist-row" style="color:var(--dim)"><span>Date</span><span>Estimate</span><span>Actual</span><span>Beat?</span></div>
        ${e.history.map(h=>{const beat=h.actual>=h.estimate;return`<div class="hist-row"><span>${h.date}</span><span>${h.estimate.toFixed(2)}</span><span style="color:${beat?'#34d399':'#f87171'}">${h.actual.toFixed(2)}</span><span>${beat?'✅':'❌'}</span></div>`;}).join('')}
      </div>`;
    } else {
      epsH.innerHTML='<div style="color:var(--dim);font-size:11px">No earnings history</div>';
    }

    // Holders
    const h=d.holders||{};
    document.getElementById('c-promoter').textContent=h.promoter_pct||'N/A';
    document.getElementById('c-inst').textContent=h.institution_pct||'N/A';
    document.getElementById('c-public').textContent=h.public_pct||'N/A';
    const instEl=document.getElementById('c-institutions');
    if(h.top_institutions&&h.top_institutions.length>0){
      instEl.innerHTML=`<div style="background:var(--bg);border:1px solid var(--border);border-radius:3px;padding:8px">
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

// Auto-click first row
window.onload=()=>{
  const first=document.querySelector('#stockBody tr');
  if(first) first.click();
};
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
