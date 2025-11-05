'use client';

import React, { useState, useEffect } from 'react';
import { Search, Brain, TrendingUp, Shield, AlertTriangle, Target, DollarSign, Clock, Zap, BookmarkPlus, Share2 } from 'lucide-react';
import StockAnalyzerChart from './StockAnalyzerChart';

interface StockAnalysisResult {
  symbol: string;
  company_name: string;
  current_price: number;
  analysis_timestamp: string;
  
  // AI Commentary (Priority 1)
  ai_recommendation: string;
  ai_commentary: string;
  confidence_score: number;
  
  // Technical Analysis (Priority 2)
  technical_indicators: {
    rsi: number;
    macd: number;
    bollinger_position: string;
    moving_averages: {
      sma_20: number;
      sma_50: number;
      ema_12: number;
      ema_26: number;
    };
    support_resistance: {
      support: number;
      resistance: number;
    };
  };
  
  // Risk Assessment (Priority 3)
  risk_metrics: {
    volatility: number;
    beta: number;
    position_size_recommendation: number;
    max_position_value: number;
    stop_loss_suggestion: number;
  };
  
  // Sentiment Analysis (Priority 4)
  sentiment_analysis: {
    news_sentiment: number;
    social_sentiment: number;
    overall_sentiment: string;
    sentiment_sources: number;
  };
}

interface StockAnalyzerProps {
  initialSymbol?: string;
  initialCompanyName?: string;
  onAnalysisStart?: () => void;
}

