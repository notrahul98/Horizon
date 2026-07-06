import {
  TrendingUp,
  TrendingDown,
  Activity,
  Database,
  BarChart3,
  Trophy,
  ChevronDown,
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
  Legend,
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
  { sector: "Banks", count: 14, avg: 536.77 },
  { sector: "Pharma", count: 9, avg: 2680.77 },
  { sector: "IT Services", count: 8, avg: 1972.26 },
  { sector: "Steel", count: 6, avg: 865.03 },
  { sector: "Auto", count: 6, avg: 7174.40 },
];

const moverData = [
  { symbol: "TCS.NS", change: 3.30, type: "gain" },
  { symbol: "INFY.NS", change: 3.46, type: "gain" },
  { symbol: "HCLTECH.NS", change: 2.90, type: "gain" },
  { symbol: "BAJFINANCE.NS", change: 2.44, type: "gain" },
  { symbol: "RELIANCE.NS", change: 2.10, type: "gain" },
  { symbol: "LT.NS", change: -1.13, type: "loss" },
  { symbol: "KOTAKBANK.NS", change: -0.42, type: "loss" },
  { symbol: "MARUTI.NS", change: -0.43, type: "loss" },
  { symbol: "AXISBANK.NS", change: -0.59, type: "loss" },
  { symbol: "ITC.NS", change: -0.22, type: "loss" },
];

const priceHistory = [
  { date: "Jan", open: 1250, close: 1280 },
  { date: "Feb", open: 1280, close: 1320 },
  { date: "Mar", open: 1320, close: 1290 },
  { date: "Apr", open: 1290, close: 1310 },
  { date: "May", open: 1310, close: 1285 },
  { date: "Jun", open: 1285, close: 1300 },
  { date: "Jul", open: 1300, close: 1303 },
];

const kpis = [
  { label: "Stocks Tracked", value: "139", icon: Database, color: "text-emerald-400", border: "border-emerald-500" },
  { label: "Price Records", value: "43,822", icon: BarChart3, color: "text-sky-400", border: "border-sky-500" },
  { label: "Avg Day Change", value: "+0.15%", icon: Activity, color: "text-emerald-400", border: "border-emerald-500" },
  { label: "Top Gainer", value: "RELIANCE +2.1%", icon: Trophy, color: "text-amber-400", border: "border-amber-500" },
];

export function Terminal() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-300 font-mono text-sm">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-[#0d0d14]">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-emerald-400 font-bold tracking-widest text-lg">
            NIFTY 150 TERMINAL
          </span>
        </div>
        <span className="text-gray-500 text-xs">02 JUL 2026 · IST 15:42:18</span>
      </nav>

      <div className="p-4 space-y-4">
        {/* KPIs */}
        <div className="grid grid-cols-4 gap-3">
          {kpis.map((k) => (
            <div
              key={k.label}
              className={`bg-[#111118] border-l-2 ${k.border} rounded p-3`}
            >
              <div className="flex items-center gap-2 mb-1">
                <k.icon className={`w-3.5 h-3.5 ${k.color}`} />
                <span className="text-[10px] uppercase tracking-wider text-gray-500">
                  {k.label}
                </span>
              </div>
              <div className={`text-xl font-bold ${k.color}`}>{k.value}</div>
            </div>
          ))}
        </div>

        {/* Main */}
        <div className="grid grid-cols-3 gap-4">
          {/* Stock Table */}
          <div className="col-span-2 bg-[#111118] rounded border border-gray-800 overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
              <span className="text-xs uppercase tracking-wider text-gray-500">
                Live Quote Feed
              </span>
              <div className="flex items-center gap-1 text-xs text-gray-500 bg-[#0a0a0f] px-2 py-1 rounded border border-gray-800">
                <span>SYMBOL</span>
                <ChevronDown className="w-3 h-3" />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="px-2 py-1.5 text-left">SYMBOL</th>
                    <th className="px-2 py-1.5 text-left">NAME</th>
                    <th className="px-2 py-1.5 text-left">SECTOR</th>
                    <th className="px-2 py-1.5 text-right">CLOSE</th>
                    <th className="px-2 py-1.5 text-right">CHG%</th>
                    <th className="px-2 py-1.5 text-right">HIGH</th>
                    <th className="px-2 py-1.5 text-right">LOW</th>
                    <th className="px-2 py-1.5 text-right">VOL</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s) => (
                    <tr
                      key={s.symbol}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a24] transition-colors cursor-pointer"
                    >
                      <td className="px-2 py-1.5 font-bold text-gray-200">
                        {s.symbol}
                      </td>
                      <td className="px-2 py-1.5 text-gray-400">{s.name}</td>
                      <td className="px-2 py-1.5">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                          {s.sector}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-right text-gray-200 font-mono">
                        {s.close.toFixed(2)}
                      </td>
                      <td
                        className={`px-2 py-1.5 text-right font-mono font-bold ${
                          s.change >= 0 ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {s.change >= 0 ? "+" : ""}
                        {s.change.toFixed(2)}%
                      </td>
                      <td className="px-2 py-1.5 text-right text-gray-400 font-mono">
                        {s.high.toFixed(2)}
                      </td>
                      <td className="px-2 py-1.5 text-right text-gray-400 font-mono">
                        {s.low.toFixed(2)}
                      </td>
                      <td className="px-2 py-1.5 text-right text-gray-500 font-mono">
                        {(s.volume / 1000000).toFixed(1)}M
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Charts */}
          <div className="space-y-3">
            {/* Sector */}
            <div className="bg-[#111118] rounded border border-gray-800 p-3">
              <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2">
                Sector Distribution
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={sectorData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis dataKey="sector" tick={{ fill: "#666", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#666", fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a24",
                      border: "1px solid #333",
                      borderRadius: 4,
                      color: "#ccc",
                      fontSize: 11,
                    }}
                  />
                  <Bar dataKey="count" fill="#0ea5e9" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Movers */}
            <div className="bg-[#111118] rounded border border-gray-800 p-3">
              <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2">
                Top Movers
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={moverData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis type="number" tick={{ fill: "#666", fontSize: 10 }} />
                  <YAxis
                    dataKey="symbol"
                    type="category"
                    tick={{ fill: "#999", fontSize: 10 }}
                    width={80}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a24",
                      border: "1px solid #333",
                      borderRadius: 4,
                      color: "#ccc",
                      fontSize: 11,
                    }}
                  />
                  <Bar dataKey="change" radius={[0, 2, 2, 0]}>
                    {moverData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.type === "gain" ? "#10b981" : "#ef4444"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Price Chart */}
        <div className="bg-[#111118] rounded border border-gray-800 p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] uppercase tracking-wider text-gray-500">
              RELIANCE.NS — Price History
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500 bg-[#0a0a0f] px-2 py-1 rounded border border-gray-800">
              <span>1Y</span>
              <ChevronDown className="w-3 h-3" />
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={priceHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#222" />
              <XAxis dataKey="date" tick={{ fill: "#666", fontSize: 10 }} />
              <YAxis
                domain={["dataMin - 20", "dataMax + 20"]}
                tick={{ fill: "#666", fontSize: 10 }}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #333",
                  borderRadius: 4,
                  color: "#ccc",
                  fontSize: 11,
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 10, color: "#666" }}
              />
              <Line
                type="monotone"
                dataKey="open"
                stroke="#64748b"
                strokeWidth={1.5}
                dot={false}
                name="Open"
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ r: 3, fill: "#10b981" }}
                name="Close"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
