"""
Phase 2: Corporate Actions Dashboard Routes
Add these routes to your existing dashboard.py
"""

from flask import Blueprint, jsonify, render_template_string
from corporate_actions import (
    get_complete_corporate_profile,
    get_upcoming_results,
    get_high_dividend_stocks,
    get_insider_buying_stocks,
    get_corporate_summary
)

corporate_bp = Blueprint('corporate', __name__)

# ============================================================
# API ROUTES
# ============================================================

@corporate_bp.route('/api/corporate/summary')
def api_corporate_summary():
    """Overall corporate actions summary"""
    return jsonify(get_corporate_summary())


@corporate_bp.route('/api/corporate/stock/<symbol>')
def api_stock_corporate(symbol):
    """Full corporate profile for one stock"""
    if not symbol.endswith('.NS'):
        symbol = symbol + '.NS'
    profile = get_complete_corporate_profile(symbol)
    return jsonify(profile)


@corporate_bp.route('/api/corporate/upcoming-results')
def api_upcoming_results():
    """Stocks with results in next 14 days"""
    results = get_upcoming_results(14)
    return jsonify({
        'count': len(results),
        'stocks': results
    })


@corporate_bp.route('/api/corporate/dividends')
def api_dividends():
    """High dividend yield stocks"""
    stocks = get_high_dividend_stocks(0.02)
    return jsonify({
        'count': len(stocks),
        'stocks': stocks
    })


@corporate_bp.route('/api/corporate/insider-buying')
def api_insider_buying():
    """Stocks with insider buying activity"""
    stocks = get_insider_buying_stocks()
    return jsonify({
        'count': len(stocks),
        'stocks': stocks
    })


# ============================================================
# CORPORATE DASHBOARD PAGE
# ============================================================

