// Real data hooks for BullsBears API integration
// Replaces demo data with actual API calls

import { useState, useEffect, useCallback } from 'react';
import {
  StockPick,
  WatchlistStock,
  AccuracyTrendPoint,
  RecentPickOutcome,
  ModelAccuracyStats,
  ApiResponse
} from '../lib/types';
import { api } from '../lib/api';

// Generic API fetch function - handles backend offline gracefully
async function fetchApi<T>(endpoint: string): Promise<T | null> {
  try {
    const response = await api.get(endpoint);

    // Backend is offline - return null
    if (response === null) {
      return null;
    }

    if (response.data?.status === 'error') {
      throw new Error(response.data.message || 'API returned error status');
    }

    return response.data?.data || response.data;
  } catch (error) {
    // Silently handle backend offline - don't spam console
    return null;
  }
}

// Hook for fetching current stock picks
export function useStockPicks() {
  const [bullishPicks, setBullishPicks] = useState<StockPick[]>([]);
  const [bearishPicks, setBearishPicks] = useState<StockPick[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPicks = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [bullishResponse, bearishResponse] = await Promise.all([
        fetchApi<StockPick[]>('/api/v1/bullish_alerts'),
        fetchApi<StockPick[]>('/api/v1/bearish_alerts')
      ]);

      setBullishPicks(bullishResponse || []);
      setBearishPicks(bearishResponse || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch picks';
      setError(errorMessage);
      console.error('Error fetching picks:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPicks();
  }, [fetchPicks]);

  return {
    bullishPicks,
    bearishPicks,
    allPicks: [...bullishPicks, ...bearishPicks],
    isLoading,
    error,
    refetch: fetchPicks
  };
}

// Hook for fetching watchlist data
export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWatchlist = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await fetchApi<WatchlistStock[]>('/api/v1/watchlist');
      setWatchlist(data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch watchlist';
      setError(errorMessage);
      console.error('Error fetching watchlist:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  return {
    watchlist,
    isLoading,
    error,
    refetch: fetchWatchlist
  };
}

// Hook for fetching model accuracy and analytics data
export function useModelAccuracy() {
  const [accuracyData, setAccuracyData] = useState<ModelAccuracyStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAccuracy = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await fetchApi<ModelAccuracyStats>('/api/v1/statistics/model-accuracy');
      // Backend offline returns null - this is OK, just show empty state
      setAccuracyData(data);
    } catch (err) {
      // Only set error for real errors, not backend offline
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch accuracy data';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAccuracy();
  }, [fetchAccuracy]);

  return {
    accuracyData,
    isLoading,
    error,
    refetch: fetchAccuracy
  };
}

// Hook for fetching recent pick outcomes
export function useRecentOutcomes() {
  const [outcomes, setOutcomes] = useState<RecentPickOutcome[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOutcomes = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await fetchApi<RecentPickOutcome[]>('/api/v1/analytics/recent-outcomes');
      setOutcomes(data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch recent outcomes';
      setError(errorMessage);
      console.error('Error fetching recent outcomes:', err);
      
      // For now, return empty array if endpoint doesn't exist
      setOutcomes([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOutcomes();
  }, [fetchOutcomes]);

  return {
    outcomes,
    isLoading,
    error,
    refetch: fetchOutcomes
  };
}

// Hook for fetching accuracy trend data
export function useAccuracyTrend(period: '7d' | '30d' | '90d' = '30d') {
  const [trendData, setTrendData] = useState<AccuracyTrendPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrend = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await fetchApi<AccuracyTrendPoint[]>(`/api/v1/analytics/accuracy-trend?period=${period}`);
      setTrendData(data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch accuracy trend';
      setError(errorMessage);
      console.error('Error fetching accuracy trend:', err);
      
      // For now, return empty array if endpoint doesn't exist
      setTrendData([]);
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchTrend();
  }, [fetchTrend]);

  return {
    trendData,
    isLoading,
    error,
    refetch: fetchTrend
  };
}
