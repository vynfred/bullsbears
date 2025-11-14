/**
 * React hook for Firebase real-time picks
 * Connects to BullsBears 18-agent system picks
 */

import { useState, useEffect, useCallback } from 'react';
import { firebaseService, FirebasePicksData, convertFirebasePickToLivePick } from '@/lib/firebase';

export interface FirebasePicksState {
  picks: any[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
  metadata: {
    total_picks: number;
    system_version: string;
    analysis_time: string;
  } | null;
}

export function useFirebasePicks() {
  const [state, setState] = useState<FirebasePicksState>({
    picks: [],
    loading: true,
    error: null,
    lastUpdated: null,
    metadata: null
  });

  const [isRealTime, setIsRealTime] = useState(false);

  // Fetch picks from Firebase
  const fetchPicks = useCallback(async () => {
    try {
      console.log("🔥 useFirebasePicks: Starting fetch...");
      setState(prev => ({ ...prev, loading: true, error: null }));

      const data = await firebaseService.getLatestPicks();

      console.log("🔥 useFirebasePicks: Received data:", data);

      if (data) {
        const convertedPicks = data.picks.map(convertFirebasePickToLivePick);

        console.log("🔥 useFirebasePicks: Converted picks:", convertedPicks);

        setState({
          picks: convertedPicks,
          loading: false,
          error: null,
          lastUpdated: data.timestamp,
          metadata: data.metadata
        });

        console.log(`🔥 useFirebasePicks: Successfully loaded ${convertedPicks.length} picks`);
      } else {
        console.warn("🔥 useFirebasePicks: No data received from Firebase");
        setState(prev => ({
          ...prev,
          loading: false,
          error: "No picks data available"
        }));
      }
    } catch (error) {
      console.error("🔥 useFirebasePicks: Error fetching picks:", error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : "Failed to load picks"
      }));
    }
  }, []);

  // Subscribe to real-time updates
  const subscribeToUpdates = useCallback(() => {
    console.log("🔥 Subscribing to real-time picks updates...");
    
    const unsubscribe = firebaseService.subscribeToPicksUpdates((data: FirebasePicksData) => {
      console.log("🔥 Real-time update received:", data);
      
      const convertedPicks = data.picks.map(convertFirebasePickToLivePick);
      
      setState({
        picks: convertedPicks,
        loading: false,
        error: null,
        lastUpdated: data.timestamp,
        metadata: data.metadata
      });
      
      setIsRealTime(true);
    });

    return unsubscribe;
  }, []);

  // Refresh picks manually
  const refreshPicks = useCallback(async () => {
    console.log("🔄 Manually refreshing picks...");
    firebaseService.clearCache();
    await fetchPicks();
  }, [fetchPicks]);

  // Test Firebase connection
  const testConnection = useCallback(async () => {
    try {
      const isConnected = await firebaseService.testConnection();
      console.log(`🔥 Firebase connection test: ${isConnected ? "✅ SUCCESS" : "❌ FAILED"}`);
      return isConnected;
    } catch (error) {
      console.error("Firebase connection test error:", error);
      return false;
    }
  }, []);

  // Initialize on mount
  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const initialize = async () => {
      console.log("🔥 Initializing Firebase picks...");
      
      // Test connection first
      const isConnected = await testConnection();
      
      if (isConnected) {
        // Fetch initial data
        await fetchPicks();
        
        // Subscribe to real-time updates
        unsubscribe = subscribeToUpdates();
      } else {
        setState(prev => ({
          ...prev,
          loading: false,
          error: "Firebase connection failed"
        }));
      }
    };

    initialize();

    // Cleanup on unmount
    return () => {
      if (unsubscribe) {
        console.log("🔥 Unsubscribing from Firebase updates");
        unsubscribe();
      }
    };
  }, [fetchPicks, subscribeToUpdates, testConnection]);

  // Auto-refresh every 5 minutes as fallback
  useEffect(() => {
    if (!isRealTime) {
      const interval = setInterval(() => {
        console.log("🔄 Auto-refreshing picks (fallback)...");
        refreshPicks();
      }, 5 * 60 * 1000); // 5 minutes

      return () => clearInterval(interval);
    }
  }, [isRealTime, refreshPicks]);

  return {
    ...state,
    isRealTime,
    refreshPicks,
    testConnection
  };
}

// Hook for Firebase analytics data
export function useFirebaseAnalytics() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await firebaseService.getAnalyticsData();
      
      if (data) {
        setAnalytics(data);
      } else {
        setError("No analytics data available");
      }
    } catch (error) {
      console.error("Error fetching analytics:", error);
      setError(error instanceof Error ? error.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return {
    analytics,
    loading,
    error,
    refreshAnalytics: fetchAnalytics
  };
}

// Hook for Firebase watchlist data
export function useFirebaseWatchlist(symbols: string[]) {
  const [watchlistData, setWatchlistData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWatchlistData = useCallback(async () => {
    if (symbols.length === 0) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const data: Record<string, any> = {};
      
      // Fetch data for each symbol
      await Promise.all(
        symbols.map(async (symbol) => {
          const symbolData = await firebaseService.getWatchlistData(symbol);
          if (symbolData) {
            data[symbol] = symbolData;
          }
        })
      );
      
      setWatchlistData(data);
    } catch (error) {
      console.error("Error fetching watchlist data:", error);
      setError(error instanceof Error ? error.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, [symbols]);

  useEffect(() => {
    fetchWatchlistData();
  }, [fetchWatchlistData]);

  return {
    watchlistData,
    loading,
    error,
    refreshWatchlist: fetchWatchlistData
  };
}
