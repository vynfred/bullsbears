/**
 * Firebase Real-time Database Service for BullsBears
 * Connects to live picks data from the 18-agent system
 */

export interface FirebasePick {
  symbol: string;
  direction: "bullish" | "bearish";
  confidence: number;
  target_low: number;
  target_medium: number;
  target_high: number;
  current_price: number;
  reasoning: string;
  agents_consensus: {
    technical_score: number;
    fundamental_score: number;
    sentiment_score: number;
    vision_score: number;
  };
  risk_level: string;
  estimated_days: number;
  created_at: string;
}

export interface FirebasePicksData {
  timestamp: string;
  picks: FirebasePick[];
  metadata: {
    total_picks: number;
    analysis_time: string;
    system_version: string;
  };
}

export interface FirebaseWatchlistData {
  symbol: string;
  current_price: number;
  change_percent: number;
  sentiment_score: number;
  last_updated: string;
  news_sentiment?: {
    score: number;
    articles_count: number;
  };
  social_sentiment?: {
    score: number;
    mentions_count: number;
  };
}

export interface FirebaseAnalyticsData {
  accuracy_metrics: {
    win_rate: number;
    total_picks: number;
    successful_picks: number;
  };
  performance_history: Array<{
    date: string;
    accuracy: number;
    picks_count: number;
  }>;
  win_rate: number;
  total_picks: number;
  last_updated: string;
}

class FirebaseService {
  private baseUrl = "https://bullsbears-xyz-default-rtdb.firebaseio.com";
  private cache = new Map<string, { data: any; timestamp: number }>();
  private cacheTimeout = 30000; // 30 seconds

  /**
   * Get latest AI picks from Firebase
   */
  async getLatestPicks(): Promise<FirebasePicksData | null> {
    try {
      const cacheKey = "latest_picks";
      const cached = this.cache.get(cacheKey);

      if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
        console.log("🔥 Using cached picks data");
        return cached.data;
      }

      const url = `${this.baseUrl}/picks/latest.json`;
      console.log("🔥 Fetching picks from:", url);

      const response = await fetch(url);

      console.log("🔥 Firebase response status:", response.status);

      if (!response.ok) {
        console.error("Failed to fetch picks:", response.status, response.statusText);
        return null;
      }

      const data = await response.json();

      console.log("🔥 Firebase data received:", data);

      if (!data) {
        console.warn("No picks data available");
        return null;
      }

      // Cache the result
      this.cache.set(cacheKey, { data, timestamp: Date.now() });

      console.log(`🔥 Successfully loaded ${data.picks?.length || 0} picks from Firebase`);

      return data;
    } catch (error) {
      console.error("🔥 Error fetching picks:", error);
      return null;
    }
  }

  /**
   * Get watchlist data for a specific symbol
   */
  async getWatchlistData(symbol: string): Promise<FirebaseWatchlistData | null> {
    try {
      const response = await fetch(`${this.baseUrl}/watchlist/${symbol}.json`);
      
      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`Error fetching watchlist data for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * Get analytics data
   */
  async getAnalyticsData(): Promise<FirebaseAnalyticsData | null> {
    try {
      const cacheKey = "analytics_data";
      const cached = this.cache.get(cacheKey);
      
      if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
        return cached.data;
      }

      const response = await fetch(`${this.baseUrl}/analytics/latest.json`);
      
      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      
      // Cache the result
      this.cache.set(cacheKey, { data, timestamp: Date.now() });
      
      return data;
    } catch (error) {
      console.error("Error fetching analytics data:", error);
      return null;
    }
  }

  /**
   * Subscribe to real-time picks updates using Server-Sent Events
   */
  subscribeToPicksUpdates(callback: (data: FirebasePicksData) => void): () => void {
    let eventSource: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;

    // Try Server-Sent Events first (if supported)
    try {
      eventSource = new EventSource(`${this.baseUrl}/pulse/latest.json`);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data) {
            callback(data);
          }
        } catch (error) {
          console.error("Error parsing SSE data:", error);
        }
      };

      eventSource.onerror = () => {
        console.warn("SSE connection failed, falling back to polling");
        eventSource?.close();
        startPolling();
      };
    } catch (error) {
      console.warn("SSE not supported, using polling");
      startPolling();
    }

    // Fallback to polling
    function startPolling() {
      pollInterval = setInterval(async () => {
        const data = await firebaseService.getLatestPicks();
        if (data) {
          callback(data);
        }
      }, 15000); // Poll every 15 seconds
    }

    // Return cleanup function
    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }

  /**
   * Test Firebase connection
   */
  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/.json`);
      return response.ok;
    } catch (error) {
      console.error("Firebase connection test failed:", error);
      return false;
    }
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }
}

// Export singleton instance
export const firebaseService = new FirebaseService();

// Utility functions for converting Firebase data to frontend format
export function convertFirebasePickToLivePick(firebasePick: FirebasePick): any {
  return {
    id: `${firebasePick.symbol}_${Date.now()}`,
    symbol: firebasePick.symbol,
    name: `${firebasePick.symbol} Corporation`, // You might want to fetch real company names
    priceAtAlert: firebasePick.current_price,
    currentPrice: firebasePick.current_price,
    change: 0, // Will be calculated based on real-time updates
    confidence: Math.round(firebasePick.confidence * 100),
    reasoning: firebasePick.reasoning,
    entryPriceMin: firebasePick.current_price * 0.98,
    entryPriceMax: firebasePick.current_price * 1.02,
    targetPriceLow: firebasePick.target_low,
    targetPriceMid: firebasePick.target_medium,
    targetPriceHigh: firebasePick.target_high,
    stopLoss: firebasePick.current_price * (firebasePick.direction === "bullish" ? 0.95 : 1.05),
    aiSummary: `Our 18-agent ML system identified ${firebasePick.symbol} with ${(firebasePick.confidence * 100).toFixed(0)}% confidence. ${firebasePick.reasoning} Technical score: ${(firebasePick.agents_consensus.technical_score * 100).toFixed(0)}%, Fundamental: ${(firebasePick.agents_consensus.fundamental_score * 100).toFixed(0)}%, Sentiment: ${(firebasePick.agents_consensus.sentiment_score * 100).toFixed(0)}%, Vision: ${(firebasePick.agents_consensus.vision_score * 100).toFixed(0)}%.`,
    sentiment: firebasePick.direction,
    targetHit: null,
    estimatedDays: firebasePick.estimated_days,
    riskLevel: firebasePick.risk_level,
    createdAt: firebasePick.created_at
  };
}

// Test function for development
export async function testFirebaseConnection() {
  console.log("🔥 Testing Firebase connection...");
  
  const isConnected = await firebaseService.testConnection();
  console.log(`Connection: ${isConnected ? "✅ SUCCESS" : "❌ FAILED"}`);
  
  if (isConnected) {
    const picks = await firebaseService.getLatestPicks();
    console.log(`Latest picks: ${picks ? `✅ ${picks.picks.length} picks found` : "❌ No picks"}`);
    
    if (picks) {
      console.log("📊 Picks data:", picks);
    }
  }
  
  return isConnected;
}
