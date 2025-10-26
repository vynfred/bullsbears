'use client';

import React, { useState, useEffect } from 'react';
import {
  BarChart3, TrendingUp, TrendingDown, DollarSign,
  Target, Shield, Clock, RefreshCw, Plus, Eye,
  Calendar, Percent, AlertTriangle, Share2
} from 'lucide-react';
import ShareableContent from './ShareableContent';

interface ChosenOption {
  id: number;
  symbol: string;
  company_name: string;
  option_type: string;
  strike: number;
  expiration: string;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  confidence_score: number;
  ai_recommendation: string;
  chosen_at: string;
  position_size: number;
  max_profit: number;
  max_loss: number;
  risk_reward_ratio: number;
  summary: string;
  key_factors: string[];
  is_expired: boolean;
  final_price?: number;
  actual_profit_loss?: number;
}

interface PortfolioStats {
  total_plays: number;
  profitable_plays: number;
  total_profit_loss: number;
  win_rate: number;
  average_profit: number;
  average_loss: number;
  best_trade: number;
  worst_trade: number;
}

export default function PortfolioTracker() {
  const [chosenOptions, setChosenOptions] = useState<ChosenOption[]>([]);
  const [portfolioStats, setPortfolioStats] = useState<PortfolioStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<ChosenOption | null>(null);
  const [shareableOption, setShareableOption] = useState<ChosenOption | null>(null);

  // Fetch portfolio data
  const fetchPortfolioData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Fetch chosen options
      const optionsResponse = await fetch('http://localhost:8000/api/v1/chosen-options');
      if (!optionsResponse.ok) {
        throw new Error('Failed to fetch portfolio data');
      }
      const options = await optionsResponse.json();
      setChosenOptions(options);

      // Fetch portfolio stats
      const statsResponse = await fetch('http://localhost:8000/api/v1/backtest', {
        method: 'POST'
      });
      if (statsResponse.ok) {
        const stats = await statsResponse.json();
        setPortfolioStats(stats);
      }
    } catch (err) {
      console.error('Error fetching portfolio data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load portfolio data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const formatCurrency = (value: number | undefined) => `$${(value || 0).toFixed(2)}`;
  const formatPercent = (value: number | undefined) => `${((value || 0) * 100).toFixed(1)}%`;
  const formatDate = (dateString: string) => new Date(dateString).toLocaleDateString();

  const getStatusColor = (option: ChosenOption) => {
    if (option.is_expired) {
      if (option.actual_profit_loss && option.actual_profit_loss > 0) {
        return 'text-green-400 bg-green-900/20 border-green-500/30';
      } else if (option.actual_profit_loss && option.actual_profit_loss < 0) {
        return 'text-red-400 bg-red-900/20 border-red-500/30';
      }
      return 'text-gray-400 bg-gray-900/20 border-gray-500/30';
    }
    return 'text-cyan-400 bg-cyan-900/20 border-cyan-500/30';
  };

  const getStatusText = (option: ChosenOption) => {
    if (option.is_expired) {
      if (option.actual_profit_loss && option.actual_profit_loss > 0) return 'PROFIT';
      if (option.actual_profit_loss && option.actual_profit_loss < 0) return 'LOSS';
      return 'EXPIRED';
    }
    return 'ACTIVE';
  };

  if (isLoading) {
    return (
      <div className="cyber-panel text-center">
        <div className="flex items-center justify-center gap-2 mb-4">
          <RefreshCw className="w-6 h-6 text-[var(--accent-cyan)] animate-spin" />
          <h2 className="text-xl font-mono text-[var(--accent-cyan)] uppercase tracking-wider">
            Loading Portfolio...
          </h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cyber-panel">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-6 h-6 text-[var(--accent-red)]" />
          <h2 className="text-xl font-mono text-[var(--accent-red)] uppercase tracking-wider">
            Portfolio Error
          </h2>
        </div>
        <p className="text-[var(--text-secondary)] mb-4">{error}</p>
        <button
          onClick={fetchPortfolioData}
          className="neon-button px-4 py-2"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Portfolio Header */}
      <div className="cyber-panel">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-[var(--accent-cyan)]" />
            <h2 className="text-xl font-mono text-[var(--accent-cyan)] uppercase tracking-wider">
              Portfolio Tracker
            </h2>
          </div>
          <button
            onClick={fetchPortfolioData}
            className="flex items-center gap-2 px-3 py-1 border border-[var(--border-color)] rounded hover:border-[var(--accent-cyan)] transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="font-mono text-xs uppercase">Refresh</span>
          </button>
        </div>

        {/* Portfolio Stats */}
        {portfolioStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800/30 p-4 rounded-lg border border-gray-700/50">
              <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Total Trades</div>
              <div className="text-2xl font-bold font-mono text-white">{portfolioStats.total_plays}</div>
            </div>
            
            <div className="bg-green-900/20 p-4 rounded-lg border border-green-500/30">
              <div className="text-xs uppercase tracking-wide text-green-400 mb-1">Win Rate</div>
              <div className="text-2xl font-bold font-mono text-green-400">
                {portfolioStats.total_plays > 0 ? formatPercent(portfolioStats.profitable_plays / portfolioStats.total_plays) : '0%'}
              </div>
            </div>
            
            <div className={`p-4 rounded-lg border ${portfolioStats.total_profit_loss >= 0 ? 'bg-green-900/20 border-green-500/30' : 'bg-red-900/20 border-red-500/30'}`}>
              <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Total P/L</div>
              <div className={`text-2xl font-bold font-mono ${portfolioStats.total_profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(portfolioStats.total_profit_loss)}
              </div>
            </div>
            
            <div className="bg-cyan-900/20 p-4 rounded-lg border border-cyan-500/30">
              <div className="text-xs uppercase tracking-wide text-cyan-400 mb-1">Best Trade</div>
              <div className="text-2xl font-bold font-mono text-cyan-400">
                {formatCurrency(portfolioStats.best_trade || 0)}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Trades List */}
      <div className="cyber-panel">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-[var(--accent-yellow)]" />
          <h3 className="font-mono text-[var(--accent-yellow)] uppercase tracking-wider">
            Trade History ({chosenOptions.length})
          </h3>
        </div>

        {chosenOptions.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-[var(--text-muted)] mb-4">
              <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p className="font-mono">No trades in portfolio yet</p>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              Execute option plays from the AI Generator to start tracking your performance
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {chosenOptions.map((option) => (
              <div
                key={option.id}
                className="bg-gray-900/30 border border-gray-700/50 rounded-lg p-4 hover:border-cyan-500/30 transition-all duration-200"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="text-xl">
                      {option.option_type === 'CALL' ? '🐂' : '🐻'}
                    </div>
                    <div>
                      <h4 className="font-bold text-white font-mono">{option.symbol}</h4>
                      <p className="text-sm text-gray-400">{option.company_name}</p>
                    </div>
                  </div>
                  
                  <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(option)}`}>
                    {getStatusText(option)}
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-400">Strike</div>
                    <div className="font-bold font-mono text-white">{formatCurrency(option.strike)}</div>
                  </div>
                  
                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-400">Entry</div>
                    <div className="font-bold font-mono text-blue-400">{formatCurrency(option.entry_price)}</div>
                  </div>
                  
                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-400">Target</div>
                    <div className="font-bold font-mono text-green-400">{formatCurrency(option.target_price)}</div>
                  </div>
                  
                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-400">P/L</div>
                    <div className={`font-bold font-mono ${
                      option.actual_profit_loss 
                        ? option.actual_profit_loss >= 0 ? 'text-green-400' : 'text-red-400'
                        : 'text-gray-400'
                    }`}>
                      {option.actual_profit_loss ? formatCurrency(option.actual_profit_loss) : 'TBD'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
                  <span>Chosen: {formatDate(option.chosen_at)}</span>
                  <span>Expires: {option.expiration}</span>
                  <span>Confidence: {option.confidence_score.toFixed(1)}%</span>
                </div>

                {/* Share Button for Completed Trades */}
                {option.is_expired && option.actual_profit_loss !== null && (
                  <div className="flex justify-end">
                    <button
                      onClick={() => setShareableOption(shareableOption?.id === option.id ? null : option)}
                      className="flex items-center gap-1 px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded transition-colors"
                    >
                      <Share2 className="w-3 h-3" />
                      {shareableOption?.id === option.id ? 'Hide Share' : 'Share Result'}
                    </button>
                  </div>
                )}

                {/* Shareable Content */}
                {shareableOption?.id === option.id && option.actual_profit_loss !== null && option.actual_profit_loss !== undefined && (
                  <div className="mt-4 pt-4 border-t border-gray-700/50">
                    <ShareableContent
                      tradeResult={{
                        symbol: option.symbol,
                        option_type: option.option_type,
                        entry_price: option.entry_price,
                        exit_price: option.final_price || option.entry_price,
                        profit_loss: option.actual_profit_loss,
                        profit_percentage: (option.actual_profit_loss / (option.entry_price * option.position_size)) * 100,
                        outcome: option.actual_profit_loss > 0 ? 'WIN' : 'LOSS'
                      }}
                      type="result"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual Trade Entry (Future Feature) */}
      <div className="cyber-panel">
        <div className="flex items-center gap-2 mb-4">
          <Plus className="w-5 h-5 text-[var(--text-muted)]" />
          <h3 className="font-mono text-[var(--text-muted)] uppercase tracking-wider">
            Manual Trade Entry
          </h3>
        </div>
        
        <div className="text-center py-6 border-2 border-dashed border-gray-700/50 rounded-lg">
          <Plus className="w-8 h-8 mx-auto mb-2 text-gray-500" />
          <p className="font-mono text-gray-500 mb-2">Coming Soon</p>
          <p className="text-sm text-gray-600">
            Manual trade entry and CSV import functionality
          </p>
        </div>
      </div>
    </div>
  );
}
