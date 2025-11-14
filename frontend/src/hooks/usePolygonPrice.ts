// src/hooks/usePolygonPrice.ts
import { useState, useEffect, useRef } from 'react';

interface PriceData {
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
}

export function usePolygonPrice({
  ticker,
  entryPrice: initialEntryPrice,
  enabled = true,
  testMode = false
}: {
  ticker: string;
  entryPrice: number;
  enabled?: boolean;
  testMode?: boolean;
}) {
  const [priceData, setPriceData] = useState<PriceData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled || !ticker || testMode) return;

    const connect = () => {
      const ws = new WebSocket('wss://socket.polygon.io/stocks');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        ws.send(JSON.stringify({ action: 'auth', params: process.env.NEXT_PUBLIC_POLYGON_KEY }));
        ws.send(JSON.stringify({ action: 'subscribe', params: `T.${ticker}` }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (Array.isArray(data)) {
          data.forEach(msg => {
            if (msg.ev === 'T' && msg.sym === ticker) {
              const newPrice = msg.p;
              const change = newPrice - initialEntryPrice;
              const changePercent = (change / initialEntryPrice) * 100;

              setPriceData({
                price: newPrice,
                change,
                changePercent,
                volume: msg.s || 0,
                timestamp: msg.t || Date.now()
              });
            }
          });
        }
      };

      ws.onerror = () => setError('WebSocket error');
      ws.onclose = () => {
        setIsConnected(false);
        setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, [ticker, initialEntryPrice, enabled, testMode]);

  // Test mode
  useEffect(() => {
    if (!testMode || !enabled) return;
    const interval = setInterval(() => {
      const volatility = 0.02;
      const randomChange = (Math.random() - 0.5) * volatility * 2;
      const newPrice = initialEntryPrice * (1 + randomChange);
      const change = newPrice - initialEntryPrice;
      const changePercent = (change / initialEntryPrice) * 100;

      setPriceData({
        price: newPrice,
        change,
        changePercent,
        volume: Math.floor(Math.random() * 1000000),
        timestamp: Date.now()
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [testMode, enabled, initialEntryPrice]);

  return {
    priceData,
    isConnected,
    error,
    formattedPrice: priceData ? `$${priceData.price.toFixed(2)}` : null,
    formattedChange: priceData ? `${priceData.changePercent >= 0 ? '+' : ''}${priceData.changePercent.toFixed(2)}%` : null,
    isPositive: priceData ? priceData.changePercent >= 0 : null
  };
}