export default function StockAnalyzer({
  initialSymbol,
  initialCompanyName,
  onAnalysisStart
}: StockAnalyzerProps = {}) {
  const [symbol, setSymbol] = useState(initialSymbol || '');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<StockAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!symbol.trim()) {
      setError('Please enter a stock symbol');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    
    try {
      // Skip API call for now (backend not running)
      // const response = await fetch(`http://localhost:8000/api/v1/analyze/${symbol.toUpperCase()}?use_precompute=true`, {
      //   method: 'GET',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      // });

      // Simulate API response with mock data
      const data = {
        success: true,
        analysis: {
          ticker: symbol.toUpperCase(),
          companyName: `${symbol.toUpperCase()} Company`,
          currentPrice: 150.00,
          aiConfidence: 75,
          targetPrice: 165.00,
          timeWindow: 3,
          reasoning: "Strong technical indicators and positive sentiment analysis suggest bullish momentum.",
          features: {
            technical: { rsi: 65, macd: 0.5, volume: 1.2 },
            sentiment: { score: 0.7, sources: 5 },
            fundamental: { pe: 25, growth: 0.15 }
          }
        }
      };

      if (data.success) {
        // Transform API response to match component interface
        const transformedData: StockAnalysisResult = {
          symbol: data.analysis.ticker,
          company_name: data.analysis.companyName,
          current_price: data.analysis.currentPrice,
          analysis_timestamp: new Date().toISOString(),

          // Map API recommendation to ai_recommendation
          ai_recommendation: 'BUY',
          ai_commentary: data.analysis.reasoning,
          confidence_score: data.analysis.aiConfidence,

          // Technical indicators with defaults
          technical_indicators: {
            rsi: data.analysis.features.technical.rsi || 50,
            macd: data.analysis.features.technical.macd || 0,
            bollinger_position: 'NEUTRAL',
            moving_averages: {
              sma_20: 0,
              sma_50: 0,
              ema_12: 0,
              ema_26: 0,
            },
            support_resistance: {
              support: data.analysis.currentPrice * 0.95,
              resistance: data.analysis.currentPrice * 1.05,
            },
          },

          // Risk metrics with defaults
          risk_metrics: {
            volatility: 0.2, // Default 20% volatility
            beta: 1.0,
            position_size_recommendation: 1000,
            max_position_value: 5000,
            stop_loss_suggestion: data.analysis.currentPrice * 0.95,
          },

          // Sentiment analysis with defaults
          sentiment_analysis: {
            news_sentiment: data.analysis.features.sentiment.score * 100,
            social_sentiment: data.analysis.features.sentiment.score * 100,
            overall_sentiment: 'POSITIVE',
            sentiment_sources: data.analysis.features.sentiment.sources,
          },
        };

        setAnalysisResult(transformedData);
      } else {
        throw new Error('Analysis failed');
      }
    } catch (err) {
      console.error('Analysis error:', err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(`🔄 Unable to analyze ${symbol.toUpperCase()} right now. Our data providers may be rate-limited. Please try again in a few minutes.`);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Auto-analyze when initialSymbol is provided (from earnings navigation)
  useEffect(() => {
    if (initialSymbol && !analysisResult) {
      // Call the callback to clear pending analysis
      if (onAnalysisStart) {
        onAnalysisStart();
      }
      // Trigger analysis
      handleAnalyze();
    }
  }, [initialSymbol]); // Only run when initialSymbol changes

  const [isAddingToWatchlist, setIsAddingToWatchlist] = useState(false);
  const [watchlistSuccess, setWatchlistSuccess] = useState<string | null>(null);

  const handleAddToWatchlist = async () => {
    if (!analysisResult) return;

    setIsAddingToWatchlist(true);
    setWatchlistSuccess(null);

    try {
      // Calculate target price based on AI recommendation
      let targetPrice = analysisResult.current_price;
      const currentPrice = analysisResult.current_price;

      // Set target based on recommendation and resistance levels
      if (analysisResult.ai_recommendation === 'BUY' || analysisResult.ai_recommendation === 'STRONG_BUY') {
        // Target is resistance level or 10% above current price, whichever is higher
        const resistanceTarget = analysisResult.technical_indicators.support_resistance.resistance;
        const percentTarget = currentPrice * 1.10;
        targetPrice = Math.max(resistanceTarget, percentTarget);
      } else if (analysisResult.ai_recommendation === 'SELL' || analysisResult.ai_recommendation === 'STRONG_SELL') {
        // Target is support level or 10% below current price, whichever is lower
        const supportTarget = analysisResult.technical_indicators.support_resistance.support;
        const percentTarget = currentPrice * 0.90;
        targetPrice = Math.min(supportTarget, percentTarget);
      } else {
        // HOLD - set modest 5% target in direction of sentiment
        if (analysisResult.sentiment_analysis.overall_sentiment === 'BULLISH') {
          targetPrice = currentPrice * 1.05;
        } else {
          targetPrice = currentPrice * 0.95;
        }
      }

      const watchlistData = {
        symbol: analysisResult.symbol,
        company_name: analysisResult.company_name,
        entry_type: 'STOCK',
        entry_price: currentPrice,
        target_price: targetPrice,
        stop_loss_price: analysisResult.risk_metrics.stop_loss_suggestion,
        ai_confidence_score: analysisResult.confidence_score,
        ai_recommendation: analysisResult.ai_recommendation,
        ai_reasoning: analysisResult.ai_commentary,
        ai_key_factors: [
          `RSI: ${analysisResult.technical_indicators.rsi.toFixed(1)}`,
          `MACD: ${analysisResult.technical_indicators.macd.toFixed(3)}`,
          `Sentiment: ${analysisResult.sentiment_analysis.overall_sentiment}`,
          `Volatility: ${(analysisResult.risk_metrics.volatility * 100).toFixed(1)}%`
        ],
        position_size_dollars: analysisResult.risk_metrics.position_size_recommendation
      };

      // Skip API call for now (backend not running)
      // const response = await fetch('http://localhost:8000/api/v1/watchlist/add', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify(watchlistData),

      // Simulate successful response
      const result = { success: true };

      if (result.success) {
        setWatchlistSuccess(`✅ ${analysisResult.symbol} added to watchlist! Target: $${targetPrice.toFixed(2)}`);
        // Clear success message after 5 seconds
        setTimeout(() => setWatchlistSuccess(null), 5000);
      } else {
        throw new Error('Failed to add to watchlist');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add to watchlist');
    } finally {
      setIsAddingToWatchlist(false);
    }
  };

  const handleShareAnalysis = async () => {
    if (!analysisResult) return;
    
    try {
      // TODO: Implement share functionality
      console.log('Sharing analysis:', analysisResult);
      // Show success notification
    } catch (err) {
      console.error('Failed to share analysis:', err);
    }
  };

  const getRecommendationColor = (recommendation: string | undefined) => {
    if (!recommendation) return 'text-[var(--text-muted)] border-[var(--text-muted)]';
    switch (recommendation.toUpperCase()) {
      case 'BUY':
      case 'STRONG_BUY':
        return 'text-[var(--accent-cyan)] border-[var(--accent-cyan)]';
      case 'SELL':
      case 'STRONG_SELL':
        return 'text-[var(--accent-red)] border-[var(--accent-red)]';
      case 'HOLD':
        return 'text-[var(--accent-yellow)] border-[var(--accent-yellow)]';
      default:
        return 'text-[var(--text-secondary)] border-[var(--border-color)]';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-[var(--accent-cyan)]';
    if (confidence >= 60) return 'text-[var(--accent-yellow)]';
    return 'text-[var(--accent-red)]';
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toUpperCase()) {
      case 'BULLISH':
      case 'POSITIVE':
        return 'text-[var(--accent-cyan)]';
      case 'BEARISH':
      case 'NEGATIVE':
        return 'text-[var(--accent-red)]';
      case 'NEUTRAL':
        return 'text-[var(--accent-yellow)]';
      default:
        return 'text-[var(--text-secondary)]';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="clean-panel">
        <div className="flex items-center gap-2 mb-4">
          <Search className="w-6 h-6 text-[var(--text-primary)]" />
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            Stock Analyzer
          </h2>
        </div>
        
        {/* Input Section */}
        <div className="flex gap-3">
          <div className="flex-1">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              onKeyPress={(e) => e.key === 'Enter' && handleAnalyze()}
              placeholder="Enter stock symbol (e.g., AAPL, TSLA, NVDA)"
              className="clean-input w-full"
              disabled={isAnalyzing}
            />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !symbol.trim()}
            className="clean-button px-6 py-2 flex items-center gap-2"
          >
            {isAnalyzing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border border-[var(--accent-cyan)] border-t-transparent"></div>
                ANALYZING...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                ANALYZE
              </>
            )}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-[var(--bg-tertiary)] border border-[var(--accent-red)] rounded">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[var(--accent-red)]" />
              <span className="font-mono text-[var(--accent-red)] text-sm">{error}</span>
            </div>
            <div className="mt-2 text-xs text-[var(--text-secondary)]">
              💡 <strong>Tip:</strong> Try popular stocks like AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META for better data availability.
            </div>
          </div>
        )}

        {/* System Status Info */}
        {!error && !analysisResult && !isAnalyzing && (
          <div className="mt-4 p-3 bg-[var(--bg-tertiary)] border border-[var(--accent-cyan)] rounded">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-[var(--accent-cyan)]" />
              <span className="font-mono text-[var(--accent-cyan)] text-sm">
                🚀 <strong>Smart Analysis System:</strong> We use pre-computed analysis for faster results and fallback to real-time data when needed.
              </span>
            </div>
          </div>
        )}

        {/* Success Display */}
        {watchlistSuccess && (
          <div className="mt-4 p-3 bg-[var(--bg-tertiary)] border border-[var(--accent-cyan)] rounded">
            <div className="flex items-center gap-2">
              <BookmarkPlus className="w-4 h-4 text-[var(--accent-cyan)]" />
              <span className="font-mono text-[var(--accent-cyan)] text-sm">{watchlistSuccess}</span>
            </div>
          </div>
        )}
      </div>

      {/* Analysis Results */}
      {analysisResult && (
        <div className="space-y-4">
          {/* Stock Info Header */}
          <div className="clean-panel">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-2xl font-mono text-[var(--text-primary)] font-bold">
                  {analysisResult.symbol}
                </h3>
                <p className="text-[var(--text-secondary)] font-mono text-sm">
                  {analysisResult.company_name}
                </p>
                <p className="text-[var(--accent-cyan)] font-mono text-lg font-bold">
                  ${analysisResult.current_price.toFixed(2)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleAddToWatchlist}
                  disabled={isAddingToWatchlist}
                  className="neon-button px-4 py-2 flex items-center gap-2"
                  title="Add to Watchlist for Performance Tracking"
                >
                  {isAddingToWatchlist ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border border-[var(--accent-cyan)] border-t-transparent"></div>
                      <span className="text-sm font-mono">ADDING...</span>
                    </>
                  ) : (
                    <>
                      <BookmarkPlus className="w-4 h-4" />
                      <span className="text-sm font-mono">ADD TO WATCHLIST</span>
                    </>
                  )}
                </button>
                <button
                  onClick={handleShareAnalysis}
                  className="neon-button-secondary p-2"
                  title="Share Analysis"
                >
                  <Share2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            
            <div className="text-xs font-mono text-[var(--text-muted)]">
              Analysis generated: {new Date(analysisResult.analysis_timestamp).toLocaleString()}
            </div>
          </div>

          {/* Interactive Chart */}
          <StockAnalyzerChart ticker={analysisResult.symbol} />

          {/* Priority 1: AI Commentary */}
          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-5 h-5 text-[var(--accent-cyan)]" />
              <h4 className="font-mono text-[var(--accent-cyan)] uppercase text-sm font-bold">
                AI Analysis
              </h4>
              <span className={`px-2 py-1 rounded text-xs font-bold border ${getRecommendationColor(analysisResult.ai_recommendation)}`}>
                {analysisResult.ai_recommendation}
              </span>
              <span className={`font-bold ${getConfidenceColor(analysisResult.confidence_score)}`}>
                {analysisResult.confidence_score.toFixed(1)}%
              </span>
            </div>
            <p className="text-[var(--text-secondary)] text-sm leading-relaxed font-mono">
              {analysisResult.ai_commentary}
            </p>
          </div>

          {/* Priority 2: Technical Analysis */}
          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-[var(--accent-yellow)]" />
              <h4 className="font-mono text-[var(--accent-yellow)] uppercase text-sm font-bold">
                Technical Indicators
              </h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">RSI</div>
                <div className="text-[var(--text-primary)] font-bold">
                  {analysisResult.technical_indicators.rsi.toFixed(1)}
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">MACD</div>
                <div className="text-[var(--text-primary)] font-bold">
                  {analysisResult.technical_indicators.macd.toFixed(3)}
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Support</div>
                <div className="text-[var(--accent-red)] font-bold">
                  ${analysisResult.technical_indicators.support_resistance.support.toFixed(2)}
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Resistance</div>
                <div className="text-[var(--accent-cyan)] font-bold">
                  ${analysisResult.technical_indicators.support_resistance.resistance.toFixed(2)}
                </div>
              </div>
            </div>
          </div>

          {/* Priority 3: Risk Assessment */}
          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-[var(--accent-red)]" />
              <h4 className="font-mono text-[var(--accent-red)] uppercase text-sm font-bold">
                Risk Assessment
              </h4>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Position Size</div>
                <div className="text-[var(--accent-cyan)] font-bold">
                  ${analysisResult.risk_metrics.position_size_recommendation.toLocaleString()}
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Stop Loss</div>
                <div className="text-[var(--accent-red)] font-bold">
                  ${analysisResult.risk_metrics.stop_loss_suggestion.toFixed(2)}
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Volatility</div>
                <div className="text-[var(--accent-yellow)] font-bold">
                  {(analysisResult.risk_metrics.volatility * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Priority 4: Sentiment Analysis */}
          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-5 h-5 text-[var(--text-secondary)]" />
              <h4 className="font-mono text-[var(--text-secondary)] uppercase text-sm font-bold">
                Market Sentiment
              </h4>
              <span className={`px-2 py-1 rounded text-xs font-bold border ${getSentimentColor(analysisResult.sentiment_analysis.overall_sentiment)}`}>
                {analysisResult.sentiment_analysis.overall_sentiment}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">News Sentiment</div>
                <div className="text-[var(--text-primary)] font-bold">
                  {(analysisResult.sentiment_analysis.news_sentiment * 100).toFixed(0)}%
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Social Sentiment</div>
                <div className="text-[var(--text-primary)] font-bold">
                  {(analysisResult.sentiment_analysis.social_sentiment * 100).toFixed(0)}%
                </div>
              </div>
              <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                <div className="text-xs font-mono text-[var(--text-muted)] mb-1">Sources</div>
                <div className="text-[var(--accent-cyan)] font-bold">
                  {analysisResult.sentiment_analysis.sentiment_sources}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No Results Message */}
      {!isAnalyzing && !analysisResult && !error && (
        <div className="cyber-panel text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Search className="w-8 h-8 text-[var(--text-muted)]" />
            <h3 className="text-xl font-mono text-[var(--text-muted)] uppercase tracking-wider">
              Ready to Analyze
            </h3>
          </div>
          <p className="font-mono text-[var(--text-secondary)] mb-2">
            &gt; Enter a stock symbol to get comprehensive AI analysis
          </p>
          <p className="font-mono text-xs text-[var(--text-muted)]">
            Includes technical indicators, sentiment analysis, and risk assessment
          </p>
        </div>
      )}
    </div>
  );
}
