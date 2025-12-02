// src/lib/api.ts
import { HistoryEntry, WatchlistNotification } from './types';
import { getAuth } from 'firebase/auth';

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

// Get Firebase auth token for authenticated requests
const getAuthToken = async (): Promise<string | null> => {
  try {
    const auth = getAuth();
    const user = auth.currentUser;
    if (user) {
      return await user.getIdToken();
    }
    return null;
  } catch (error) {
    console.error('Failed to get auth token:', error);
    return null;
  }
};

const fetchWithError = async (url: string, options: RequestInit = {}, requireAuth = false) => {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    // Add auth token if required
    if (requireAuth) {
      const token = await getAuthToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers,
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
    sentiment?: 'bullish' | 'bearish';
    limit?: number;
    min_confidence?: number;
    period?: 'today' | '7d' | 'all' | 'active';
    outcome?: 'wins' | 'losses';
  }): Promise<any[]> => {
    const queryParams = new URLSearchParams();
    if (params.sentiment) queryParams.append('sentiment', params.sentiment);
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.min_confidence !== undefined) queryParams.append('min_confidence', params.min_confidence.toString());
    if (params.period) queryParams.append('period', params.period);
    if (params.outcome) queryParams.append('outcome', params.outcome);

    return fetchWithError(`/api/v1/picks/live?${queryParams.toString()}`);
  },

  // WATCHLIST (requires auth)
  getWatchlistEntries: async (): Promise<HistoryEntry[]> => {
    return fetchWithError('/api/v1/watchlist', {}, true);
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
    return fetchWithError('/api/v1/watchlist', {
      method: 'POST',
      body: JSON.stringify(request),
    }, true);
  },

  removeFromWatchlist: async (symbol: string) => {
    return fetchWithError(`/api/v1/watchlist/${symbol}`, {
      method: 'DELETE',
    }, true);
  },

  // NOTIFICATIONS (requires auth)
  getWatchlistNotifications: async (): Promise<WatchlistNotification[]> => {
    return fetchWithError('/api/v1/watchlist/notifications', {}, true);
  },

  // HISTORY
  getHistory: async (): Promise<HistoryEntry[]> => {
    return fetchWithError('/api/v1/history');
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

  // REAL-TIME QUOTES (FMP)
  getQuotes: async (symbols: string[]): Promise<Record<string, { price: number; change?: number; changePercent?: number }>> => {
    if (symbols.length === 0) return {};
    const symbolsStr = symbols.join(',');
    const data = await fetchWithError(`/api/v1/quotes?symbols=${encodeURIComponent(symbolsStr)}`);
    return data || {};
  },
};