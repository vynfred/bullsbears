'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, AIVsWatchlistPerformance } from '@/lib/api';

export interface UseAIVsWatchlistPerformanceReturn {
  // Data
  performanceData: AIVsWatchlistPerformance | null;
  
  // Loading states
  isLoading: boolean;
  isRefreshing: boolean;
  
  // Error handling
  error: string | null;
  
  // Actions
  fetchPerformance: (days: number) => Promise<void>;
  refreshPerformance: () => Promise<void>;
  
  // Computed values
  aiAdvantage: number;
  watchlistAdvantage: number;
  betterPerformer: 'ai' | 'watchlist' | 'tie';
  performanceGap: number;
  
  // Period management
  selectedPeriod: number;
  setSelectedPeriod: (days: number) => void;
}

export function useAIVsWatchlistPerformance(initialPeriod: number = 30): UseAIVsWatchlistPerformanceReturn {
  const [performanceData, setPerformanceData] = useState<AIVsWatchlistPerformance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(initialPeriod);

  // Fetch performance data
  const fetchPerformance = useCallback(async (days: number) => {
    try {
      setError(null);
      const data = await api.getAIVsWatchlistPerformance(days);
      setPerformanceData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Refresh current data
  const refreshPerformance = useCallback(async () => {
    setIsRefreshing(true);
    await fetchPerformance(selectedPeriod);
  }, [fetchPerformance, selectedPeriod]);

  // Update selected period and fetch new data
  const handlePeriodChange = useCallback((days: number) => {
    setSelectedPeriod(days);
    setIsLoading(true);
    fetchPerformance(days);
  }, [fetchPerformance]);

  // Initial data fetch
  useEffect(() => {
    fetchPerformance(selectedPeriod);
  }, [fetchPerformance, selectedPeriod]);

  // Computed values
  const aiAdvantage = performanceData ? 
    performanceData.ai_performance.average_return_percent - performanceData.watchlist_performance.average_return_percent : 0;
  
  const watchlistAdvantage = performanceData ? 
    performanceData.watchlist_performance.average_return_percent - performanceData.ai_performance.average_return_percent : 0;
  
  const betterPerformer: 'ai' | 'watchlist' | 'tie' = performanceData ? 
    (performanceData.comparison.better_performer === 'ai' ? 'ai' : 
     performanceData.comparison.better_performer === 'watchlist' ? 'watchlist' : 'tie') : 'tie';
  
  const performanceGap = performanceData ? Math.abs(performanceData.comparison.performance_advantage_percent) : 0;

  return {
    // Data
    performanceData,
    
    // Loading states
    isLoading,
    isRefreshing,
    
    // Error handling
    error,
    
    // Actions
    fetchPerformance,
    refreshPerformance,
    
    // Computed values
    aiAdvantage,
    watchlistAdvantage,
    betterPerformer,
    performanceGap,
    
    // Period management
    selectedPeriod,
    setSelectedPeriod: handlePeriodChange,
  };
}

// Additional utility functions for performance analysis
export function calculatePerformanceMetrics(data: AIVsWatchlistPerformance) {
  const ai = data.ai_performance;
  const watchlist = data.watchlist_performance;
  
  return {
    // Return comparison
    returnDifference: watchlist.average_return_percent - ai.average_return_percent,
    returnRatio: ai.average_return_percent !== 0 ? watchlist.average_return_percent / ai.average_return_percent : 0,
    
    // Win rate comparison
    winRateDifference: watchlist.win_rate - ai.win_rate,
    winRateRatio: ai.win_rate !== 0 ? watchlist.win_rate / ai.win_rate : 0,
    
    // Volume comparison
    aiPicksPerDay: ai.total_picks / data.comparison_period_days,
    watchlistTradesPerDay: watchlist.closed_entries / data.comparison_period_days,
    
    // Risk metrics
    aiVolatility: Math.abs(ai.best_pick_return - ai.worst_pick_return),
    watchlistVolatility: Math.abs(watchlist.best_pick_return - watchlist.worst_pick_return),
    
    // Consistency metrics
    aiConsistency: ai.win_rate * (1 - Math.abs(ai.best_pick_return - ai.worst_pick_return) / 100),
    watchlistConsistency: watchlist.win_rate * (1 - Math.abs(watchlist.best_pick_return - watchlist.worst_pick_return) / 100),
  };
}

export function getPerformanceInsights(data: AIVsWatchlistPerformance): string[] {
  const metrics = calculatePerformanceMetrics(data);
  const insights: string[] = [];
  
  // Performance insights
  if (Math.abs(metrics.returnDifference) > 5) {
    const winner = metrics.returnDifference > 0 ? 'Watchlist' : 'AI';
    insights.push(`${winner} significantly outperforms with ${Math.abs(metrics.returnDifference).toFixed(1)}% higher average returns`);
  }
  
  // Win rate insights
  if (Math.abs(metrics.winRateDifference) > 0.1) {
    const winner = metrics.winRateDifference > 0 ? 'Watchlist' : 'AI';
    insights.push(`${winner} has a ${Math.abs(metrics.winRateDifference * 100).toFixed(1)}% higher win rate`);
  }
  
  // Volume insights
  if (metrics.aiPicksPerDay > metrics.watchlistTradesPerDay * 2) {
    insights.push(`AI generates ${metrics.aiPicksPerDay.toFixed(1)} picks per day vs ${metrics.watchlistTradesPerDay.toFixed(1)} watchlist trades`);
  }
  
  // Risk insights
  if (metrics.aiVolatility > metrics.watchlistVolatility * 1.5) {
    insights.push('AI picks show higher volatility in outcomes');
  } else if (metrics.watchlistVolatility > metrics.aiVolatility * 1.5) {
    insights.push('Watchlist trades show higher volatility in outcomes');
  }
  
  // Consistency insights
  if (metrics.aiConsistency > metrics.watchlistConsistency) {
    insights.push('AI picks demonstrate more consistent performance');
  } else if (metrics.watchlistConsistency > metrics.aiConsistency) {
    insights.push('Watchlist trades show more consistent performance');
  }
  
  return insights.length > 0 ? insights : ['Performance data is too limited for detailed insights'];
}
