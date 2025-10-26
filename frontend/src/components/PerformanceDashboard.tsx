'use client';

import React, { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, Target, Brain, Shield,
  Calendar, DollarSign, Percent, Trophy, AlertTriangle,
  BarChart3, PieChart, Activity, BookmarkPlus, Clock,
  CheckCircle, XCircle, Minus
} from 'lucide-react';

interface WatchlistEntry {
  id: number;
  symbol: string;
  company_name: string;
  entry_type: string;
  entry_price: number;
  target_price: number;
  stop_loss_price?: number;
  entry_date: string;
  current_price?: number;
  current_return_percent?: number;
  current_return_dollars?: number;
  unrealized_pnl?: number;
  status: string;
  is_winner?: boolean;
  days_held?: number;
  ai_confidence_score: number;
  ai_recommendation: string;
  ai_reasoning: string;
  strike_price?: number;
  expiration_date?: string;
  position_size_dollars?: number;
}

interface PerformanceMetrics {
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

export default function PerformanceDashboard() {
  const [watchlistEntries, setWatchlistEntries] = useState<WatchlistEntry[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'ACTIVE' | 'CLOSED' | 'STOCKS' | 'OPTIONS'>('ALL');

  useEffect(() => {
    fetchWatchlistData();
    fetchPerformanceMetrics();
  }, []);

  const fetchWatchlistData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/watchlist/entries');
      if (!response.ok) {
        throw new Error(`Failed to fetch watchlist: ${response.statusText}`);
      }
      const data = await response.json();
      setWatchlistEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch watchlist');
    }
  };

