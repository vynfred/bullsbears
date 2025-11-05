'use client';

import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Target, Trophy, BarChart3, RefreshCw, Calendar, Star } from 'lucide-react';
import { api, AIVsWatchlistPerformance } from '@/lib/api';
import { WatchlistNotifications } from './WatchlistNotifications';
import { NotificationTestPanel } from './NotificationTestPanel';

interface AIVsWatchlistDashboardProps {
  className?: string;
}

export function AIVsWatchlistDashboard({ className = '' }: AIVsWatchlistDashboardProps) {
  const [performanceData, setPerformanceData] = useState<AIVsWatchlistPerformance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);

  const fetchPerformanceData = async (days: number) => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.getAIVsWatchlistPerformance(days);
      setPerformanceData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceData(selectedPeriod);
  }, [selectedPeriod]);

  const handlePeriodChange = (days: number) => {
    setSelectedPeriod(days);
  };

  const handleRefresh = () => {
    fetchPerformanceData(selectedPeriod);
  };

  if (isLoading) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-400">Loading performance data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-400 mb-4">Error loading performance data</div>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!performanceData) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="text-center text-gray-400">No performance data available</div>
      </div>
    );
  }

  const { ai_performance, watchlist_performance, comparison } = performanceData;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">AI vs Watchlist Performance</h2>
          <p className="text-gray-400">Compare AI picks against your personal watchlist performance</p>
        </div>
        <div className="flex items-center space-x-4">
          {/* Period Selector */}
          <div className="flex bg-gray-800 rounded-lg p-1">
            {[7, 30, 90].map((days) => (
              <button
                key={days}
                onClick={() => handlePeriodChange(days)}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  selectedPeriod === days
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {days}d
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 text-gray-400 hover:text-white transition-colors"
            disabled={isLoading}
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notifications Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <WatchlistNotifications className="lg:col-span-1" />
        <NotificationTestPanel className="lg:col-span-1" />
      </div>

      {/* Performance Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* AI Performance Card */}
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">AI Picks</h3>
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-5 h-5 text-blue-500" />
              <span className="text-sm text-gray-400">{ai_performance.total_picks} picks</span>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Average Return</span>
              <span className={`font-semibold ${ai_performance.average_return_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {ai_performance.average_return_percent >= 0 ? '+' : ''}{ai_performance.average_return_percent.toFixed(1)}%
              </span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Win Rate</span>
              <span className="text-white font-semibold">{(ai_performance.win_rate * 100).toFixed(1)}%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Best Pick</span>
              <span className="text-green-400 font-semibold">+{ai_performance.best_pick_return.toFixed(1)}%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Worst Pick</span>
              <span className="text-red-400 font-semibold">{ai_performance.worst_pick_return.toFixed(1)}%</span>
            </div>
            
            <div className="pt-2 border-t border-gray-700">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Bullish: {ai_performance.bullish_picks}</span>
                <span className="text-gray-400">Bearish: {ai_performance.bearish_picks}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Watchlist Performance Card */}
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Your Watchlist</h3>
            <div className="flex items-center space-x-2">
              <Star className="w-5 h-5 text-yellow-500" />
              <span className="text-sm text-gray-400">{watchlist_performance.closed_entries} trades</span>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Average Return</span>
              <span className={`font-semibold ${watchlist_performance.average_return_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {watchlist_performance.average_return_percent >= 0 ? '+' : ''}{watchlist_performance.average_return_percent.toFixed(1)}%
              </span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Win Rate</span>
              <span className="text-white font-semibold">{(watchlist_performance.win_rate * 100).toFixed(1)}%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Best Trade</span>
              <span className="text-green-400 font-semibold">+{watchlist_performance.best_pick_return.toFixed(1)}%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Worst Trade</span>
              <span className="text-red-400 font-semibold">{watchlist_performance.worst_pick_return.toFixed(1)}%</span>
            </div>
            
            <div className="pt-2 border-t border-gray-700">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Active: {watchlist_performance.active_entries}</span>
                <span className="text-gray-400">Closed: {watchlist_performance.closed_entries}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Winner Banner */}
      <div className={`rounded-lg p-6 ${comparison.better_performer === 'watchlist' ? 'bg-green-900/30 border border-green-500/30' : 'bg-blue-900/30 border border-blue-500/30'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Trophy className={`w-8 h-8 ${comparison.better_performer === 'watchlist' ? 'text-green-400' : 'text-blue-400'}`} />
            <div>
              <h3 className="text-xl font-bold text-white">
                {comparison.better_performer === 'watchlist' ? 'Your Watchlist Wins!' : 'AI Picks Win!'}
              </h3>
              <p className="text-gray-400">
                Outperforming by {comparison.advantage_magnitude.toFixed(1)}% average return
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className={`text-2xl font-bold ${comparison.better_performer === 'watchlist' ? 'text-green-400' : 'text-blue-400'}`}>
              +{comparison.advantage_magnitude.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">advantage</div>
          </div>
        </div>
      </div>

      {/* Insights */}
      <div className="bg-gray-900 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Key Insights</h3>
        <div className="space-y-2">
          {comparison.insights.map((insight, index) => (
            <div key={index} className="flex items-start space-x-3">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-300">{insight}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Top Performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top AI Picks */}
        <div className="bg-gray-900 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Top AI Picks</h3>
          <div className="space-y-3">
            {ai_performance.top_picks.slice(0, 3).map((pick, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                <div>
                  <div className="font-semibold text-white">{pick.symbol}</div>
                  <div className="text-sm text-gray-400 capitalize">{pick.alert_type}</div>
                </div>
                <div className="text-right">
                  <div className="text-blue-400 font-semibold">{pick.confidence}%</div>
                  <div className="text-xs text-gray-400">confidence</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Watchlist Trades */}
        <div className="bg-gray-900 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Top Watchlist Trades</h3>
          <div className="space-y-3">
            {watchlist_performance.top_picks.slice(0, 3).map((trade, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                <div>
                  <div className="font-semibold text-white">{trade.symbol}</div>
                  <div className="text-sm text-gray-400">{trade.days_held} days</div>
                </div>
                <div className="text-right">
                  <div className="text-green-400 font-semibold">+{trade.return_percent.toFixed(1)}%</div>
                  <div className="text-xs text-gray-400">${trade.entry_price.toFixed(2)} → ${trade.exit_price.toFixed(2)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
