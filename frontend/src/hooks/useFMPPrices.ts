'use client';

/**
 * FMP Real-time Price Hook (Multiple Symbols)
 * Fetches current prices for multiple stocks using FMP API
 * 5-minute caching per symbol, auto-detects market hours
 */

import { useState, useEffect, useCallback } from 'react';

const FMP_API_KEY = process.env.NEXT_PUBLIC_FMP_API_KEY;
const FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export interface PriceData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  dayHigh: number;
  dayLow: number;
  previousClose: number;
  timestamp: number;
}

interface PriceCache {
  [symbol: string]: {
    data: PriceData;
    timestamp: number;
  };
}

const priceCache: PriceCache = {};

/**
 * Check if current time is during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
 */
function isMarketHours(): boolean {
  const now = new Date();
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  
  const day = et.getDay();
  const hour = et.getHours();
  const minute = et.getMinutes();
  
  // Weekend
  if (day === 0 || day === 6) return false;
  
  // Before 9:30 AM
  if (hour < 9 || (hour === 9 && minute < 30)) return false;
  
  // After 4:00 PM
  if (hour >= 16) return false;
  
  return true;
}

/**
 * Fetch price from FMP API
 */
async function fetchFMPPrice(symbol: string): Promise<PriceData | null> {
  if (!FMP_API_KEY) {
    console.warn('FMP API key not configured');
    return null;
  }

  try {
    const url = `${FMP_BASE_URL}/quote/${symbol}?apikey=${FMP_API_KEY}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      console.error(`FMP API error for ${symbol}:`, response.status);
      return null;
    }

    const data = await response.json();
    
    if (!data || data.length === 0) {
      console.warn(`No data returned for ${symbol}`);
      return null;
    }

    const quote = data[0];
    
    return {
      symbol: quote.symbol,
      price: quote.price,
      change: quote.change,
      changePercent: quote.changesPercentage,
      volume: quote.volume,
      dayHigh: quote.dayHigh,
      dayLow: quote.dayLow,
      previousClose: quote.previousClose,
      timestamp: Date.now(),
    };
  } catch (error) {
    console.error(`Error fetching price for ${symbol}:`, error);
    return null;
  }
}

/**
 * Get cached price or fetch new one
 */
async function getCachedPrice(symbol: string): Promise<PriceData | null> {
  const cached = priceCache[symbol];
  const now = Date.now();
  
  // Return cached if still valid
  if (cached && (now - cached.timestamp) < CACHE_TTL) {
    return cached.data;
  }
  
  // Fetch new price
  const priceData = await fetchFMPPrice(symbol);
  
  if (priceData) {
    priceCache[symbol] = {
      data: priceData,
      timestamp: now,
    };
  }
  
  // If fetch failed but we have expired cache, return it as fallback
  if (!priceData && cached) {
    return cached.data;
  }
  
  return priceData;
}

/**
 * Hook to fetch real-time prices for multiple symbols
 */
export function useFMPPrices(symbols: string[], enabled: boolean = true) {
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPrices = useCallback(async () => {
    if (!enabled || symbols.length === 0) return;

    setIsLoading(true);
    setError(null);

    try {
      const pricePromises = symbols.map(symbol => getCachedPrice(symbol));
      const results = await Promise.all(pricePromises);
      
      const priceMap: Record<string, PriceData> = {};
      results.forEach((priceData, index) => {
        if (priceData) {
          priceMap[symbols[index]] = priceData;
        }
      });
      
      setPrices(priceMap);
    } catch (err) {
      setError('Failed to fetch prices');
      console.error('Error fetching prices:', err);
    } finally {
      setIsLoading(false);
    }
  }, [symbols, enabled]);

  // Initial fetch
  useEffect(() => {
    fetchPrices();
  }, [fetchPrices]);

  // Auto-refresh during market hours (every 5 minutes)
  useEffect(() => {
    if (!enabled || symbols.length === 0) return;

    const interval = setInterval(() => {
      if (isMarketHours()) {
        fetchPrices();
      }
    }, CACHE_TTL);

    return () => clearInterval(interval);
  }, [fetchPrices, enabled, symbols.length]);

  return {
    prices,
    isLoading,
    error,
    refresh: fetchPrices,
  };
}