  const fetchPerformanceMetrics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/watchlist/performance');
      if (!response.ok) {
        throw new Error(`Failed to fetch performance: ${response.statusText}`);
      }
      const data = await response.json();
      setPerformanceMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance metrics');
    } finally {
      setIsLoading(false);
    }
  };

  const updatePrices = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:8000/api/v1/watchlist/update-prices', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Failed to update prices: ${response.statusText}`);
      }
      await fetchWatchlistData();
      await fetchPerformanceMetrics();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update prices');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = (status: string, isWinner?: boolean) => {
    switch (status) {
      case 'ACTIVE':
        return <Activity className="w-4 h-4 text-[var(--accent-cyan)]" />;
      case 'CLOSED':
        return isWinner ? 
          <CheckCircle className="w-4 h-4 text-[var(--text-primary)]" /> :
          <XCircle className="w-4 h-4 text-[var(--accent-red)]" />;
      case 'EXPIRED':
        return <Clock className="w-4 h-4 text-[var(--text-muted)]" />;
      default:
        return <Minus className="w-4 h-4 text-[var(--text-muted)]" />;
    }
  };

  const getReturnColor = (returnPercent?: number) => {
    if (!returnPercent) return 'text-[var(--text-muted)]';
    if (returnPercent > 0) return 'text-[var(--text-primary)]';
    if (returnPercent < 0) return 'text-[var(--accent-red)]';
    return 'text-[var(--text-muted)]';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-[var(--text-primary)]';
    if (confidence >= 60) return 'text-[var(--accent-cyan)]';
    return 'text-[var(--accent-yellow)]';
  };

  const formatCurrency = (amount?: number) => {
    if (!amount) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercent = (value?: number) => {
    if (!value) return '0.0%';
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  const filteredEntries = watchlistEntries.filter(entry => {
    switch (selectedFilter) {
      case 'ACTIVE':
        return entry.status === 'ACTIVE';
      case 'CLOSED':
        return entry.status === 'CLOSED';
      case 'STOCKS':
        return entry.entry_type === 'STOCK';
      case 'OPTIONS':
        return entry.entry_type.includes('OPTION');
      default:
        return true;
    }
  });

  if (isLoading && watchlistEntries.length === 0) {
    return (
      <div className="cyber-panel text-center">
        <div className="animate-spin rounded-full h-8 w-8 border border-[var(--accent-cyan)] border-t-transparent mx-auto mb-4"></div>
        <p className="font-mono text-[var(--text-secondary)]">Loading performance data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="cyber-panel">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-[var(--accent-cyan)]" />
            <h2 className="text-2xl font-mono text-[var(--text-primary)] font-bold uppercase">
              Performance Dashboard
            </h2>
          </div>
          <button
            onClick={updatePrices}
            disabled={isLoading}
            className="neon-button-secondary px-4 py-2 flex items-center gap-2"
          >
            {isLoading ? (
              <div className="animate-spin rounded-full h-4 w-4 border border-[var(--accent-cyan)] border-t-transparent"></div>
            ) : (
              <Activity className="w-4 h-4" />
            )}
            <span className="font-mono text-sm">UPDATE PRICES</span>
          </button>
        </div>
        
        {error && (
          <div className="bg-[var(--bg-tertiary)] border border-[var(--accent-red)] rounded p-3 mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[var(--accent-red)]" />
              <span className="font-mono text-[var(--accent-red)] text-sm">{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Performance Metrics */}
      {performanceMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-2">
              <Trophy className="w-5 h-5 text-[var(--accent-yellow)]" />
              <span className="font-mono text-[var(--text-muted)] uppercase text-xs">Win Rate</span>
            </div>
            <div className="text-2xl font-bold text-[var(--accent-yellow)]">
              {(performanceMetrics.win_rate * 100).toFixed(1)}%
            </div>
            <div className="text-xs font-mono text-[var(--text-secondary)]">
              {performanceMetrics.winning_trades}W / {performanceMetrics.losing_trades}L
            </div>
          </div>

          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-[var(--text-primary)]" />
              <span className="font-mono text-[var(--text-muted)] uppercase text-xs">Total Return</span>
            </div>
            <div className={`text-2xl font-bold ${getReturnColor(performanceMetrics.total_return)}`}>
              {formatPercent(performanceMetrics.total_return)}
            </div>
            <div className="text-xs font-mono text-[var(--text-secondary)]">
              Avg: {formatPercent(performanceMetrics.average_return)}
            </div>
          </div>

          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-[var(--accent-cyan)]" />
              <span className="font-mono text-[var(--text-muted)] uppercase text-xs">Active Trades</span>
            </div>
            <div className="text-2xl font-bold text-[var(--accent-cyan)]">
              {performanceMetrics.active_trades}
            </div>
            <div className="text-xs font-mono text-[var(--text-secondary)]">
              Total: {performanceMetrics.total_trades}
            </div>
          </div>

          <div className="cyber-panel">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-5 h-5 text-[var(--accent-cyan)]" />
              <span className="font-mono text-[var(--text-muted)] uppercase text-xs">AI Accuracy</span>
            </div>
            <div className="text-2xl font-bold text-[var(--accent-cyan)]">
              {(performanceMetrics.high_confidence_accuracy * 100).toFixed(1)}%
            </div>
            <div className="text-xs font-mono text-[var(--text-secondary)]">
              High Confidence
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="cyber-panel">
        <div className="flex flex-wrap gap-2">
          {(['ALL', 'ACTIVE', 'CLOSED', 'STOCKS', 'OPTIONS'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedFilter(filter)}
              className={`px-4 py-2 rounded font-mono text-sm uppercase transition-colors ${
                selectedFilter === filter
                  ? 'bg-[var(--accent-cyan)] text-[var(--bg-primary)] border border-[var(--accent-cyan)]'
                  : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:border-[var(--accent-cyan)]'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Watchlist Entries */}
      {filteredEntries.length === 0 ? (
        <div className="cyber-panel text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <BookmarkPlus className="w-8 h-8 text-[var(--text-muted)]" />
            <h3 className="text-xl font-mono text-[var(--text-muted)] uppercase tracking-wider">
              No Watchlist Entries
            </h3>
          </div>
          <p className="font-mono text-[var(--text-secondary)] mb-2">
            &gt; Use the Stock Analyzer or Options Generator to add trades to your watchlist
          </p>
          <p className="font-mono text-xs text-[var(--text-muted)]">
            Performance tracking will appear here once you add some positions
          </p>
        </div>
      ) : (
        <div className="cyber-panel">
          <div className="overflow-x-auto">
            <table className="w-full font-mono text-sm">
              <thead className="bg-[var(--bg-tertiary)] border-b border-[var(--border-color)]">
                <tr>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Status</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Symbol</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Type</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Entry</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Current</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Return</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">P&L</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Confidence</th>
                  <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Days</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-[var(--border-color)] hover:bg-[var(--bg-secondary)] transition-colors"
                  >
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(entry.status, entry.is_winner)}
                        <span className="text-xs uppercase text-[var(--text-secondary)]">
                          {entry.status}
                        </span>
                      </div>
                    </td>
                    <td className="p-3">
                      <div>
                        <div className="font-bold text-[var(--text-primary)]">{entry.symbol}</div>
                        {entry.strike_price && (
                          <div className="text-xs text-[var(--text-secondary)]">
                            ${entry.strike_price} {entry.expiration_date && new Date(entry.expiration_date).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold border ${
                        entry.entry_type === 'STOCK'
                          ? 'text-[var(--accent-cyan)] border-[var(--accent-cyan)]'
                          : entry.entry_type === 'OPTION_CALL'
                          ? 'text-[var(--text-primary)] border-[var(--text-primary)]'
                          : 'text-[var(--accent-red)] border-[var(--accent-red)]'
                      }`}>
                        {entry.entry_type.replace('OPTION_', '')}
                      </span>
                    </td>
                    <td className="p-3 text-[var(--text-primary)]">
                      {formatCurrency(entry.entry_price)}
                    </td>
                    <td className="p-3 text-[var(--text-primary)]">
                      {entry.current_price ? formatCurrency(entry.current_price) : '-'}
                    </td>
                    <td className="p-3">
                      <span className={`font-bold ${getReturnColor(entry.current_return_percent)}`}>
                        {formatPercent(entry.current_return_percent)}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`font-bold ${getReturnColor(entry.current_return_dollars)}`}>
                        {formatCurrency(entry.current_return_dollars)}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`font-bold ${getConfidenceColor(entry.ai_confidence_score)}`}>
                        {entry.ai_confidence_score.toFixed(1)}%
                      </span>
                    </td>
                    <td className="p-3 text-[var(--text-secondary)]">
                      {entry.days_held || 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}