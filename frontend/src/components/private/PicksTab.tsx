// src/components/private/PicksTab.tsx
'use client';

import React, { useState, useMemo } from "react";
import {
  ChevronDown,
  TrendingUp,
  TrendingDown,
  Plus,
  Clock,
  Sparkles,
  RefreshCw,
  X
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  } = useWatchlist();

  const isInWatchlist = (symbol: string) => 
    watchlistEntries.some(entry => entry.ticker === symbol);

  const [sortBy, setSortBy] = useState<"confidence" | "change" | "time">("confidence");
  const [filterSentiment, setFilterSentiment] = useState<"all" | "bullish" | "bearish">("all");
  const [openPickId, setOpenPickId] = useState<string | null>(null);

  const filteredPicks = useMemo(() => {
    let picksToShow = filterSentiment === "all" ? picks : 
      filterSentiment === "bullish" ? picks.filter(p => p.sentiment === "bullish") : 
      picks.filter(p => p.sentiment === "bearish");

    return [...picksToShow].sort((a, b) => {
      if (sortBy === "confidence") return b.confidence - a.confidence;
      if (sortBy === "change") return b.change - a.change;
      if (sortBy === "time") return b.timestamp.getTime() - a.timestamp.getTime();
      return 0;
    });
  }, [picks, filterSentiment, sortBy]);

  const formatTimeToTarget = (hours?: number) => {
    if (!hours) return "—";
    const days = Math.floor(hours / 24);
    const h = hours % 24;
    return days > 0 ? `${days}d ${h}h` : `${h}h`;
  };

  return (
    <div className="space-y-6">
      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mb-4"></div>
          <p className="text-gray-400">Loading live AI picks...</p>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="text-center py-20">
          <p className="text-red-400 mb-4">Error loading picks: {error}</p>
          <Button onClick={refresh} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      )}

      {/* Main Content */}
      {!isLoading && !error && (
        <>
          {/* Header */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                <Sparkles className="w-6 h-6 text-yellow-500" />
                Live AI Picks
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                {picks.length} active picks • Last updated: {lastUpdated?.toLocaleTimeString() || "—"}
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Select value={filterSentiment} onValueChange={(v) => setFilterSentiment(v as any)}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Picks</SelectItem>
                  <SelectItem value="bullish">Bullish Only</SelectItem>
                  <SelectItem value="bearish">Bearish Only</SelectItem>
                </SelectContent>
              </Select>

              <Select value={sortBy} onValueChange={(v) => setSortBy(v as any)}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="confidence">Confidence</SelectItem>
                  <SelectItem value="change">% Change</SelectItem>
                  <SelectItem value="time">Newest First</SelectItem>
                </SelectContent>
              </Select>

              <Button onClick={refresh} variant="outline" size="sm" disabled={isRefreshing}>
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>

          {/* Picks Grid */}
          {filteredPicks.length === 0 ? (
            <div className="text-center py-20">
              <Sparkles className="w-16 h-16 mx-auto mb-4 text-yellow-500 opacity-30" />
              <p className="text-xl text-gray-400">No live picks right now</p>
              <p className="text-sm text-gray-500 mt-2">The AI is scanning 3,800+ stocks for the next explosive move...</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredPicks.map((pick, index) => {
                const isBullish = pick.sentiment === "bullish";
                const changeSinceAlert = pick.change;
                const alreadyInWatchlist = isInWatchlist(pick.symbol);

                return (
                  <motion.div
                    key={pick.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Collapsible
                      open={openPickId === pick.id}
                      onOpenChange={(open) => setOpenPickId(open ? pick.id : null)}
                    >
                      <Card className="bg-slate-900/50 border-slate-700 hover:border-slate-600 transition-all">
                        <CollapsibleTrigger asChild>
                          <CardHeader 
                            className="cursor-pointer"
                            onClick={() => onPickClick?.(isBullish ? "bullish" : "bearish")}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-4">
                                <img src={isBullish ? bullIcon : bearIcon} alt={isBullish ? "Bull" : "Bear"} className="w-10 h-10" />
                                <div>
                                  <CardTitle className="text-lg flex items-center gap-2">
                                    {pick.symbol}
                                    <span className="text-sm font-normal text-gray-400">{pick.name}</span>
                                  </CardTitle>
                                  <div className="flex items-center gap-4 mt-1">
                                    <Badge variant={isBullish ? "default" : "destructive"}>
                                      {isBullish ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                                      {isBullish ? "BULLISH" : "BEARISH"}
                                    </Badge>
                                    <span className="text-sm text-gray-400">Confidence: {pick.confidence}%</span>
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center gap-6">
                                <div className="text-right">
                                  <p className="text-2xl font-bold text-white">${pick.currentPrice.toFixed(2)}</p>
                                  <p className={`text-sm ${changeSinceAlert >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                    {changeSinceAlert >= 0 ? "+" : ""}{changeSinceAlert.toFixed(2)}%
                                  </p>
                                </div>
                                <ChevronDown className={`w-5 h-5 transition-transform ${openPickId === pick.id ? "rotate-180" : ""}`} />
                              </div>
                            </div>
                          </CardHeader>
                        </CollapsibleTrigger>

                        <CollapsibleContent>
                          <CardContent className="pt-0 pb-4 space-y-4 border-t border-slate-700/50">
                            {/* Your expanded content here */}
                            
                            <Button
                              className={`w-full shadow-lg ${isBullish ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                addToWatchlist({
                                  symbol: pick.symbol,
                                  name: pick.name || pick.symbol,
                                  entry_type: isBullish ? "long" : "short",
                                  entry_price: pick.currentPrice,
                                  target_price: isBullish ? pick.targetPriceHigh : pick.targetPriceLow,
                                  ai_confidence_score: pick.confidence,
                                  ai_recommendation: pick.aiSummary || pick.reasoning || "High-confidence AI pick",
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
        </>
      )}
    </div>
  );
}