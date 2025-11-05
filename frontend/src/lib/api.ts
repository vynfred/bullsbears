/**
 * API client for connecting to the FastAPI backend
 */
import axios from 'axios';

// API base URL - connects to FastAPI backend
const API_BASE_URL = 'http://127.0.0.1:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes timeout for AI generation (free APIs are slow)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging (reduced verbosity)
apiClient.interceptors.request.use(
  (config) => {
    // Only log non-health check requests to reduce console spam
    if (!config.url?.includes('/health')) {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // Only log non-health check responses to reduce console spam
    if (!response.config.url?.includes('/health')) {
      console.log(`API Response: ${response.status} ${response.config.url}`);
    }
    return response;
  },
  (error) => {
    // Only log errors that aren't network connection issues to reduce console spam
    if (error.code !== 'ERR_NETWORK' && error.message !== 'Network Error') {
      console.error('API Response Error:', error.response?.data || error instanceof Error ? error.message : String(error));
    }
    return Promise.reject(error);
  }
);

// Types for API responses
export interface AnalysisResult {
  success: boolean;
  data: {
    symbol: string;
    timestamp: string;
    confidence_score: number;
    confidence_level: 'LOW' | 'MEDIUM' | 'HIGH';
    recommendation: 'STRONG_BUY' | 'BUY' | 'WEAK_BUY' | 'HOLD' | 'WEAK_SELL' | 'SELL' | 'STRONG_SELL';
    recommendation_strength: number;
    current_price: number;
    technical_analysis: {
      technical_score: number;
      signals: {
        overall_signal: string;
        rsi_signal: string;
        macd_signal: string;
        ma_signal: string;
        volume_signal: string;
        bb_signal: string;
      };
      indicators: {
        rsi: number;
        macd: {
          macd: number;
          signal: number;
          histogram: number;
        };
        bollinger_bands: {
          upper: number;
          middle: number;
          lower: number;
        };
        moving_averages: {
          sma_20: number;
          sma_50: number;
          sma_200: number;
          ema_20: number;
          ema_50: number;
        };
        volume_analysis: {
          avg_volume: number;
          current_volume: number;
          volume_ratio: number;
        };
        support_resistance: {
          support: number;
          resistance: number;
        };
      };
    };
    news_analysis: {
      news_score: number;
      sentiment_analysis: {
        overall_sentiment: string;
        sentiment_score: number;
        confidence: number;
        positive_articles: number;
        negative_articles: number;
        neutral_articles: number;
      };
    };
    social_analysis: {
      social_score: number;
      sentiment_analysis: {
        overall_sentiment: string;
        sentiment_score: number;
        confidence: number;
        total_posts: number;
        platform_breakdown: {
          twitter?: { sentiment: number; posts: number };
          reddit?: { sentiment: number; posts: number };
          stocktwits?: { sentiment: number; posts: number };
        };
      };
    };
    risk_assessment: {
      risk_level: 'low' | 'medium' | 'high';
      downside_risk_percent: number;
      upside_potential_percent: number;
      risk_reward_ratio: number;
      max_position_size_percent: number;
      stop_loss_price: number;
      take_profit_price: number;
      volatility_assessment: string;
      time_horizon: string;
    };
    analysis_summary: string;
  };
  disclaimer: string;
}

export interface OptionsData {
  success: boolean;
  data: {
    symbol: string;
    timestamp: string;
    expiration_date: string;
    available_expirations: string[];
    options_chain: {
      calls: OptionContract[];
      puts: OptionContract[];
    };
    unusual_activity: {
      has_unusual_activity: boolean;
      unusual_options: UnusualOption[];
      average_volume: number;
      average_open_interest: number;
    };
    recommendations: {
      strategies: OptionStrategy[];
      risk_warning: string;
      unusual_activity_note?: string;
    };
    stock_context: {
      current_price: number;
      recommendation: string;
      confidence_level: string;
    };
  };
  disclaimer: string;
}

export interface UnusualOptionsActivity {
  success: boolean;
  data: {
    timestamp: string;
    time_range: string;
    filter_criteria: {
      min_volume_ratio: number;
      min_premium: number;
      symbols_analyzed: number;
    };
    ai_summary: {
      summary: string;
      key_trends: string[];
      market_sentiment: string;
      confidence: number;
      last_updated: string;
    };
    unusual_options: UnusualOptionContract[];
    large_trades: LargeOptionTrade[];
    sector_activity: Record<string, SectorActivity>;
    market_metrics: {
      total_unusual_contracts: number;
      total_large_trades: number;
      total_premium_flow: number;
      call_put_ratio: number;
    };
  };
  disclaimer: string;
}

export interface UnusualOptionContract {
  symbol: string;
  contract_symbol: string;
  option_type: string;
  strike: number;
  expiration: string;
  volume: number;
  open_interest: number;
  volume_oi_ratio: number;
  last_price: number;
  premium_value: number;
  timestamp: string;
}

export interface LargeOptionTrade {
  symbol: string;
  contract_symbol: string;
  option_type: string;
  strike: number;
  premium_value: number;
  volume: number;
  last_price: number;
  timestamp: string;
}

export interface SectorActivity {
  call_volume: number;
  put_volume: number;
  total_premium: number;
}

export interface OptionContract {
  strike: number;
  option_type: 'CALL' | 'PUT';
  last_price: number;
  bid: number;
  ask: number;
  volume: number;
  open_interest: number;
  implied_volatility: number;
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  rho?: number;
}

export interface UnusualOption {
  strike: number;
  option_type: 'CALL' | 'PUT';
  volume: number;
  open_interest: number;
  last_price: number;
  implied_volatility: number;
}

export interface OptionStrategy {
  strategy: string;
  option_type: 'CALL' | 'PUT';
  strike: number;
  rationale: string;
  max_risk: number;
  breakeven: number;
}

export interface SentimentData {
  success: boolean;
  data: {
    symbol: string;
    timestamp: string;
    news_sentiment: {
      overall_sentiment: string;
      sentiment_score: number;
      confidence: number;
      article_breakdown: {
        total_articles: number;
        positive_articles: number;
        negative_articles: number;
        neutral_articles: number;
      };
      sources: string[];
    };
    social_sentiment: {
      overall_sentiment: string;
      sentiment_score: number;
      confidence: number;
      platform_breakdown: Record<string, unknown>;
      total_posts: number;
    };
    combined_sentiment: {
      news_weight: number;
      social_weight: number;
      weighted_score: number;
    };
  };
  disclaimer: string;
}

// AI Option Play Generation Types
export interface AIOptionPlay {
  symbol: string;
  company_name: string;
  option_type: string;
  strike: number;
  expiration: string;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  probability_profit: number;
  max_profit: number;
  max_loss: number;
  risk_reward_ratio: number;
  position_size: number;
  confidence_score: number;
  technical_score: number;
  news_sentiment: number;
  catalyst_impact: number;
  volume_score: number;
  ai_recommendation: string;
  ai_confidence: number;
  risk_warning?: string;
  summary: string;
  key_factors: string[];
  catalysts: any[];
  volume_alerts: any[];
  polymarket_events: any[];
  generated_at: string;
  expires_at: string;
}

export interface GeneratePlaysParams {
  symbol?: string;
  max_plays?: number;
  min_confidence?: number;
  timeframe_days?: number;
  position_size?: number;
  risk_tolerance?: 'LOW' | 'MODERATE' | 'HIGH';
  directional_bias?: 'BULLISH' | 'BEARISH' | 'AI_DECIDES';
  // Advanced settings
  insight_style?: string;
  iv_threshold?: number;
  earnings_alert?: boolean;
  shares_owned?: Record<string, number>;
}

export interface GeneratePlaysResponse {
  success: boolean;
  plays: AIOptionPlay[];
  count: number;
  parameters: GeneratePlaysParams;
  generated_at: string;
  error?: string;
  rate_limit_exceeded?: boolean;
  rate_limit_info?: {
    current_usage: number;
    daily_limit: number;
    remaining: number;
  };
}

export interface RateLimitStatus {
  current_usage: number;
  daily_limit: number;
  remaining: number;
  resets_in_seconds: number;
  reset_time_est: string;
  can_generate: boolean;
}

export interface UserPreferences {
  user_id: string;
  risk_tolerance: string;
  max_position_size: number;
  preferred_expiration_days: number;
  min_confidence_threshold: number;
  shares_owned: Record<string, number>;
  iv_threshold: number;
  earnings_alert: boolean;
  insight_style: string;
  theme: string;
  show_greeks: boolean;
  show_technical_indicators: boolean;
  watchlist_symbols: string[];
}

// Watchlist interfaces
export interface WatchlistEntry {
  id: number;
  symbol: string;
  company_name?: string;
  entry_type: string; // 'STOCK', 'OPTION_CALL', 'OPTION_PUT'
  entry_price: number;
  target_price: number;
  stop_loss_price?: number;
  current_price?: number;
  current_return_percent?: number;
  current_return_dollars?: number;
  ai_confidence_score: number;
  ai_recommendation: string;
  status: string; // 'ACTIVE', 'CLOSED', 'EXPIRED'
  is_winner?: boolean;
  days_held: number;
  entry_date: string;
  last_price_update?: string;
  strike_price?: number;
  expiration_date?: string;
  // Exit details (when trade is closed)
  exit_price?: number;
  exit_date?: string;
  exit_reason?: string;
  final_return_percent?: number;
  final_return_dollars?: number;
}

export interface AddToWatchlistRequest {
  symbol: string;
  company_name?: string;
  entry_type: string;
  entry_price: number;
  target_price: number;
  stop_loss_price?: number;
  ai_confidence_score: number;
  ai_recommendation: string;
  ai_reasoning?: string;
  ai_key_factors?: string[];
  position_size_dollars?: number;
  strike_price?: number;
  expiration_date?: string;
  option_contract_symbol?: string;
}

export interface UpdateWatchlistEntryRequest {
  entry_price?: number;
  target_price?: number;
  stop_loss_price?: number;
  ai_confidence_score?: number;
  ai_recommendation?: string;
  ai_reasoning?: string;
  ai_key_factors?: string[];
  position_size_dollars?: number;
  status?: string;
  exit_price?: number;
  exit_reason?: string;
}

export interface BulkWatchlistOperation {
  operation: string; // 'delete', 'close', 'update_status'
  entry_ids: number[];
  new_status?: string;
  exit_reason?: string;
}

export interface WatchlistPerformanceMetrics {
  total_trades: number;
  active_trades: number;
  closed_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  average_return: number;
  total_return: number;
  best_trade_return: number;
  worst_trade_return: number;
  high_confidence_accuracy: number;
  medium_confidence_accuracy: number;
  low_confidence_accuracy: number;
  stock_win_rate: number;
  option_win_rate: number;
}

export interface AIVsWatchlistPerformance {
  comparison_period_days: number;
  ai_performance: {
    total_picks: number;
    bullish_picks: number;
    bearish_picks: number;
    average_return_percent: number;
    win_rate: number;
    best_pick_return: number;
    worst_pick_return: number;
    top_picks: Array<{
      symbol: string;
      confidence: number;
      alert_type: string;
      timestamp: string;
    }>;
  };
  watchlist_performance: {
    total_entries: number;
    active_entries: number;
    closed_entries: number;
    average_return_percent: number;
    win_rate: number;
    best_pick_return: number;
    worst_pick_return: number;
    top_picks: Array<{
      symbol: string;
      entry_price: number;
      exit_price: number;
      return_percent: number;
      days_held: number;
      ai_confidence: number;
    }>;
  };
  comparison: {
    performance_advantage_percent: number;
    win_rate_advantage: number;
    better_performer: 'watchlist' | 'ai';
    advantage_magnitude: number;
    insights: string[];
  };
}

export interface RiskProfileStrategy {
  name: string;
  description: string;
  risk_level: string;
  max_loss: string;
  profit_potential: string;
  delta_range?: string;
  theta_focus: boolean;
  vega_sensitivity: string;
}

export interface RiskProfileInfo {
  description: {
    name: string;
    description: string;
    characteristics: string;
    max_risk_per_trade: string;
    preferred_strategies: string;
  };
  strategies: {
    bullish: RiskProfileStrategy[];
    bearish: RiskProfileStrategy[];
    neutral: RiskProfileStrategy[];
  };
  sizing_rules: {
    max_risk_per_trade: number;
    max_portfolio_allocation: number;
    preferred_win_rate: number;
    max_dte: number;
    profit_target: number;
    stop_loss: number;
  };
}

// API functions
export const api = {
  /**
   * Analyze a stock symbol
   */
  analyzeStock: async (symbol: string, companyName?: string): Promise<AnalysisResult> => {
    const params = companyName ? { company_name: companyName } : {};
    const response = await apiClient.get(`/api/v1/analyze/${symbol.toUpperCase()}`, { params });
    return response.data;
  },

  /**
   * Get options chain and analysis
   */
  getOptionsData: async (symbol: string, expirationDate?: string): Promise<OptionsData> => {
    const params = expirationDate ? { expiration_date: expirationDate } : {};
    const response = await apiClient.get(`/api/v1/options/${symbol.toUpperCase()}`, { params });
    return response.data;
  },

  /**
   * Get unusual options activity across all symbols
   */
  getUnusualOptionsActivity: async (
    limit?: number,
    minVolumeRatio?: number,
    minPremium?: number,
    timeRange?: string
  ): Promise<UnusualOptionsActivity> => {
    const params: any = {};
    if (limit) params.limit = limit;
    if (minVolumeRatio) params.min_volume_ratio = minVolumeRatio;
    if (minPremium) params.min_premium = minPremium;
    if (timeRange) params.time_range = timeRange;

    const response = await apiClient.get('/api/v1/unusual-options', { params });
    return response.data;
  },

  /**
   * Get detailed sentiment breakdown
   */
  getSentimentData: async (symbol: string, companyName?: string): Promise<SentimentData> => {
    const params = companyName ? { company_name: companyName } : {};
    const response = await apiClient.get(`/api/v1/sentiment/${symbol.toUpperCase()}`, { params });
    return response.data;
  },

  /**
   * Get daily recommendations
   */
  getDailyRecommendations: async (limit = 10, minConfidence = 'MEDIUM') => {
    const response = await apiClient.get('/api/v1/recommendations/daily', {
      params: { limit, min_confidence: minConfidence }
    });
    return response.data;
  },

  /**
   * Check if backend is healthy
   */
  healthCheck: async (): Promise<boolean> => {
    try {
      const response = await apiClient.get('/health');
      return response.status === 200;
    } catch (error) {
      // Don't log network errors to reduce console spam
      if (error instanceof Error && error.message !== 'Network Error') {
        console.error('Backend health check failed:', error);
      }
      return false;
    }
  },

  /**
   * Generate AI-powered option plays
   */
  generateOptionPlays: async (params: GeneratePlaysParams = {}): Promise<GeneratePlaysResponse> => {
    try {
      const response = await apiClient.post('/api/v1/generate-plays', null, {
        params,
        timeout: 180000 // 3 minutes for AI generation specifically
      });
      return response.data;
    } catch (error: unknown) {
      // Handle timeout and other errors gracefully
      if (error instanceof Error && (error as { code?: string; message?: string }).code === 'ECONNABORTED' || error instanceof Error ? error.message : String(error)?.includes('timeout')) {
        throw new Error('AI generation is taking longer than expected. This may be due to API rate limits. Please try again in a few minutes.');
      }
      throw error;
    }
  },

  /**
   * Get current rate limit status
   */
  getRateLimitStatus: async (): Promise<RateLimitStatus> => {
    const response = await apiClient.get('/api/v1/rate-limit-status');
    return response.data;
  },

  /**
   * Get configuration health status - DISABLED to prevent API spam
   */
  getConfigurationHealth: async () => {
    // Temporarily disabled to prevent excessive API calls
    return {
      status: "unknown",
      status_color: "yellow",
      demo_mode: true,
      critical_apis: { configured: 0, total: 2, apis: {} },
      optional_apis: { configured: 0, total: 4, apis: {} },
      timestamp: Date.now()
    };
  },

  // Stock OHLC data for charts
  async fetchStockOHLC(symbol: string, period: string = '1y', interval: string = '1d') {
    try {
      const response = await apiClient.get(`/api/v1/stock/${symbol}/ohlc`, {
        params: { period, interval }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching OHLC data:', error);
      throw error;
    }
  },

  // User Preferences API
  async getUserPreferences(userId: string): Promise<{ success: boolean; data: UserPreferences; message: string }> {
    try {
      const response = await apiClient.get(`/api/v1/preferences/${userId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching user preferences:', error);
      throw error;
    }
  },

  // AI Options Review API - New user-driven options analysis system
  async validateStockSymbol(symbol: string): Promise<{ success: boolean; symbol: string; company_name?: string; current_price?: number; is_valid: boolean; error_message?: string }> {
    try {
      const response = await apiClient.post('/api/v1/options-review/validate-symbol', { symbol });
      return response.data;
    } catch (error) {
      console.error('Error validating stock symbol:', error);
      throw error;
    }
  },

  async getExpirationDates(symbol: string): Promise<{ success: boolean; symbol: string; expirations: any[]; error_message?: string }> {
    try {
      const response = await apiClient.get(`/api/v1/options-review/expirations/${symbol}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching expiration dates:', error);
      throw error;
    }
  },

  async analyzeOptionsStrategy(params: {
    symbol: string;
    expiration_date: string;
    strategy_type: string;
    max_position_size: number;
    shares_owned?: number;
    account_size?: number;
  }): Promise<{ success: boolean; symbol: string; strategy_type: string; analysis: any; recommendations: any[]; risk_analysis: any; interactive_data: any; disclaimer: string; error_message?: string }> {
    try {
      const response = await apiClient.post('/api/v1/options-review/analyze', params, {
        timeout: 180000 // 3 minutes for AI analysis
      });
      return response.data;
    } catch (error) {
      console.error('Error analyzing options strategy:', error);
      throw error;
    }
  },

  // Bullish/Bearish Alert APIs
  /**
   * Get latest bullish alerts for dashboard
   */
  getBullishAlerts: async (limit: number = 10): Promise<BullishAlert[]> => {
    try {
      const response = await apiClient.get(`/api/v1/bullish_alerts/latest?limit=${limit}`);
      return response.data.map(transformBullishAlertResponse);
    } catch (error) {
      console.error('Error fetching bullish alerts:', error);
      throw error;
    }
  },

  /**
   * Get latest bearish alerts for dashboard
   */
  getBearishAlerts: async (limit: number = 10): Promise<BullishAlert[]> => {
    try {
      const response = await apiClient.get(`/api/v1/bearish_alerts/latest?limit=${limit}`);
      return response.data.map(transformBearishAlertResponse);
    } catch (error) {
      console.error('Error fetching bearish alerts:', error);
      throw error;
    }
  },

  // Legacy aliases for backward compatibility
  getMoonAlerts: async (limit: number = 10): Promise<BullishAlert[]> => {
    return api.getBullishAlerts(limit);
  },

  getRugAlerts: async (limit: number = 10): Promise<BullishAlert[]> => {
    return api.getBearishAlerts(limit);
  },

  /**
   * Get all alerts (bullish + bearish) for dashboard
   */
  getAllAlerts: async (bullishLimit: number = 10, bearishLimit: number = 10): Promise<BullishAlert[]> => {
    try {
      const [bullishAlerts, bearishAlerts] = await Promise.all([
        api.getBullishAlerts(bullishLimit),
        api.getBearishAlerts(bearishLimit)
      ]);

      // Combine and sort by timestamp (newest first)
      const allAlerts = [...bullishAlerts, ...bearishAlerts];
      return allAlerts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    } catch (error) {
      console.error('Error fetching all alerts:', error);
      throw error;
    }
  },

  /**
   * Analyze symbol for bullish potential
   */
  analyzeBullishPotential: async (symbol: string, companyName?: string): Promise<BullishAlert> => {
    try {
      const response = await apiClient.post('/api/v1/bullish_alerts/analyze', {
        symbol: symbol.toUpperCase(),
        company_name: companyName
      });
      return transformBullishAlertResponse(response.data);
    } catch (error) {
      console.error('Error analyzing bullish potential:', error);
      throw error;
    }
  },

  /**
   * Analyze symbol for bearish potential
   */
  analyzeBearishPotential: async (symbol: string, companyName?: string): Promise<BullishAlert> => {
    try {
      const response = await apiClient.post('/api/v1/bearish_alerts/analyze', {
        symbol: symbol.toUpperCase(),
        company_name: companyName
      });
      return transformBearishAlertResponse(response.data);
    } catch (error) {
      console.error('Error analyzing bearish potential:', error);
      throw error;
    }
  },

  // Legacy aliases for backward compatibility
  analyzeMoonPotential: async (symbol: string, companyName?: string): Promise<BullishAlert> => {
    return api.analyzeBullishPotential(symbol, companyName);
  },

  analyzeRugPotential: async (symbol: string, companyName?: string): Promise<BullishAlert> => {
    return api.analyzeBearishPotential(symbol, companyName);
  },

  // Gut Check APIs
  /**
   * Get pending anonymous alerts for gut check voting
   */
  getPendingGutCheckAlerts: async (userId: string, limit: number = 10): Promise<AnonymousAlert[]> => {
    try {
      const response = await apiClient.get(`/api/v1/gut-check/pending/${userId}?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching pending gut check alerts:', error);
      throw error;
    }
  },

  /**
   * Submit gut check vote
   */
  submitGutCheckVote: async (userId: string, voteData: GutCheckVoteData): Promise<GutCheckVoteResponse> => {
    try {
      const response = await apiClient.post(`/api/v1/gut-check/vote/${userId}`, voteData);
      return response.data;
    } catch (error) {
      console.error('Error submitting gut check vote:', error);
      throw error;
    }
  },

  /**
   * Get user gut check statistics
   */
  getUserGutCheckStats: async (userId: string): Promise<UserGutStats> => {
    try {
      const response = await apiClient.get(`/api/v1/gut-check/stats/${userId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching user gut check stats:', error);
      throw error;
    }
  },

  /**
   * Complete gut check session and reveal actual symbols
   */
  completeGutCheckSession: async (userId: string, sessionId: string): Promise<GutCheckSessionResult> => {
    try {
      const response = await apiClient.post(`/api/v1/gut-check/complete-session/${userId}`, {
        session_id: sessionId
      });
      return response.data;
    } catch (error) {
      console.error('Error completing gut check session:', error);
      throw error;
    }
  },

  /**
   * Generate new gut check session
   */
  generateGutCheckSession: async (userId: string, alertCount: number = 7): Promise<GutCheckSession> => {
    try {
      const response = await apiClient.post(`/api/v1/gut-check/generate-session/${userId}`, {
        alert_count: alertCount
      });
      return response.data;
    } catch (error) {
      console.error('Error generating gut check session:', error);
      throw error;
    }
  },

  async updateUserPreferences(userId: string, preferences: Partial<UserPreferences>): Promise<{ success: boolean; data: UserPreferences; message: string }> {
    try {
      const response = await apiClient.put(`/api/v1/preferences/${userId}`, preferences);
      return response.data;
    } catch (error) {
      console.error('Error updating user preferences:', error);
      throw error;
    }
  },

  async getRiskProfiles(): Promise<{ success: boolean; data: Record<string, RiskProfileInfo>; message: string }> {
    try {
      const response = await apiClient.get('/api/v1/risk-profiles');
      return response.data;
    } catch (error) {
      console.error('Error fetching risk profiles:', error);
      throw error;
    }
  },

  async updateSharesOwned(userId: string, sharesData: Record<string, number>): Promise<{ success: boolean; data: any; message: string }> {
    try {
      const response = await apiClient.post(`/api/v1/preferences/${userId}/shares`, sharesData);
      return response.data;
    } catch (error) {
      console.error('Error updating shares owned:', error);
      throw error;
    }
  },

  async getCoveredCallOpportunities(userId: string): Promise<{ success: boolean; data: any; message: string }> {
    try {
      const response = await apiClient.get(`/api/v1/preferences/${userId}/covered-calls`);
      return response.data;
    } catch (error) {
      console.error('Error fetching covered call opportunities:', error);
      throw error;
    }
  },

  async getDefaultPreferences(): Promise<{ success: boolean; data: Partial<UserPreferences>; message: string }> {
    try {
      const response = await apiClient.get('/api/v1/preferences/defaults');
      return response.data;
    } catch (error) {
      console.error('Error fetching default preferences:', error);
      throw error;
    }
  },

  // Watchlist API
  async addToWatchlist(request: AddToWatchlistRequest): Promise<{ success: boolean; message: string; watchlist_entry_id: number }> {
    try {
      const response = await apiClient.post('/api/v1/watchlist/add', request);
      return response.data;
    } catch (error) {
      console.error('Error adding to watchlist:', error);
      throw error;
    }
  },

  async getWatchlistEntries(status?: string, entryType?: string, limit?: number): Promise<WatchlistEntry[]> {
    try {
      const params: any = {};
      if (status) params.status = status;
      if (entryType) params.entry_type = entryType;
      if (limit) params.limit = limit;

      const response = await apiClient.get('/api/v1/watchlist/entries', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching watchlist entries:', error);
      throw error;
    }
  },

  async getWatchlistEntry(entryId: number): Promise<WatchlistEntry> {
    try {
      const response = await apiClient.get(`/api/v1/watchlist/entry/${entryId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching watchlist entry:', error);
      throw error;
    }
  },

  async updateWatchlistEntry(entryId: number, request: UpdateWatchlistEntryRequest): Promise<{ success: boolean; message: string }> {
    try {
      const response = await apiClient.put(`/api/v1/watchlist/entry/${entryId}`, request);
      return response.data;
    } catch (error) {
      console.error('Error updating watchlist entry:', error);
      throw error;
    }
  },

  async removeFromWatchlist(entryId: number): Promise<{ success: boolean; message: string }> {
    try {
      const response = await apiClient.delete(`/api/v1/watchlist/entry/${entryId}`);
      return response.data;
    } catch (error) {
      console.error('Error removing from watchlist:', error);
      throw error;
    }
  },

  async bulkWatchlistOperation(request: BulkWatchlistOperation): Promise<{ success: boolean; message: string; affected_count: number }> {
    try {
      const response = await apiClient.post('/api/v1/watchlist/bulk-operation', request);
      return response.data;
    } catch (error) {
      console.error('Error performing bulk watchlist operation:', error);
      throw error;
    }
  },

  async getWatchlistPerformance(days?: number): Promise<WatchlistPerformanceMetrics> {
    try {
      const params = days ? { days } : {};
      const response = await apiClient.get('/api/v1/watchlist/performance', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching watchlist performance:', error);
      throw error;
    }
  },

  async updateWatchlistPrices(): Promise<{ success: boolean; message: string; updated_count: number }> {
    try {
      const response = await apiClient.post('/api/v1/watchlist/update-prices');
      return response.data;
    } catch (error) {
      console.error('Error updating watchlist prices:', error);
      throw error;
    }
  },

  async getWatchlistSymbols(status?: string): Promise<string[]> {
    try {
      const params = status ? { status } : {};
      const response = await apiClient.get('/api/v1/watchlist/symbols', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching watchlist symbols:', error);
      throw error;
    }
  },

  async getWatchlistSummary(): Promise<any> {
    try {
      const response = await apiClient.get('/api/v1/watchlist/summary');
      return response.data;
    } catch (error) {
      console.error('Error fetching watchlist summary:', error);
      throw error;
    }
  },

  async getAIVsWatchlistPerformance(days?: number): Promise<AIVsWatchlistPerformance> {
    try {
      const params = days ? { days } : {};
      const response = await apiClient.get('/api/v1/watchlist/ai-vs-watchlist-performance', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching AI vs Watchlist performance:', error);
      throw error;
    }
  },

  // Notification functions
  async checkNotifications(): Promise<any[]> {
    try {
      console.log('🔔 Checking watchlist notifications...');
      const response = await apiClient.get('/api/v1/watchlist/notifications/check');
      console.log('📬 Notifications checked:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error checking notifications:', error);
      throw error;
    }
  },

  async getDailySummary(): Promise<any> {
    try {
      console.log('📊 Getting daily summary...');
      const response = await apiClient.get('/api/v1/watchlist/notifications/daily-summary');
      console.log('📈 Daily summary:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error getting daily summary:', error);
      throw error;
    }
  },

  async testNotifications(entryId: number): Promise<any> {
    try {
      console.log(`🧪 Testing notifications for entry ${entryId}...`);
      const response = await apiClient.post(`/api/v1/watchlist/notifications/test/${entryId}`);
      console.log('🧪 Test notifications result:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error testing notifications:', error);
      throw error;
    }
  }
};

// Type definitions for Bullish/Bearish alerts and Gut Check
export interface BullishAlert {
  id: string;
  randomId: number;
  ticker: string;
  companyName: string;
  confidence: number;
  topReason: string;
  targetRange: {
    low: number;
    avg: number;
    high: number;
    estimatedDays: number;
  };
  entryPrice: number;
  currentPrice: number;
  timestamp: Date;
  isNew?: boolean;
  type: 'bullish' | 'bearish';
  daysToTarget: number;
  gutVote?: 'BULLISH' | 'BEARISH' | 'PASS';
  finalConfidence?: number;
}

// Alias for backward compatibility during transition
export type MoonAlert = BullishAlert;

export interface AnonymousAlert {
  id: number;
  random_id: string;
  symbol: string;
  ml_confidence_bullish: number;
  ml_confidence_bearish: number;
  prediction_type: 'BULLISH' | 'BEARISH';
  target_price_range: string; // JSON string
  expires_at: string;
  created_at: string;
}

export interface GutCheckVoteData {
  anonymous_alert_id: number;
  vote: 'BULLISH' | 'BEARISH' | 'PASS';
  response_time_ms: number;
  confidence_level?: number;
  session_id: string;
  vote_order: number;
  total_session_votes: number;
}

export interface GutCheckVoteResponse {
  success: boolean;
  vote_id: number;
  updated_confidence: number;
  user_stats: UserGutStats;
}

export interface UserGutStats {
  user_id: string;
  total_votes: number;
  correct_votes: number;
  accuracy_rate: number;
  bullish_votes: number;
  bearish_votes: number;
  pass_votes: number;
  bullish_accuracy: number;
  bearish_accuracy: number;
  confidence_boost_factor: number;
  streak_current: number;
  streak_best: number;
  global_rank?: number;
  percentile?: number;
}

export interface GutCheckSessionResult {
  session_id: string;
  votes: Array<{
    vote: string;
    actual_symbol: string;
    was_correct: boolean;
    confidence_boost: number;
  }>;
  session_stats: {
    total_votes: number;
    correct_votes: number;
    accuracy_rate: number;
    average_response_time: number;
  };
  updated_user_stats: UserGutStats;
}

export interface GutCheckSession {
  session_id: string;
  alerts: AnonymousAlert[];
  expires_at: string;
}

// Transformation functions to convert backend responses to frontend types
function transformBullishAlertResponse(backendAlert: any): BullishAlert {
  const targetRange = backendAlert.target_price_range ?
    JSON.parse(backendAlert.target_price_range) :
    { low: 5, avg: 15, high: 25, estimatedDays: 2 };

  return {
    id: `bullish_${backendAlert.id}`,
    randomId: Math.floor(Math.random() * 900000) + 100000, // Generate 6-digit random ID
    ticker: backendAlert.symbol,
    companyName: backendAlert.company_name || backendAlert.symbol,
    confidence: Math.round(backendAlert.confidence),
    topReason: backendAlert.reasons?.[0] || 'Technical analysis indicates bullish momentum',
    targetRange: {
      low: targetRange.low || 5,
      avg: targetRange.avg || 15,
      high: targetRange.high || 25,
      estimatedDays: targetRange.estimatedDays || 2
    },
    entryPrice: backendAlert.entry_price || 100, // Will be updated with real price
    currentPrice: backendAlert.current_price || 100, // Will be updated with real price
    timestamp: new Date(backendAlert.timestamp),
    isNew: true,
    type: 'bullish',
    daysToTarget: targetRange.estimatedDays || 2,
    finalConfidence: backendAlert.confidence
  };
}

// Legacy alias for backward compatibility
const transformMoonAlertResponse = transformBullishAlertResponse;

function transformBearishAlertResponse(backendAlert: any): BullishAlert {
  const targetRange = backendAlert.target_price_range ?
    JSON.parse(backendAlert.target_price_range) :
    { low: -25, avg: -15, high: -5, estimatedDays: 2 };

  return {
    id: `bearish_${backendAlert.id}`,
    randomId: Math.floor(Math.random() * 900000) + 100000, // Generate 6-digit random ID
    ticker: backendAlert.symbol,
    companyName: backendAlert.company_name || backendAlert.symbol,
    confidence: Math.round(backendAlert.confidence),
    topReason: backendAlert.reasons?.[0] || 'Technical analysis indicates bearish momentum',
    targetRange: {
      low: targetRange.low || -25,
      avg: targetRange.avg || -15,
      high: targetRange.high || -5,
      estimatedDays: targetRange.estimatedDays || 2
    },
    entryPrice: backendAlert.entry_price || 100, // Will be updated with real price
    currentPrice: backendAlert.current_price || 100, // Will be updated with real price
    timestamp: new Date(backendAlert.timestamp),
    isNew: true,
    type: 'bearish',
    daysToTarget: targetRange.estimatedDays || 2,
    finalConfidence: backendAlert.confidence
  };
}

// Legacy alias for backward compatibility
const transformRugAlertResponse = transformBearishAlertResponse;

export default api;
