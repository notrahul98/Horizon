"""
Phase 2: Corporate Actions Module
Fetches results, dividends, insider trading, bulk/block deals
for Nifty 150 stocks
"""

import yfinance as yf
import pandas as pd
import sqlite3
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'swing_trader.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# 1. RESULTS CALENDAR
# ============================================================

def get_earnings_data(symbol: str) -> dict:
    """
    Fetch quarterly earnings data for a stock
    Returns: EPS, revenue, surprises, next results date
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get earnings history
        earnings = ticker.earnings_history
        quarterly = ticker.quarterly_earnings

        result = {
            'symbol': symbol,
            'next_earnings_date': None,
            'last_eps_actual': None,
            'last_eps_estimate': None,
            'eps_surprise_pct': None,
            'last_revenue': None,
            'earnings_history': []
        }

        # Get next earnings date from calendar
        try:
            calendar = ticker.calendar
            if calendar is not None and 'Earnings Date' in calendar.index:
                result['next_earnings_date'] = str(calendar.loc['Earnings Date'].iloc[0])
        except Exception:
            pass

        # Get quarterly earnings history
        if quarterly is not None and not quarterly.empty:
            latest = quarterly.iloc[0]
            result['last_eps_actual'] = float(latest.get('Actual', 0) or 0)
            result['last_eps_estimate'] = float(latest.get('Estimate', 0) or 0)

            if result['last_eps_estimate'] and result['last_eps_estimate'] != 0:
                surprise = ((result['last_eps_actual'] - result['last_eps_estimate'])
                           / abs(result['last_eps_estimate'])) * 100
                result['eps_surprise_pct'] = round(surprise, 2)

            # Build history
            for date, row in quarterly.iterrows():
                result['earnings_history'].append({
                    'date': str(date),
                    'actual': float(row.get('Actual', 0) or 0),
                    'estimate': float(row.get('Estimate', 0) or 0),
                })

        return result

    except Exception as e:
        return {'symbol': symbol, 'error': str(e)}


# ============================================================
# 2. DIVIDEND TRACKER
# ============================================================

def get_dividend_data(symbol: str) -> dict:
    """
    Fetch dividend history, yield, ex-dates for a stock
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        dividends = ticker.dividends

        result = {
            'symbol': symbol,
            'dividend_yield': None,
            'last_dividend_amount': None,
            'last_dividend_date': None,
            'ex_dividend_date': None,
            'annual_dividend': None,
            'dividend_history': [],
            'payout_frequency': None
        }

        # Get yield and ex-date from info
        try:
            full_info = ticker.info
            result['dividend_yield'] = full_info.get('dividendYield', None)
            result['annual_dividend'] = full_info.get('dividendRate', None)
            ex_date = full_info.get('exDividendDate', None)
            if ex_date:
                result['ex_dividend_date'] = datetime.fromtimestamp(ex_date).strftime('%Y-%m-%d')
        except Exception:
            pass

        # Get dividend history
        if dividends is not None and not dividends.empty:
            result['last_dividend_amount'] = float(dividends.iloc[-1])
            result['last_dividend_date'] = str(dividends.index[-1].date())

            # Last 8 dividends
            for date, amount in dividends.tail(8).items():
                result['dividend_history'].append({
                    'date': str(date.date()),
                    'amount': round(float(amount), 2)
                })

            # Determine payout frequency
            if len(dividends) >= 2:
                dates = dividends.index
                avg_gap = (dates[-1] - dates[-2]).days
                if avg_gap < 100:
                    result['payout_frequency'] = 'Quarterly'
                elif avg_gap < 200:
                    result['payout_frequency'] = 'Semi-Annual'
                else:
                    result['payout_frequency'] = 'Annual'

        return result

    except Exception as e:
        return {'symbol': symbol, 'error': str(e)}


# ============================================================
# 3. INSIDER TRADING / PROMOTER ACTIVITY
# ============================================================

