// src/components/private/WatchlistTab.tsx
'use client';

import React from 'react';
import { useWatchlist } from '@/hooks/useWatchlist';
import { HistoryEntry } from '@/lib/types';
import { TrendingUp, TrendingDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function WatchlistTab() {
  const {
    watchlistEntries,
    isAdding,
    error,
    refresh,
    isInWatchlist,
    addToWatchlist,
  } = useWatchlist();

  if (error) {
    return (
      <div className="p-4 text-center text-red-400">
        Error: {error}
        <Button onClick={refresh} variant="outline" className="ml-2">
          Retry
        </Button>
      </div>
    );
  }

  if (watchlistEntries.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400">
        <p className="text-lg">Your watchlist is empty</p>
        <p className="text-sm mt-2">Add picks from the AI feed to start tracking</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {watchlistEntries.map(entry => {
        const isPositive = entry.actual_percent >= 0;
        return (
          <Card key={entry.id} className="bg-gray-800 border-gray-700">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg text-white">
                  {entry.ticker}
                  <span className="text-sm font-normal text-gray-400 ml-2">
                    {entry.company_name}
                  </span>
                </CardTitle>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-gray-400 hover:text-red-400"
                  onClick={() => {
                    // Optional: remove from watchlist
                  }}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-400">Entry</p>
                  <p className="text-white">${entry.entry_price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-gray-400">Current</p>
                  <p className="text-white">${entry.current_price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-gray-400">Change</p>
                  <p className={isPositive ? 'text-emerald-400' : 'text-red-400'}>
                    {isPositive ? <TrendingUp className="inline w-4 h-4 mr-1" /> : <TrendingDown className="inline w-4 h-4 mr-1" />}
                    {entry.actual_percent.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-gray-400">Days to Hit</p>
                  <p className="text-white">{entry.days_to_hit}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}