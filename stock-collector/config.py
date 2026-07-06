"""
Central configuration for the stock data collector.
Fetches top 150 Indian stocks from Nifty indices (lazy, on demand).
"""

import json
import os
from datetime import datetime

# ── Paths (absolute, relative to this config.py file) ──────────
_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(_HERE, "data", "nifty_150_cache.json")
DB_PATH = os.path.join(_HERE, "data", "stocks.db")

# ── Schedule constants (used by main.py & scheduler.py) ──────────
SCHEDULES = {
    "intraday_minutes": 15,
    "daily_hour": 18,
    "daily_minute": 0,
    "weekly_day": "sun",
    "weekly_hour": 8,
    "weekly_minute": 0,
}

HISTORICAL_PERIOD = "1y"
INTRADAY_PERIOD = "1d"
INTRADAY_INTERVAL = "5m"
CACHE_EXPIRY_HOURS = 24

# ── Nifty 150 base symbols (Nifty 50 + Nifty Next 50 + Nifty Midcap 50)
# Cleaned to well-known, actively traded NSE tickers.
_NIFTY_150_SYMBOLS = [
    # NIFTY 50
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFY.NS", "SBIN.NS", "HINDUNILVR.NS", "ITC.NS", "LT.NS",
    "BAJFINANCE.NS", "KOTAKBANK.NS", "HCLTECH.NS", "AXISBANK.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ONGC.NS", "ULTRACEMCO.NS", "ADANIENT.NS",
    "NTPC.NS", "POWERGRID.NS", "M&M.NS", "WIPRO.NS", "ASIANPAINT.NS",
    "JSWSTEEL.NS", "COALINDIA.NS", "TATAMOTORS.NS", "ADANIPORTS.NS", "NESTLEIND.NS",
    "BAJAJFINSV.NS", "BAJAJ-AUTO.NS", "TECHM.NS", "GRASIM.NS", "DRREDDY.NS",
    "TATASTEEL.NS", "SBILIFE.NS", "CIPLA.NS", "APOLLOHOSP.NS", "EICHERMOT.NS",
    "DIVISLAB.NS", "HEROMOTOCO.NS", "BPCL.NS", "HINDALCO.NS", "ADANIGREEN.NS",
    "BRITANNIA.NS", "INDUSINDBK.NS", "TATACONSUM.NS", "HDFCLIFE.NS", "HAL.NS",
    # NIFTY NEXT 50
    "PAYTM.NS", "ZOMATO.NS", "AMBUJACEM.NS", "PIDILITIND.NS", "GODREJCP.NS",
    "SIEMENS.NS", "DMART.NS", "ADANIPOWER.NS", "DLF.NS", "DABUR.NS",
    "HDFCAMC.NS", "VEDL.NS", "SHREECEM.NS", "TORNTPHARM.NS", "GAIL.NS",
    "CHOLAFIN.NS", "MCDOWELL-N.NS", "PAGEIND.NS", "ICICIGI.NS", "ABB.NS",
    "CANBK.NS", "BAJAJHLDNG.NS", "MUTHOOTFIN.NS", "SRF.NS", "IOC.NS",
    "PIIND.NS", "LUPIN.NS", "BIOCON.NS", "BERGEPAINT.NS", "JINDALSTEL.NS",
    "TATAPOWER.NS", "INDIGO.NS", "IRCTC.NS", "BANKBARODA.NS", "POLYCAB.NS",
    "ATGL.NS", "BOSCHLTD.NS", "HDFCBANK.NS", "NAUKRI.NS", "AUROPHARMA.NS",
    "PFC.NS", "RECLTD.NS", "UNIONBANK.NS", "MRF.NS", "INDHOTEL.NS",
    # NIFTY MIDCAP 50
    "ALOKINDS.NS", "ASHOKLEY.NS", "BATAINDIA.NS", "BEL.NS", "CUMMINSIND.NS",
    "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GMRINFRA.NS", "GODREJIND.NS",
    "JUBLFOOD.NS", "MPHASIS.NS", "NMDC.NS", "OBEROIRLTY.NS", "OFSS.NS",
    "PGHH.NS", "SAIL.NS", "TRENT.NS", "UBL.NS", "IDEA.NS",
    "NHPC.NS", "PETRONET.NS", "RATNAMANI.NS", "RELAXO.NS", "SUPREMEIND.NS",
    "TVSMOTOR.NS", "WHIRLPOOL.NS", "YESBANK.NS", "ZEE.NS", "GLAND.NS",
    "IPCALAB.NS", "JSWENERGY.NS", "LTTS.NS", "MFSL.NS", "PERSISTENT.NS",
    "ABCAPITAL.NS", "BANDHANBNK.NS", "CONCOR.NS", "DALBHARAT.NS", "FACT.NS",
    "GUJGASLTD.NS", "HINDPETRO.NS", "IDFCFIRSTB.NS", "INDUSTOWER.NS", "MAXHEALTH.NS",
    "METROPOLIS.NS", "PHOENIXLTD.NS", "RBLBANK.NS", "SYNGENE.NS", "UPL.NS",
]


def get_watchlist(cache_ok=True) -> list[dict]:
    """Return watchlist as a list of dicts {symbol, name, sector}.

    Uses a local JSON cache so repeated CLI calls are instant.
    Set cache_ok=False to force a fresh fetch (slow — hits yfinance for every symbol).
    """
    # 1. try cache first
    if cache_ok and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        cache_time = datetime.fromisoformat(cache["timestamp"])
        hours_old = (datetime.now() - cache_time).total_seconds() / 3600
        if hours_old < CACHE_EXPIRY_HOURS:
            return cache["stocks"]

    # 2. fresh fetch (slow — avoid calling on every import!)
    print("📥 Fetching Nifty 150 metadata from yfinance (this may take a minute) ...")

    import yfinance as yf  # lazy import so config.py loads fast

    stocks_data = []
    for symbol in _NIFTY_150_SYMBOLS:
        try:
            info = yf.Ticker(symbol).info
            stocks_data.append({
                "symbol": symbol,
                "name": info.get("longName") or info.get("shortName") or symbol.replace(".NS", ""),
                "sector": info.get("industry", info.get("sector", "Unknown")),
            })
        except Exception:
            stocks_data.append({
                "symbol": symbol,
                "name": symbol.replace(".NS", ""),
                "sector": "Unknown",
            })

    # write cache
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "stocks": stocks_data}, f)

    print(f"✅  Cached {len(stocks_data)} stocks")
    return stocks_data


# Convenience: static fallback if everything else fails
FALLBACK_WATCHLIST = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "TCS.NS",      "name": "Tata Consultancy Services", "sector": "Technology"},
    {"symbol": "INFY.NS",     "name": "Infosys Ltd", "sector": "Technology"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Financials"},
    {"symbol": "ICICIBANK.NS","name": "ICICI Bank", "sector": "Financials"},
    {"symbol": "HINDUNILVR.NS","name": "Hindustan Unilever", "sector": "Consumer"},
    {"symbol": "SBIN.NS",     "name": "State Bank of India", "sector": "Financials"},
    {"symbol": "BHARTIARTL.NS","name": "Bharti Airtel", "sector": "Communication"},
    {"symbol": "ITC.NS",      "name": "ITC Ltd", "sector": "Consumer"},
    {"symbol": "LT.NS",       "name": "Larsen & Toubro", "sector": "Construction"},
]
