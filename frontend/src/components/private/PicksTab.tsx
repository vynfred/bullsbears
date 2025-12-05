// src/components/private/PicksTab.tsx
'use client';

import React, { useState, useMemo, useCallback } from "react";
import {
  ChevronDown,
  ChevronUp,
  Plus,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion } from "framer-motion";
import { useLivePicks } from "@/hooks/useLivePicks";
import { useWatchlist } from "@/hooks/useWatchlist";

// BullsBears official side icons
const bullIcon = "/assets/BullsBears-Side-Bull-Icon.png";
const bearIcon = "/assets/BullsBears-Side-Bear-Icon.png";

// Unified filter configuration
const FILTERS = [
  { id: 'today', label: "Today's Picks", period: 'today' as const, sentiment: undefined, outcome: undefined },
  { id: 'week', label: "Past 7 Days", period: '7d' as const, sentiment: undefined, outcome: undefined },
  { id: 'all', label: "All Time", period: 'all' as const, sentiment: undefined, outcome: undefined },
  { id: 'bull', label: "Bullish", period: 'active' as const, sentiment: 'bullish' as const, outcome: undefined },
  { id: 'bear', label: "Bearish", period: 'active' as const, sentiment: 'bearish' as const, outcome: undefined },
  { id: 'wins', label: "Wins", period: 'all' as const, sentiment: undefined, outcome: 'wins' as const },
  { id: 'misses', label: "Misses", period: 'all' as const, sentiment: undefined, outcome: 'losses' as const },
  { id: 'active', label: "All Active (30d)", period: 'active' as const, sentiment: undefined, outcome: undefined },
] as const;

type FilterId = typeof FILTERS[number]['id'];

