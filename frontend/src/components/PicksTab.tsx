import { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Plus, Clock, Sparkles, ArrowUpDown, Skull, X, RefreshCw } from "lucide-react";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { motion } from "motion/react";
import { useLivePicks, LivePick } from "@/hooks/useLivePicks";
const bullIcon = "/assets/bull-icon.png";
const bearIcon = "/assets/bear-icon.png";

// Use LivePick interface from the hook
type StockPick = LivePick & {
  stopLossTriggered?: boolean;
  stopLossExplanation?: string;
  percentLost?: number;
};

const mockPicks: StockPick[] = [
  {
    id: "1",
    symbol: "NVDA",
    name: "NVIDIA Corporation",
    priceAtAlert: 483.50,
    currentPrice: 495.32,
    change: 2.45,
    confidence: 92,
    reasoning: "Strong momentum in AI chip demand, positive earnings trend",
    entryPriceMin: 480.00,
    entryPriceMax: 490.00,
    targetPriceLow: 510.00,
    targetPriceMid: 525.00,
    targetPriceHigh: 545.00,
    stopLoss: 465.00,
    aiSummary: "Our ML model identified NVDA based on exceptional volume surge (+340% vs 30-day avg), positive sentiment from 847 social signals mentioning 'AI datacenter demand', and technical breakout above resistance at $480. The stock shows strong institutional accumulation with insider buying activity. Risk/reward ratio of 2.8:1 supports this high-confidence pick.",
    sentiment: "bullish",
    targetHit: null
  },
  {
    id: "2",
    symbol: "AAPL",
    name: "Apple Inc.",
    priceAtAlert: 180.20,
    currentPrice: 178.54,
    change: -0.92,
    confidence: 88,
    reasoning: "iPhone 16 sales exceeding expectations, services growth",
    entryPriceMin: 176.00,
    entryPriceMax: 182.00,
    targetPriceLow: 188.00,
    targetPriceMid: 195.00,
    targetPriceHigh: 205.00,
    stopLoss: 172.00,
    aiSummary: "Strong buy signal triggered by Services revenue acceleration (+12% YoY) and better-than-expected iPhone 16 pre-orders in China. RSI indicates oversold conditions at current levels. Our sentiment analysis of 2,340 financial articles shows 78% positive tone. Historical patterns suggest Q4 typically strong for AAPL.",
    sentiment: "bullish",
    targetHit: null
  },
  {
    id: "3",
    symbol: "MSFT",
    name: "Microsoft Corporation",
    priceAtAlert: 407.50,
    currentPrice: 412.78,
    change: 1.30,
    confidence: 90,
    reasoning: "Azure cloud growth, AI integration in Office suite",
    entryPriceMin: 405.00,
    entryPriceMax: 415.00,
    targetPriceLow: 430.00,
    targetPriceMid: 445.00,
    targetPriceHigh: 465.00,
    stopLoss: 395.00,
    aiSummary: "Azure revenue growth of 29% combined with successful Copilot rollout creates compelling entry. Our ML model detected increasing correlation with AI infrastructure spending trends. Options flow shows heavy call buying at $420 strike. Analyst upgrades from 12 firms in past 2 weeks signal institutional conviction.",
    sentiment: "bullish",
    targetHit: null
  },
  {
    id: "4",
    symbol: "TSLA",
    name: "Tesla, Inc.",
    priceAtAlert: 234.80,
    currentPrice: 242.19,
    change: 3.15,
    confidence: 75,
    reasoning: "Cybertruck production ramping up, energy storage demand",
    entryPriceMin: 232.00,
    entryPriceMax: 240.00,
    targetPriceLow: 260.00,
    targetPriceMid: 275.00,
    targetPriceHigh: 295.00,
    stopLoss: 225.00,
    aiSummary: "Momentum play based on Cybertruck delivery acceleration and energy storage segment growth. Social sentiment turned positive with 1,240 mentions in past 24h. Price action shows bullish reversal pattern. Note: Medium confidence due to broader EV sector volatility and macro headwinds.",
    sentiment: "bullish",
    targetHit: null
  },
  {
    id: "5",
    symbol: "SQQQ",
    name: "ProShares UltraPro Short QQQ",
    priceAtAlert: 12.30,
    currentPrice: 12.85,
    change: 4.47,
    confidence: 78,
    reasoning: "Tech sector overextension, correction signals detected",
    entryPriceMin: 12.10,
    entryPriceMax: 12.50,
    targetPriceLow: 13.50,
    targetPriceMid: 14.50,
    targetPriceHigh: 15.80,
    stopLoss: 11.80,
    aiSummary: "Our bearish indicator triggered on tech sector overvaluation metrics. VIX climbing, put/call ratios increasing. Economic data suggests potential Fed hawkishness. This inverse ETF profits from QQQ decline. Technical overbought conditions on NASDAQ support short-term correction thesis.",
    sentiment: "bearish",
    targetHit: null
  },
  {
    id: "6",
    symbol: "GOOGL",
    name: "Alphabet Inc.",
    priceAtAlert: 141.90,
    currentPrice: 142.87,
    change: 0.68,
    confidence: 87,
    reasoning: "Search dominance, Gemini AI improvements, cloud momentum",
    entryPriceMin: 140.00,
    entryPriceMax: 145.00,
    targetPriceLow: 152.00,
    targetPriceMid: 160.00,
    targetPriceHigh: 172.00,
    stopLoss: 136.00,
    aiSummary: "Gemini AI adoption accelerating with enterprise customers. Search revenue stability despite AI chatbot competition fears. YouTube Shorts monetization improving. Our NLP analysis of earnings calls shows management confidence at 2-year high. GCP growth trajectory compelling.",
    sentiment: "bullish",
    targetHit: null
  }
];

