// src/hooks/useLivePicks.ts
'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

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
  timestamp: Date;
}

interface UseLivePicksOptions {
  bullishLimit?: number;
  bearishLimit?: number;
  refreshInterval?: number;
  enabled?: boolean;
  minConfidence?: number;
}

export function useLivePicks({
  bullishLimit = 25,
  bearishLimit = 25,
  refreshInterval = 5 * 60 * 1000,
  enabled = true,
  minConfidence = 0.48,
}: UseLivePicksOptions = {}) {
  const [picks, setPicks] = useState<LivePick[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchPicks = useCallback(async () => {
    if (!enabled) return;

    try {
      setError(null);
      setIsLoading(true);

      const minConfidencePercent = Math.round(minConfidence * 100);

      const [bullishData, bearishData] = await Promise.all([
        api.getLivePicks({ sentiment: 'bullish', limit: bullishLimit, min_confidence: minConfidencePercent }),
        api.getLivePicks({ sentiment: 'bearish', limit: bearishLimit, min_confidence: minConfidencePercent }),
      ]);

      const transform = (alert: any, sentiment: 'bullish' | 'bearish'): LivePick => {
        const priceAtAlert = alert.entry_price || alert.current_price || 0;
        const currentPrice = alert.current_price || priceAtAlert;
        const change = priceAtAlert > 0 ? ((currentPrice - priceAtAlert) / priceAtAlert) * 100 : 0;

        return {
          id: alert.id?.toString() || `${alert.symbol}-${Date.now()}`,
          symbol: alert.symbol,
          name: alert.company_name || `${alert.symbol} Inc.`,
          priceAtAlert,
          currentPrice,
          change,
          confidence: Math.round((alert.confidence || 0) * 100),
          reasoning: alert.reasons?.[0] || 'AI pattern detected',
          entryPriceMin: priceAtAlert * 0.98,
          entryPriceMax: priceAtAlert * 1.02,
          targetPriceLow: alert.target_price_low || priceAtAlert * (sentiment === 'bullish' ? 1.10 : 0.90),
          targetPriceMid: alert.target_price_mid || priceAtAlert * (sentiment === 'bullish' ? 1.20 : 0.80),
          targetPriceHigh: alert.target_price_high || priceAtAlert * (sentiment === 'bullish' ? 1.35 : 0.65),
          stopLoss: alert.stop_loss || priceAtAlert * (sentiment === 'bullish' ? 0.92 : 1.08),
          aiSummary: `Confidence: ${Math.round((alert.confidence || 0) * 100)}%`,
          sentiment,
          timestamp: new Date(alert.timestamp || Date.now()),
        };
      };

      const bullishPicks = bullishData.map(a => transform(a, 'bullish'));
      const bearishPicks = bearishData.map(a => transform(a, 'bearish'));
      const allPicks = [...bullishPicks, ...bearishPicks].sort((a, b) => b.confidence - a.confidence);

      setPicks(allPicks);
      setLastUpdated(new Date());
    } catch (err) {
      setError('Failed to load picks');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [bullishLimit, bearishLimit, minConfidence, enabled]);

  const refresh = useCallback(() => {
    setIsRefreshing(true);
    return fetchPicks();
  }, [fetchPicks]);

  useEffect(() => {
    fetchPicks();
    if (refreshInterval > 0) {
      const id = setInterval(fetchPicks, refreshInterval);
      return () => clearInterval(id);
    }
  }, [fetchPicks, refreshInterval]);

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
    bearishCount: bearishPicks.length,
  };
}