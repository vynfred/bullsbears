// src/components/private/PicksTab.tsx
'use client';

import React, { useState, useMemo } from "react";
import {
  ChevronDown,
  ChevronUp,
  Plus,
  Clock,
  Sparkles,
  RefreshCw,
  ArrowUpDown
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion } from "framer-motion";
import { useLivePicks } from "@/hooks/useLivePicks";
import { useWatchlist } from "@/hooks/useWatchlist";

const bullIcon = "/assets/bull-icon.png";
const bearIcon = "/assets/bear-icon.png";

interface PicksTabProps {
  onPickClick?: (type: "bullish" | "bearish") => void;
}

type SortOption = "confidence" | "bullish" | "bearish" | "entry";

export default function PicksTab({ onPickClick }: PicksTabProps = {}) {
  const {
    picks,
    isLoading,
    isRefreshing,
    error,
    lastUpdated,
    refresh
  } = useLivePicks({
    bullishLimit: 25,
    bearishLimit: 25,
    refreshInterval: 5 * 60 * 1000,
    enabled: true,
    minConfidence: 0.48
  });

  const {
    watchlistEntries,
    addToWatchlist,
    isAdding,
    isInWatchlist,
  } = useWatchlist();

  const [sortBy, setSortBy] = useState<SortOption>("confidence");
  const [filterSentiment, setFilterSentiment] = useState<"all" | "bullish" | "bearish">("all");
  const [openPickId, setOpenPickId] = useState<string | null>(null);

  const filteredPicks = useMemo(() => {
    let picksToShow = picks;

    // Apply sentiment filter
    if (filterSentiment === "bullish") {
      picksToShow = picks.filter(p => p.sentiment === "bullish");
    } else if (filterSentiment === "bearish") {
      picksToShow = picks.filter(p => p.sentiment === "bearish");
    }

    // Apply sort
    if (sortBy === "bullish") {
      picksToShow = picksToShow.filter(p => p.sentiment === "bullish");
    } else if (sortBy === "bearish") {
      picksToShow = picksToShow.filter(p => p.sentiment === "bearish");
    }

    return [...picksToShow].sort((a, b) => {
      if (sortBy === "confidence") return b.confidence - a.confidence;
      if (sortBy === "entry") {
        const aDiff = Math.abs(a.change);
        const bDiff = Math.abs(b.change);
        return aDiff - bDiff;
      }
      return b.confidence - a.confidence;
    });
  }, [picks, filterSentiment, sortBy]);

  const bullishCount = picks.filter(p => p.sentiment === "bullish").length;
  const bearishCount = picks.filter(p => p.sentiment === "bearish").length;

  const getConfidenceLevel = (confidence: number): { label: string; color: string } => {
    if (confidence >= 80) return { label: "High", color: "text-emerald-400" };
    if (confidence >= 65) return { label: "Medium", color: "text-yellow-400" };
    return { label: "Low", color: "text-orange-400" };
  };

  const formatTimeToTarget = (hours?: number) => {
    if (!hours) return "—";
    const days = Math.floor(hours / 24);
    const h = Math.floor(hours % 24);
    return days > 0 ? `${days}d ${h}h` : `${h}h`;
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
            className="w-48 h-48 rounded-full p-1 shadow-2xl"
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
            <div className="w-full h-full rounded-full bg-slate-900 flex flex-col items-center justify-center">
              <span className="text-[10px] text-slate-400 uppercase tracking-widest mb-2">Today&apos;s Picks</span>
              <div className="flex items-center justify-center gap-6">
                {/* Bullish side */}
                <button
                  onClick={() => setFilterSentiment(filterSentiment === "bullish" ? "all" : "bullish")}
                  className={`flex flex-col items-center transition-all ${filterSentiment === "bullish" ? "scale-110" : "hover:scale-105"}`}
                >
                  <span className="text-4xl font-bold text-emerald-400">{bullishCount}</span>
                  <img
                    src={bullIcon}
                    alt="bull"
                    className="w-5 h-5 mt-1"
                    style={{ filter: 'brightness(0) saturate(100%) invert(78%) sepia(23%) saturate(1234%) hue-rotate(94deg) brightness(91%) contrast(86%)' }}
                  />
                  <span className="text-[10px] text-emerald-400 mt-1 uppercase tracking-wide">Bullish</span>
                </button>

                {/* Divider */}
                <div className="h-16 w-px bg-slate-700" />

                {/* Bearish side */}
                <button
                  onClick={() => setFilterSentiment(filterSentiment === "bearish" ? "all" : "bearish")}
                  className={`flex flex-col items-center transition-all ${filterSentiment === "bearish" ? "scale-110" : "hover:scale-105"}`}
                >
                  <span className="text-4xl font-bold text-rose-400">{bearishCount}</span>
                  <img
                    src={bearIcon}
                    alt="bear"
                    className="w-5 h-5 mt-1"
                    style={{ filter: 'brightness(0) saturate(100%) invert(60%) sepia(98%) saturate(3959%) hue-rotate(316deg) brightness(96%) contrast(92%)' }}
                  />
                  <span className="text-[10px] text-rose-400 mt-1 uppercase tracking-wide">Bearish</span>
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Filter and Sort Options */}
      <div className="flex items-center justify-center gap-3">
        <Select value={filterSentiment} onValueChange={(v) => setFilterSentiment(v as typeof filterSentiment)}>
          <SelectTrigger className="w-[140px] bg-slate-800 border-slate-600 text-slate-100">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-900 border-slate-700">
            <SelectItem value="all" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">All Picks</SelectItem>
            <SelectItem value="bullish" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">Bullish Only</SelectItem>
            <SelectItem value="bearish" className="text-slate-200 focus:bg-slate-800 focus:text-slate-100">Bearish Only</SelectItem>
          </SelectContent>
        </Select>

        <Button onClick={refresh} variant="outline" size="sm" disabled={isRefreshing} className="bg-slate-800 border-slate-600">
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
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

            const borderClass = isBullish
              ? 'border-2 bg-gradient-to-br from-emerald-950/60 via-slate-900/40 to-emerald-900/30 border-emerald-700/40 hover:border-emerald-500/60'
              : 'border-2 bg-gradient-to-br from-rose-950/60 via-slate-900/40 to-rose-900/30 border-rose-700/40 hover:border-rose-500/60';

            return (
              <motion.div
                key={pick.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Collapsible open={isOpen} onOpenChange={(open) => setOpenPickId(open ? pick.id : null)}>
                  <Card className={`shadow-lg hover:shadow-2xl transition-all duration-300 ${borderClass}`}>
                    <CollapsibleTrigger className="w-full">
                      <CardContent className="py-4">
                        <div className="space-y-3">
                          {/* Row 1: Symbol (left) + Confidence/Sentiment (right) */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="text-left min-w-0">
                              <div className="text-xl font-bold text-slate-100">{pick.symbol}</div>
                              <p className="text-slate-400 text-sm truncate">{pick.name}</p>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <Badge
                                className={`text-xs px-2 py-1 ${confidenceLevel.color} bg-slate-800/50 border-slate-600`}
                                variant="outline"
                              >
                                {pick.confidence}%
                              </Badge>
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

                          {/* Row 2: Current Price + Change % */}
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <div className="text-left">
                              <p className="text-slate-500 text-xs mb-0.5">Current Price</p>
                              <div className="flex items-center gap-2">
                                <span className="text-lg text-slate-100 font-medium">
                                  ${pick.currentPrice > 0 ? pick.currentPrice.toFixed(2) : '—'}
                                </span>
                                {pick.change !== 0 && (
                                  <span className={`text-sm font-medium ${pick.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {pick.change >= 0 ? '+' : ''}{pick.change.toFixed(2)}%
                                  </span>
                                )}
                              </div>
                              <p className="text-slate-600 text-xs">
                                Picked @ ${pick.priceAtAlert > 0 ? pick.priceAtAlert.toFixed(2) : '—'}
                              </p>
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
                </Collapsible>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}