// Mock recent picks from last 7 days
const recentPicks: StockPick[] = [
  {
    id: "r1",
    symbol: "AMD",
    name: "Advanced Micro Devices",
    priceAtAlert: 142.30,
    currentPrice: 156.45,
    change: 9.94,
    confidence: 85,
    reasoning: "Strong datacenter demand",
    entryPriceMin: 140.00,
    entryPriceMax: 145.00,
    targetPriceLow: 155.00,
    targetPriceMid: 168.00,
    targetPriceHigh: 180.00,
    stopLoss: 135.00,
    aiSummary: "",
    sentiment: "bullish",
    targetHit: "low",
    timeToTargetHours: 36 // 1 day 12 hours
  },
  {
    id: "r2",
    symbol: "COIN",
    name: "Coinbase Global",
    priceAtAlert: 82.50,
    currentPrice: 74.20,
    change: -10.06,
    confidence: 68,
    reasoning: "Crypto market volatility",
    entryPriceMin: 80.00,
    entryPriceMax: 85.00,
    targetPriceLow: 90.00,
    targetPriceMid: 95.00,
    targetPriceHigh: 102.00,
    stopLoss: 75.00,
    aiSummary: "",
    sentiment: "bullish",
    targetHit: null,
    stopLossTriggered: true,
    percentLost: -10.06,
    stopLossExplanation: "Bitcoin experienced unexpected regulatory pressure from multiple countries, causing a sharp decline across crypto-related stocks. Selling pressure intensified as institutional investors reduced exposure to the sector."
  },
  {
    id: "r3",
    symbol: "PLTR",
    name: "Palantir Technologies",
    priceAtAlert: 38.40,
    currentPrice: 42.10,
    change: 9.64,
    confidence: 79,
    reasoning: "Government contract wins",
    entryPriceMin: 37.50,
    entryPriceMax: 40.00,
    targetPriceLow: 43.00,
    targetPriceMid: 48.00,
    targetPriceHigh: 54.00,
    stopLoss: 36.00,
    aiSummary: "",
    sentiment: "bullish",
    targetHit: "mid",
    timeToTargetHours: 52 // 2 days 4 hours
  },
  {
    id: "r4",
    symbol: "HOOD",
    name: "Robinhood Markets",
    priceAtAlert: 24.80,
    currentPrice: 22.95,
    change: -7.46,
    confidence: 71,
    reasoning: "Trading volume concerns",
    entryPriceMin: 24.00,
    entryPriceMax: 26.00,
    targetPriceLow: 27.00,
    targetPriceMid: 29.50,
    targetPriceHigh: 33.00,
    stopLoss: 22.00,
    aiSummary: "",
    sentiment: "bullish",
    targetHit: null
  },
  {
    id: "r5",
    symbol: "RIVN",
    name: "Rivian Automotive",
    priceAtAlert: 16.20,
    currentPrice: 17.85,
    change: 10.19,
    confidence: 65,
    reasoning: "Production ramp progress",
    entryPriceMin: 15.80,
    entryPriceMax: 16.50,
    targetPriceLow: 19.00,
    targetPriceMid: 22.00,
    targetPriceHigh: 26.00,
    stopLoss: 14.50,
    aiSummary: "",
    sentiment: "bullish",
    targetHit: "high",
    timeToTargetHours: 98 // 4 days 2 hours
  }
];

