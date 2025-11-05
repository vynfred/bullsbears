'use client';

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { MoonAlert } from '@/lib/demoData';

interface DetailedPickCardProps {
  alert: MoonAlert;
  onDetails: (alertId: string) => void;
  onAddToWatchlist: (alertId: string) => void;
}

export function DetailedPickCard({ alert, onDetails, onAddToWatchlist }: DetailedPickCardProps) {
  // Calculate current performance
  const currentPrice = alert.currentPrice || alert.entryPrice;
  const changePercent = ((currentPrice - alert.entryPrice) / alert.entryPrice) * 100;
  const isPositive = changePercent >= 0;

  // Calculate age and visual state
  const now = new Date();
  const daysOld = Math.floor((now.getTime() - new Date(alert.timestamp).getTime()) / 86400000);
  const isToday = daysOld === 0;
  const isRecent = daysOld > 0 && daysOld <= 6;

  // Determine border color and pick type
  const borderColor = isToday
    ? (alert.type === 'bullish' ? 'border-green-400' : 'border-red-400')
    : 'border-gray-700';
  const pickType = alert.type === 'bullish' ? 'BULLISH PICK' : 'BEARISH PICK';
  const pickTypeColor = alert.type === 'bullish' ? 'text-green-400' : 'text-red-400';

  // Format date and time
  const pickDate = new Date(alert.timestamp);
  const formattedDate = pickDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
  const formattedTime = pickDate.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  // Calculate price targets (actual prices, not percentages)
  // For bearish picks, targets are negative percentages (going down)
  const targetLowPct = alert.targetRange?.low || (alert.type === 'bullish' ? 18 : -18);
  const targetAvgPct = alert.targetRange?.avg || (alert.type === 'bullish' ? 23 : -23);
  const targetHighPct = alert.targetRange?.high || (alert.type === 'bullish' ? 31 : -31);

  const lowTarget = alert.entryPrice * (1 + targetLowPct / 100);
  const medTarget = alert.entryPrice * (1 + targetAvgPct / 100);
  const highTarget = alert.entryPrice * (1 + targetHighPct / 100);

  // Calculate stop loss
  const stopLoss = alert.type === 'bullish'
    ? alert.entryPrice * 0.95  // 5% below entry for bullish picks (stop loss if it goes down)
    : alert.entryPrice * 1.05; // 5% above entry for bearish picks (stop loss if it goes up)

  // Combined confidence (ML-learned, no manual boosts)
  const combinedConfidence = alert.finalConfidence || alert.confidence;

  // Hide if older than 6 days (7+ days go to Performance tab)
  if (daysOld > 6) return null;

  return (
    <div className={`relative rounded-2xl p-5 border-2 transition-all ${
      isToday
        ? `${borderColor} bg-[#111827] shadow-lg ${alert.type === 'bullish' ? 'shadow-green-500/50' : 'shadow-red-500/50'}`
        : isRecent
          ? 'border-gray-700 bg-gray-900/50 opacity-70'
          : 'hidden'
    }`}>
      {/* LIVE Badge for Today's Picks */}
      {isToday && (
        <div className="absolute -top-3 -right-3 bg-green-500 text-white px-3 py-1 rounded-full text-xs font-bold animate-pulse">
          LIVE
        </div>
      )}

      {/* Header Row - Pick Type and Confidence */}
      <div className="flex justify-between items-start mb-3">
        <div className={`text-xs font-bold ${pickTypeColor} bg-gray-700 px-2 py-1 rounded`}>
          {pickType}
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">{alert.confidence}%</div>
          <div className="text-xs text-gray-400">Confidence Score</div>
        </div>
      </div>

      {/* Age Label for Old Picks */}
      {!isToday && (
        <div className="text-xs text-gray-500 mb-3">{daysOld}d old</div>
      )}

      {/* Stock Info Row */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-xl font-bold text-white">{alert.ticker}</h3>
          <div className="text-sm text-gray-300">${currentPrice.toFixed(2)}</div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">Since Alert</div>
          <div className={`text-lg font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '+' : ''}{changePercent.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Price When Alerted with Date/Time */}
      <div className="flex justify-between items-center mb-4 text-sm">
        <div>
          <span className="text-gray-400">Price when alerted:</span>
          <div className="text-xs text-gray-500 mt-1">{formattedDate} • {formattedTime}</div>
        </div>
        <span className="text-white font-medium">${alert.entryPrice.toFixed(2)}</span>
      </div>

      {/* Price Targets & Stop Loss Box */}
      <div className="bg-gray-700 rounded-lg p-4 mb-4">
        <div className="mb-3">
          <div className="text-xs text-gray-400 mb-2">Price Targets</div>
          <div className="flex justify-between text-sm">
            <div className="text-center">
              <div className="text-yellow-400 font-semibold">${lowTarget.toFixed(2)}</div>
              <div className="text-xs text-gray-500">Low</div>
            </div>
            <div className="text-center">
              <div className="text-green-400 font-semibold">${medTarget.toFixed(2)}</div>
              <div className="text-xs text-gray-500">Med</div>
            </div>
            <div className="text-center">
              <div className="text-cyan-400 font-semibold">${highTarget.toFixed(2)}</div>
              <div className="text-xs text-gray-500">High</div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-600 pt-3">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-400">Recommended stop loss:</span>
            <span className="text-red-400 font-medium">${stopLoss.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Confidence Breakdown */}
      <div className="mb-4">
        <div className="text-xs text-gray-400 mb-2">Confidence Breakdown</div>
        <div className="flex justify-between items-center text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-400">AI:</span>
            <span className="text-cyan-400 font-semibold">{alert.confidence}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">AI Confidence:</span>
            <span className="text-cyan-400 font-semibold">
              {alert.confidence}%
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Combined:</span>
            <span className="text-white font-bold">{combinedConfidence}%</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => onDetails(alert.id)}
          className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          Details
        </button>
        <button
          onClick={() => onAddToWatchlist(alert.id)}
          className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          Add to Watchlist
        </button>
      </div>
    </div>
  );
}
