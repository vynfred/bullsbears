'use client';

import React, { useState } from 'react';
import { Star, TrendingUp, TrendingDown } from 'lucide-react';
import { MoonAlert } from '@/lib/demoData';
import { usePolygonPrice } from '@/hooks/usePolygonPrice';

interface PulseStockCardProps {
  alert: MoonAlert;
  onVote: (alertId: string, vote: 'UP' | 'DOWN' | 'PASS') => void;
  onAddToWatchlist?: (alertId: string) => void;
  onShowDetails?: (alertId: string) => void;
  onGutCheck?: (alertId: string) => void;
}

interface LivePrice {
  price: number;
  change: number;
  changePercent: number;
}

export function PulseStockCard({
  alert,
  onVote,
  onAddToWatchlist,
  onShowDetails,
  onGutCheck
}: PulseStockCardProps) {
  const [isInWatchlist, setIsInWatchlist] = useState(false);

  // Real-time price tracking with Polygon.io (test mode enabled for development)
  const { priceData, isConnected, formattedPrice, formattedChange, isPositive } = usePolygonPrice({
    ticker: alert.ticker,
    entryPrice: alert.entryPrice,
    enabled: true,
    testMode: true // Switch to false when ready for production
  });

  // Use real-time data if available, otherwise fall back to alert data
  const currentPrice = priceData?.price || alert.currentPrice || alert.entryPrice;
  const priceChange = priceData?.changePercent || ((currentPrice - alert.entryPrice) / alert.entryPrice) * 100;
  const dollarChange = priceData?.change || (currentPrice - alert.entryPrice);

  // Format alert time
  const alertTime = new Date(alert.timestamp).toLocaleString('en-US', {
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  // Calculate target prices
  const lowTargetPrice = alert.entryPrice * (1 + alert.targetRange.low / 100);
  const avgTargetPrice = alert.entryPrice * (1 + alert.targetRange.avg / 100);
  const highTargetPrice = alert.entryPrice * (1 + alert.targetRange.high / 100);
  const stopLossPrice = alert.entryPrice * 0.95; // -5% stop loss

  // Price blink animation when price updates
  const [priceBlinking, setPriceBlinking] = useState(false);

  React.useEffect(() => {
    if (priceData) {
      setPriceBlinking(true);
      const timeout = setTimeout(() => setPriceBlinking(false), 500);
      return () => clearTimeout(timeout);
    }
  }, [priceData?.timestamp]);

  const handleWatchlistToggle = () => {
    setIsInWatchlist(!isInWatchlist);
    onAddToWatchlist?.(alert.id);
  };

  const handleGutCheckClick = () => {
    onGutCheck?.(alert.id);
  };

  // Display values (using real-time data when available)
  const displayPrice = currentPrice;
  const displayChange = priceChange;
  const displayIsPositive = isPositive !== null ? isPositive : priceChange >= 0;

  return (
    <div className="bg-[#111827] rounded-2xl p-5 border border-cyan-500/30">
      {/* Ticker + Star */}
      <div className="flex justify-between items-center mb-3">
        <div className="font-mono text-2xl font-black text-cyan-400">
          {alert.ticker}
        </div>
        <button 
          onClick={handleWatchlistToggle}
          className="text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          <Star className={`w-5 h-5 ${isInWatchlist ? 'fill-current' : ''}`} />
          <span className="ml-1 text-sm">Add to Watchlist</span>
        </button>
      </div>

      {/* Price + Change */}
      <div className={`text-3xl font-black mb-1 transition-all duration-300 ${
        priceBlinking ? 'scale-105' : ''
      } ${
        displayIsPositive ? 'text-green-400' : 'text-red-400'
      }`}>
        {displayIsPositive ? '+' : ''}{displayChange.toFixed(1)}%
      </div>
      <div className="text-sm text-gray-400">
        ${alert.entryPrice.toFixed(2)} → ${displayPrice.toFixed(2)}
      </div>

      {/* Alert Time */}
      <div className="text-xs text-gray-500 mt-1">
        Alerted: {alertTime}
      </div>

      {/* Window */}
      <div className="bg-gray-800/50 rounded-lg px-4 py-2 my-4 text-sm">
        {alert.targetRange.estimatedDays}-day window — {alert.type} possible
      </div>

      {/* Targets */}
      <div className="grid grid-cols-3 gap-3 text-sm mb-4">
        <div>
          <div className="text-gray-500">Low</div>
          <div className="font-bold text-yellow-400">+{alert.targetRange.low}%</div>
          <div className="text-xs">${lowTargetPrice.toFixed(0)}</div>
        </div>
        <div className="text-center">
          <div className="text-gray-500">Target</div>
          <div className="font-bold text-green-400">+{alert.targetRange.avg}%</div>
          <div className="text-xs">${avgTargetPrice.toFixed(0)}</div>
        </div>
        <div className="text-right">
          <div className="text-gray-500">High</div>
          <div className="font-bold text-cyan-400">+{alert.targetRange.high}%</div>
          <div className="text-xs">${highTargetPrice.toFixed(0)}</div>
        </div>
      </div>

      {/* Stop Loss */}
      <div className="text-sm mb-4">
        <span className="text-gray-500">Stop Loss:</span>
        <span className="font-bold text-red-400"> –5% (${stopLossPrice.toFixed(0)})</span>
      </div>

      {/* Confidence Breakdown */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-xs text-gray-500">AI</div>
            <div className="text-cyan-400 font-bold">{alert.confidence}%</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500">Gut</div>
            <div className={`font-bold ${
              alert.gutVote === 'UP' ? 'text-green-400' :
              alert.gutVote === 'DOWN' ? 'text-red-400' : 'text-gray-500'
            }`}>
              {alert.gutVote === 'UP' ? (
                <><TrendingUp className="w-4 h-4 inline" /> UP</>
              ) : alert.gutVote === 'DOWN' ? (
                <><TrendingDown className="w-4 h-4 inline" /> DOWN</>
              ) : (
                'PASS'
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">Overall</div>
          <div className="text-white font-bold text-xl">
            {alert.finalConfidence || alert.confidence}%
          </div>
        </div>
      </div>

      {/* Mini Chart */}
      <div className="h-24 bg-black/30 rounded-lg relative overflow-hidden mb-4">
        {/* Polygon.io Chart Iframe (test placeholder for now) */}
        <iframe 
          src={`https://charts.polygon.io/embeds/${alert.ticker}/1/day?dark=true`}
          className="w-full h-full border-0"
          title={`${alert.ticker} Chart`}
        />
        {/* Live Price Indicator */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-3 h-3 bg-green-400 rounded-full animate-ping"></div>
          <div className="w-3 h-3 bg-green-400 rounded-full absolute"></div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => onShowDetails?.(alert.id)}
          className="flex-1 bg-gray-700 text-gray-300 py-3 rounded-xl text-sm hover:bg-gray-600 transition-colors"
        >
          Analysis Details
        </button>
        <button
          onClick={() => onAddToWatchlist?.(alert.id)}
          className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-600 text-white py-3 rounded-xl font-bold hover:from-cyan-600 hover:to-blue-700 transition-all"
        >
          Track Progress
        </button>
      </div>
    </div>
  );
}
