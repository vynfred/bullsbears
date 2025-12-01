// src/hooks/useWatchlist.ts
// Uses Firebase Realtime Database for user-specific watchlist storage
import { useState, useEffect, useCallback } from 'react';
import { getDatabase, ref, onValue, push, remove, set } from 'firebase/database';
import { useAuth } from './useAuth';
import { api } from '@/lib/api';

export interface WatchlistEntry {
  id: string;
  symbol: string;
  name?: string;
  entry_type: string;  // 'long' or 'short'
  entry_price: number;
  target_price: number;
  ai_confidence_score: number;
  ai_recommendation: string;
  added_at: string;
  // Computed fields (from FMP API)
  current_price?: number;
  price_change?: number;
  price_change_percent?: number;
}

export interface UseWatchlistReturn {
  watchlistEntries: WatchlistEntry[];
  addToWatchlist: (request: {
    symbol: string;
    name?: string;
    entry_type: string;
    entry_price: number;
    target_price: number;
    ai_confidence_score: number;
    ai_recommendation: string;
  }) => Promise<boolean>;
  removeFromWatchlist: (symbol: string) => Promise<boolean>;
  isAdding: boolean;
  error: string | null;
  refresh: () => void;
  isInWatchlist: (symbol: string) => boolean;
}

export function useWatchlist(): UseWatchlistReturn {
  const { user } = useAuth();
  const [watchlistEntries, setWatchlistEntries] = useState<WatchlistEntry[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch real-time prices for watchlist symbols
  const fetchPrices = useCallback(async (entries: WatchlistEntry[]) => {
    if (entries.length === 0) return entries;

    try {
      const symbols = entries.map(e => e.symbol);
      const prices = await api.getQuotes(symbols);

      return entries.map(entry => {
        const quote = prices[entry.symbol];
        if (quote) {
          const currentPrice = quote.price || entry.entry_price;
          const priceChange = currentPrice - entry.entry_price;
          const priceChangePercent = entry.entry_price > 0
            ? ((currentPrice - entry.entry_price) / entry.entry_price) * 100
            : 0;

          return {
            ...entry,
            current_price: currentPrice,
            price_change: priceChange,
            price_change_percent: priceChangePercent,
          };
        }
        return entry;
      });
    } catch (err) {
      console.warn('Failed to fetch watchlist prices:', err);
      return entries;
    }
  }, []);

  // Subscribe to Firebase Realtime Database for watchlist updates
  useEffect(() => {
    if (!user?.uid) {
      setWatchlistEntries([]);
      return;
    }

    const db = getDatabase();
    const watchlistRef = ref(db, `users/${user.uid}/watchlist`);

    const unsubscribe = onValue(watchlistRef, async (snapshot) => {
      const data = snapshot.val();
      if (data) {
        let entries: WatchlistEntry[] = Object.entries(data).map(([key, value]: [string, any]) => ({
          id: key,
          symbol: value.symbol,
          name: value.name,
          entry_type: value.entry_type,
          entry_price: value.entry_price,
          target_price: value.target_price,
          ai_confidence_score: value.ai_confidence_score,
          ai_recommendation: value.ai_recommendation,
          added_at: value.added_at,
          current_price: value.current_price,
          price_change: value.price_change,
          price_change_percent: value.price_change_percent,
        }));
        // Sort by added_at descending (newest first)
        entries.sort((a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime());

        // Fetch real-time prices from FMP
        entries = await fetchPrices(entries);

        setWatchlistEntries(entries);
      } else {
        setWatchlistEntries([]);
      }
      setError(null);
    }, (err) => {
      console.error('Firebase watchlist error:', err);
      setError('Failed to load watchlist');
    });

    return () => unsubscribe();
  }, [user?.uid, fetchPrices]);

  const addToWatchlist = useCallback(async (request: {
    symbol: string;
    name?: string;
    entry_type: string;
    entry_price: number;
    target_price: number;
    ai_confidence_score: number;
    ai_recommendation: string;
  }) => {
    if (!user?.uid) {
      setError('Must be logged in to add to watchlist');
      return false;
    }

    // Check if already in watchlist
    if (watchlistEntries.some(e => e.symbol === request.symbol)) {
      setError(`${request.symbol} already in watchlist`);
      return false;
    }

    try {
      setIsAdding(true);
      setError(null);

      const db = getDatabase();
      const watchlistRef = ref(db, `users/${user.uid}/watchlist`);

      await push(watchlistRef, {
        symbol: request.symbol,
        name: request.name || request.symbol,
        entry_type: request.entry_type,
        entry_price: request.entry_price,
        target_price: request.target_price,
        ai_confidence_score: request.ai_confidence_score,
        ai_recommendation: request.ai_recommendation,
        added_at: new Date().toISOString(),
      });

      return true;
    } catch (err) {
      console.error('Failed to add to watchlist:', err);
      setError('Failed to add to watchlist');
      return false;
    } finally {
      setIsAdding(false);
    }
  }, [user?.uid, watchlistEntries]);

  const removeFromWatchlist = useCallback(async (symbol: string) => {
    if (!user?.uid) {
      setError('Must be logged in');
      return false;
    }

    const entry = watchlistEntries.find(e => e.symbol === symbol);
    if (!entry) {
      setError(`${symbol} not found in watchlist`);
      return false;
    }

    try {
      const db = getDatabase();
      const entryRef = ref(db, `users/${user.uid}/watchlist/${entry.id}`);
      await remove(entryRef);
      return true;
    } catch (err) {
      console.error('Failed to remove from watchlist:', err);
      setError('Failed to remove from watchlist');
      return false;
    }
  }, [user?.uid, watchlistEntries]);

  const isInWatchlist = useCallback(
    (symbol: string) => watchlistEntries.some(e => e.symbol === symbol),
    [watchlistEntries]
  );

  const refresh = useCallback(() => {
    // Firebase onValue listener auto-refreshes, but we can trigger a manual check
    // by just clearing error state
    setError(null);
  }, []);

  return {
    watchlistEntries,
    addToWatchlist,
    removeFromWatchlist,
    isAdding,
    error,
    refresh,
    isInWatchlist,
  };
}