def get_insider_data(symbol: str) -> dict:
    """
    Fetch insider/promoter transactions
    Uses yfinance major holders + institutional holders
    """
    try:
        ticker = yf.Ticker(symbol)

        result = {
            'symbol': symbol,
            'promoter_holding_pct': None,
            'fii_holding_pct': None,
            'dii_holding_pct': None,
            'public_holding_pct': None,
            'insider_transactions': [],
            'major_holders': {},
            'institutional_holders': []
        }

        # Major holders (promoter, FII, DII breakdown)
        try:
            major = ticker.major_holders
            if major is not None and not major.empty:
                for _, row in major.iterrows():
                    desc = str(row.iloc[1]).lower()
                    pct = row.iloc[0]
                    if 'insider' in desc or 'promoter' in desc:
                        result['promoter_holding_pct'] = pct
                    elif 'institution' in desc:
                        result['fii_holding_pct'] = pct
                    result['major_holders'][str(row.iloc[1])] = pct
        except Exception:
            pass

        # Institutional holders
        try:
            inst = ticker.institutional_holders
            if inst is not None and not inst.empty:
                for _, row in inst.head(10).iterrows():
                    result['institutional_holders'].append({
                        'holder': str(row.get('Holder', '')),
                        'shares': int(row.get('Shares', 0)),
                        'pct_held': float(row.get('% Out', 0) or 0),
                        'date_reported': str(row.get('Date Reported', ''))
                    })
        except Exception:
            pass

        # Insider transactions
        try:
            insider = ticker.insider_transactions
            if insider is not None and not insider.empty:
                for _, row in insider.head(10).iterrows():
                    result['insider_transactions'].append({
                        'date': str(row.get('Start Date', '')),
                        'insider': str(row.get('Insider', '')),
                        'transaction': str(row.get('Transaction', '')),
                        'shares': int(row.get('Shares', 0) or 0),
                        'value': float(row.get('Value', 0) or 0),
                        'ownership': str(row.get('Ownership', ''))
                    })
        except Exception:
            pass

        return result

    except Exception as e:
        return {'symbol': symbol, 'error': str(e)}


# ============================================================
# 4. BULK & BLOCK DEALS
# ============================================================

