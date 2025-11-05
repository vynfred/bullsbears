import React, { useState } from "react";
import { Trash2, ChevronDown, ChevronUp, TrendingUp, TrendingDown, Bell, Flame, Edit2, Check, X, Target, Sparkles } from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "./ui/chart";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, ReferenceLine } from "recharts";
import { Textarea } from "./ui/textarea";
import { motion } from "motion/react";

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
}

interface Alert {
  id: string;
  symbol: string;
  type: "bullish" | "bearish" | "neutral";
  message: string;
  time: string;
}

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
    performanceData: [
      { date: "10/29", value: 478.50 },
      { date: "10/30", value: 481.20 },
      { date: "10/31", value: 479.80 },
      { date: "11/1", value: 483.40 },
      { date: "11/2", value: 485.10 },
      { date: "11/3", value: 482.90 },
      { date: "11/5", value: 486.32 }
    ],
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
    performanceData: [
      { date: "10/29", value: 180.40 },
      { date: "10/30", value: 179.20 },
      { date: "10/31", value: 181.50 },
      { date: "11/1", value: 180.80 },
      { date: "11/2", value: 178.40 },
      { date: "11/3", value: 177.90 },
      { date: "11/5", value: 173.80 }
    ],
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
    performanceData: [
      { date: "10/29", value: 598.20 },
      { date: "10/30", value: 602.10 },
      { date: "10/31", value: 605.80 },
      { date: "11/1", value: 608.40 },
      { date: "11/2", value: 606.20 },
      { date: "11/3", value: 609.50 },
      { date: "11/5", value: 643.50 }
    ],
    targetHit: "low"
  }
];

