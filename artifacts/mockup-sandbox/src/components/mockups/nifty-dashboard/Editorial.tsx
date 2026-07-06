import {
  TrendingUp,
  TrendingDown,
  Activity,
  Database,
  BarChart3,
  Trophy,
  ChevronDown,
  Search,
  Clock,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
} from "recharts";

const stocks = [
  { symbol: "RELIANCE.NS", name: "Reliance Industries", sector: "Oil & Gas", close: 1303.70, change: 2.10, high: 1313.20, low: 1299.00, volume: 14347980 },
  { symbol: "TCS.NS", name: "Tata Consultancy", sector: "IT Services", close: 2074.40, change: 3.30, high: 2076.90, low: 2002.50, volume: 5281922 },
  { symbol: "ICICIBANK.NS", name: "ICICI Bank", sector: "Banks", close: 1401.60, change: 1.40, high: 1402.00, low: 1376.80, volume: 12431040 },
  { symbol: "BHARTIARTL.NS", name: "Bharti Airtel", sector: "Telecom", close: 1879.30, change: 1.00, high: 1883.80, low: 1850.20, volume: 4171893 },
  { symbol: "INFY.NS", name: "Infosys", sector: "IT Services", close: 1041.20, change: 3.46, high: 1041.90, low: 1006.00, volume: 14395037 },
  { symbol: "SBIN.NS", name: "State Bank", sector: "Banks", close: 1054.00, change: 0.30, high: 1059.80, low: 1045.00, volume: 12200205 },
  { symbol: "HINDUNILVR.NS", name: "Hindustan Unilever", sector: "Household", close: 2210.50, change: 1.12, high: 2216.00, low: 2179.20, volume: 2084082 },
  { symbol: "ITC.NS", name: "ITC", sector: "Tobacco", close: 290.05, change: -0.22, high: 291.00, low: 287.70, volume: 10875372 },
  { symbol: "LT.NS", name: "Larsen & Toubro", sector: "Engineering", close: 4053.70, change: -1.13, high: 4110.00, low: 4012.00, volume: 2015551 },
  { symbol: "BAJFINANCE.NS", name: "Bajaj Finance", sector: "Credit", close: 1019.00, change: 2.44, high: 1025.70, low: 993.40, volume: 6872817 },
  { symbol: "KOTAKBANK.NS", name: "Kotak Bank", sector: "Banks", close: 398.75, change: -0.42, high: 405.00, low: 397.30, volume: 10010556 },
  { symbol: "HCLTECH.NS", name: "HCL Technologies", sector: "IT Services", close: 1079.40, change: 2.90, high: 1082.90, low: 1048.00, volume: 3098767 },
  { symbol: "AXISBANK.NS", name: "Axis Bank", sector: "Banks", close: 1365.90, change: -0.59, high: 1375.50, low: 1358.10, volume: 3084362 },
  { symbol: "MARUTI.NS", name: "Maruti Suzuki", sector: "Auto", close: 14369.00, change: -0.43, high: 14490.00, low: 14275.00, volume: 270512 },
  { symbol: "SUNPHARMA.NS", name: "Sun Pharma", sector: "Pharma", close: 1872.90, change: -0.17, high: 1882.00, low: 1868.30, volume: 1111288 },
];

const sectorData = [
  { sector: "Banks", count: 14 },
  { sector: "Pharma", count: 9 },
  { sector: "IT Services", count: 8 },
  { sector: "Steel", count: 6 },
  { sector: "Auto", count: 6 },
  { sector: "Oil & Gas", count: 5 },
  { sector: "Credit", count: 5 },
  { sector: "Materials", count: 5 },
];

const priceHistory = [
  { date: "Jan", close: 1250 },
  { date: "Feb", close: 1320 },
  { date: "Mar", close: 1290 },
  { date: "Apr", close: 1310 },
  { date: "May", close: 1285 },
  { date: "Jun", close: 1300 },
  { date: "Jul", close: 1303 },
];

const kpis = [
  { label: "Stocks Tracked", value: "139" },
  { label: "Price Records", value: "43,822" },
  { label: "Avg Change", value: "+0.15%" },
  { label: "Top Gainer", value: "RELIANCE +2.1%" },
];

const gainers = stocks.filter((s) => s.change > 0).sort((a, b) => b.change - a.change).slice(0, 5);
const losers = stocks.filter((s) => s.change < 0).sort((a, b) => a.change - b.change).slice(0, 5);