CORPORATE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Corporate Actions - TradeFlow</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 20px 30px;
            border-bottom: 1px solid #333;
        }
        .header h1 { color: #7c3aed; font-size: 1.8em; }
        .header p { color: #888; margin-top: 5px; }
        .nav { display: flex; gap: 15px; margin-top: 15px; }
        .nav a {
            color: #7c3aed;
            text-decoration: none;
            padding: 8px 16px;
            border: 1px solid #7c3aed;
            border-radius: 5px;
            font-size: 0.9em;
            transition: all 0.3s;
        }
        .nav a:hover { background: #7c3aed; color: white; }
        .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 25px;
            border: 1px solid #333;
        }
        .card h2 { color: #7c3aed; margin-bottom: 15px; font-size: 1.1em; }
        .kpi { font-size: 2.5em; font-weight: bold; color: white; }
        .kpi-label { color: #888; font-size: 0.9em; margin-top: 5px; }
        .table-card { background: #1a1a2e; border-radius: 12px; padding: 25px; border: 1px solid #333; margin-bottom: 20px; }
        .table-card h2 { color: #7c3aed; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #16213e; padding: 12px; text-align: left; color: #888; font-size: 0.85em; text-transform: uppercase; }
        td { padding: 12px; border-bottom: 1px solid #222; }
        tr:hover { background: #16213e; }
        .signal-STRONG_BUY { color: #10b981; font-weight: bold; }
        .signal-BUY { color: #34d399; }
        .signal-NEUTRAL { color: #888; }
        .signal-CAUTION { color: #fbbf24; }
        .signal-AVOID { color: #ef4444; }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge-warning { background: #fbbf24; color: black; }
        .badge-danger { background: #ef4444; color: white; }
        .badge-success { background: #10b981; color: white; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .search-box {
            width: 100%;
            padding: 12px 15px;
            background: #16213e;
            border: 1px solid #333;
            border-radius: 8px;
            color: white;
            font-size: 1em;
            margin-bottom: 20px;
        }
        .search-box:focus { outline: none; border-color: #7c3aed; }
        .refresh-btn {
            background: #7c3aed;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            margin-bottom: 20px;
        }
        .refresh-btn:hover { background: #6d28d9; }
        .flag { color: #fbbf24; font-size: 0.85em; }
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .kpi { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Corporate Actions</h1>
        <p>Results Calendar • Dividends • Insider Activity • Bulk Deals</p>
        <div class="nav">
            <a href="/">← Dashboard</a>
            <a href="/corporate">Corporate Actions</a>
            <a href="/api/corporate/summary">API</a>
        </div>
    </div>

    <div class="container">
        <!-- KPI Cards -->
        <div class="grid" id="kpiCards">
            <div class="card">
                <div class="kpi" id="totalStocks">-</div>
                <div class="kpi-label">📊 Stocks Analyzed</div>
            </div>
            <div class="card">
                <div class="kpi" id="upcomingResults">-</div>
                <div class="kpi-label">📅 Results in 14 Days</div>
            </div>
            <div class="card">
                <div class="kpi" id="insiderBuying">-</div>
                <div class="kpi-label">👔 Insider Buying</div>
            </div>
            <div class="card">
                <div class="kpi" id="highDividend">-</div>
                <div class="kpi-label">💰 High Dividend Yield</div>
            </div>
        </div>

        <!-- Upcoming Results -->
        <div class="table-card">
            <h2>📅 Upcoming Results (Next 14 Days) - AVOID or Trade with Caution!</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Results Date</th>
                        <th>Days Away</th>
                        <th>Signal</th>
                        <th>Flags</th>
                    </tr>
                </thead>
                <tbody id="upcomingTable">
                    <tr><td colspan="5" class="loading">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- High Dividend Stocks -->
        <div class="table-card">
            <h2>💰 High Dividend Yield Stocks</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Dividend Yield</th>
                        <th>Ex-Date</th>
                        <th>Signal</th>
                    </tr>
                </thead>
                <tbody id="dividendTable">
                    <tr><td colspan="4" class="loading">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Insider Buying -->
        <div class="table-card">
            <h2>👔 Insider Buying Activity</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Signal</th>
                        <th>Score</th>
                        <th>Reasons</th>
                    </tr>
                </thead>
                <tbody id="insiderTable">
                    <tr><td colspan="4" class="loading">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Single Stock Lookup -->
        <div class="table-card">
            <h2>🔍 Look Up Any Stock</h2>
            <input type="text" class="search-box" id="stockInput" placeholder="Enter stock symbol (e.g. RELIANCE or RELIANCE.NS)">
            <button class="refresh-btn" onclick="lookupStock()">🔍 Get Corporate Data</button>
            <div id="stockResult"></div>
        </div>
    </div>

    <script>
        async function loadData() {
            // Load summary
            try {
                const resp = await fetch('/api/corporate/summary');
                const data = await resp.json();
                document.getElementById('totalStocks').textContent = data.total_stocks || 0;
                document.getElementById('upcomingResults').textContent = data.upcoming_results_14days || 0;
            } catch(e) {}

            // Load upcoming results
            try {
                const resp = await fetch('/api/corporate/upcoming-results');
                const data = await resp.json();
                document.getElementById('upcomingResults').textContent = data.count || 0;

                const tbody = document.getElementById('upcomingTable');
                if (data.stocks && data.stocks.length > 0) {
                    tbody.innerHTML = data.stocks.map(s => {
                        const days = s.next_earnings_date ?
                            Math.ceil((new Date(s.next_earnings_date) - new Date()) / (1000*60*60*24)) : '-';
                        const flags = s.flags ? JSON.parse(s.flags).join(', ') : '';
                        return `
                        <tr>
                            <td><strong>${s.symbol}</strong></td>
                            <td>${s.next_earnings_date || '-'}</td>
                            <td>${days} days</td>
                            <td class="signal-${s.corporate_signal}">${s.corporate_signal || '-'}</td>
                            <td class="flag">${flags}</td>
                        </tr>`;
                    }).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" style="color:#888; text-align:center">No upcoming results in 14 days</td></tr>';
                }
            } catch(e) {
                document.getElementById('upcomingTable').innerHTML = '<tr><td colspan="5" style="color:#888">No data yet - run corporate_actions.py first</td></tr>';
            }

            // Load dividends
            try {
                const resp = await fetch('/api/corporate/dividends');
                const data = await resp.json();
                document.getElementById('highDividend').textContent = data.count || 0;

                const tbody = document.getElementById('dividendTable');
                if (data.stocks && data.stocks.length > 0) {
                    tbody.innerHTML = data.stocks.map(s => `
                        <tr>
                            <td><strong>${s.symbol}</strong></td>
                            <td>${s.dividend_yield ? (s.dividend_yield*100).toFixed(2)+'%' : '-'}</td>
                            <td>${s.ex_dividend_date || '-'}</td>
                            <td class="signal-${s.corporate_signal}">${s.corporate_signal || '-'}</td>
                        </tr>`
                    ).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="color:#888; text-align:center">No data yet</td></tr>';
                }
            } catch(e) {}

            // Load insider buying
            try {
                const resp = await fetch('/api/corporate/insider-buying');
                const data = await resp.json();
                document.getElementById('insiderBuying').textContent = data.count || 0;

                const tbody = document.getElementById('insiderTable');
                if (data.stocks && data.stocks.length > 0) {
                    tbody.innerHTML = data.stocks.map(s => {
                        const reasons = s.reasons ? JSON.parse(s.reasons).join(', ') : '';
                        return `
                        <tr>
                            <td><strong>${s.symbol}</strong></td>
                            <td class="signal-${s.corporate_signal}">${s.corporate_signal || '-'}</td>
                            <td>${s.corporate_score || 0}</td>
                            <td style="color:#10b981; font-size:0.85em">${reasons}</td>
                        </tr>`;
                    }).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="color:#888; text-align:center">No insider buying detected</td></tr>';
                }
            } catch(e) {}
        }

        async function lookupStock() {
            let symbol = document.getElementById('stockInput').value.trim().toUpperCase();
            if (!symbol) return;
            if (!symbol.endsWith('.NS')) symbol += '.NS';

            document.getElementById('stockResult').innerHTML = '<p style="color:#888">Loading...</p>';

            try {
                const resp = await fetch(`/api/corporate/stock/${symbol}`);
                const data = await resp.json();

                const signal = data.signal || {};
                const earnings = data.earnings || {};
                const dividends = data.dividends || {};
                const insider = data.insider || {};

                document.getElementById('stockResult').innerHTML = `
                    <div style="margin-top:20px; padding:20px; background:#16213e; border-radius:8px;">
                        <h3 style="color:#7c3aed; margin-bottom:15px">${symbol} - Corporate Profile</h3>

                        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:15px; margin-bottom:20px">
                            <div style="padding:15px; background:#1a1a2e; border-radius:8px;">
                                <div style="color:#888; font-size:0.85em">Corporate Signal</div>
                                <div class="signal-${signal.signal}" style="font-size:1.5em; font-weight:bold">${signal.signal || 'N/A'}</div>
                                <div style="color:#888; font-size:0.85em">Score: ${signal.score || 0}</div>
                            </div>
                            <div style="padding:15px; background:#1a1a2e; border-radius:8px;">
                                <div style="color:#888; font-size:0.85em">Next Results</div>
                                <div style="font-size:1.2em">${earnings.next_earnings_date || 'Unknown'}</div>
                            </div>
                            <div style="padding:15px; background:#1a1a2e; border-radius:8px;">
                                <div style="color:#888; font-size:0.85em">EPS Surprise</div>
                                <div style="font-size:1.2em; color:${earnings.eps_surprise_pct > 0 ? '#10b981' : '#ef4444'}">
                                    ${earnings.eps_surprise_pct ? earnings.eps_surprise_pct.toFixed(1)+'%' : 'N/A'}
                                </div>
                            </div>
                            <div style="padding:15px; background:#1a1a2e; border-radius:8px;">
                                <div style="color:#888; font-size:0.85em">Dividend Yield</div>
                                <div style="font-size:1.2em">${dividends.dividend_yield ? (dividends.dividend_yield*100).toFixed(2)+'%' : 'N/A'}</div>
                                <div style="color:#888; font-size:0.8em">Ex-Date: ${dividends.ex_dividend_date || 'N/A'}</div>
                            </div>
                        </div>

                        ${signal.reasons && signal.reasons.length > 0 ? `
                        <div style="margin-bottom:10px">
                            <strong style="color:#10b981">✅ Positive Signals:</strong>
                            <ul style="margin-top:5px; padding-left:20px; color:#34d399">
                                ${signal.reasons.map(r => `<li>${r}</li>`).join('')}
                            </ul>
                        </div>` : ''}

                        ${signal.flags && signal.flags.length > 0 ? `
                        <div>
                            <strong style="color:#fbbf24">⚠️ Flags:</strong>
                            <ul style="margin-top:5px; padding-left:20px; color:#fbbf24">
                                ${signal.flags.map(f => `<li>${f}</li>`).join('')}
                            </ul>
                        </div>` : ''}
                    </div>
                `;
            } catch(e) {
                document.getElementById('stockResult').innerHTML = `<p style="color:#ef4444">Error loading data</p>`;
            }
        }

        // Load on page start
        loadData();

        // Refresh every 5 minutes
        setInterval(loadData, 5 * 60 * 1000);
    </script>
</body>
</html>
"""

@corporate_bp.route('/corporate')
def corporate_dashboard():
    """Corporate actions dashboard page"""
    return render_template_string(CORPORATE_HTML)