export default function PicksTab() {
  const [activeFilter, setActiveFilter] = useState<FilterId>('active');
  const [openPickId, setOpenPickId] = useState<string | null>(null);

  // Get current filter config
  const currentFilterConfig = FILTERS.find(f => f.id === activeFilter) || FILTERS[7]; // Default to 'active'

  const {
    picks,
    isLoading,
    isRefreshing,
    error,
    lastUpdated,
    refresh,
    setPeriod,
    setOutcome,
  } = useLivePicks({
    bullishLimit: 50,
    bearishLimit: 50,
    refreshInterval: 5 * 60 * 1000,
    enabled: true,
    minConfidence: 0,
    period: currentFilterConfig.period,
    outcome: currentFilterConfig.outcome,
  });

  const {
    addToWatchlist,
    isAdding,
    isInWatchlist,
  } = useWatchlist();

  // Handle unified filter change
  const handleFilterChange = useCallback((newFilterId: FilterId) => {
    setActiveFilter(newFilterId);
    const config = FILTERS.find(f => f.id === newFilterId);
    if (config) {
      setPeriod(config.period);
      if (config.outcome) {
        setOutcome(config.outcome);
      } else {
        setOutcome(undefined);
      }
    }
  }, [setPeriod, setOutcome]);

  // Apply local sentiment filter if needed
  const filteredPicks = useMemo(() => {
    let picksToShow = picks;

    // Apply sentiment filter for bull/bear options (local filtering)
    if (currentFilterConfig.sentiment === "bullish") {
      picksToShow = picks.filter(p => p.sentiment === "bullish");
    } else if (currentFilterConfig.sentiment === "bearish") {
      picksToShow = picks.filter(p => p.sentiment === "bearish");
    }

    // Sort by confidence descending
    return [...picksToShow].sort((a, b) => b.confidence - a.confidence);
  }, [picks, currentFilterConfig.sentiment]);

  // Badge counts based on filtered picks
  const bullishCount = filteredPicks.filter(p => p.sentiment === "bullish").length;
  const bearishCount = filteredPicks.filter(p => p.sentiment === "bearish").length;

  const getConfidenceLevel = (confidence: number): { label: string; color: string } => {
    if (confidence >= 80) return { label: "High", color: "text-emerald-400" };
    if (confidence >= 65) return { label: "Medium", color: "text-yellow-400" };
    return { label: "Low", color: "text-orange-400" };
  };

  return (
    <div className="space-y-4">
      {/* Circular Stats Badge */}
      <div className="flex justify-center">
        <motion.div
          animate={{
            scale: [1, 1.02, 1],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="relative"
        >
          {/* Conic gradient border ring - emerald LEFT, rose RIGHT */}
          <div
            className="w-60 h-60 rounded-full p-1 shadow-2xl"
            style={{
              background: `conic-gradient(from 180deg at 50% 50%,
                rgb(249, 115, 22) 0deg,
                rgb(16, 185, 129) 45deg,
                rgb(16, 185, 129) 135deg,
                rgb(249, 115, 22) 180deg,
                rgb(244, 63, 94) 225deg,
                rgb(244, 63, 94) 315deg,
                rgb(249, 115, 22) 360deg)`
            }}
          >
            <div className="w-full h-full rounded-full bg-slate-900 flex flex-col items-center justify-center px-3">
              {/* Filter label at top - cream color */}
              <span className="text-sm uppercase tracking-widest mb-4" style={{ color: '#FCF9EA' }}>
                {currentFilterConfig.label}
              </span>

              {/* Main content: Number (outside) | Icon | divider | Icon | Number (outside) */}
              <div className="flex items-center justify-center">
                {/* Bullish: Number on left, Icon next to divider */}
                <button
                  onClick={() => handleFilterChange(activeFilter === 'bull' ? 'active' : 'bull')}
                  className={`flex items-center gap-2 transition-all ${activeFilter === 'bull' ? "scale-110" : "hover:scale-105"}`}
                >
                  <span className="text-4xl font-bold text-emerald-400">{bullishCount}</span>
                  <img src={bullIcon} alt="bull" className="w-12 h-12" />
                </button>

                {/* Divider */}
                <div className="h-14 w-px bg-slate-600 mx-2" />

                {/* Bearish: Icon next to divider, Number on right */}
                <button
                  onClick={() => handleFilterChange(activeFilter === 'bear' ? 'active' : 'bear')}
                  className={`flex items-center gap-2 transition-all ${activeFilter === 'bear' ? "scale-110" : "hover:scale-105"}`}
                >
                  <img src={bearIcon} alt="bear" className="w-12 h-12" />
                  <span className="text-4xl font-bold text-rose-400">{bearishCount}</span>
                </button>
              </div>

              {/* Labels row - larger */}
              <div className="flex items-center justify-center gap-10 mt-2">
                <span className="text-xs text-emerald-400 uppercase tracking-wider font-semibold">Bullish</span>
                <span className="text-xs text-rose-400 uppercase tracking-wider font-semibold">Bearish</span>
              </div>

              {/* Date at bottom */}
              <span className="text-xs text-slate-400 mt-3">
                {activeFilter === 'today'
                  ? new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
                  : activeFilter === 'week'
                    ? `Since ${new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}`
                  : activeFilter === 'active'
                    ? `Since ${new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
                  : activeFilter === 'all'
                    ? 'All Time'
                  : ''
                }
              </span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Unified Filter Dropdown */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Select value={activeFilter} onValueChange={(v) => handleFilterChange(v as FilterId)}>
          <SelectTrigger className="w-[160px] bg-slate-800 border-slate-600 text-slate-100 text-sm">
            <SelectValue placeholder="Select filter" />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-700">
            {FILTERS.map((filter) => (
              <SelectItem
                key={filter.id}
                value={filter.id}
                className="text-slate-200 focus:bg-slate-800 focus:text-slate-100"
              >
                {filter.id === 'wins' && '🏆 '}
                {filter.id === 'misses' && '💔 '}
                {filter.id === 'bull' && '🐂 '}
                {filter.id === 'bear' && '🐻 '}
                {filter.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button onClick={refresh} variant="outline" size="sm" disabled={isRefreshing} className="bg-slate-800 border-slate-600">
          <RefreshCw className={`w-4 h-4 mr-1 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Last Updated */}
      <div className="text-center text-sm text-slate-400">
        Last updated: {lastUpdated?.toLocaleTimeString() || "—"}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mb-4"></div>
          <p className="text-gray-400">Loading live AI picks...</p>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="text-center py-10">
          <p className="text-red-400 mb-4">Error loading picks: {error}</p>
          <Button onClick={refresh} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      )}

      {/* No Picks */}
      {!isLoading && !error && filteredPicks.length === 0 && (
        <div className="text-center py-20">
          <Sparkles className="w-16 h-16 mx-auto mb-4 text-yellow-500 opacity-30" />
          <p className="text-xl text-gray-400">No live picks right now</p>
          <p className="text-sm text-gray-500 mt-2">The AI is scanning 3,800+ stocks for the next explosive move...</p>
        </div>
      )}

      {/* Picks List */}
      {!isLoading && !error && filteredPicks.length > 0 && (
        <div className="space-y-4">
          {filteredPicks.map((pick, index) => {
            const isOpen = openPickId === pick.id;
            const alreadyInWatchlist = isInWatchlist(pick.symbol);
            const isBullish = pick.sentiment === "bullish";
            const confidenceLevel = getConfidenceLevel(pick.confidence);
            const outcomeStatus = pick.outcomeStatus || 'active';

            // Outcome-based styling
            // Active: Green (bull) / Red (bear)
            // Win (primary/target2): Gold
            // Moonshot: Gold with sparkle animation
            // Loss/Miss: Purple
            let borderClass = '';
            let shouldSparkle = false;
            let outcomeLabel = '';

            if (outcomeStatus === 'moonshot') {
              borderClass = 'border-2 bg-gradient-to-br from-yellow-950/60 via-amber-900/40 to-yellow-900/30 border-yellow-500/60 hover:border-yellow-400/80';
              shouldSparkle = true;
              outcomeLabel = '🌙 Moonshot Hit!';
            } else if (outcomeStatus === 'win') {
              borderClass = 'border-2 bg-gradient-to-br from-yellow-950/60 via-amber-900/40 to-yellow-900/30 border-yellow-600/50 hover:border-yellow-500/70';
              outcomeLabel = '🎯 Target Hit!';
            } else if (outcomeStatus === 'loss') {
              borderClass = 'border-2 bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-purple-900/30 border-purple-700/40 hover:border-purple-500/60';
              outcomeLabel = '❌ Expired';
            } else {
              // Active - use bull/bear colors
              borderClass = isBullish
                ? 'border-2 bg-gradient-to-br from-emerald-950/60 via-slate-900/40 to-emerald-900/30 border-emerald-700/40 hover:border-emerald-500/60'
                : 'border-2 bg-gradient-to-br from-rose-950/60 via-slate-900/40 to-rose-900/30 border-rose-700/40 hover:border-rose-500/60';
            }

            return (
              <motion.div
                key={pick.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Collapsible open={isOpen} onOpenChange={(open) => setOpenPickId(open ? pick.id : null)}>
                  <motion.div
                    animate={shouldSparkle ? {
                      boxShadow: [
                        '0 0 20px rgba(234, 179, 8, 0.3)',
                        '0 0 40px rgba(234, 179, 8, 0.6)',
                        '0 0 20px rgba(234, 179, 8, 0.3)',
                      ],
                    } : {}}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                    className="rounded-lg"
                  >
                  <Card className={`shadow-lg hover:shadow-2xl transition-all duration-300 ${borderClass}`}>
                    <CollapsibleTrigger className="w-full">
                      <CardContent className="py-4">
                        <div className="space-y-3">
                          {/* Row 1: Symbol (left) + Confidence/Sentiment (right) */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="text-left min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xl font-bold text-slate-100">{pick.symbol}</span>
                                {outcomeLabel && (
                                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                                    outcomeStatus === 'moonshot' ? 'bg-yellow-500/30 text-yellow-300' :
                                    outcomeStatus === 'win' ? 'bg-amber-500/30 text-amber-300' :
                                    outcomeStatus === 'loss' ? 'bg-purple-500/30 text-purple-300' : ''
                                  }`}>
                                    {outcomeLabel}
                                  </span>
                                )}
                              </div>
                              <p className="text-slate-400 text-sm truncate">{pick.name}</p>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              {/* Confidence Badge with Tooltip */}
                              <div className="relative group">
                                <Badge
                                  className={`text-xs px-2 py-1 ${confidenceLevel.color} bg-slate-800/50 border-slate-600 cursor-help`}
                                  variant="outline"
                                >
                                  {pick.confidence}%
                                </Badge>
                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-lg">
                                  <div className="font-medium text-slate-100 mb-1">AI Confidence Score</div>
                                  <div>How certain our AI model is about this pick</div>
                                  <div className="mt-1 text-slate-400">
                                    80%+ High • 65-79% Medium • &lt;65% Low
                                  </div>
                                  {/* Arrow */}
                                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-600"></div>
                                </div>
                              </div>
                              <Badge
                                className={`text-xs px-2 py-1 ${
                                  isBullish
                                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                                    : 'bg-rose-500/20 text-rose-300 border-rose-500/50'
                                }`}
                                variant="outline"
                              >
                                {isBullish ? '↑ Bull' : '↓ Bear'}
                              </Badge>
                              {isOpen ? (
                                <ChevronUp className="w-5 h-5 text-slate-400" />
                              ) : (
                                <ChevronDown className="w-5 h-5 text-slate-400" />
                              )}
                            </div>
                          </div>

                          {/* Row 2: Picked @ + Current Price (same sizes) */}
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <div className="text-left space-y-1">
                              {/* Line 1: Picked @ with date */}
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-300">
                                  Picked @ ${pick.priceAtAlert > 0 ? pick.priceAtAlert.toFixed(2) : '—'}
                                </span>
                                <span className="text-sm text-slate-500">
                                  on {pick.timestamp ? new Date(pick.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }).replace(',', '') : '—'}
                                </span>
                              </div>
                              {/* Line 2: Current Price with change */}
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-300">
                                  Current ${pick.currentPrice > 0 ? pick.currentPrice.toFixed(2) : '—'}
                                </span>
                                {pick.change !== 0 && (
                                  <span className={`text-sm font-medium ${pick.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {pick.change >= 0 ? '+' : ''}{pick.change.toFixed(2)}%
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="text-right">
                              <p className="text-slate-500 text-xs mb-0.5">Target Range</p>
                              <div className={`text-lg font-medium ${isBullish ? 'text-emerald-400' : 'text-rose-400'}`}>
                                ${pick.targetPriceLow?.toFixed(2) || '—'} → ${pick.targetPriceHigh?.toFixed(2) || '—'}
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <CardContent className="pt-0 pb-4 space-y-4 border-t border-slate-700/50">
                        {/* Chart + Analysis Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
                          {/* Left: Chart Image */}
                          {pick.chartUrl ? (
                            <div className="flex items-center">
                              <img
                                src={pick.chartUrl}
                                alt={`${pick.symbol} chart`}
                                className="w-full rounded-lg border border-slate-700/50"
                              />
                            </div>
                          ) : (
                            <div className="flex items-center justify-center bg-slate-800/30 rounded-lg border border-slate-700/50 min-h-[200px]">
                              <p className="text-slate-500 text-sm">Chart not available</p>
                            </div>
                          )}

                          {/* Right: AI Analysis + Targets */}
                          <div className="flex flex-col gap-3">
                            {/* Target Range Box */}
                            <div className={`p-4 rounded-lg ${isBullish ? 'bg-emerald-900/20 border border-emerald-700/30' : 'bg-rose-900/20 border border-rose-700/30'}`}>
                              <p className="text-slate-400 text-xs mb-2 uppercase tracking-wider">Target Range</p>
                              <div className="flex items-center gap-2">
                                <span className={`text-2xl font-bold ${isBullish ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  ${pick.targetPriceLow?.toFixed(2) || '—'}
                                </span>
                                <span className="text-slate-500">→</span>
                                <span className={`text-2xl font-bold ${isBullish ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  ${pick.targetPriceHigh?.toFixed(2) || '—'}
                                </span>
                              </div>
                              {pick.priceAtAlert > 0 && (
                                <p className="text-slate-500 text-xs mt-2">
                                  {isBullish ? 'Upside' : 'Downside'}: {Math.abs(((pick.targetPriceHigh || 0) - pick.priceAtAlert) / pick.priceAtAlert * 100).toFixed(1)}%
                                </p>
                              )}
                            </div>

                            {/* AI Analysis Bullet Points */}
                            {(pick.reasoning || pick.aiSummary) && (
                              <div className="p-4 bg-slate-800/30 rounded-lg flex-1">
                                <p className="text-slate-400 text-xs mb-3 uppercase tracking-wider">AI Analysis</p>
                                <ul className="space-y-2">
                                  {(pick.reasoning || pick.aiSummary || '').split('\n').filter(Boolean).map((point: string, idx: number) => (
                                    <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                                      <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${isBullish ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
                                      <span>{point.replace(/^[•\-]\s*/, '')}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Add to Watchlist Button */}
                        <Button
                          className={`w-full shadow-lg ${isBullish ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            addToWatchlist({
                              symbol: pick.symbol,
                              name: pick.name || pick.symbol,
                              entry_type: isBullish ? "long" : "short",
                              entry_price: pick.priceAtAlert,
                              target_price: isBullish ? pick.targetPriceHigh : pick.targetPriceLow,
                              ai_confidence_score: pick.confidence,
                              ai_recommendation: pick.reasoning || "High-confidence AI pick",
                            });
                          }}
                          disabled={isAdding || alreadyInWatchlist}
                        >
                          {alreadyInWatchlist ? (
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
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}