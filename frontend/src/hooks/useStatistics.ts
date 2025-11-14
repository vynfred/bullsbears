// src/hooks/useStatistics.ts
'use client';

import { useState, useEffect, useReducer, useCallback } from 'react';
import { api } from '@/lib/api';

// Types for statistics data
export interface PicksStatistics {
  total_picks_today: number;
  bullish_count: number;
  bearish_count: number;
  high_confidence_count: number;
  avg_confidence: number;
  week_win_rate: number;
}

export interface WatchlistStatistics {
  total_stocks: number;
  winners: number;
  losers: number;
  avg_performance: number;
  total_return_dollars: number;
  best_performer: { symbol: string; return_percent: number } | null;
  worst_performer: { symbol: string; return_percent: number } | null;
}

export interface AnalyticsStatistics {
  model_accuracy: number;
  total_predictions: number;
  bullish_accuracy: number;
  bearish_accuracy: number;
  high_confidence_accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
}

export interface StatsBarData {
  daily_scans: number;
  alert_rate: number;
  bullish_win_rate: number;
  bearish_win_rate: number;
}

export interface ProfileStatistics {
  total_picks_month: number;
  win_rate_month: number;
  avg_days_to_target: number;
  closed_positions: number;
  closed_win_rate: number;
}

export interface BadgeData {
  picks_tab: PicksStatistics;
  watchlist_tab: WatchlistStatistics;
  analytics_tab: AnalyticsStatistics;
  stats_bar: StatsBarData;
  profile: ProfileStatistics;
}

interface UseStatisticsOptions {
  refreshInterval?: number;
  enabled?: boolean;
  autoRefresh?: boolean;
}

interface UseStatisticsReturn {
  badgeData: BadgeData | null;
  picksStats: PicksStatistics | null;
  watchlistStats: WatchlistStatistics | null;
  analyticsStats: AnalyticsStatistics | null;
  statsBarData: StatsBarData | null;
  profileStats: ProfileStatistics | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
  refreshCache: () => Promise<void>;
}

const defaultBadgeData: BadgeData = {
  picks_tab: {
    total_picks_today: 0,
    bullish_count: 0,
    bearish_count: 0,
    high_confidence_count: 0,
    avg_confidence: 0,
    week_win_rate: 0,
  },
  watchlist_tab: {
    total_stocks: 0,
    winners: 0,
    losers: 0,
    avg_performance: 0,
    total_return_dollars: 0,
    best_performer: null,
    worst_performer: null,
  },
  analytics_tab: {
    model_accuracy: 0,
    total_predictions: 0,
    bullish_accuracy: 0,
    bearish_accuracy: 0,
    high_confidence_accuracy: 0,
    precision: 0,
    recall: 0,
    f1_score: 0,
  },
  stats_bar: {
    daily_scans: 0,
    alert_rate: 0,
    bullish_win_rate: 0,
    bearish_win_rate: 0,
  },
  profile: {
    total_picks_month: 0,
    win_rate_month: 0,
    avg_days_to_target: 0,
    closed_positions: 0,
    closed_win_rate: 0,
  },
};

interface StatisticsState {
  badgeData: BadgeData | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastUpdated: Date | null;
  initialized: boolean;
}

type StatisticsAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_REFRESHING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_BADGE_DATA'; payload: BadgeData }
  | { type: 'SET_LAST_UPDATED'; payload: Date }
  | { type: 'SET_INITIALIZED'; payload: boolean }
  | { type: 'RESET' };

const initialState: StatisticsState = {
  badgeData: null,
  isLoading: true,
  isRefreshing: false,
  error: null,
  lastUpdated: null,
  initialized: false,
};