type SortOption = "confidence" | "bullish" | "bearish" | "entry";
type TimePeriod = "today" | "7days";

interface PicksTabProps {
  onPickClick?: (type: "bullish" | "bearish") => void;
}

export function PicksTab({ onPickClick }: PicksTabProps) {
  // Live data hook
  const {
    picks: livePicks,
    bullishPicks,
    bearishPicks,
    isLoading,
    isRefreshing,
    error,
    refresh,
    lastUpdated
  } = useLivePicks({
    bullishLimit: 25,
    bearishLimit: 25,
    minConfidence: 0.48, // 48% threshold
    refreshInterval: 5 * 60 * 1000 // 5 minutes
  });

  const [openCards, setOpenCards] = useState<Set<string>>(new Set());
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<SortOption>("confidence");
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("today");
  const [countdown, setCountdown] = useState({
    hours: 2,
    minutes: 45,
    seconds: 30
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        let { hours, minutes, seconds } = prev;
        
        if (seconds > 0) {
          seconds--;
        } else if (minutes > 0) {
          minutes--;
          seconds = 59;
        } else if (hours > 0) {
          hours--;
          minutes = 59;
          seconds = 59;
        }
        
        return { hours, minutes, seconds };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const toggleCard = (id: string) => {
    const newOpen = new Set(openCards);
    if (newOpen.has(id)) {
      newOpen.delete(id);
    } else {
      newOpen.add(id);
    }
    setOpenCards(newOpen);
  };

  const addToWatchlist = (symbol: string) => {
    const newWatchlist = new Set(watchlist);
    newWatchlist.add(symbol);
    setWatchlist(newWatchlist);
  };

  const getConfidenceLevel = (confidence: number): { label: string; color: string } => {
    if (confidence >= 80) return { label: "High", color: "text-emerald-400" };
    if (confidence >= 65) return { label: "Medium", color: "text-yellow-400" };
    return { label: "Low", color: "text-orange-400" };
  };

  const sortPicks = (picks: StockPick[]) => {
    const sorted = [...picks];
    switch (sortBy) {
      case "confidence":
        return sorted.sort((a, b) => b.confidence - a.confidence);
      case "bullish":
        return sorted.filter(p => p.sentiment === "bullish");
      case "bearish":
        return sorted.filter(p => p.sentiment === "bearish");
      case "entry":
        return sorted.sort((a, b) => {
          const aDiff = Math.abs(a.currentPrice - a.priceAtAlert);
          const bDiff = Math.abs(b.currentPrice - b.priceAtAlert);
          return aDiff - bDiff;
        });
      default:
        return sorted;
    }
  };

  // Use live data or fallback to mock data
  const allPicks = livePicks.length > 0 ? livePicks : (timePeriod === "today" ? mockPicks : [...mockPicks, ...recentPicks]);
  const sortedPicks = sortPicks(allPicks);

  const picksCount = allPicks.length;
  const bullishCount = allPicks.filter(p => p.sentiment === "bullish").length;
  const bearishCount = allPicks.filter(p => p.sentiment === "bearish").length;

  const formatTimeToTarget = (hours: number): string => {
    const days = Math.floor(hours / 24);
    const remainingHours = Math.floor(hours % 24);
    const minutes = Math.floor((hours % 1) * 60);
    
    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (remainingHours > 0) parts.push(`${remainingHours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    
    return parts.join(' ') || '0m';
  };

  return (
    <div className="space-y-4">
      {/* Stats Badge */}
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
          <div className="w-48 h-48 rounded-full bg-gradient-to-br from-emerald-500 via-purple-500 to-rose-500 p-1 shadow-2xl">
            <div className="w-full h-full rounded-full bg-gradient-to-br from-emerald-500/5 via-purple-500/5 to-rose-500/5 flex flex-col items-center justify-center" style={{ backgroundColor: 'var(--bg-primary)' }}>
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-emerald-500/5 via-purple-500/5 to-rose-500/5"></div>
              <div className="relative z-10 flex flex-col items-center justify-center h-full">
                <div className="flex items-center gap-1 mb-1">
                  <Sparkles className="w-6 h-6 text-purple-400" />
                  <div className="text-6xl text-purple-400">{picksCount}</div>
                </div>
                <div className="text-xs text-purple-400 uppercase">Picks Today</div>
                <div className="flex items-center gap-2 mt-2 text-xs">
                  <span className="flex items-center gap-1 text-emerald-400">
                    <img src={bullIcon} alt="bull" className="w-4 h-4 brightness-0 invert" style={{ filter: 'brightness(0) saturate(100%) invert(78%) sepia(23%) saturate(1234%) hue-rotate(94deg) brightness(91%) contrast(86%)' }} />
                    {bullishCount}
                  </span>
                  <span className="text-slate-600">|</span>
                  <span className="flex items-center gap-1 text-rose-400">
                    <img src={bearIcon} alt="bear" className="w-4 h-4 brightness-0 invert" style={{ filter: 'brightness(0) saturate(100%) invert(60%) sepia(98%) saturate(3959%) hue-rotate(316deg) brightness(96%) contrast(92%)' }} />
                    {bearishCount}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Update Status */}
      <div className="space-y-2 text-center">
        <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
          <Clock className="w-4 h-4" />
          <span>
            {lastUpdated
              ? `Last updated: ${lastUpdated.toLocaleString()}`
              : "Loading live data..."
            }
          </span>
          {isRefreshing && <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />}
        </div>

        {/* Error Display */}
        {error && (
          <div className="text-sm text-rose-400 bg-rose-500/10 px-3 py-2 rounded-lg border border-rose-500/20">
            ⚠️ {error} - Using demo data
          </div>
        )}

        {/* Manual Refresh Button */}
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={refresh}
            disabled={isRefreshing}
            className="text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <span className="text-slate-400">•</span>
          <span className="text-sm text-slate-400">
            {livePicks.length > 0 ? 'Live data' : 'Demo data'}
          </span>
        </div>

        <div className="flex items-center justify-center gap-2 text-sm">
          <span className="text-slate-400">Next update in:</span>
          <span className="font-mono text-emerald-400">
            {countdown.hours}h {countdown.minutes.toString().padStart(2, '0')}m {countdown.seconds.toString().padStart(2, '0')}s
          </span>
        </div>
      </div>

      {/* Filter and Sort Options */}
      <div className="flex items-center justify-between gap-4">
        <Select value={timePeriod} onValueChange={(value) => setTimePeriod(value as TimePeriod)}>
          <SelectTrigger className="w-[200px] bg-slate-800/50 border-slate-600 text-slate-100 font-semibold">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900/50 border-slate-700">
            <SelectItem value="today" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100 font-semibold">Today's Picks</SelectItem>
            <SelectItem value="7days" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">All Picks Past 7 Days</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-4 h-4 text-slate-400" />
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortOption)}>
            <SelectTrigger className="w-[180px] bg-slate-800/50 border-slate-600 text-slate-200 font-semibold">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900/50 border-slate-700">
              <SelectItem value="confidence" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100 font-semibold">Confidence</SelectItem>
              <SelectItem value="entry" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">Closest to Entry</SelectItem>
              <SelectItem value="bullish" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">Bullish Only</SelectItem>
              <SelectItem value="bearish" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">Bearish Only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {sortedPicks.map((pick) => {
        const isOpen = openCards.has(pick.id);
        const isInWatchlist = watchlist.has(pick.symbol);
        const changeSinceAlert = ((pick.currentPrice - pick.priceAtAlert) / pick.priceAtAlert * 100);
        const isBullish = pick.sentiment === "bullish";
        const confidenceLevel = getConfidenceLevel(pick.confidence);

        // Styling for past picks with targets hit or stop loss
        let borderClass = '';
        let shouldPulseBorder = false;
        
        if (pick.stopLossTriggered) {
          borderClass = 'border-4 border-red-900/80 bg-gradient-to-br from-red-950/40 via-slate-800/60 to-red-900/20';
        } else if (pick.targetHit === 'low') {
          borderClass = 'border-2 border-yellow-500 bg-gradient-to-br from-yellow-900/20 via-slate-800/60 to-yellow-800/10';
          shouldPulseBorder = true;
        } else if (pick.targetHit === 'mid') {
          borderClass = 'border-4 border-yellow-500 bg-gradient-to-br from-yellow-900/25 via-slate-800/60 to-yellow-800/15';
          shouldPulseBorder = true;
        } else if (pick.targetHit === 'high') {
          borderClass = 'border-[6px] border-yellow-500 bg-gradient-to-br from-yellow-900/30 via-slate-800/60 to-yellow-800/20';
          shouldPulseBorder = true;
        } else if (isBullish) {
          borderClass = 'border-2 bg-gradient-to-br from-emerald-950/60 via-slate-900/40 to-emerald-900/30 border-emerald-700/40 hover:border-emerald-500/60';
        } else {
          borderClass = 'border-2 bg-gradient-to-br from-rose-950/60 via-slate-900/40 to-rose-900/30 border-rose-700/40 hover:border-rose-500/60';
        }

        return (
          <Collapsible key={pick.id} open={isOpen} onOpenChange={() => toggleCard(pick.id)}>
            <motion.div
              animate={shouldPulseBorder ? {
                boxShadow: [
                  '0 0 20px rgba(234, 179, 8, 0.4)',
                  '0 0 40px rgba(234, 179, 8, 0.7)',
                  '0 0 20px rgba(234, 179, 8, 0.4)',
                ],
              } : {}}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="rounded-lg"
            >
            <Card
              className={`shadow-lg hover:shadow-2xl transition-all duration-300 ${borderClass}`}
              onClick={() => onPickClick?.(pick.sentiment)}
            >
              <CollapsibleTrigger className="w-full">
                <CardContent className="py-4">
                  <div className="space-y-3">
                    {/* First Line: Symbol and Price Info */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-left flex-1 min-w-0">
                        <div className="text-lg text-slate-100">{pick.symbol}</div>
                        <p className="text-slate-400 text-sm truncate">{pick.name}</p>
                      </div>

                      <div className="text-center shrink-0">
                        <div className="text-2xl text-slate-100">${pick.priceAtAlert.toFixed(2)}</div>
                        <p className="text-slate-500 text-xs whitespace-nowrap">at alert</p>
                      </div>

                      <div className="text-center shrink-0 min-w-[85px]">
                        <div className={`flex items-center justify-center gap-1 text-2xl ${changeSinceAlert >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {changeSinceAlert >= 0 ? (
                            <TrendingUp className="w-5 h-5" />
                          ) : (
                            <TrendingDown className="w-5 h-5" />
                          )}
                          <span>{changeSinceAlert >= 0 ? '+' : ''}{changeSinceAlert.toFixed(2)}%</span>
                        </div>
                        <p className="text-slate-500 text-xs whitespace-nowrap">change since</p>
                      </div>

                      {isOpen ? (
                        <ChevronUp className="w-5 h-5 text-slate-400 shrink-0" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
                      )}
                    </div>

                    {/* Second Line: Confidence with Sentiment */}
                    <div className="flex items-center justify-center gap-3">
                      <div className="flex flex-col items-center gap-1">
                        <span className="text-xs text-slate-400">Confidence Level:</span>
                        <Badge 
                          className={`text-sm px-3 py-1 ${confidenceLevel.color} bg-slate-800/50 border-slate-600`}
                          variant="outline"
                        >
                          {confidenceLevel.label}
                        </Badge>
                      </div>
                      <div className="flex flex-col items-center gap-1">
                        <span className="text-xs text-slate-400">Sentiment:</span>
                        <Badge 
                          className={`text-sm px-3 py-1 ${
                            isBullish 
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50' 
                              : 'bg-rose-500/20 text-rose-300 border-rose-500/50'
                          }`}
                          variant="outline"
                        >
                          {isBullish ? 'Bullish' : 'Bearish'}
                        </Badge>
                      </div>
                    </div>

                    {/* Target Hit / Stop Loss Status */}
                    {pick.targetHit && (
                      <div className="flex items-center justify-center gap-2">
                        <Badge className="text-sm px-3 py-1 bg-yellow-500/20 text-yellow-300 border-yellow-500/50 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" />
                          {pick.targetHit === 'low' && 'Low Target Hit'}
                          {pick.targetHit === 'mid' && 'Mid Target Hit'}
                          {pick.targetHit === 'high' && 'High Target Hit'}
                        </Badge>
                        {pick.timeToTargetHours && (
                          <span className="text-xs text-yellow-400">
                            {formatTimeToTarget(pick.timeToTargetHours)}
                          </span>
                        )}
                      </div>
                    )}
                    {pick.stopLossTriggered && (
                      <div className="flex items-center justify-center">
                        <Badge className="text-sm px-3 py-1 bg-red-500/20 text-red-300 border-red-500/50 flex items-center gap-1">
                          <Skull className="w-3 h-3" />
                          Stop Loss Hit
                        </Badge>
                      </div>
                    )}
                  </div>
                </CardContent>
              </CollapsibleTrigger>

              <CollapsibleContent>
                <CardContent className="pt-0 pb-4 space-y-4 border-t border-slate-700/50">
                  <div className="grid grid-cols-2 gap-3 pt-4">
                    <div className="text-center p-3 bg-slate-800/30 rounded-lg">
                      <p className="text-slate-400 text-xs mb-1">Price When Alerted</p>
                      <p className="text-slate-100">${pick.priceAtAlert.toFixed(2)}</p>
                    </div>
                    <div className="text-center p-3 bg-slate-800/30 rounded-lg">
                      <p className="text-slate-400 text-xs mb-1">% Change Since Alert</p>
                      <p className={changeSinceAlert >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        {changeSinceAlert >= 0 ? '+' : ''}{changeSinceAlert.toFixed(2)}%
                      </p>
                    </div>
                    <div className="text-center p-3 bg-slate-800/30 rounded-lg col-span-2">
                      <p className="text-slate-400 text-xs mb-1">Entry Price Range</p>
                      <p className="text-slate-100">${pick.entryPriceMin.toFixed(2)} - ${pick.entryPriceMax.toFixed(2)}</p>
                    </div>
                  </div>

                  {pick.targetHit && pick.timeToTargetHours && (
                    <div className={`p-4 rounded-lg text-center ${
                      pick.targetHit === 'high' 
                        ? 'bg-yellow-900/30 border-2 border-yellow-500/60' 
                        : 'bg-yellow-900/20 border border-yellow-500/40'
                    }`}>
                      <p className="text-yellow-400 mb-1">
                        🎯 {pick.targetHit === 'low' ? 'Low' : pick.targetHit === 'mid' ? 'Medium' : 'High'} Target Hit!
                      </p>
                      <p className="text-slate-300 text-sm">
                        Time to target: {formatTimeToTarget(pick.timeToTargetHours)}
                      </p>
                    </div>
                  )}

                  {pick.stopLossTriggered && (
                    <div className="p-4 bg-red-950/40 border-2 border-red-900/60 rounded-lg">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <Skull className="w-6 h-6 text-red-400" />
                        <p className="text-red-400">Stop Loss Triggered</p>
                      </div>
                      <p className="text-center text-rose-300 mb-2">
                        Loss: {pick.percentLost?.toFixed(2)}%
                      </p>
                      <p className="text-slate-300 text-sm text-center leading-relaxed">
                        {pick.stopLossExplanation}
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-2">
                    <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${pick.targetHit === 'low' ? 'ring-2 ring-yellow-500/70' : ''}`}>
                      <p className="text-slate-400 text-xs mb-1">Low Target</p>
                      <p className="text-emerald-400">${pick.targetPriceLow.toFixed(2)}</p>
                    </div>
                    <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${pick.targetHit === 'mid' ? 'ring-4 ring-double ring-yellow-500/80' : ''}`}>
                      <p className="text-slate-400 text-xs mb-1">Medium Target</p>
                      <p className="text-emerald-400">${pick.targetPriceMid.toFixed(2)}</p>
                    </div>
                    <div className={`text-center p-3 bg-slate-800/30 rounded-lg ${pick.targetHit === 'high' ? 'ring-[6px] ring-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.3)]' : ''}`}>
                      <p className="text-slate-400 text-xs mb-1">High Target</p>
                      <p className="text-emerald-400">${pick.targetPriceHigh.toFixed(2)}</p>
                    </div>
                  </div>

                  <div className="text-center p-3 bg-slate-800/30 rounded-lg">
                    <p className="text-slate-400 text-xs mb-1">Suggested Stop Loss</p>
                    <p className="text-rose-400">${pick.stopLoss.toFixed(2)}</p>
                  </div>

                  {!pick.stopLossTriggered && (
                    <div className="p-4 bg-slate-800/30 rounded-lg">
                      <p className="text-slate-400 mb-2 text-center">Analysis</p>
                      <p className="text-sm leading-relaxed text-center text-slate-300">{pick.aiSummary || pick.reasoning}</p>
                    </div>
                  )}

                  <Button 
                    className={`w-full shadow-lg ${isBullish ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      addToWatchlist(pick.symbol);
                    }}
                    disabled={isInWatchlist}
                  >
                    {isInWatchlist ? (
                      "Added to Watchlist"
                    ) : (
                      <>
                        <Plus className="w-4 h-4 mr-2" />
                        Add to Watchlist
                      </>
                    )}
                  </Button>
                </CardContent>
              </CollapsibleContent>
            </Card>
            </motion.div>
          </Collapsible>
        );
      })}
    </div>
  );
}
