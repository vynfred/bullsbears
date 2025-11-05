/**
 * Hook for managing live moon/rug alerts from the backend
 */
import { useState, useEffect, useCallback } from 'react';
import api, { MoonAlert } from '@/lib/api';

interface UseLiveAlertsOptions {
  moonLimit?: number;
  rugLimit?: number;
  refreshInterval?: number; // in milliseconds
  enabled?: boolean;
}

interface UseLiveAlertsReturn {
  alerts: MoonAlert[];
  moonAlerts: MoonAlert[];
  rugAlerts: MoonAlert[];
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
}

export function useLiveAlerts(options: UseLiveAlertsOptions = {}): UseLiveAlertsReturn {
  const {
    moonLimit = 10,
    rugLimit = 10,
    refreshInterval = 5 * 60 * 1000, // 5 minutes default
    enabled = true
  } = options;

  const [alerts, setAlerts] = useState<MoonAlert[]>([]);
  const [moonAlerts, setMoonAlerts] = useState<MoonAlert[]>([]);
  const [rugAlerts, setRugAlerts] = useState<MoonAlert[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAlerts = useCallback(async () => {
    if (!enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      console.log('🔄 Fetching live alerts from backend...');
      
      // Fetch both moon and rug alerts in parallel
      const [moonData, rugData] = await Promise.all([
        api.getMoonAlerts(moonLimit).catch(err => {
          console.warn('Moon alerts failed, using empty array:', err.message);
          return [];
        }),
        api.getRugAlerts(rugLimit).catch(err => {
          console.warn('Rug alerts failed, using empty array:', err.message);
          return [];
        })
      ]);

      console.log(`✅ Fetched ${moonData.length} moon alerts, ${rugData.length} rug alerts`);

      // Update individual alert arrays
      setMoonAlerts(moonData);
      setRugAlerts(rugData);

      // Combine and sort by timestamp (newest first)
      const allAlerts = [...moonData, ...rugData];
      const sortedAlerts = allAlerts.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

      setAlerts(sortedAlerts);
      setLastUpdated(new Date());
      
      console.log(`📊 Total alerts loaded: ${sortedAlerts.length}`);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch alerts';
      console.error('❌ Error fetching live alerts:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [enabled, moonLimit, rugLimit]);

  // Initial fetch
  useEffect(() => {
    if (enabled) {
      fetchAlerts();
    }
  }, [fetchAlerts, enabled]);

  // Set up refresh interval
  useEffect(() => {
    if (!enabled || refreshInterval <= 0) return;

    const interval = setInterval(() => {
      console.log('🔄 Auto-refreshing alerts...');
      fetchAlerts();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchAlerts, refreshInterval, enabled]);

  const refresh = useCallback(async () => {
    await fetchAlerts();
  }, [fetchAlerts]);

  return {
    alerts,
    moonAlerts,
    rugAlerts,
    isLoading,
    error,
    lastUpdated,
    refresh
  };
}

// Future: Add watchlist hooks here
