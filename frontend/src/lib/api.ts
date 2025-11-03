/**
 * API client for connecting to the FastAPI backend
 */
import axios from 'axios';

// API base URL - connects to FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

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
  }
};

export default api;
