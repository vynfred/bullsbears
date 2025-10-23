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
  max_plays?: number;
  min_confidence?: number;
  timeframe_days?: number;
  position_size?: number;
  risk_tolerance?: 'LOW' | 'MODERATE' | 'HIGH';
  directional_bias?: 'BULLISH' | 'BEARISH' | 'AI_DECIDES';
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
  }
};

export default api;
