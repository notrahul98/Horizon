import {
  TrendingUp,
  TrendingDown,
  Activity,
  Database,
  BarChart3,
  Trophy,
  ChevronDown,
  Search,
  Zap,
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
  AreaChart,
  Area,
  PieChart,
  Pie,
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

const sectorPie = [
  { name: "Banks", value: 14, color: "#64b5f6" },
  { name: "Pharma", value: 9, color: "#81c784" },
  { name: "IT", value: 8, color: "#ffb74d" },
  { name: "Steel", value: 6, color: "#e57373" },
  { name: "Auto", value: 6, color: "#ba68c8" },
  { name: "Other", value: 96, color: "#4db6ac" },
];

const moverData = [
  { symbol: "TCS.NS", change: 3.30, type: "gain" },
  { symbol: "INFY.NS", change: 3.46, type: "gain" },
  { symbol: "HCLTECH.NS", change: 2.90, type: "gain" },
  { symbol: "BAJFINANCE.NS", change: 2.44, type: "gain" },
  { symbol: "RELIANCE.NS", change: 2.10, type: "gain" },
  { symbol: "LT.NS", change: -1.13, type: "loss" },
  { symbol: "AXISBANK.NS", change: -0.59, type: "loss" },
  { symbol: "MARUTI.NS", change: -0.43, type: "loss" },
  { symbol: "KOTAKBANK.NS", change: -0.42, type: "loss" },
  { symbol: "ITC.NS", change: -0.22, type: "loss" },
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
  { label: "Stocks Tracked", value: "139", icon: Database, accent: "from-emerald-500/20 to-emerald-500/5", border: "border-emerald-500/30", text: "text-emerald-400" },
  { label: "Price Records", value: "43,822", icon: BarChart3, accent: "from-sky-500/20 to-sky-500/5", border: "border-sky-500/30", text: "text-sky-400" },
  { label: "Avg Day Change", value: "+0.15%", icon: TrendingUp, accent: "from-emerald-500/20 to-emerald-500/5", border: "border-emerald-500/30", text: "text-emerald-400" },
  { label: "Top Gainer", value: "RELIANCE", icon: Trophy, accent: "from-amber-500/20 to-amber-500/5", border: "border-amber-500/30", text: "text-amber-400" },
];

export function Spotlight() {
  return (
    <div className="min-h-screen bg-[#0f0f1a] text-gray-300">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-sky-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="text-xl font-bold text-white tracking-tight">
            Nifty 150
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm">
            <Search className="w-4 h-4 text-gray-500" />
            <span className="text-gray-500">Search stocks...</span>
          </div>
          <div className="text-xs text-gray-500">02 Jul 2026 · IST</div>
        </div>
      </header>

      <div className="p-5 space-y-5">
        {/* KPIs */}
        <div className="grid grid-cols-4 gap-4">
          {kpis.map((k) => (
            <div
              key={k.label}
              className={`relative overflow-hidden rounded-xl border ${k.border} bg-gradient-to-br ${k.accent} p-4 backdrop-blur-sm`}
            >
              <div className="absolute top-0 right-0 w-20 h-20 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-xl" />
              <div className="relative">
                <div className="flex items-center gap-2 mb-2">
                  <k.icon className={`w-4 h-4 ${k.text}`} />
                  <span className="text-[10px] uppercase tracking-wider text-gray-500">
                    {k.label}
                  </span>
                </div>
                <div className={`text-3xl font-bold ${k.text}`}>{k.value}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Main */}
        <div className="grid grid-cols-2 gap-5">
          {/* Stock Table */}
          <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Market Quotes</h3>
              <div className="flex items-center gap-1 text-xs text-gray-500 bg-white/5 px-2 py-1 rounded border border-white/10">
                <span>All Sectors</span>
                <ChevronDown className="w-3 h-3" />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-white/5">
                    <th className="pb-2 text-left font-medium">Symbol</th>
                    <th className="pb-2 text-left font-medium">Name</th>
                    <th className="pb-2 text-right font-medium">Close</th>
                    <th className="pb-2 text-right font-medium">Chg%</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s) => (
                    <tr
                      key={s.symbol}
                      className="border-b border-white/[0.03] hover:bg-white/[0.05] transition-colors cursor-pointer"
                    >
                      <td className="py-2 font-bold text-white">{s.symbol}</td>
                      <td className="py-2 text-gray-400">{s.name}</td>
                      <td className="py-2 text-right font-mono text-gray-200">
                        {s.close.toFixed(2)}
                      </td>
                      <td className="py-2 text-right">
                        <span
                          className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                            s.change >= 0
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "bg-red-500/15 text-red-400"
                          }`}
                        >
                          {s.change >= 0 ? (
                            <TrendingUp className="w-3 h-3" />
                          ) : (
                            <TrendingDown className="w-3 h-3" />
                          )}
                          {s.change >= 0 ? "+" : ""}
                          {s.change.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Charts */}
          <div className="space-y-4">
            {/* Sector Donut */}
            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
              <h3 className="text-sm font-semibold text-white mb-2">Sector Breakdown</h3>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={sectorPie}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {sectorPie.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a2e",
                      border: "1px solid #333",
                      borderRadius: 8,
                      color: "#ccc",
                      fontSize: 11,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-2 mt-1">
                {sectorPie.slice(0, 5).map((s) => (
                  <div key={s.name} className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                    <span className="text-[10px] text-gray-400">{s.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Movers */}
            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
              <h3 className="text-sm font-semibold text-white mb-2">Top Movers</h3>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={moverData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis type="number" tick={{ fill: "#666", fontSize: 10 }} />
                  <YAxis
                    dataKey="symbol"
                    type="category"
                    tick={{ fill: "#999", fontSize: 10 }}
                    width={80}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a2e",
                      border: "1px solid #333",
                      borderRadius: 8,
                      color: "#ccc",
                      fontSize: 11,
                    }}
                  />
                  <Bar dataKey="change" radius={[0, 4, 4, 0]} barSize={14}>
                    {moverData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.type === "gain" ? "#00e676" : "#ff5252"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Price Chart */}
        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">RELIANCE.NS</h3>
              <p className="text-xs text-gray-500">1 Year Price History</p>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500 bg-white/5 px-2 py-1 rounded border border-white/10">
              <span>1Y</span>
              <ChevronDown className="w-3 h-3" />
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={priceHistory}>
              <defs>
                <linearGradient id="spotlightArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00e676" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#00e676" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
              <XAxis dataKey="date" tick={{ fill: "#666", fontSize: 10 }} />
              <YAxis
                domain={["dataMin - 30", "dataMax + 30"]}
                tick={{ fill: "#666", fontSize: 10 }}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1a2e",
                  border: "1px solid #333",
                  borderRadius: 8,
                  color: "#ccc",
                  fontSize: 11,
                }}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke="#00e676"
                strokeWidth={2.5}
                fill="url(#spotlightArea)"
                dot={{ r: 4, fill: "#00e676", stroke: "#0f0f1a", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
