'use client';

import React from 'react';
import { HistoryEntry, getClassificationColor } from '@/lib/demoData';

interface HistoryCardProps {
  entry: HistoryEntry;
  onSelect: () => void;
}

export default function HistoryCard({ entry, onSelect }: HistoryCardProps) {
  const classificationStyle = getClassificationColor(entry.classification);
  const isWin = ['MOON', 'PARTIAL_MOON', 'WIN'].includes(entry.classification);
  const isLoss = ['MISS', 'RUG', 'NUCLEAR_RUG'].includes(entry.classification);

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      weekday: 'short'
    });
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  return (
    <div
      className="bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-700 hover:shadow-xl hover:border-gray-600 transition-all cursor-pointer"
      onClick={onSelect}
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          {/* Date and Stock Info */}
          <div className="text-sm text-gray-400 mb-1">
            {formatDate(entry.callTime)}
          </div>
          <div className="font-bold text-xl text-white">
            {entry.ticker}
          </div>
          <div className="text-sm text-gray-300">
            {entry.companyName}
          </div>
        </div>

        {/* Classification Badge */}
        <div className={`px-3 py-1 rounded-lg text-sm font-bold ${classificationStyle}`}>
          {entry.classification.replace('_', ' ')}
        </div>
      </div>

      {/* Price Information */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-xs text-gray-400 uppercase tracking-wide">Entry Price</div>
          <div className="text-lg font-bold text-white">{formatPrice(entry.entryPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-400 uppercase tracking-wide">Current Price</div>
          <div className="text-lg font-bold text-white">{formatPrice(entry.currentPrice)}</div>
        </div>
      </div>

      {/* Performance - Big % Change */}
      <div className="text-center mb-4">
        <div className={`text-4xl font-bold ${
          entry.actualPct >= 0 ? 'text-green-400' : 'text-red-400'
        }`}>
          {entry.actualPct >= 0 ? '+' : ''}{entry.actualPct}%
        </div>
        <div className="text-sm text-gray-400">
          {entry.daysToHit} days elapsed
        </div>
      </div>

      {/* AI & Gut Tags */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 bg-blue-900 text-blue-300 rounded text-xs font-medium">
            AI: {entry.aiConfidence}%
          </span>
          <span className="px-2 py-1 bg-cyan-900 text-cyan-300 rounded text-xs font-medium">
            AI Pick
          </span>
        </div>
        <div className="text-xs text-gray-400">
          Max: {entry.maxGain}% • Peak: {entry.daysToPeak}d
        </div>
      </div>

      {/* Additional Details */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div>
          Peak in {entry.daysToPeak}d
        </div>
        {entry.postMoonRug && (
          <div className="text-red-600 font-medium">
            Post-moon rug
          </div>
        )}
        <div>
          Target: +{entry.targetPct}%
        </div>
      </div>
    </div>
  );
}