function statisticsReducer(state: StatisticsState, action: StatisticsAction): StatisticsState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_REFRESHING':
      return { ...state, isRefreshing: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_BADGE_DATA':
      return { ...state, badgeData: action.payload, isLoading: false, error: null };
    case 'SET_LAST_UPDATED':
      return { ...state, lastUpdated: action.payload };
    case 'SET_INITIALIZED':
      return { ...state, initialized: action.payload };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useStatistics(options: UseStatisticsOptions = {}): UseStatisticsReturn {
  const {
    refreshInterval = 300000,
    enabled = true,
    autoRefresh = true,
  } = options;

  const [state, dispatch] = useReducer(statisticsReducer, initialState);

  const fetchBadgeData = useCallback(
    async (isRefresh = false) => {
      if (!enabled) return;

      try {
        if (isRefresh) {
          dispatch({ type: 'SET_REFRESHING', payload: true });
        } else {
          dispatch({ type: 'SET_LOADING', payload: true });
        }
        dispatch({ type: 'SET_ERROR', payload: null });

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/statistics/badge-data`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        if (data?.status === 'success' && data?.data) {
          dispatch({ type: 'SET_BADGE_DATA', payload: data.data });
          dispatch({ type: 'SET_LAST_UPDATED', payload: new Date() });
        } else {
          throw new Error('Invalid response');
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to fetch';
        dispatch({ type: 'SET_ERROR', payload: msg });
        dispatch({ type: 'SET_BADGE_DATA', payload: defaultBadgeData });
        dispatch({ type: 'SET_LAST_UPDATED', payload: new Date() });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
        dispatch({ type: 'SET_REFRESHING', payload: false });
      }
    },
    [enabled]
  );

  const refresh = useCallback(() => fetchBadgeData(true), [fetchBadgeData]);

  const refreshCache = useCallback(async () => {
    try {
      dispatch({ type: 'SET_REFRESHING', payload: true });
      await api.refreshStatsCache?.();
      await refresh();
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: 'Cache refresh failed' });
    } finally {
      dispatch({ type: 'SET_REFRESHING', payload: false });
    }
  }, [refresh]);

  useEffect(() => {
    if (!state.initialized && enabled) {
      dispatch({ type: 'SET_INITIALIZED', payload: true });
      fetchBadgeData();
    }
  }, [state.initialized, enabled, fetchBadgeData]);

  useEffect(() => {
    if (!autoRefresh || !enabled || refreshInterval <= 0) return;
    const id = setInterval(() => fetchBadgeData(true), refreshInterval);
    return () => clearInterval(id);
  }, [autoRefresh, enabled, refreshInterval, fetchBadgeData]);

  const picksStats = state.badgeData?.picks_tab ?? null;
  const watchlistStats = state.badgeData?.watchlist_tab ?? null;
  const analyticsStats = state.badgeData?.analytics_tab ?? null;
  const statsBarData = state.badgeData?.stats_bar ?? null;
  const profileStats = state.badgeData?.profile ?? null;

  return {
    badgeData: state.badgeData,
    picksStats,
    watchlistStats,
    analyticsStats,
    statsBarData,
    profileStats,
    isLoading: state.isLoading,
    isRefreshing: state.isRefreshing,
    error: state.error,
    lastUpdated: state.lastUpdated,
    refresh,
    refreshCache,
  };
}

// Utility hooks
export function usePicksStatistics(options?: UseStatisticsOptions) {
  const { picksStats, isLoading, error, refresh } = useStatistics(options);
  return { picksStats, isLoading, error, refresh };
}

export function useWatchlistStatistics(options?: UseStatisticsOptions) {
  const { watchlistStats, isLoading, error, refresh } = useStatistics(options);
  return { watchlistStats, isLoading, error, refresh };
}

export function useAnalyticsStatistics(options?: UseStatisticsOptions) {
  const { analyticsStats, isLoading, error, refresh } = useStatistics(options);
  return { analyticsStats, isLoading, error, refresh };
}

export function useStatsBarData(options?: UseStatisticsOptions) {
  const { statsBarData, isLoading, error, refresh } = useStatistics(options);
  return { statsBarData, isLoading, error, refresh };
}