def get_bulk_block_deals(symbol: str) -> dict:
    """
    Fetch bulk and block deal data
    Uses NSE API where available
    """
    try:
        # NSE bulk deals API
        clean_symbol = symbol.replace('.NS', '').replace('.BO', '')

        result = {
            'symbol': symbol,
            'bulk_deals': [],
            'block_deals': [],
            'recent_large_trades': []
        }

        # Try NSE API for bulk deals
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
                'Referer': 'https://www.nseindia.com'
            }

            session = requests.Session()
            session.get('https://www.nseindia.com', headers=headers, timeout=5)

            bulk_url = f'https://www.nseindia.com/api/bulk-deals?symbol={clean_symbol}'
            resp = session.get(bulk_url, headers=headers, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    for deal in data['data'][:10]:
                        result['bulk_deals'].append({
                            'date': deal.get('BD_DT_DATE', ''),
                            'client': deal.get('BD_CLIENT_NAME', ''),
                            'buy_sell': deal.get('BD_BUY_SELL', ''),
                            'quantity': deal.get('BD_QTY_TRD', 0),
                            'price': deal.get('BD_TP_WATP', 0)
                        })
        except Exception:
            pass

        return result

    except Exception as e:
        return {'symbol': symbol, 'error': str(e)}


# ============================================================
# 5. CORPORATE EVENTS (SPLITS, BONUS, RIGHTS)
# ============================================================

def get_corporate_events(symbol: str) -> dict:
    """
    Fetch stock splits, bonus issues, rights issues
    """
    try:
        ticker = yf.Ticker(symbol)
        splits = ticker.splits
        actions = ticker.actions

        result = {
            'symbol': symbol,
            'splits': [],
            'bonus_issues': [],
            'recent_actions': []
        }

        # Stock splits
        if splits is not None and not splits.empty:
            for date, ratio in splits.items():
                result['splits'].append({
                    'date': str(date.date()),
                    'ratio': float(ratio),
                    'type': 'Stock Split'
                })

        # Corporate actions (dividends + splits combined)
        if actions is not None and not actions.empty:
            for date, row in actions.tail(10).iterrows():
                action = {
                    'date': str(date.date()),
                    'dividend': float(row.get('Dividends', 0) or 0),
                    'split': float(row.get('Stock Splits', 0) or 0)
                }
                result['recent_actions'].append(action)

        return result

    except Exception as e:
        return {'symbol': symbol, 'error': str(e)}


# ============================================================
# 6. COMPLETE CORPORATE PROFILE
# ============================================================

def get_complete_corporate_profile(symbol: str) -> dict:
    """
    Combines ALL corporate action data into one profile
    Use this for full analysis of a stock
    """
    print(f"  Fetching corporate profile for {symbol}...")

    profile = {
        'symbol': symbol,
        'timestamp': datetime.now().isoformat(),
        'earnings': get_earnings_data(symbol),
        'dividends': get_dividend_data(symbol),
        'insider': get_insider_data(symbol),
        'bulk_block': get_bulk_block_deals(symbol),
        'events': get_corporate_events(symbol)
    }

    # Generate corporate signal
    profile['signal'] = generate_corporate_signal(profile)

    return profile


def generate_corporate_signal(profile: dict) -> dict:
    """
    Generate a BUY/SELL/NEUTRAL signal based on corporate actions
    """
    score = 0
    reasons = []
    flags = []

    # ---- EARNINGS SIGNALS ----
    earnings = profile.get('earnings', {})

    # Positive earnings surprise = bullish
    surprise = earnings.get('eps_surprise_pct')
    if surprise:
        if surprise > 10:
            score += 2
            reasons.append(f"Strong earnings beat: +{surprise:.1f}%")
        elif surprise > 0:
            score += 1
            reasons.append(f"Earnings beat: +{surprise:.1f}%")
        elif surprise < -10:
            score -= 2
            flags.append(f"Earnings miss: {surprise:.1f}%")
        else:
            score -= 1
            flags.append(f"Slight earnings miss: {surprise:.1f}%")

    # Results coming up = caution
    next_date = earnings.get('next_earnings_date')
    if next_date:
        try:
            days_to_results = (pd.Timestamp(next_date) - pd.Timestamp.now()).days
            if 0 < days_to_results <= 7:
                flags.append(f"⚠️ Results in {days_to_results} days - HIGH RISK")
                score -= 1
            elif 0 < days_to_results <= 14:
                flags.append(f"Results in {days_to_results} days - be cautious")
        except Exception:
            pass

    # ---- DIVIDEND SIGNALS ----
    dividends = profile.get('dividends', {})

    # High dividend yield = bullish
    div_yield = dividends.get('dividend_yield')
    if div_yield:
        if isinstance(div_yield, str):
            div_yield = float(div_yield.replace('%', '')) / 100
        if div_yield > 0.03:  # > 3% yield
            score += 1
            reasons.append(f"High dividend yield: {div_yield*100:.1f}%")

    # Ex-dividend coming = sell pressure
    ex_date = dividends.get('ex_dividend_date')
    if ex_date:
        try:
            days_to_ex = (pd.Timestamp(ex_date) - pd.Timestamp.now()).days
            if 0 < days_to_ex <= 5:
                flags.append(f"Ex-dividend in {days_to_ex} days")
        except Exception:
            pass

    # ---- INSIDER SIGNALS ----
    insider = profile.get('insider', {})
    transactions = insider.get('insider_transactions', [])

    buy_count = sum(1 for t in transactions
                   if 'buy' in str(t.get('transaction', '')).lower())
    sell_count = sum(1 for t in transactions
                    if 'sell' in str(t.get('transaction', '')).lower())

    if buy_count > sell_count and buy_count > 0:
        score += 1
        reasons.append(f"Insider buying: {buy_count} buy transactions")
    elif sell_count > buy_count and sell_count > 1:
        score -= 1
        flags.append(f"Insider selling: {sell_count} sell transactions")

    # ---- GENERATE SIGNAL ----
    if score >= 2:
        signal = 'STRONG_BUY'
    elif score == 1:
        signal = 'BUY'
    elif score == -1:
        signal = 'CAUTION'
    elif score <= -2:
        signal = 'AVOID'
    else:
        signal = 'NEUTRAL'

    return {
        'signal': signal,
        'score': score,
        'reasons': reasons,
        'flags': flags,
        'confidence': min(abs(score) * 25, 100)
    }


# ============================================================
# 7. SAVE TO DATABASE
# ============================================================

def save_corporate_data(profile: dict):
    """Save corporate profile to database"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS corporate_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp TEXT,
            next_earnings_date TEXT,
            eps_surprise_pct REAL,
            dividend_yield REAL,
            ex_dividend_date TEXT,
            promoter_holding_pct TEXT,
            corporate_signal TEXT,
            corporate_score INTEGER,
            flags TEXT,
            reasons TEXT,
            full_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        earnings = profile.get('earnings', {})
        dividends = profile.get('dividends', {})
        insider = profile.get('insider', {})
        signal = profile.get('signal', {})

        cursor.execute('''
        INSERT OR REPLACE INTO corporate_actions
        (symbol, timestamp, next_earnings_date, eps_surprise_pct,
         dividend_yield, ex_dividend_date, promoter_holding_pct,
         corporate_signal, corporate_score, flags, reasons, full_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile['symbol'],
            profile['timestamp'],
            earnings.get('next_earnings_date'),
            earnings.get('eps_surprise_pct'),
            dividends.get('dividend_yield'),
            dividends.get('ex_dividend_date'),
            str(insider.get('promoter_holding_pct', '')),
            signal.get('signal'),
            signal.get('score', 0),
            json.dumps(signal.get('flags', [])),
            json.dumps(signal.get('reasons', [])),
            json.dumps(profile)
        ))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"Error saving corporate data: {e}")
        return False


# ============================================================
# 8. BATCH FETCH FOR ALL STOCKS
# ============================================================

def fetch_all_corporate_data(symbols: list, max_stocks: int = 150):
    """
    Fetch corporate data for all Nifty 150 stocks
    Runs daily/weekly
    """
    print(f"\n{'='*60}")
    print(f"PHASE 2: CORPORATE ACTIONS DATA FETCH")
    print(f"{'='*60}")
    print(f"Fetching data for {min(len(symbols), max_stocks)} stocks...")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = {
        'success': 0,
        'failed': 0,
        'total': 0,
        'alerts': []
    }

    for i, symbol in enumerate(symbols[:max_stocks]):
        try:
            print(f"[{i+1}/{min(len(symbols), max_stocks)}] {symbol}")

            profile = get_complete_corporate_profile(symbol)
            save_corporate_data(profile)

            signal = profile.get('signal', {})
            flags = signal.get('flags', [])

            # Collect important alerts
            if flags:
                results['alerts'].append({
                    'symbol': symbol,
                    'signal': signal.get('signal'),
                    'flags': flags
                })

            results['success'] += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results['failed'] += 1

        results['total'] += 1

    print(f"\n{'='*60}")
    print(f"PHASE 2 FETCH COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Success: {results['success']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⚠️  Alerts: {len(results['alerts'])}")

    if results['alerts']:
        print(f"\n🚨 IMPORTANT ALERTS:")
        for alert in results['alerts']:
            print(f"  {alert['symbol']}: {', '.join(alert['flags'])}")

    return results


# ============================================================
# 9. QUERY FUNCTIONS
# ============================================================

def get_upcoming_results(days_ahead: int = 14) -> list:
    """Get stocks with results in next N days"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT symbol, next_earnings_date, corporate_signal, flags
        FROM corporate_actions
        WHERE next_earnings_date IS NOT NULL
        AND date(next_earnings_date) BETWEEN date('now') AND date('now', ?)
        ORDER BY next_earnings_date
        ''', (f'+{days_ahead} days',))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return []


def get_high_dividend_stocks(min_yield: float = 0.02) -> list:
    """Get stocks with dividend yield above threshold"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT symbol, dividend_yield, ex_dividend_date, corporate_signal
        FROM corporate_actions
        WHERE dividend_yield > ?
        ORDER BY dividend_yield DESC
        ''', (min_yield,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return []


def get_insider_buying_stocks() -> list:
    """Get stocks with active insider buying"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT symbol, corporate_signal, corporate_score, reasons
        FROM corporate_actions
        WHERE reasons LIKE '%Insider buying%'
        AND corporate_score > 0
        ORDER BY corporate_score DESC
        ''')

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return []


def get_corporate_summary() -> dict:
    """Get summary of all corporate data"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as total FROM corporate_actions')
        total = cursor.fetchone()['total']

        cursor.execute('''
        SELECT corporate_signal, COUNT(*) as count
        FROM corporate_actions
        GROUP BY corporate_signal
        ''')
        signals = {row['corporate_signal']: row['count']
                  for row in cursor.fetchall()}

        cursor.execute('''
        SELECT COUNT(*) as count FROM corporate_actions
        WHERE next_earnings_date IS NOT NULL
        AND date(next_earnings_date) BETWEEN date('now') AND date('now', '+14 days')
        ''')
        upcoming = cursor.fetchone()['count']

        conn.close()

        return {
            'total_stocks': total,
            'signals': signals,
            'upcoming_results_14days': upcoming,
            'last_updated': datetime.now().isoformat()
        }
    except Exception as e:
        return {}


if __name__ == '__main__':
    # Test with a few stocks
    test_stocks = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'WIPRO.NS']

    print("Testing Phase 2 Corporate Actions Module")
    print("="*50)

    for symbol in test_stocks:
        print(f"\nTesting {symbol}...")
        profile = get_complete_corporate_profile(symbol)
        signal = profile.get('signal', {})

        print(f"  Signal: {signal.get('signal')}")
        print(f"  Score: {signal.get('score')}")
        if signal.get('reasons'):
            print(f"  Reasons: {', '.join(signal.get('reasons', []))}")
        if signal.get('flags'):
            print(f"  ⚠️  Flags: {', '.join(signal.get('flags', []))}")

    print("\n✅ Phase 2 Test Complete!")
