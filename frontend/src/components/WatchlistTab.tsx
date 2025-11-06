import React, { useState } from "react";
import { Trash2, ChevronDown, ChevronUp, TrendingUp, TrendingDown, Bell, Flame, Edit2, Check, X, Target, Sparkles, RefreshCw, Plus } from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "./ui/chart";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, ReferenceLine } from "recharts";
import { Textarea } from "./ui/textarea";
import { motion } from "motion/react";
import { demoAllAlerts, demoHistoryEntries } from "../lib/demoData";
import { useLiveWatchlist, LiveWatchlistStock } from "@/hooks/useLiveWatchlist";

interface WatchlistStock {
  id: string;
  symbol: string;
  name: string;
  addedPrice: number;
  currentPrice: number;
  change: number;
  targetLow: number;
  targetMid: number;
  targetHigh: number;
  stopLoss: number;
  notes: string;
  performanceData: { date: string; value: number }[];
  targetHit?: "low" | "mid" | "high" | null;
  removedDate?: string; // Date when stock was removed from watchlist
}

interface Alert {
  id: string;
  symbol: string;
  type: "bullish" | "bearish" | "neutral";
  message: string;
  time: string;
}

// Generate realistic performance data for a stock
const generatePerformanceData = (startPrice: number, currentPrice: number, days: number = 365) => {
  const data = [];
  const totalChange = (currentPrice - startPrice) / startPrice;
  const dailyVolatility = 0.02; // 2% daily volatility

  let price = startPrice;
  const baseDate = new Date();
  baseDate.setDate(baseDate.getDate() - days);

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate);
    date.setDate(baseDate.getDate() + i);

    // Add some realistic price movement with trend toward final price
    const progress = i / (days - 1);
    const trendComponent = startPrice + (totalChange * startPrice * progress);
    const randomComponent = (Math.random() - 0.5) * dailyVolatility * price;

    price = Math.max(0.01, trendComponent + randomComponent);

    // Format date based on time range for better readability
    let formattedDate: string;
    if (days <= 7) {
      // For 1D-1W: show time or day/month
      formattedDate = date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
    } else if (days <= 90) {
      // For 1M-3M: show month/day
      formattedDate = date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
    } else {
      // For 6M+: show month/year or month/day/year
      formattedDate = date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' });
    }

    data.push({
      date: formattedDate,
      value: Math.round(price * 100) / 100
    });
  }

  // Ensure the last price matches the current price
  data[data.length - 1].value = currentPrice;

  return data;
};

const initialWatchlist: WatchlistStock[] = [
  {
    id: "1",
    symbol: "META",
    name: "Meta Platforms Inc.",
    addedPrice: 478.50,
    currentPrice: 486.32,
    change: 1.63,
    targetLow: 510.00,
    targetMid: 520.00,
    targetHigh: 535.00,
    stopLoss: 460.00,
    notes: "Waiting for better entry point",
    performanceData: generatePerformanceData(478.50, 486.32, 365),
    targetHit: null
  },
  {
    id: "2",
    symbol: "AMZN",
    name: "Amazon.com Inc.",
    addedPrice: 180.40,
    currentPrice: 173.80,
    change: -3.66,
    targetLow: 188.00,
    targetMid: 195.00,
    targetHigh: 205.00,
    stopLoss: 172.00,
    notes: "Strong AWS growth potential",
    performanceData: generatePerformanceData(180.40, 173.80, 365),
    targetHit: null
  },
  {
    id: "3",
    symbol: "NFLX",
    name: "Netflix Inc.",
    addedPrice: 598.20,
    currentPrice: 643.50,
    change: 7.57,
    targetLow: 640.00,
    targetMid: 650.00,
    targetHigh: 670.00,
    stopLoss: 580.00,
    notes: "Content slate looks promising",
    performanceData: generatePerformanceData(598.20, 643.50, 365),
    targetHit: "low"
  },
  {
    id: "4",
    symbol: "TSLA",
    name: "Tesla Inc.",
    addedPrice: 248.50,
    currentPrice: 267.80,
    change: 7.76,
    targetLow: 275.00,
    targetMid: 290.00,
    targetHigh: 310.00,
    stopLoss: 235.00,
    notes: "EV market leader with strong fundamentals",
    performanceData: generatePerformanceData(248.50, 267.80, 365),
    targetHit: null
  },
  {
    id: "5",
    symbol: "NVDA",
    name: "NVIDIA Corp.",
    addedPrice: 125.40,
    currentPrice: 142.60,
    change: 13.72,
    targetLow: 150.00,
    targetMid: 165.00,
    targetHigh: 180.00,
    stopLoss: 115.00,
    notes: "AI chip demand continues to grow",
    performanceData: generatePerformanceData(125.40, 142.60, 365),
    targetHit: null
  },
  {
    id: "6",
    symbol: "AAPL",
    name: "Apple Inc.",
    addedPrice: 185.20,
    currentPrice: 178.90,
    change: -3.40,
    targetLow: 195.00,
    targetMid: 205.00,
    targetHigh: 220.00,
    stopLoss: 175.00,
    notes: "Removed due to weak iPhone sales",
    performanceData: generatePerformanceData(185.20, 178.90, 180),
    targetHit: null,
    removedDate: "10/15/24" // Removed 3 weeks ago
  }
];



