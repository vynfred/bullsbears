// src/hooks/useWatchlist.ts
import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { HistoryEntry } from '@/lib/types';

export interface UseWatchlistReturn {
  watchlistEntries: HistoryEntry[];
  addToWatchlist: (request: {
    symbol: string;
    name?: string;
    entry_type: string;
    entry_price: number;
    target_price: number;
    ai_confidence_score: number;
    ai_recommendation: string;
  }) => Promise<boolean>;
  isAdding: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  isInWatchlist: (symbol: string) => boolean;
}

export function useWatchlist(): UseWatchlistReturn {
  const [watchlistEntries, setWatchlistEntries] = useState<HistoryEntry[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWatchlist = useCallback(async () => {
    try {
      setError(null);
      const data = await api.getWatchlistEntries();
      setWatchlistEntries(data);
    } catch (err) {
      setError('Failed to load watchlist');
    }
  }, []);

  const addToWatchlist = useCallback(async (request: any) => {
    try {
      setIsAdding(true);
      setError(null);
      const result = await api.addToWatchlist(request);
      if (result.success) {
        await fetchWatchlist();
        return true;
      }
      setError(result.message || 'Failed to add');
      return false;
    } catch (err) {
      setError('Network error');
      return false;
    } finally {
      setIsAdding(false);
    }
  }, [fetchWatchlist]);

  const isInWatchlist = useCallback(
    (symbol: string) => watchlistEntries.some(e => e.ticker === symbol),
    [watchlistEntries]
  );

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  return {
    watchlistEntries,
    addToWatchlist,
    isAdding,
    error,
    refresh: fetchWatchlist,
    isInWatchlist,
  };
}