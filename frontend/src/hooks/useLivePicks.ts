// src/hooks/useLivePicks.ts
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
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
  chartUrl?: string;
}

interface UseLivePicksOptions {
  bullishLimit?: number;
  bearishLimit?: number;
  refreshInterval?: number;
  enabled?: boolean;
  minConfidence?: number;
  enableSSE?: boolean;
  cacheTimeout?: number;
}

interface CacheEntry {
  data: LivePick[];
  timestamp: number;
}

export function useLivePicks({
  bullishLimit = 25,
  bearishLimit = 25,
  refreshInterval = 5 * 60 * 1000,
  enabled = true,
  minConfidence = 0.48,
  enableSSE = true,
  cacheTimeout = 30 * 1000, // 30 seconds
}: UseLivePicksOptions = {}) {
  const [picks, setPicks] = useState<LivePick[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRealTime, setIsRealTime] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  // Refs for cleanup
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const cacheRef = useRef<CacheEntry | null>(null);

  // Cache management
  const getCachedData = useCallback((): LivePick[] | null => {
    if (!cacheRef.current) return null;
    
    const isExpired = Date.now() - cacheRef.current.timestamp > cacheTimeout;
    if (isExpired) {
      cacheRef.current = null;
      return null;
    }
    
    return cacheRef.current.data;
  }, [cacheTimeout]);

  const setCachedData = useCallback((data: LivePick[]) => {
    cacheRef.current = {
      data,
      timestamp: Date.now()
    };
  }, []);

  const clearCache = useCallback(() => {
    cacheRef.current = null;
  }, []);

  // Transform API data to LivePick format
  const transformData = useCallback((alert: any, sentiment: 'bullish' | 'bearish'): LivePick => {
    const priceAtAlert = alert.entry_price || 0;
    // Use real-time current_price from FMP if available, otherwise fall back to entry price
    const currentPrice = alert.current_price || priceAtAlert;
    // Use pre-calculated change_pct from backend if available (real-time from FMP)
    const change = alert.change_pct ?? (priceAtAlert > 0 ? ((currentPrice - priceAtAlert) / priceAtAlert) * 100 : 0);

    // Dynamic entry ranges based on volatility and confidence
    const volatilityMultiplier = alert.volatility || 0.02; // Default 2%
    const confidenceValue = alert.confidence || 0;
    const confidenceAdjustment = confidenceValue > 80 ? 0.5 : 1.0; // Tighter range for high confidence

    const entryRange = volatilityMultiplier * confidenceAdjustment;

    // Confidence is already a percentage from backend (e.g., 85 not 0.85)
    const confidencePct = Math.round(confidenceValue);

    return {
      id: alert.id?.toString() || `${alert.symbol}-${Date.now()}`,
      symbol: alert.symbol,
      name: alert.company_name || `${alert.symbol} Inc.`,
      priceAtAlert,
      currentPrice,
      change,
      confidence: confidencePct,
      reasoning: alert.reasoning || alert.reasons?.[0] || 'AI pattern detected',
      entryPriceMin: priceAtAlert * (1 - entryRange),
      entryPriceMax: priceAtAlert * (1 + entryRange),
      targetPriceLow: alert.target_low || priceAtAlert * (sentiment === 'bullish' ? 1.10 : 0.90),
      targetPriceMid: alert.target_mid || ((alert.target_low || 0) + (alert.target_high || 0)) / 2 || priceAtAlert * (sentiment === 'bullish' ? 1.20 : 0.80),
      targetPriceHigh: alert.target_high || priceAtAlert * (sentiment === 'bullish' ? 1.35 : 0.65),
      stopLoss: alert.stop_loss || priceAtAlert * (sentiment === 'bullish' ? 0.92 : 1.08),
      aiSummary: alert.reasoning || `AI Confidence: ${confidencePct}%`,
      sentiment,
      timestamp: new Date(alert.created_at || alert.timestamp || Date.now()),
      chartUrl: alert.chart_url,
    };
  }, []);

  // Fetch picks from API
  const fetchPicks = useCallback(async (useCache = true): Promise<LivePick[]> => {
    if (!enabled) return [];

    // Check cache first
    if (useCache) {
      const cached = getCachedData();
      if (cached) {
        console.log('🔥 Using cached picks data');
        return cached;
      }
    }

    try {
      const minConfidencePercent = Math.round(minConfidence * 100);

      const [bullishData, bearishData] = await Promise.all([
        api.getLivePicks({ sentiment: 'bullish', limit: bullishLimit, min_confidence: minConfidencePercent }),
        api.getLivePicks({ sentiment: 'bearish', limit: bearishLimit, min_confidence: minConfidencePercent }),
      ]);

      const bullishPicks = bullishData.map(a => transformData(a, 'bullish'));
      const bearishPicks = bearishData.map(a => transformData(a, 'bearish'));
      const allPicks = [...bullishPicks, ...bearishPicks].sort((a, b) => b.confidence - a.confidence);

      // Cache the result
      setCachedData(allPicks);
      
      return allPicks;
    } catch (err) {
      console.error('Failed to fetch picks:', err);
      throw err;
    }
  }, [bullishLimit, bearishLimit, minConfidence, enabled, getCachedData, setCachedData, transformData]);

  // Setup Server-Sent Events
  const setupSSE = useCallback(() => {
    if (!enableSSE || !enabled) return;

    try {
      console.log('🔥 Setting up SSE connection...');
      setConnectionStatus('connecting');
      
      const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/picks/live/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('🔥 SSE connection established');
        setConnectionStatus('connected');
        setIsRealTime(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('🔥 Real-time update received:', data);
          
          if (data.picks && Array.isArray(data.picks)) {
            const transformedPicks = data.picks.map((pick: any) => 
              transformData(pick, pick.sentiment || 'bullish')
            );
            
            setPicks(transformedPicks);
            setCachedData(transformedPicks);
            setLastUpdated(new Date());
            setError(null);
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.warn('SSE connection failed, falling back to polling:', error);
        setConnectionStatus('disconnected');
        setIsRealTime(false);
        eventSource.close();
        startPolling();
      };

    } catch (error) {
      console.warn('SSE not supported, using polling:', error);
      setConnectionStatus('disconnected');
      startPolling();
    }
  }, [enableSSE, enabled, transformData, setCachedData]);

  // Setup polling fallback
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    console.log('🔄 Starting polling mode...');
    setIsRealTime(false);
    setConnectionStatus('disconnected');

    const poll = async () => {
      try {
        const data = await fetchPicks(true);
        setPicks(data);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        setError('Failed to load picks');
      }
    };

    // Initial fetch
    poll();

    // Setup interval
    if (refreshInterval > 0) {
      pollIntervalRef.current = setInterval(poll, refreshInterval);
    }
  }, [fetchPicks, refreshInterval]);

  // Manual refresh
  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    clearCache();
    
    try {
      const data = await fetchPicks(false);
      setPicks(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError('Failed to refresh picks');
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchPicks, clearCache]);

  // Test connection
  const testConnection = useCallback(async () => {
    try {
      await api.get('/health');
      return true;
    } catch {
      return false;
    }
  }, []);

  // Initialize
  useEffect(() => {
    if (!enabled) return;

    setIsLoading(true);
    
    // Try SSE first, fallback to polling
    if (enableSSE) {
      setupSSE();
    } else {
      startPolling();
    }

    // Initial data load
    fetchPicks(true).then(data => {
      setPicks(data);
      setLastUpdated(new Date());
      setIsLoading(false);
    }).catch(err => {
      setError('Failed to load initial picks');
      setIsLoading(false);
    });

    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [enabled, enableSSE, setupSSE, startPolling, fetchPicks]);

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
    
    // Advanced features
    isRealTime,
    connectionStatus,
    clearCache,
    testConnection,
  };
}