const mockAlerts: Alert[] = [
  {
    id: "1",
    symbol: "META",
    type: "bullish",
    message: "META showing strong volume surge +240% above average. Institutional buying detected.",
    time: "2h ago"
  },
  {
    id: "2",
    symbol: "AMZN",
    type: "bearish",
    message: "AMZN approaching stop loss level. Consider risk management.",
    time: "4h ago"
  },
  {
    id: "3",
    symbol: "NFLX",
    type: "bullish",
    message: "NFLX breaking above resistance at $610. Momentum increasing.",
    time: "6h ago"
  }
];

const globalHotBets = [
  { rank: 1, symbol: "NVDA", change: 18.2, users: 2847, confidence: 92 },
  { rank: 2, symbol: "TSLA", change: 14.7, users: 2103, confidence: 75 },
  { rank: 3, symbol: "AMD", change: 11.3, users: 1789, confidence: 85 },
  { rank: 4, symbol: "COIN", change: -9.4, users: 1204, confidence: 68 },
  { rank: 5, symbol: "HOOD", change: 8.1, users: 987, confidence: 73 }
];

const chartConfig = {
  value: {
    label: "Performance",
    color: "hsl(var(--chart-1))"
  }
};

// Color palette for multiple lines
const stockColors = [
  "#a855f7", // purple
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ec4899", // pink
  "#06b6d4", // cyan
];

type TimePeriod = "1D" | "1W" | "1M" | "3M" | "6M" | "YTD" | "ALL";

