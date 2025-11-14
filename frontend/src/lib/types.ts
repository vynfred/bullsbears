// Real data types for BullsBears API integration
// Replaces demoData.ts with actual API response types

// src/lib/types.ts
export interface StockPick {
  id: string;
  symbol: string;
  company_name: string;
  entry_price: number;
  current_price: number;
  change: number;
  confidence: number;
  reasons: string[];
  entry_price_min: number;
  entry_price_max: number;
  target_price_low: number;
  target_price_mid: number;
  target_price_high: number;
  stop_loss: number;
  ai_summary: string;
  sentiment: 'bullish' | 'bearish';
  timestamp: string;
  target_hit?: 'low' | 'midedora' | 'high';
  time_to_target_hours?: number;
}
export interface HistoryEntry {
  id: string;
  ticker: string;
  company_name: string;
  entry_price: number;
  current_price: number;
  actual_percent: number;
  days_to_hit: number;
  ai_confidence: number;
  target_percent: number;
  classification: 'MOON' | 'PARTIAL_MOON' | 'WIN' | 'MISS' | 'RUG' | 'NUCLEAR_RUG';
  call_time: string;
  outcome: 'win' | 'loss' | 'partial' | 'pending';
}

export interface WatchlistNotification {
  id: string;
  type: 'target_hit' | 'stop_loss_hit' | 'performance_milestone';
  severity: 'low' | 'medium' | 'high';
  title: string;
  message: string;
  gain_percent: number;
  current_price: number;
  metadata: { days_held: number };
  timestamp: string;
}

export interface WatchlistStock {
  id: string;
  symbol: string;
  name: string;
  added_price: number;
  current_price: number;
  change_percent: number;
  target_low?: number;
  target_mid?: number;
  target_high?: number;
  stop_loss?: number;
  notes?: string;
  added_at: string;
  performance_data?: Array<{
    date: string;
    price: number;
    change_percent: number;
  }>;
}

export interface AccuracyTrendPoint {
  date: string;
  accuracy: number;
  total_picks: number;
  bullish_accuracy: number;
  bearish_accuracy: number;
  high_confidence_accuracy: number;
}

export interface RecentPickOutcome {
  id: string;
  symbol: string;
  sentiment: 'bullish' | 'bearish';
  confidence: number;
  outcome: 'win' | 'loss' | 'partial';
  change_percent: number;
  days_to_outcome: number;
  created_at: string;
}

export interface ModelAccuracyStats {
  overall_accuracy: number;
  total_predictions: number;
  bullish_accuracy: number;
  bearish_accuracy: number;
  high_confidence_accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy_trend: AccuracyTrendPoint[];
}

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
  best_performer: {
    symbol: string;
    change_percent: number;
  } | null;
  worst_performer: {
    symbol: string;
    change_percent: number;
  } | null;
}

export interface BadgeData {
  picks_tab: PicksStatistics;
  watchlist_tab: WatchlistStatistics;
  analytics_tab: ModelAccuracyStats;
  stats_bar: {
    daily_scans: number;
    alert_rate: number;
    bullish_win_rate: number;
    bearish_win_rate: number;
  };
  profile: {
    total_picks_month: number;
    win_rate_month: number;
    avg_days_to_target: number;
    closed_positions: number;
    closed_win_rate: number;
  };
}

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data: T;
  message?: string;
  timestamp: string;
}

