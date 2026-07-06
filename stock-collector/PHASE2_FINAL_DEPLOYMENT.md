# 🚀 PHASE 2 COMPLETE DEPLOYMENT GUIDE

## Files to Upload to GitHub

Upload these files to your `stock-collector/` folder:

1. **`dashboard_updated.py`** → Rename to `dashboard.py` (replaces old one)
2. **`corporate_actions.py`** → New file (Phase 2 core)
3. **`corporate_dashboard.py`** → New file (Phase 2 UI routes)

---

## Step-by-Step Deployment

### Step 1: Delete Old dashboard.py
In GitHub, delete the old `stock-collector/dashboard.py`

### Step 2: Upload New Files
1. Go to: https://github.com/notrahul98/Horizon
2. Navigate to: `stock-collector/` folder
3. Upload the 3 files:
   - `dashboard_updated.py` (rename to `dashboard.py` after upload)
   - `corporate_actions.py`
   - `corporate_dashboard.py`

### Step 3: Update requirements.txt
Add `requests` if not already there:
```
Flask==2.3.2
yfinance==0.2.32
pandas==2.0.3
plotly==5.15.0
sqlalchemy==2.0.19
apscheduler==3.10.4
python-dotenv==1.0.0
requests==2.31.0
```

### Step 4: Commit and Push
Commit all changes to GitHub

### Step 5: Railway Auto-Redeploys
Wait 2-3 minutes for Railway to detect changes and redeploy

---

## Access Your Dashboard

After deployment:

```
Main Dashboard (with Phase 2 indicator):
https://pulse-production-1d2a.up.railway.app/

Corporate Actions Dashboard:
https://pulse-production-1d2a.up.railway.app/corporate

API Endpoints:
GET /api/corporate/summary
GET /api/corporate/stock/RELIANCE.NS
GET /api/corporate/upcoming-results
GET /api/corporate/dividends
GET /api/corporate/insider-buying
```

---

## Initial Data Load

First time only, fetch corporate data for all 150 stocks:

In Railway Console or Replit Shell:
```bash
cd stock-collector
python -c "from corporate_actions import fetch_all_corporate_data; fetch_all_corporate_data(['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'], max_stocks=150)"
```

This takes ~10 minutes and fetches:
- ✅ Results calendar for all 150 stocks
- ✅ Dividend data
- ✅ Insider holdings
- ✅ Bulk/block deals
- ✅ Corporate events

---

## What Phase 2 Adds to Your Dashboard

### Enhanced Main Dashboard (/):
- New KPI card showing "Phase 2 Status" with count of analyzed stocks
- Corporate signal indicators (🟢🔴⚠️) next to each stock in the table
- Link to `/corporate` page in navigation

### New Corporate Dashboard (/corporate):
- 📅 **Upcoming Results**: Results in next 14 days with ⚠️ warnings
- 💰 **Dividend Tracker**: High yield stocks with ex-dividend dates
- 👔 **Insider Activity**: Stocks with promoter/insider buying
- 🔍 **Stock Lookup**: Search any stock for full corporate profile

### API Endpoints:
- `/api/corporate/summary` - Overall statistics
- `/api/corporate/stock/<symbol>` - Full profile for one stock
- `/api/corporate/upcoming-results` - Results calendar
- `/api/corporate/dividends` - Dividend stocks
- `/api/corporate/insider-buying` - Insider activity

---

## Features of corporate_actions.py

### Data Collection:
1. **Earnings Calendar** - Next results date, EPS actual vs estimate, surprise %
2. **Dividends** - Yield, ex-dates, history, payout frequency
3. **Insider Trading** - Promoter holdings, FII/DII %, insider transactions
4. **Bulk/Block Deals** - NSE API for large trades
5. **Corporate Events** - Stock splits, bonus issues, rights issues

### Signals Generated:
Each stock gets a corporate signal:
- **STRONG_BUY** - Earnings beat + insider buying + high dividend
- **BUY** - Mixed positive signals
- **NEUTRAL** - No strong corporate signals
- **CAUTION** - Results coming, ex-dividend, etc.
- **AVOID** - Earnings miss, insider selling

### Scoring:
- +2 for strong earnings beat (>10%)
- +1 for mild beat, high dividend
- -1 for miss, ex-dividend coming, insider selling
- -2 for major miss

---

## Scheduling (Optional)

Add to your scheduler to update daily:

```python
# Weekly full corporate refresh (Sunday 9 AM IST)
from apscheduler.schedulers.background import BackgroundScheduler
from corporate_actions import fetch_all_corporate_data

def schedule_corporate_updates():
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
    scheduler.add_job(
        fetch_all_corporate_data,
        'cron',
        day_of_week='sun',
        hour=9,
        minute=0,
        args=[get_all_symbols(), 150]
    )
    scheduler.start()
```

---

## What Gets Stored in Database

Phase 2 creates a `corporate_actions` table:
- `symbol` - Stock symbol
- `next_earnings_date` - When results are due
- `eps_surprise_pct` - Last EPS surprise %
- `dividend_yield` - Current yield
- `ex_dividend_date` - Ex-dividend date
- `promoter_holding_pct` - Promoter stake %
- `corporate_signal` - STRONG_BUY/BUY/NEUTRAL/CAUTION/AVOID
- `corporate_score` - Numerical score
- `flags` - Important warnings (JSON)
- `reasons` - Positive signals (JSON)
- `full_data` - Complete profile (JSON)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'corporate_actions'"
- Make sure files are in `stock-collector/` folder
- Restart Railway or Replit

### No corporate data showing
- Run `python corporate_actions.py` to fetch initial data
- Wait for first run to complete (~10 minutes for 150 stocks)

### API returns empty
- Check database was created: `ls data/swing_trader.db`
- Check if corporate_actions table exists
- Run fetch_all_corporate_data() first

---

## Testing Phase 2 Locally

```bash
cd stock-collector

# Test with a few stocks
python -c "
from corporate_actions import get_complete_corporate_profile
profile = get_complete_corporate_profile('RELIANCE.NS')
print(profile['signal'])
"

# Fetch for all 150 stocks
python corporate_actions.py
```

---

## What's Next?

After Phase 2 is working:

**Phase 3**: Enhanced Technical Analysis
- More indicators (Stochastic, Williams %R, CCI)
- Sector rotation signals
- Market breadth analysis

**Phase 4**: Full AI Agent Integration
- Connect DeepSeek, Claude, Gemini APIs
- Real quantitative analysis
- Natural language insights

**Phase 5**: Alerts & Reports
- Telegram daily reports
- Email summaries
- SMS alerts for high-conviction trades

---

## Questions?

1. Make sure all 3 files are in `stock-collector/`
2. Update dashboard imports correctly
3. Wait for deployment (2-3 min)
4. Check `/corporate` page loads
5. Run corporate_actions.py to populate data

You're building an institutional-grade trading system! 🚀
