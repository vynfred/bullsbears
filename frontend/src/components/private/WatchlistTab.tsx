// src/components/private/WatchlistTab.tsx
'use client';

import React, { useState } from 'react';
import { useWatchlist, WatchlistEntry } from '@/hooks/useWatchlist';
import { TrendingUp, TrendingDown, X, Eye, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function WatchlistTab() {
  const {
    watchlistEntries,
    removeFromWatchlist,
    error,
    refresh,
  } = useWatchlist();

  const [removingSymbol, setRemovingSymbol] = useState<string | null>(null);

  const handleRemove = async (symbol: string) => {
    setRemovingSymbol(symbol);
    await removeFromWatchlist(symbol);
    setRemovingSymbol(null);
  };

  // Calculate days since added
  const getDaysSinceAdded = (addedAt: string) => {
    const added = new Date(addedAt);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - added.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  if (error) {
    return (
      <div className="p-4 text-center text-red-400">
        <p>Error: {error}</p>
        <Button onClick={refresh} variant="outline" className="mt-2">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  if (watchlistEntries.length === 0) {
    return (
      <div className="p-8 text-center">
        <Eye className="w-16 h-16 mx-auto mb-4 text-slate-500 opacity-30" />
        <p className="text-lg text-slate-400">Your watchlist is empty</p>
        <p className="text-sm mt-2 text-slate-500">Add picks from the AI feed to start tracking</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-2">
        <h2 className="text-lg font-semibold text-slate-200">
          Watching {watchlistEntries.length} stock{watchlistEntries.length !== 1 ? 's' : ''}
        </h2>
      </div>

      {watchlistEntries.map((entry: WatchlistEntry) => {
        const changePercent = entry.price_change_percent || 0;
        const isPositive = changePercent >= 0;
        const isBullish = entry.entry_type === 'long';
        const daysSinceAdded = getDaysSinceAdded(entry.added_at);

        return (
          <Card
            key={entry.id}
            className={`border-2 transition-all ${
              isBullish
                ? 'bg-gradient-to-br from-emerald-950/40 via-slate-900/40 to-emerald-900/20 border-emerald-700/30'
                : 'bg-gradient-to-br from-rose-950/40 via-slate-900/40 to-rose-900/20 border-rose-700/30'
            }`}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-lg text-slate-100">
                    {entry.symbol}
                  </CardTitle>
                  <Badge
                    variant="outline"
                    className={isBullish ? 'text-emerald-400 border-emerald-500/50' : 'text-rose-400 border-rose-500/50'}
                  >
                    {isBullish ? 'LONG' : 'SHORT'}
                  </Badge>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-slate-400 hover:text-red-400 hover:bg-red-500/10"
                  onClick={() => handleRemove(entry.symbol)}
                  disabled={removingSymbol === entry.symbol}
                >
                  {removingSymbol === entry.symbol ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <X className="w-4 h-4" />
                  )}
                </Button>
              </div>
              {entry.name && (
                <p className="text-sm text-slate-400">{entry.name}</p>
              )}
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500 text-xs uppercase">Price When Picked</p>
                  <p className="text-slate-200 text-lg">${entry.entry_price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase">Target</p>
                  <p className="text-slate-200 text-lg">${entry.target_price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase">Change Since</p>
                  <p className={`text-lg flex items-center gap-1 ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase">Days Held</p>
                  <p className="text-slate-200 text-lg">{daysSinceAdded}d</p>
                </div>
              </div>

              {/* AI Confidence */}
              <div className="mt-4 pt-4 border-t border-slate-700/50">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 text-xs uppercase">AI Confidence</span>
                  <span className={`text-sm ${entry.ai_confidence_score >= 70 ? 'text-emerald-400' : entry.ai_confidence_score >= 50 ? 'text-yellow-400' : 'text-orange-400'}`}>
                    {entry.ai_confidence_score}%
                  </span>
                </div>
                {entry.ai_recommendation && (
                  <p className="text-slate-400 text-xs mt-2 italic">{entry.ai_recommendation}</p>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}