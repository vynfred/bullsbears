// src/lib/api.ts
import { HistoryEntry, WatchlistNotification } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// AI vs Watchlist Performance type
export interface AIVsWatchlistPerformance {
  ai_performance: {
    average_return_percent: number;
    win_rate: number;
    total_picks: number;
    best_pick_return: number;
    worst_pick_return: number;
  };
  watchlist_performance: {
    average_return_percent: number;
    win_rate: number;
    total_picks: number;
    closed_entries: number;
    best_pick_return: number;
    worst_pick_return: number;
  };
  comparison: {
    better_performer: 'ai' | 'watchlist' | 'tie';
    performance_advantage_percent: number;
  };
  comparison_period_days: number;
  ai_picks_count: number;
  watchlist_picks_count: number;
  period: string;
}

const fetchWithError = async (url: string, options: RequestInit = {}) => {
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || `HTTP ${res.status}`);
    }

    return res.json();
  } catch (error) {
    // Silently fail when backend is offline - don't spam console
    // The hooks will handle the error state and show empty UI
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      // Backend is offline - this is expected during development
      return null;
    }
    throw error;
  }
};

export const api = {
  // Generic GET method for useRealData hooks
  get: async (endpoint: string) => {
    return fetchWithError(endpoint);
  },

  // Generic POST method
  post: async (endpoint: string, data?: any) => {
    return fetchWithError(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  // LIVE PICKS
  getLivePicks: async (params: {
    sentiment: 'bullish' | 'bearish';
    limit: number;
    min_confidence: number;
  }): Promise<any[]> => {
    const { sentiment, limit, min_confidence } = params;
    return fetchWithError(
      `/picks/live?sentiment=${sentiment}&limit=${limit}&min_confidence=${min_confidence}`
    );
  },

  // WATCHLIST
  getWatchlistEntries: async (): Promise<HistoryEntry[]> => {
    return fetchWithError('/watchlist');
  },

  addToWatchlist: async (request: {
    symbol: string;
    name?: string;
    entry_type: string;
    entry_price: number;
    target_price: number;
    ai_confidence_score: number;
    ai_recommendation: string;
  }) => {
    return fetchWithError('/watchlist', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // NOTIFICATIONS
  getWatchlistNotifications: async (): Promise<WatchlistNotification[]> => {
    return fetchWithError('/watchlist/notifications');
  },

  // HISTORY
  getHistory: async (): Promise<HistoryEntry[]> => {
    return fetchWithError('/history');
  },

  // STATS
  getStatistics: async () => {
    return fetchWithError('/api/v1/statistics/badge-data');
  },

  // CACHE REFRESH
  refreshStatsCache: async () => {
    await fetchWithError('/api/v1/statistics/refresh-cache', { method: 'POST' });
  },

  // AI VS WATCHLIST PERFORMANCE
  getAIVsWatchlistPerformance: async (days: number = 30): Promise<AIVsWatchlistPerformance> => {
    return fetchWithError(`/api/v1/analytics/ai-vs-watchlist?days=${days}`);
  },

  // LIVE ALERTS
  getBullishAlerts: async (limit: number = 10) => {
    return fetchWithError(`/api/v1/alerts/bullish?limit=${limit}`);
  },

  getBearishAlerts: async (limit: number = 10) => {
    return fetchWithError(`/api/v1/alerts/bearish?limit=${limit}`);
  },
};