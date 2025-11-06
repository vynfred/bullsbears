'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, BullishAlertResponse, BearishAlertResponse } from '@/lib/api';

export interface LivePick {
  id: string;
  symbol: string;
  name: string;
  priceAtAlert: number;
  currentPrice: number;
  change: number;
  confidence: number;
  reasoning: string;
  entryPriceMin: number;
  entryPriceMax: number;
  targetPriceLow: number;
  targetPriceMid: number;
  targetPriceHigh: number;
  stopLoss: number;
  aiSummary: string;
  sentiment: 'bullish' | 'bearish';
  targetHit?: 'low' | 'mid' | 'high';
  timeToTargetHours?: number;
  timestamp: Date;
}

interface UseLivePicksOptions {
  bullishLimit?: number;
  bearishLimit?: number;
  refreshInterval?: number; // in milliseconds
  enabled?: boolean;
  minConfidence?: number;
}

interface UseLivePicksReturn {
  // Data
  picks: LivePick[];
  bullishPicks: LivePick[];
  bearishPicks: LivePick[];
  
  // Loading states
  isLoading: boolean;
  isRefreshing: boolean;
  
  // Error handling
  error: string | null;
  
  // Metadata
  lastUpdated: Date | null;
  
  // Actions
  refresh: () => Promise<void>;
  
  // Stats
  totalPicks: number;
  bullishCount: number;
  bearishCount: number;
}

// Transform backend response to frontend format
function transformBullishAlert(alert: BullishAlertResponse): LivePick {
  const currentPrice = alert.current_price || alert.entry_price || 100; // Fallback
  const priceAtAlert = alert.entry_price || currentPrice;
  const change = ((currentPrice - priceAtAlert) / priceAtAlert) * 100;
  
  return {
    id: alert.id.toString(),
    symbol: alert.symbol,
    name: alert.company_name || `${alert.symbol} Corporation`,
    priceAtAlert,
    currentPrice,
    change,
    confidence: Math.round(alert.confidence * 100),
    reasoning: alert.reasons?.[0] || 'AI-identified bullish pattern',
    entryPriceMin: priceAtAlert * 0.98,
    entryPriceMax: priceAtAlert * 1.02,
    targetPriceLow: priceAtAlert * 1.10,
    targetPriceMid: priceAtAlert * 1.20,
    targetPriceHigh: priceAtAlert * 1.35,
    stopLoss: priceAtAlert * 0.92,
    aiSummary: `Technical: ${alert.technical_score}/100, Sentiment: ${alert.sentiment_score}/100, Social: ${alert.social_score}/100. ${alert.reasons?.join('. ') || 'Strong bullish signals detected.'}`,
    sentiment: 'bullish',
    timestamp: new Date(alert.timestamp),
    targetHit: alert.alert_outcome === 'WIN' ? 'low' : undefined,
    timeToTargetHours: alert.days_to_move ? alert.days_to_move * 24 : undefined
  };
}

function transformBearishAlert(alert: BearishAlertResponse): LivePick {
  const currentPrice = alert.current_price || alert.entry_price || 100; // Fallback
  const priceAtAlert = alert.entry_price || currentPrice;
  const change = ((currentPrice - priceAtAlert) / priceAtAlert) * 100;
  
  return {
    id: alert.id.toString(),
    symbol: alert.symbol,
    name: alert.company_name || `${alert.symbol} Corporation`,
    priceAtAlert,
    currentPrice,
    change,
    confidence: Math.round(alert.confidence * 100),
    reasoning: alert.reasons?.[0] || 'AI-identified bearish pattern',
    entryPriceMin: priceAtAlert * 0.98,
    entryPriceMax: priceAtAlert * 1.02,
    targetPriceLow: priceAtAlert * 0.90,
    targetPriceMid: priceAtAlert * 0.80,
    targetPriceHigh: priceAtAlert * 0.65,
    stopLoss: priceAtAlert * 1.08,
    aiSummary: `Technical: ${alert.technical_score}/100, Sentiment: ${alert.sentiment_score}/100, Social: ${alert.social_score}/100. ${alert.reasons?.join('. ') || 'Strong bearish signals detected.'}`,
    sentiment: 'bearish',
    timestamp: new Date(alert.timestamp),
    targetHit: alert.alert_outcome === 'WIN' ? 'low' : undefined,
    timeToTargetHours: alert.days_to_move ? alert.days_to_move * 24 : undefined
  };
}

export function useLivePicks(options: UseLivePicksOptions = {}): UseLivePicksReturn {
  const {
    bullishLimit = 25,
    bearishLimit = 25,
    refreshInterval = 5 * 60 * 1000, // 5 minutes default
    enabled = true,
    minConfidence = 0.48 // 48% minimum confidence
  } = options;

  const [picks, setPicks] = useState<LivePick[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchPicks = useCallback(async () => {
    if (!enabled) return;

    try {
      setError(null);
      console.log('🔄 Fetching live picks from backend...');
      
      // Fetch both bullish and bearish alerts in parallel
      const [bullishData, bearishData] = await Promise.all([
        api.getBullishAlerts(bullishLimit, minConfidence).catch(err => {
          console.warn('Bullish alerts failed, using empty array:', err.message);
          return [];
        }),
        api.getBearishAlerts(bearishLimit, minConfidence).catch(err => {
          console.warn('Bearish alerts failed, using empty array:', err.message);
          return [];
        })
      ]);

      // Transform and combine data
      const bullishPicks = bullishData.map(transformBullishAlert);
      const bearishPicks = bearishData.map(transformBearishAlert);
      const allPicks = [...bullishPicks, ...bearishPicks];

      // Sort by confidence descending, then by timestamp descending
      allPicks.sort((a, b) => {
        if (b.confidence !== a.confidence) {
          return b.confidence - a.confidence;
        }
        return b.timestamp.getTime() - a.timestamp.getTime();
      });

      setPicks(allPicks);
      setLastUpdated(new Date());
      console.log(`✅ Loaded ${allPicks.length} picks (${bullishPicks.length} bullish, ${bearishPicks.length} bearish)`);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch picks';
      console.error('❌ Error fetching picks:', errorMessage);
      setError(errorMessage);
    }
  }, [enabled, bullishLimit, bearishLimit, minConfidence]);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    await fetchPicks();
    setIsRefreshing(false);
  }, [fetchPicks]);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      await fetchPicks();
      setIsLoading(false);
    };
    
    loadData();
  }, [fetchPicks]);

  // Auto-refresh interval
  useEffect(() => {
    if (!enabled || refreshInterval <= 0) return;

    const interval = setInterval(fetchPicks, refreshInterval);
    return () => clearInterval(interval);
  }, [enabled, refreshInterval, fetchPicks]);

  // Computed values
  const bullishPicks = picks.filter(p => p.sentiment === 'bullish');
  const bearishPicks = picks.filter(p => p.sentiment === 'bearish');

  return {
    picks,
    bullishPicks,
    bearishPicks,
    isLoading,
    isRefreshing,
    error,
    lastUpdated,
    refresh,
    totalPicks: picks.length,
    bullishCount: bullishPicks.length,
    bearishCount: bearishPicks.length
  };
}