export function Editorial() {
  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#1a1a1a]">
      {/* Masthead */}
      <header className="border-b-2 border-[#1a1a1a] px-8 py-6">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="font-['Playfair_Display'] text-5xl font-bold tracking-tight">
              Nifty 150
            </h1>
            <p className="font-['Playfair_Display'] text-lg text-gray-500 mt-1 italic">
              Indian Equity Market Monitor
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-[0.2em] text-gray-400">
              Thursday, 2 July 2026
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Asia/Kolkata · Market Closed
            </p>
          </div>
        </div>
      </header>

      {/* Hero / Market at a Glance */}
      <section className="px-8 py-6 border-b border-gray-200">
        <div className="flex gap-8 items-start">
          <div className="flex-1">
            <h2 className="font-['Playfair_Display'] text-2xl font-semibold mb-3">
              Market at a Glance
            </h2>
            <p className="text-gray-600 leading-relaxed text-sm max-w-xl">
              Markets opened strong with Information Technology and Banking sectors leading gains.
              Reliance Industries surged on positive quarterly outlook, while Larsen & Toubro
              faced profit-booking after recent highs. Overall breadth remains positive with
              advancing issues outpacing decliners across the Nifty 150 universe.
            </p>
          </div>
          <div className="flex gap-6">
            {kpis.map((k) => (
              <div key={k.label} className="text-center px-4 border-l border-gray-300 first:border-l-0">
                <div className="font-['Playfair_Display'] text-2xl font-bold text-[#1a1a1a]">
                  {k.value}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mt-1">
                  {k.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Three-column newspaper layout */}
      <div className="px-8 py-6 grid grid-cols-12 gap-6">
        {/* Left: Stock Table */}
        <div className="col-span-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-['Playfair_Display'] text-lg font-semibold">
              Closing Prices
            </h3>
            <div className="flex items-center gap-2 text-xs text-gray-400 border border-gray-300 rounded px-2 py-1">
              <Search className="w-3 h-3" />
              <span>Select stock...</span>
              <ChevronDown className="w-3 h-3" />
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-t-2 border-b border-[#1a1a1a]">
                <th className="py-2 text-left font-semibold text-xs uppercase tracking-wider">Symbol</th>
                <th className="py-2 text-left font-semibold text-xs uppercase tracking-wider">Name</th>
                <th className="py-2 text-left font-semibold text-xs uppercase tracking-wider">Sector</th>
                <th className="py-2 text-right font-semibold text-xs uppercase tracking-wider">Close</th>
                <th className="py-2 text-right font-semibold text-xs uppercase tracking-wider">Chg%</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => (
                <tr
                  key={s.symbol}
                  className="border-b border-gray-200 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <td className="py-2 font-bold text-xs">{s.symbol}</td>
                  <td className="py-2 text-gray-600 text-xs font-['Playfair_Display']">{s.name}</td>
                  <td className="py-2">
                    <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                      {s.sector}
                    </span>
                  </td>
                  <td className="py-2 text-right font-mono text-xs">{s.close.toFixed(2)}</td>
                  <td
                    className={`py-2 text-right font-mono text-xs font-semibold ${
                      s.change >= 0 ? "text-[#2d6a4f]" : "text-[#c1121f]"
                    }`}
                  >
                    {s.change >= 0 ? "+" : ""}
                    {s.change.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Middle: Sector Chart */}
        <div className="col-span-3">
          <h3 className="font-['Playfair_Display'] text-lg font-semibold mb-3">
            By Sector
          </h3>
          <div className="border border-gray-200 rounded p-3 bg-white">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={sectorData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis type="number" tick={{ fill: "#888", fontSize: 10 }} />
                <YAxis
                  dataKey="sector"
                  type="category"
                  tick={{ fill: "#555", fontSize: 10 }}
                  width={70}
                />
                <Tooltip
                  contentStyle={{
                    background: "#faf8f5",
                    border: "1px solid #ddd",
                    borderRadius: 4,
                    fontSize: 11,
                  }}
                />
                <Bar dataKey="count" fill="#2d6a4f" radius={[0, 2, 2, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Movers */}
        <div className="col-span-3">
          <h3 className="font-['Playfair_Display'] text-lg font-semibold mb-3">
            Top Movers
          </h3>
          <div className="space-y-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#2d6a4f] font-semibold mb-2">
                Gainers
              </p>
              <div className="space-y-1.5">
                {gainers.map((s) => (
                  <div
                    key={s.symbol}
                    className="flex items-center justify-between py-1.5 border-b border-gray-100"
                  >
                    <div>
                      <span className="font-bold text-xs">{s.symbol}</span>
                      <span className="text-[10px] text-gray-400 ml-1">{s.name}</span>
                    </div>
                    <span className="text-[#2d6a4f] font-mono text-xs font-bold">
                      +{s.change.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#c1121f] font-semibold mb-2">
                Losers
              </p>
              <div className="space-y-1.5">
                {losers.map((s) => (
                  <div
                    key={s.symbol}
                    className="flex items-center justify-between py-1.5 border-b border-gray-100"
                  >
                    <div>
                      <span className="font-bold text-xs">{s.symbol}</span>
                      <span className="text-[10px] text-gray-400 ml-1">{s.name}</span>
                    </div>
                    <span className="text-[#c1121f] font-mono text-xs font-bold">
                      {s.change.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom: Price Chart */}
      <div className="px-8 pb-8">
        <h3 className="font-['Playfair_Display'] text-lg font-semibold mb-3">
          RELIANCE.NS — One Year Price History
        </h3>
        <div className="border border-gray-200 rounded p-4 bg-white">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={priceHistory}>
              <defs>
                <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2d6a4f" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#2d6a4f" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="date" tick={{ fill: "#888", fontSize: 10 }} />
              <YAxis
                domain={["dataMin - 30", "dataMax + 30"]}
                tick={{ fill: "#888", fontSize: 10 }}
              />
              <Tooltip
                contentStyle={{
                  background: "#faf8f5",
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  fontSize: 11,
                }}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke="#2d6a4f"
                strokeWidth={2}
                fill="url(#colorClose)"
                dot={{ r: 3, fill: "#2d6a4f" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
