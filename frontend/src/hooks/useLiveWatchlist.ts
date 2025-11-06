'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, WatchlistEntryResponse } from '@/lib/api';

export interface LiveWatchlistStock {
  id: string;
  symbol: string;
  name: string;
  addedAt: number;
  currentPrice: number;
  changeSince: number;
  changePercent: number;
  aiConfidence: number;
  notes: string;
  isWinner: boolean;
  daysHeld: number;
  entryDate: Date;
  targetPrice: number;
  stopLoss?: number;
  status: string;
  aiRecommendation: string;
}

interface UseLiveWatchlistOptions {
  refreshInterval?: number; // in milliseconds
  enabled?: boolean;
}

interface UseLiveWatchlistReturn {
  // Data
  stocks: LiveWatchlistStock[];
  
  // Loading states
  isLoading: boolean;
  isRefreshing: boolean;
  
  // Error handling
  error: string | null;
  
  // Metadata
  lastUpdated: Date | null;
  
  // Actions
  refresh: () => Promise<void>;
  addStock: (symbol: string, entryPrice: number, targetPrice: number, confidence: number, recommendation: string) => Promise<void>;
  updateStock: (id: string, updates: Partial<LiveWatchlistStock>) => Promise<void>;
  removeStock: (id: string) => Promise<void>;
  
  // Stats
  totalStocks: number;
  totalValue: number;
  totalGainLoss: number;
  totalGainLossPercent: number;
  winnersCount: number;
  losersCount: number;
}

// Transform backend response to frontend format
function transformWatchlistEntry(entry: WatchlistEntryResponse): LiveWatchlistStock {
  const changeSince = (entry.current_price || entry.entry_price) - entry.entry_price;
  const changePercent = (changeSince / entry.entry_price) * 100;
  
  return {
    id: entry.id.toString(),
    symbol: entry.symbol,
    name: entry.company_name || `${entry.symbol} Corporation`,
    addedAt: entry.entry_price,
    currentPrice: entry.current_price || entry.entry_price,
    changeSince,
    changePercent,
    aiConfidence: Math.round(entry.ai_confidence_score * 100),
    notes: `AI: ${entry.ai_recommendation}`,
    isWinner: entry.is_winner || false,
    daysHeld: entry.days_held,
    entryDate: new Date(entry.entry_date),
    targetPrice: entry.target_price,
    stopLoss: entry.stop_loss_price,
    status: entry.status,
    aiRecommendation: entry.ai_recommendation
  };
}

export function useLiveWatchlist(options: UseLiveWatchlistOptions = {}): UseLiveWatchlistReturn {
  const {
    refreshInterval = 5 * 60 * 1000, // 5 minutes default
    enabled = true
  } = options;

  const [stocks, setStocks] = useState<LiveWatchlistStock[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchWatchlist = useCallback(async () => {
    if (!enabled) return;

    try {
      setError(null);
      console.log('🔄 Fetching live watchlist from backend...');
      
      const watchlistData = await api.getWatchlistEntries();
      
      // Transform data
      const transformedStocks = watchlistData.map(transformWatchlistEntry);
      
      // Sort by entry date descending (newest first)
      transformedStocks.sort((a, b) => b.entryDate.getTime() - a.entryDate.getTime());

      setStocks(transformedStocks);
      setLastUpdated(new Date());
      console.log(`✅ Loaded ${transformedStocks.length} watchlist entries`);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch watchlist';
      console.error('❌ Error fetching watchlist:', errorMessage);
      setError(errorMessage);
    }
  }, [enabled]);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    await fetchWatchlist();
    setIsRefreshing(false);
  }, [fetchWatchlist]);

  const addStock = useCallback(async (
    symbol: string, 
    entryPrice: number, 
    targetPrice: number, 
    confidence: number, 
    recommendation: string
  ) => {
    try {
      setError(null);
      await api.addToWatchlist({
        symbol: symbol.toUpperCase(),
        entry_price: entryPrice,
        target_price: targetPrice,
        ai_confidence_score: confidence / 100,
        ai_recommendation: recommendation,
        ai_reasoning: `Added manually with ${confidence}% confidence`
      });
      
      // Refresh data after adding
      await fetchWatchlist();
      console.log(`✅ Added ${symbol} to watchlist`);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add stock to watchlist';
      console.error('❌ Error adding to watchlist:', errorMessage);
      setError(errorMessage);
      throw err;
    }
  }, [fetchWatchlist]);

  const updateStock = useCallback(async (id: string, updates: Partial<LiveWatchlistStock>) => {
    try {
      setError(null);
      
      // Transform frontend updates to backend format
      const backendUpdates: any = {};
      if (updates.addedAt !== undefined) backendUpdates.entry_price = updates.addedAt;
      if (updates.targetPrice !== undefined) backendUpdates.target_price = updates.targetPrice;
      if (updates.stopLoss !== undefined) backendUpdates.stop_loss_price = updates.stopLoss;
      if (updates.notes !== undefined) backendUpdates.ai_reasoning = updates.notes;
      
      await api.updateWatchlistEntry(parseInt(id), backendUpdates);
      
      // Refresh data after updating
      await fetchWatchlist();
      console.log(`✅ Updated watchlist entry ${id}`);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update watchlist entry';
      console.error('❌ Error updating watchlist:', errorMessage);
      setError(errorMessage);
      throw err;
    }
  }, [fetchWatchlist]);

  const removeStock = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.removeFromWatchlist(parseInt(id));
      
      // Refresh data after removing
      await fetchWatchlist();
      console.log(`✅ Removed watchlist entry ${id}`);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove from watchlist';
      console.error('❌ Error removing from watchlist:', errorMessage);
      setError(errorMessage);
      throw err;
    }
  }, [fetchWatchlist]);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      await fetchWatchlist();
      setIsLoading(false);
    };
    
    loadData();
  }, [fetchWatchlist]);

  // Auto-refresh interval
  useEffect(() => {
    if (!enabled || refreshInterval <= 0) return;

    const interval = setInterval(fetchWatchlist, refreshInterval);
    return () => clearInterval(interval);
  }, [enabled, refreshInterval, fetchWatchlist]);

  // Computed values
  const totalValue = stocks.reduce((sum, stock) => sum + (stock.currentPrice * 100), 0); // Assume 100 shares each
  const totalGainLoss = stocks.reduce((sum, stock) => sum + stock.changeSince, 0);
  const totalGainLossPercent = stocks.length > 0 ? 
    stocks.reduce((sum, stock) => sum + stock.changePercent, 0) / stocks.length : 0;
  const winnersCount = stocks.filter(s => s.changePercent > 0).length;
  const losersCount = stocks.filter(s => s.changePercent < 0).length;

  return {
    stocks,
    isLoading,
    isRefreshing,
    error,
    lastUpdated,
    refresh,
    addStock,
    updateStock,
    removeStock,
    totalStocks: stocks.length,
    totalValue,
    totalGainLoss,
    totalGainLossPercent,
    winnersCount,
    losersCount
  };
}
