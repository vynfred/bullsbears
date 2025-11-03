'use client';

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { MoonAlert } from '@/lib/demoData';

interface CleanStockCardProps {
  alert: MoonAlert;
  onAnalysisDetails: (alertId: string) => void;
  onTrackProgress: (alertId: string) => void;
}

export function CleanStockCard({ alert, onAnalysisDetails, onTrackProgress }: CleanStockCardProps) {
  // Calculate current performance
  const currentPrice = alert.currentPrice || alert.entryPrice;
  const changePercent = ((currentPrice - alert.entryPrice) / alert.entryPrice) * 100;
  const isPositive = changePercent >= 0;
  
  // Determine border color based on type
  const borderColor = alert.type === 'moon' ? 'border-l-green-500' : 'border-l-red-500';
  
  // Calculate days remaining in window
  const windowEnd = new Date(alert.timestamp);
  windowEnd.setDate(windowEnd.getDate() + (alert.timeWindow || 3));
  const daysRemaining = Math.max(0, Math.ceil((windowEnd.getTime() - Date.now()) / (1000 * 60 * 60 * 24)));

  return (
    <div className={`bg-gray-800 rounded-lg border-l-4 ${borderColor} p-4 hover:bg-gray-750 transition-colors`}>
      {/* Header Row */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-xl font-bold text-white">{alert.ticker}</h3>
          <div className="flex items-center gap-3 mt-1">
            <span className={`text-lg font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}{changePercent.toFixed(1)}%
            </span>
            <span className="text-2xl font-bold text-white">
              {(alert.finalConfidence || alert.confidence)}%
            </span>
          </div>
        </div>
      </div>

      {/* Price Info */}
      <div className="flex items-center gap-2 text-gray-300 mb-4">
        <span>${alert.entryPrice.toFixed(2)}</span>
        <span>→</span>
        <span>${alert.targetPrice?.toFixed(2) || (alert.entryPrice * 1.2).toFixed(2)}</span>
        <span className="text-gray-500">•</span>
        <span className="text-gray-400">{daysRemaining}d window</span>
      </div>

      {/* Target Ranges */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-400 mb-2">
          <span>Low</span>
          <span>Target</span>
          <span>High</span>
        </div>
        <div className="flex justify-between text-sm font-semibold">
          <span className="text-yellow-400">
            +{alert.targetRanges?.low || '18'}%
          </span>
          <span className="text-green-400">
            +{alert.targetRanges?.target || '23'}%
          </span>
          <span className="text-cyan-400">
            +{alert.targetRanges?.high || '31'}%
          </span>
        </div>
      </div>

      {/* AI and Gut Confidence */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
          <div className="text-sm">
            <span className="text-gray-400">AI: </span>
            <span className="text-cyan-400 font-semibold">{alert.confidence}%</span>
          </div>
          <div className="text-sm">
            <span className="text-gray-400">Gut: </span>
            <span className={`font-semibold flex items-center gap-1 ${
              alert.gutVote === 'UP' ? 'text-green-400' : 
              alert.gutVote === 'DOWN' ? 'text-red-400' : 'text-gray-400'
            }`}>
              {alert.gutVote === 'UP' && <TrendingUp className="w-3 h-3" />}
              {alert.gutVote === 'DOWN' && <TrendingDown className="w-3 h-3" />}
              {alert.gutVote || 'PASS'} {alert.gutVoteCount || 5}
            </span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => onAnalysisDetails(alert.id)}
          className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          Analysis Details
        </button>
        <button
          onClick={() => onTrackProgress(alert.id)}
          className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          Track Progress
        </button>
      </div>
    </div>
  );
}