// Mini Sparkline Component for individual stock cards
const MiniSparkline = ({ data, isPositive }: { data: { date: string; value: number }[], isPositive: boolean }) => {
  if (!data || data.length === 0) return null;

  // Calculate percentage change from entry price (first data point)
  const entryPrice = data[0]?.value || 0;
  const sparklineData = data.map(point => ({
    date: point.date,
    percent: entryPrice > 0 ? ((point.value - entryPrice) / entryPrice) * 100 : 0
  }));

  return (
    <div className="h-8 w-16">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={sparklineData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Line
            type="monotone"
            dataKey="percent"
            stroke={isPositive ? "#10b981" : "#ef4444"}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export function WatchlistTab() {
  // Live data hook
  const {
    stocks: liveStocks,
    isLoading,
    isRefreshing,
    error,
    refresh,
    addStock,
    updateStock,
    removeStock,
    lastUpdated,
    totalGainLoss,
    totalGainLossPercent,
    winnersCount,
    losersCount
  } = useLiveWatchlist({
    refreshInterval: 5 * 60 * 1000 // 5 minutes
  });

  // Use live data or fallback to mock data
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>(initialWatchlist);
  const [openCards, setOpenCards] = useState<Set<string>>(new Set());
  const [alertsExpanded, setAlertsExpanded] = useState(false);
  // Remove chartView and selectedStocks - always show portfolio only
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("1M");
  const [editingNotes, setEditingNotes] = useState<string | null>(null);
  const [tempNotes, setTempNotes] = useState<string>("");
  const [editingPrice, setEditingPrice] = useState<string | null>(null);
  const [tempPrice, setTempPrice] = useState<string>("");

  // Calculate overall portfolio performance dynamically - EQUAL WEIGHTING, PERCENTAGE ONLY
  const calculateOverallPerformance = () => {
    if (watchlist.length === 0) return [];

    // Find the maximum number of data points across all stocks
    const maxDataPoints = Math.max(...watchlist.map(stock => stock.performanceData.length));

    return Array.from({ length: maxDataPoints }, (_, dayIndex) => {
      let totalPercentChange = 0;
      let stocksWithData = 0;

      watchlist.forEach(stock => {
        if (stock.performanceData[dayIndex]) {
          const currentValue = stock.performanceData[dayIndex].value;
          const entryPrice = stock.addedPrice; // Use exact entry price from when user added stock

          // Calculate percentage change from entry date (Day 0 = 0%)
          const percentChange = ((currentValue - entryPrice) / entryPrice) * 100;

          totalPercentChange += percentChange;
          stocksWithData++;
        }
      });

      if (stocksWithData === 0) return { date: `Day ${dayIndex}`, value: 0 };

      // Equal weighting - simple average of all percentage changes
      const avgPercentChange = totalPercentChange / stocksWithData;

      return {
        date: watchlist[0]?.performanceData[dayIndex]?.date || `Day ${dayIndex}`,
        value: avgPercentChange // Portfolio percentage change from all entry dates
      };
    });
  };

  // Generate dynamic alerts based on price proximity
  const generateAlerts = (): Alert[] => {
    const alerts: Alert[] = [];
    
    watchlist.forEach((stock) => {
      const currentPrice = stock.currentPrice;
      
      // Check if within 1% of stop loss
      const stopLossDistance = ((currentPrice - stock.stopLoss) / stock.stopLoss) * 100;
      if (stopLossDistance > 0 && stopLossDistance <= 1) {
        alerts.push({
          id: `${stock.id}-stoploss`,
          symbol: stock.symbol,
          type: "bearish",
          message: `${stock.symbol} is ${stopLossDistance.toFixed(2)}% away from stop loss at $${stock.stopLoss.toFixed(2)}. Risk management advised.`,
          time: "Live"
        });
      }
      
      // Check if within 1% of low target
      const lowTargetDistance = Math.abs(((currentPrice - stock.targetLow) / stock.targetLow) * 100);
      if (lowTargetDistance <= 1) {
        alerts.push({
          id: `${stock.id}-targetlow`,
          symbol: stock.symbol,
          type: "bullish",
          message: `${stock.symbol} is ${lowTargetDistance.toFixed(2)}% away from Low Target at $${stock.targetLow.toFixed(2)}!`,
          time: "Live"
        });
      }
      
      // Check if within 1% of mid target
      const midTargetDistance = Math.abs(((currentPrice - stock.targetMid) / stock.targetMid) * 100);
      if (midTargetDistance <= 1) {
        alerts.push({
          id: `${stock.id}-targetmid`,
          symbol: stock.symbol,
          type: "bullish",
          message: `${stock.symbol} is ${midTargetDistance.toFixed(2)}% away from Medium Target at $${stock.targetMid.toFixed(2)}!`,
          time: "Live"
        });
      }
      
      // Check if within 1% of high target
      const highTargetDistance = Math.abs(((currentPrice - stock.targetHigh) / stock.targetHigh) * 100);
      if (highTargetDistance <= 1) {
        alerts.push({
          id: `${stock.id}-targethigh`,
          symbol: stock.symbol,
          type: "bullish",
          message: `${stock.symbol} is ${highTargetDistance.toFixed(2)}% away from High Target at $${stock.targetHigh.toFixed(2)}!`,
          time: "Live"
        });
      }
    });
    
    // Add some baseline alerts if none generated
    if (alerts.length === 0) {
      return mockAlerts;
    }
    
    return alerts;
  };

  const dynamicAlerts = generateAlerts();

  const toggleCard = (id: string) => {
    const newOpen = new Set(openCards);
    if (newOpen.has(id)) {
      newOpen.delete(id);
    } else {
      newOpen.add(id);
    }
    setOpenCards(newOpen);
  };

  const handleRemoveStock = (id: string) => {
    setWatchlist(watchlist.filter(stock => stock.id !== id));
  };



  const startEditingNotes = (stockId: string, currentNotes: string) => {
    setEditingNotes(stockId);
    setTempNotes(currentNotes);
  };

  const saveNotes = (stockId: string) => {
    setWatchlist(watchlist.map(stock => 
      stock.id === stockId ? { ...stock, notes: tempNotes } : stock
    ));
    setEditingNotes(null);
    setTempNotes("");
  };

  const cancelEditingNotes = () => {
    setEditingNotes(null);
    setTempNotes("");
  };

  const startEditPrice = (stockId: string, currentPrice: number) => {
    setEditingPrice(stockId);
    setTempPrice(currentPrice.toString());
  };

  const savePrice = (stockId: string) => {
    const newPrice = parseFloat(tempPrice);
    if (!isNaN(newPrice) && newPrice > 0) {
      setWatchlist(watchlist.map(stock =>
        stock.id === stockId ? { ...stock, addedPrice: newPrice } : stock
      ));
    }
    setEditingPrice(null);
    setTempPrice("");
  };

  const cancelEditPrice = () => {
    setEditingPrice(null);
    setTempPrice("");
  };

  // Helper function to get date range based on time period
  const getDateRange = (period: TimePeriod): { startDate: Date; endDate: Date } => {
    const endDate = new Date();
    const startDate = new Date();

    switch (period) {
      case "1D":
        startDate.setDate(endDate.getDate() - 1);
        break;
      case "1W":
        startDate.setDate(endDate.getDate() - 7);
        break;
      case "1M":
        startDate.setMonth(endDate.getMonth() - 1);
        break;
      case "3M":
        startDate.setMonth(endDate.getMonth() - 3);
        break;
      case "6M":
        startDate.setMonth(endDate.getMonth() - 6);
        break;
      case "YTD":
        startDate.setMonth(0, 1); // January 1st of current year
        break;
      case "ALL":
        startDate.setFullYear(2020, 0, 1); // Go back to 2020 for "ALL"
        break;
      default:
        startDate.setMonth(endDate.getMonth() - 1);
    }

    return { startDate, endDate };
  };

  // Helper function to parse date strings consistently
  const parseDate = (dateStr: string): Date => {
    // Handle different date formats: "M/D", "M/D/YY", "MM/DD/YYYY"
    const parts = dateStr.split('/');
    if (parts.length === 2) {
      // Format: "M/D" - assume current year
      const currentYear = new Date().getFullYear();
      return new Date(currentYear, parseInt(parts[0]) - 1, parseInt(parts[1]));
    } else if (parts.length === 3) {
      // Format: "M/D/YY" or "MM/DD/YYYY"
      let year = parseInt(parts[2]);
      if (year < 100) {
        year += 2000; // Convert 2-digit year to 4-digit
      }
      return new Date(year, parseInt(parts[0]) - 1, parseInt(parts[1]));
    }
    // Fallback to standard Date parsing
    return new Date(dateStr);
  };

  // Helper function to format X-axis labels based on time period
  const formatXAxisLabel = (dateStr: string): string => {
    const date = parseDate(dateStr);

    switch (timePeriod) {
      case "1D":
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      case "1W":
        return date.toLocaleDateString('en-US', { weekday: 'short' });
      case "1M":
        return date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
      case "3M":
      case "6M":
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      case "YTD":
      case "ALL":
        return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      default:
        return dateStr;
    }
  };

  // Helper function to filter data based on date range and stock removal
  const filterDataByTimeRange = (data: { date: string; value: number }[], stockRemovedDate?: string): { date: string; value: number }[] => {
    const { startDate, endDate } = getDateRange(timePeriod);

    return data.filter(point => {
      const pointDate = parseDate(point.date);

      // Check if point is within selected time range
      const withinRange = pointDate >= startDate && pointDate <= endDate;

      // If stock was removed, only show data up to removal date
      if (stockRemovedDate && withinRange) {
        const removedDate = parseDate(stockRemovedDate);
        return pointDate <= removedDate;
      }

      return withinRange;
    });
  };

  const getChartData = () => {
    // Always show portfolio performance only (equal-weighted percentage change)
    const overallData = calculateOverallPerformance();
    const filteredData = filterDataByTimeRange(overallData);
    return filteredData.map((d, index) => ({
      day: d.date,
      portfolio: d.value, // Portfolio percentage change from entry dates
      dayIndex: index
    }));
  };




  // Calculate watchlist stats
  const totalStocks = watchlist.length;
  const avgPerformance = watchlist.length > 0 
    ? watchlist.reduce((sum, stock) => {
        const change = ((stock.currentPrice - stock.addedPrice) / stock.addedPrice) * 100;
        return sum + change;
      }, 0) / watchlist.length
    : 0;
  
  const targetsHit = watchlist.filter(stock => stock.currentPrice >= stock.targetPrice).length;
  const targetsHitPercent = watchlist.length > 0 ? (targetsHit / watchlist.length) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Watchlist Stats Badge */}
      <div className="flex justify-center">
        <motion.div
          animate={{
            scale: [1, 1.05, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="relative"
        >
          <div className="w-48 h-48 rounded-full bg-gradient-to-br from-purple-500 via-pink-500 to-blue-500 p-1 shadow-2xl">
            <div className="w-full h-full rounded-full flex flex-col items-center justify-center relative" style={{ backgroundColor: 'var(--bg-primary)' }}>
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple-500/5 via-pink-500/5 to-blue-500/5"></div>
              <div className="relative z-10 flex flex-col items-center justify-center h-full">
                <div className="flex items-center gap-1 mb-1">
                  <Target className="w-5 h-5 text-purple-400" />
                  <div className="text-3xl text-purple-400">{totalStocks}</div>
                </div>
                <div className="text-xs text-purple-400 uppercase">Stocks Tracked</div>
                <div className="flex items-center gap-2 mt-3 text-sm">
                  <div className="text-center">
                    <div className={`flex items-center gap-1 ${avgPerformance >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {avgPerformance >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      <span>{avgPerformance >= 0 ? '+' : ''}{avgPerformance.toFixed(1)}%</span>
                    </div>
                    <div className="text-xs text-purple-400">avg return</div>
                  </div>
                </div>
                <div className="mt-2 text-center">
                  <div className="text-sm text-blue-400">{targetsHitPercent.toFixed(0)}%</div>
                  <div className="text-xs text-purple-400">targets hit</div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Performance Chart */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-center text-slate-100">
            Portfolio Performance (Equal-Weighted)
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0 pb-4">
          <ChartContainer config={chartConfig} className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={getChartData()} margin={{ top: 5, right: 15, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
                <XAxis
                  dataKey="day"
                  stroke="rgba(148, 163, 184, 0.6)"
                  tick={{ fontSize: 11, fill: 'rgba(148, 163, 184, 0.8)' }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  tickFormatter={formatXAxisLabel}
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke="rgba(148, 163, 184, 0.6)"
                  tick={{ fontSize: 11, fill: 'rgba(148, 163, 184, 0.8)' }}
                  width={55}
                  tickFormatter={(value) => `${value > 0 ? '+' : ''}${value.toFixed(1)}%`}
                  domain={['dataMin - 1', 'dataMax + 1']}
                />
                <ReferenceLine
                  y={0}
                  stroke="rgba(148, 163, 184, 0.8)"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  label={{ value: '0%', position: 'right', fill: 'rgba(148, 163, 184, 0.8)', fontSize: 12 }}
                />
                <ChartTooltip
                  content={<ChartTooltipContent />}
                  formatter={(value: any, name: any) => {
                    if (value === null || value === undefined) return null;
                    return [`Portfolio: ${value > 0 ? '+' : ''}${value.toFixed(2)}%`, 'Equal-Weighted Performance'];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="portfolio"
                  stroke="#60a5fa"
                  strokeWidth={3}
                  dot={false}
                  activeDot={{ r: 6, fill: '#60a5fa', strokeWidth: 2, stroke: '#1e293b' }}
                  name="Portfolio"
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>

        {/* Time Period Selector */}
        <div className="px-4 pb-4">
          {/* Time Period Selector */}
          <div className="flex gap-1 justify-center flex-wrap">
            <Button
              size="sm"
              variant={timePeriod === "1D" ? "default" : "outline"}
              onClick={() => setTimePeriod("1D")}
              className="shadow-md text-xs px-2"
            >
              1D
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "1W" ? "default" : "outline"}
              onClick={() => setTimePeriod("1W")}
              className="shadow-md text-xs px-2"
            >
              1W
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "1M" ? "default" : "outline"}
              onClick={() => setTimePeriod("1M")}
              className="shadow-md text-xs px-2"
            >
              1M
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "3M" ? "default" : "outline"}
              onClick={() => setTimePeriod("3M")}
              className="shadow-md text-xs px-2"
            >
              3M
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "6M" ? "default" : "outline"}
              onClick={() => setTimePeriod("6M")}
              className="shadow-md text-xs px-2"
            >
              6M
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "YTD" ? "default" : "outline"}
              onClick={() => setTimePeriod("YTD")}
              className="shadow-md text-xs px-2"
            >
              YTD
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "ALL" ? "default" : "outline"}
              onClick={() => setTimePeriod("ALL")}
              className="shadow-md text-xs px-2"
            >
              ALL
            </Button>
          </div>
        </div>
      </Card>

      {/* Alerts Section - Collapsible */}
      <Collapsible open={alertsExpanded} onOpenChange={setAlertsExpanded}>
        <Card className="shadow-xl bg-gradient-to-br from-amber-950/60 via-slate-900/40 to-orange-950/30 border-2 border-amber-700/40">
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-slate-800/20 transition-colors py-3">
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-amber-400" />
                  <CardTitle className="text-base text-slate-100">AI Alerts for Your Watchlist</CardTitle>
                  <Badge variant="outline" className="bg-amber-500/20 text-amber-300 border-amber-500/50">
                    {dynamicAlerts.length}
                  </Badge>
                </div>
                {alertsExpanded ? (
                  <ChevronUp className="w-5 h-5 text-slate-400 shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
                )}
              </div>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="space-y-3 pt-0">
              {dynamicAlerts.map((alert) => (
                <div 
                  key={alert.id} 
                  className={`p-4 rounded-lg border-l-4 ${
                    alert.type === "bullish" 
                      ? "bg-emerald-950/50 border-emerald-500" 
                      : alert.type === "bearish"
                      ? "bg-rose-950/50 border-rose-500"
                      : "bg-slate-800/50 border-slate-500"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="bg-slate-800 text-slate-200 border-slate-600">
                          {alert.symbol}
                        </Badge>
                        <Badge 
                          variant="outline" 
                          className={
                            alert.type === "bullish"
                              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                              : alert.type === "bearish"
                              ? "bg-rose-500/20 text-rose-300 border-rose-500/50"
                              : "bg-slate-500/20 text-slate-300 border-slate-500/50"
                          }
                        >
                          {alert.type}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-300">{alert.message}</p>
                    </div>
                    <span className="text-xs text-slate-500 whitespace-nowrap">{alert.time}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      {/* Watchlist Header */}
      <div className="text-center">
        <h2 className="text-slate-100">My Watchlist ({watchlist.length})</h2>
      </div>

      {/* Watchlist Cards */}
      <div className="space-y-3">
        {watchlist.length === 0 ? (
          <Card className="shadow-lg bg-slate-900/60 border-slate-700">
            <CardContent className="py-12 text-center text-slate-400">
              <p>Your watchlist is empty</p>
              <p>Add stocks from the Picks tab to start tracking</p>
            </CardContent>
          </Card>
        ) : (
          watchlist.map((stock) => {
            const isOpen = openCards.has(stock.id);
            const changeSinceAdded = ((stock.currentPrice - stock.addedPrice) / stock.addedPrice * 100);
            const isEditingThisNote = editingNotes === stock.id;
            
            // Calculate proximity alerts
            const stopLossProximity = ((stock.currentPrice - stock.stopLoss) / stock.stopLoss) * 100;
            const isNearStopLoss = stopLossProximity > 0 && stopLossProximity <= 1;
            const isNearLowTarget = Math.abs(((stock.currentPrice - stock.targetLow) / stock.targetLow) * 100) <= 1;
            const isNearMidTarget = Math.abs(((stock.currentPrice - stock.targetMid) / stock.targetMid) * 100) <= 1;
            const isNearHighTarget = Math.abs(((stock.currentPrice - stock.targetHigh) / stock.targetHigh) * 100) <= 1;

            // Border class and label based on target hit level
            let borderClass = '';
            let targetLabel = '';
            
            if (stock.targetHit === 'low') {
              borderClass = 'border-2 border-yellow-500/70 bg-gradient-to-br from-yellow-900/20 via-slate-800/60 to-yellow-800/10 shadow-[0_0_20px_rgba(234,179,8,0.3)]';
              targetLabel = 'LOW TARGET HIT';
            } else if (stock.targetHit === 'mid') {
              borderClass = 'border-4 border-double border-yellow-500/80 bg-gradient-to-br from-yellow-900/25 via-slate-800/60 to-yellow-800/15 shadow-[0_0_25px_rgba(234,179,8,0.4)]';
              targetLabel = 'MID TARGET HIT';
            } else if (stock.targetHit === 'high') {
              borderClass = 'border-[6px] border-yellow-500 bg-gradient-to-br from-yellow-900/30 via-slate-800/60 to-yellow-800/20 shadow-[0_0_30px_rgba(234,179,8,0.5)] animate-pulse';
              targetLabel = 'HIGH TARGET HIT';
            } else {
              borderClass = 'border-2 border-slate-700/50 bg-gradient-to-br from-slate-900/60 via-slate-800/40 to-slate-900/30 hover:border-slate-600/70';
            }

            return (
              <Collapsible key={stock.id} open={isOpen} onOpenChange={() => toggleCard(stock.id)}>
                <Card className={`shadow-lg hover:shadow-xl transition-all duration-300 ${borderClass}`}>
                  <CollapsibleTrigger className="w-full">
                    <CardContent className="py-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 flex-1">
                          <div className="text-left">
                            <div className="flex items-center gap-2">
                              <span className="text-lg text-slate-100">{stock.symbol}</span>
                              {/* Mini Sparkline showing % change from entry */}
                              <MiniSparkline
                                data={stock.performanceData}
                                isPositive={changeSinceAdded >= 0}
                              />
                            </div>
                            <p className="text-slate-400 text-sm">{stock.name}</p>
                            <p className="text-slate-500 text-xs">
                              {changeSinceAdded >= 0 ? '+' : ''}{changeSinceAdded.toFixed(2)}% since added
                            </p>
                          </div>
                        </div>

                        <div className="text-center">
                          {editingPrice === stock.id ? (
                            <div className="flex flex-col items-center gap-1">
                              <input
                                type="number"
                                step="0.01"
                                value={tempPrice}
                                onChange={(e) => setTempPrice(e.target.value)}
                                className="w-20 px-2 py-1 text-center text-lg bg-slate-700 border border-slate-600 rounded text-slate-100"
                                onClick={(e) => e.stopPropagation()}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    e.stopPropagation();
                                    savePrice(stock.id);
                                  } else if (e.key === 'Escape') {
                                    e.stopPropagation();
                                    cancelEditPrice();
                                  }
                                }}
                                autoFocus
                              />
                              <div className="flex gap-1">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    savePrice(stock.id);
                                  }}
                                  className="p-1 text-emerald-400 hover:text-emerald-300"
                                >
                                  <Check className="w-3 h-3" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    cancelEditPrice();
                                  }}
                                  className="p-1 text-rose-400 hover:text-rose-300"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div
                              className="cursor-pointer hover:bg-slate-700/50 rounded px-2 py-1 transition-colors"
                              onClick={(e) => {
                                e.stopPropagation();
                                startEditPrice(stock.id, stock.addedPrice);
                              }}
                            >
                              <div className="text-2xl text-slate-100">${stock.addedPrice.toFixed(2)}</div>
                              <p className="text-slate-500 text-xs">added at</p>
                            </div>
                          )}
                        </div>

                        <div className="text-center min-w-[90px]">
                          <div className="text-2xl text-slate-100">${stock.currentPrice.toFixed(2)}</div>
                          <p className="text-slate-500 text-xs">current price</p>
                        </div>

                        {isOpen ? (
                          <ChevronUp className="w-5 h-5 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-slate-400" />
                        )}
                      </div>

                      {/* Target Hit Label */}
                      {targetLabel && (
                        <div className="flex items-center justify-center gap-2 pt-2">
                          <Badge className="bg-yellow-900/40 text-yellow-300 border-yellow-500/60 px-4 py-1.5 flex items-center gap-1.5 shadow-[0_0_15px_rgba(234,179,8,0.3)]">
                            <Sparkles className="w-4 h-4 animate-pulse" />
                            <span className="font-semibold">{targetLabel}</span>
                            <Sparkles className="w-4 h-4 animate-pulse" />
                          </Badge>
                        </div>
                      )}
                    </CardContent>
                  </CollapsibleTrigger>

                  <CollapsibleContent>
                    <CardContent className="pt-0 pb-4 space-y-4 border-t border-slate-700/50">
                      {/* Proximity Alerts */}
                      {(isNearStopLoss || isNearLowTarget || isNearMidTarget || isNearHighTarget) && (
                        <div className="pt-2 space-y-2">
                          {isNearStopLoss && (
                            <div className="p-3 bg-rose-950/40 border border-rose-500/40 rounded-lg">
                              <p className="text-rose-400 text-sm text-center">
                                ⚠️ Within 1% of Stop Loss: ${stock.stopLoss.toFixed(2)}
                              </p>
                            </div>
                          )}
                          {isNearLowTarget && (
                            <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 rounded-lg">
                              <p className="text-emerald-400 text-sm text-center">
                                🎯 Within 1% of Low Target: ${stock.targetLow.toFixed(2)}
                              </p>
                            </div>
                          )}
                          {isNearMidTarget && (
                            <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 rounded-lg">
                              <p className="text-emerald-400 text-sm text-center">
                                🎯 Within 1% of Medium Target: ${stock.targetMid.toFixed(2)}
                              </p>
                            </div>
                          )}
                          {isNearHighTarget && (
                            <div className="p-3 bg-yellow-950/40 border border-yellow-500/60 rounded-lg">
                              <p className="text-yellow-400 text-sm text-center">
                                🎯 Within 1% of High Target: ${stock.targetHigh.toFixed(2)}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-3 pt-4">
                        <div className="text-center p-3 bg-slate-800/30 rounded-lg">
                          <p className="text-slate-400 text-xs mb-1">Current Price</p>
                          <p className="text-slate-100">${stock.currentPrice.toFixed(2)}</p>
                        </div>
                        <div className="text-center p-3 bg-slate-800/30 rounded-lg">
                          <p className="text-slate-400 text-xs mb-1">Added At</p>
                          <p className="text-slate-100">${stock.addedPrice.toFixed(2)}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-2">
                        <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${stock.targetHit === 'low' ? 'ring-2 ring-yellow-500/70' : ''}`}>
                          <p className="text-slate-400 text-xs mb-1">Target L</p>
                          <p className="text-emerald-400">${stock.targetLow.toFixed(2)}</p>
                        </div>
                        <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${stock.targetHit === 'mid' ? 'ring-4 ring-double ring-yellow-500/80' : ''}`}>
                          <p className="text-slate-400 text-xs mb-1">Target M</p>
                          <p className="text-emerald-400">${stock.targetMid.toFixed(2)}</p>
                        </div>
                        <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${stock.targetHit === 'high' ? 'ring-[6px] ring-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.3)]' : ''}`}>
                          <p className="text-slate-400 text-xs mb-1">Target H</p>
                          <p className="text-emerald-400">${stock.targetHigh.toFixed(2)}</p>
                        </div>
                      </div>

                      <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${isNearStopLoss ? 'ring-2 ring-rose-500/70' : ''}`}>
                        <p className="text-slate-400 text-xs mb-1">Stop Loss</p>
                        <p className="text-rose-400">${stock.stopLoss.toFixed(2)}</p>
                      </div>

                      {/* Notes Section with Edit */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-slate-400 text-sm">Notes</p>
                          {!isEditingThisNote && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                startEditingNotes(stock.id, stock.notes);
                              }}
                              className="h-7 px-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                            >
                              <Edit2 className="w-3 h-3 mr-1" />
                              Edit
                            </Button>
                          )}
                        </div>
                        {isEditingThisNote ? (
                          <div className="space-y-2">
                            <Textarea
                              value={tempNotes}
                              onChange={(e) => setTempNotes(e.target.value)}
                              className="bg-slate-800 border-slate-600 text-slate-100 min-h-[80px]"
                              placeholder="Add your trading notes..."
                              onClick={(e) => e.stopPropagation()}
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  saveNotes(stock.id);
                                }}
                                className="bg-emerald-600 hover:bg-emerald-500"
                              >
                                <Check className="w-4 h-4 mr-1" />
                                Save
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  cancelEditingNotes();
                                }}
                                className="border-slate-600 text-slate-200 hover:bg-slate-800"
                              >
                                <X className="w-4 h-4 mr-1" />
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-slate-300 bg-slate-800/30 p-3 rounded-lg min-h-[60px]">
                            {stock.notes || "No notes added yet"}
                          </p>
                        )}
                      </div>

                      <Button
                        variant="destructive"
                        className="w-full shadow-lg bg-rose-600 hover:bg-rose-500"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveStock(stock.id);
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Remove from Watchlist
                      </Button>
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>
            );
          })
        )}
      </div>

      {/* Global Hot Bets */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40 mt-6">
        <CardHeader>
          <CardTitle className="flex items-center justify-center gap-2 text-slate-100">
            <Flame className="w-5 h-5 text-orange-500" />
            Global Hot Bets
          </CardTitle>
          <p className="text-center text-slate-400 text-sm">Most tracked picks right now</p>
        </CardHeader>
        <CardContent className="space-y-3">
          {globalHotBets.map((bet) => (
            <div key={bet.rank} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg shadow-md backdrop-blur-sm">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 p-0.5 text-white shadow-lg">
                  <div className="w-full h-full rounded-full bg-gradient-to-br from-purple-500/5 to-pink-500/5 flex items-center justify-center" style={{ backgroundColor: 'var(--bg-primary)' }}>
                    <div className="absolute inset-0.5 rounded-full bg-gradient-to-br from-purple-500/5 to-pink-500/5"></div>
                    <span className="relative z-10 text-white font-medium">{bet.rank}</span>
                  </div>
                </div>
                <div className="text-left">
                  <div className="flex items-center gap-2">
                    <span className="text-lg text-slate-100">{bet.symbol}</span>
                    <Badge variant="outline" className="text-xs border-slate-600 text-slate-300">{bet.confidence}%</Badge>
                  </div>
                  <p className="text-slate-400 text-sm">{bet.users.toLocaleString()} users</p>
                </div>
              </div>
              <div className={`flex items-center gap-1 text-lg ${bet.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {bet.change >= 0 ? (
                  <TrendingUp className="w-5 h-5" />
                ) : (
                  <TrendingDown className="w-5 h-5" />
                )}
                <span>{bet.change >= 0 ? '+' : ''}{bet.change}%</span>
              </div>
            </div>
          ))}
          <p className="text-center text-slate-400 pt-2">
            12,430 traders are riding these right now.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