const overallPerformanceData = [
  { date: "10/29", value: 0 },
  { date: "10/30", value: 0.42 },
  { date: "10/31", value: -0.28 },
  { date: "11/1", value: 1.12 },
  { date: "11/2", value: -0.35 },
  { date: "11/3", value: 0.95 },
  { date: "11/5", value: 1.85 }
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

type TimePeriod = "7d" | "30d" | "90d";
type ChartView = "overall" | "individual";

export function WatchlistTab() {
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>(initialWatchlist);
  const [openCards, setOpenCards] = useState<Set<string>>(new Set());
  const [alertsExpanded, setAlertsExpanded] = useState(false);
  const [chartView, setChartView] = useState<ChartView>("overall");
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set());
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("7d");
  const [editingNotes, setEditingNotes] = useState<string | null>(null);
  const [tempNotes, setTempNotes] = useState<string>("");

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
    const newSelected = new Set(selectedStocks);
    newSelected.delete(id);
    setSelectedStocks(newSelected);
  };

  const toggleStockSelection = (id: string) => {
    const newSelected = new Set(selectedStocks);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedStocks(newSelected);
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

  const getChartData = () => {
    if (chartView === "overall") {
      // Use the overall performance data directly - values are already percentages
      return overallPerformanceData.map((d, index) => ({
        day: `Day ${index}`,
        value: d.value
      }));
    } else {
      // For individual view, transform data to show selected stocks
      if (selectedStocks.size === 0) return [];
      
      let maxDataPoints = 0;
      watchlist.forEach(stock => {
        if (selectedStocks.has(stock.id) && stock.performanceData.length > maxDataPoints) {
          maxDataPoints = stock.performanceData.length;
        }
      });
      
      return Array.from({ length: maxDataPoints }, (_, dayIndex) => {
        const dataPoint: any = { day: `Day ${dayIndex}` };
        watchlist.forEach((stock) => {
          if (selectedStocks.has(stock.id)) {
            const stockData = stock.performanceData[dayIndex];
            if (stockData) {
              const percentChange = ((stockData.value - stock.addedPrice) / stock.addedPrice) * 100;
              dataPoint[stock.symbol] = percentChange;
            }
          }
        });
        return dataPoint;
      });
    }
  };

  // Split data into segments based on zero crossings
  const createSegments = (data: any[], valueKey: string) => {
    if (data.length === 0) return [];
    
    const segments: { points: any[], isPositive: boolean }[] = [];
    let currentSegment: any[] = [];
    let currentIsPositive = true;
    
    for (let i = 0; i < data.length; i++) {
      const value = data[i][valueKey];
      if (value === undefined || value === null) continue;
      
      const isPositive = value >= 0;
      
      // First point or continuing same segment
      if (currentSegment.length === 0) {
        currentIsPositive = isPositive;
        currentSegment.push(data[i]);
      } else if (isPositive === currentIsPositive) {
        // Same sign, continue segment
        currentSegment.push(data[i]);
      } else {
        // Crossed zero - interpolate the crossing point
        const prevPoint = data[i - 1];
        const prevValue = prevPoint[valueKey];
        
        // Calculate interpolated zero crossing
        const ratio = Math.abs(prevValue) / (Math.abs(prevValue) + Math.abs(value));
        const dayNum = i - 1 + ratio;
        const crossingPoint = {
          day: `Day ${dayNum.toFixed(2)}`,
          [valueKey]: 0
        };
        
        // Close current segment with crossing point
        currentSegment.push(crossingPoint);
        segments.push({ points: currentSegment, isPositive: currentIsPositive });
        
        // Start new segment from crossing point
        currentSegment = [crossingPoint, data[i]];
        currentIsPositive = isPositive;
      }
    }
    
    // Add final segment
    if (currentSegment.length > 0) {
      segments.push({ points: currentSegment, isPositive: currentIsPositive });
    }
    
    return segments;
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
            <div className="w-full h-full rounded-full bg-slate-900 flex flex-col items-center justify-center">
              <div className="flex items-center gap-1 mb-1">
                <Target className="w-5 h-5 text-purple-400" />
                <div className="text-3xl text-purple-400">{totalStocks}</div>
              </div>
              <div className="text-xs text-slate-400 uppercase">Stocks Tracked</div>
              <div className="flex items-center gap-2 mt-3 text-sm">
                <div className="text-center">
                  <div className={`flex items-center gap-1 ${avgPerformance >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {avgPerformance >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    <span>{avgPerformance >= 0 ? '+' : ''}{avgPerformance.toFixed(1)}%</span>
                  </div>
                  <div className="text-xs text-slate-500">avg return</div>
                </div>
              </div>
              <div className="mt-2 text-center">
                <div className="text-sm text-blue-400">{targetsHitPercent.toFixed(0)}%</div>
                <div className="text-xs text-slate-500">targets hit</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Performance Chart */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-center text-slate-100">
            {chartView === "overall" ? "Overall Watchlist Performance" : "Individual Stock Performance"}
          </CardTitle>
          
          {/* View Toggle */}
          <div className="flex gap-2 justify-center pt-3">
            <Button
              size="sm"
              variant={chartView === "overall" ? "default" : "outline"}
              onClick={() => {
                setChartView("overall");
                setSelectedStocks(new Set());
              }}
              className="shadow-md bg-purple-600 hover:bg-purple-500 border-purple-500"
            >
              Overall
            </Button>
            <Button
              size="sm"
              variant={chartView === "individual" ? "default" : "outline"}
              onClick={() => {
                setChartView("individual");
                if (watchlist.length > 0 && selectedStocks.size === 0) {
                  setSelectedStocks(new Set([watchlist[0].id]));
                }
              }}
              className="shadow-md bg-purple-600 hover:bg-purple-500 border-purple-500"
            >
              Individual Stocks
            </Button>
          </div>

          {/* Individual Stock Selector - Multiple Selection */}
          {chartView === "individual" && (
            <div className="flex gap-2 flex-wrap justify-center pt-2">
              {watchlist.map(stock => (
                <Button
                  key={stock.id}
                  size="sm"
                  variant={selectedStocks.has(stock.id) ? "default" : "outline"}
                  onClick={() => toggleStockSelection(stock.id)}
                  className="shadow-md bg-slate-700 hover:bg-slate-600 border-slate-600"
                >
                  {stock.symbol}
                </Button>
              ))}
            </div>
          )}

          {/* Time Period Selector */}
          <div className="flex gap-2 justify-center pt-2">
            <Button
              size="sm"
              variant={timePeriod === "7d" ? "default" : "outline"}
              onClick={() => setTimePeriod("7d")}
              className="shadow-md"
            >
              7D
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "30d" ? "default" : "outline"}
              onClick={() => setTimePeriod("30d")}
              className="shadow-md"
            >
              30D
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "90d" ? "default" : "outline"}
              onClick={() => setTimePeriod("90d")}
              className="shadow-md"
            >
              90D
            </Button>
          </div>
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
                    return [`${value > 0 ? '+' : ''}${value.toFixed(2)}%`, name || 'Performance'];
                  }}
                />
                {chartView === "overall" ? (
                  <>
                    {createSegments(getChartData(), 'value').map((segment, idx) => (
                      <Line
                        key={`overall-seg-${idx}`}
                        data={segment.points}
                        type="monotone"
                        dataKey="value"
                        stroke={segment.isPositive ? "#10b981" : "#ef4444"}
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 6, fill: segment.isPositive ? "#10b981" : "#ef4444" }}
                        isAnimationActive={false}
                      />
                    ))}
                  </>
                ) : (
                  watchlist.map((stock) => {
                    if (!selectedStocks.has(stock.id)) return null;
                    
                    const segments = createSegments(getChartData(), stock.symbol);
                    
                    return (
                      <React.Fragment key={stock.id}>
                        {segments.map((segment, idx) => (
                          <Line
                            key={`${stock.symbol}-seg-${idx}`}
                            data={segment.points}
                            type="monotone"
                            dataKey={stock.symbol}
                            stroke={segment.isPositive ? "#10b981" : "#ef4444"}
                            strokeWidth={3}
                            dot={false}
                            activeDot={{ r: 6, fill: segment.isPositive ? "#10b981" : "#ef4444" }}
                            name={stock.symbol}
                            isAnimationActive={false}
                          />
                        ))}
                      </React.Fragment>
                    );
                  })
                )}
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>
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
                            </div>
                            <p className="text-slate-400 text-sm">{stock.name}</p>
                          </div>
                        </div>

                        <div className="text-center">
                          <div className="text-2xl text-slate-100">${stock.addedPrice.toFixed(2)}</div>
                          <p className="text-slate-500 text-xs">added at</p>
                        </div>

                        <div className="text-center min-w-[90px]">
                          <div className={`flex items-center justify-center gap-1 text-2xl ${changeSinceAdded >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {changeSinceAdded >= 0 ? (
                              <TrendingUp className="w-5 h-5" />
                            ) : (
                              <TrendingDown className="w-5 h-5" />
                            )}
                            <span>{changeSinceAdded >= 0 ? '+' : ''}{changeSinceAdded.toFixed(2)}%</span>
                          </div>
                          <p className="text-slate-500 text-xs">return</p>
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
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 text-white shadow-lg">
                  {bet.rank}
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
