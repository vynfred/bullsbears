'use client';

import { useState, useEffect, useRef } from 'react';

interface PriceData {
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
}

interface UsePolygonPriceOptions {
  ticker: string;
  entryPrice: number;
  enabled?: boolean;
  testMode?: boolean; // For development with mock data
}

export function usePolygonPrice({ 
  ticker, 
  entryPrice, 
  enabled = true, 
  testMode = true // Default to test mode during development
}: UsePolygonPriceOptions) {
  const [priceData, setPriceData] = useState<PriceData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!enabled || !ticker) return;

    if (testMode) {
      // Mock data for development
      const generateMockPrice = () => {
        const basePrice = entryPrice;
        const volatility = 0.02; // 2% volatility
        const randomChange = (Math.random() - 0.5) * volatility * 2;
        const newPrice = basePrice * (1 + randomChange);
        const change = newPrice - entryPrice;
        const changePercent = (change / entryPrice) * 100;
        
        setPriceData({
          price: newPrice,
          change,
          changePercent,
          volume: Math.floor(Math.random() * 1000000) + 100000,
          timestamp: Date.now()
        });
      };

      // Initial price
      generateMockPrice();
      
      // Update every 5 seconds for testing
      const interval = setInterval(generateMockPrice, 5000);
      
      return () => clearInterval(interval);
    }

    // Real Polygon.io WebSocket connection
    const connectWebSocket = () => {
      try {
        // Note: In production, API key should come from environment variables
        const apiKey = process.env.NEXT_PUBLIC_POLYGON_API_KEY || 'YOUR_FREE_KEY';
        
        wsRef.current = new WebSocket('wss://socket.polygon.io/stocks');
        
        wsRef.current.onopen = () => {
          console.log('Polygon WebSocket connected');
          setIsConnected(true);
          setError(null);
          
          // Authenticate
          wsRef.current?.send(JSON.stringify({
            action: 'auth',
            params: apiKey
          }));
          
          // Subscribe to ticker
          wsRef.current?.send(JSON.stringify({
            action: 'subscribe',
            params: `T.${ticker}`
          }));
        };

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // Handle different message types
            if (Array.isArray(data)) {
              data.forEach((message) => {
                if (message.ev === 'T' && message.sym === ticker) {
                  // Trade message
                  const newPrice = message.p;
                  const change = newPrice - entryPrice;
                  const changePercent = (change / entryPrice) * 100;
                  
                  setPriceData({
                    price: newPrice,
                    change,
                    changePercent,
                    volume: message.s || 0,
                    timestamp: message.t || Date.now()
                  });
                }
              });
            } else if (data.ev === 'status') {
              console.log('Polygon status:', data.message);
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('Polygon WebSocket error:', error);
          setError('WebSocket connection error');
          setIsConnected(false);
        };

        wsRef.current.onclose = (event) => {
          console.log('Polygon WebSocket closed:', event.code, event.reason);
          setIsConnected(false);
          
          // Attempt to reconnect after 5 seconds
          if (enabled) {
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log('Attempting to reconnect...');
              connectWebSocket();
            }, 5000);
          }
        };

      } catch (err) {
        console.error('Error creating WebSocket connection:', err);
        setError('Failed to create WebSocket connection');
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [ticker, entryPrice, enabled, testMode]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    priceData,
    isConnected,
    error,
    // Helper functions
    isPositive: priceData ? priceData.changePercent >= 0 : null,
    formattedPrice: priceData ? `$${priceData.price.toFixed(2)}` : null,
    formattedChange: priceData ? `${priceData.changePercent >= 0 ? '+' : ''}${priceData.changePercent.toFixed(1)}%` : null,
    formattedVolume: priceData ? priceData.volume.toLocaleString() : null
  };
}
