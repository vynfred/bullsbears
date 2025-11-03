'use client';

import React from 'react';

interface PerformanceMetrics {
  totalCalls: number;
  gutAccuracy: number;
  aiAccuracy: number;
  combinedAccuracy: number;
  currentStreak: number;
  bestStreak: number;
  winRate: {
    moon: number;
    partialMoon: number;
    win: number;
    miss: number;
    rug: number;
  };
}

interface PerformanceHeaderProps {
  metrics: PerformanceMetrics;
}

export default function PerformanceHeader({ metrics }: PerformanceHeaderProps) {
  return (
    <div className="bg-white rounded-xl p-4 mb-6 shadow-sm border">
      {/* Main Stats */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Your Performance</h2>
          <div className="text-sm text-gray-600">
            {metrics.totalCalls} total calls • {metrics.currentStreak} day streak
          </div>
        </div>
        
        {/* Streak Badge */}
        <div className="bg-yellow-100 text-yellow-800 px-3 py-2 rounded-lg text-center">
          <div className="text-2xl font-bold">{metrics.currentStreak}</div>
          <div className="text-xs">Day Streak</div>
        </div>
      </div>

      {/* Accuracy Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">
            {metrics.gutAccuracy}%
          </div>
          <div className="text-xs text-gray-600">Your Gut</div>
          <div className="text-xs text-gray-500">
            ({Math.round(metrics.totalCalls * metrics.gutAccuracy / 100)}/{metrics.totalCalls})
          </div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">
            {metrics.aiAccuracy}%
          </div>
          <div className="text-xs text-gray-600">AI Only</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">
            {metrics.combinedAccuracy}%
          </div>
          <div className="text-xs text-gray-600">Combined</div>
        </div>
      </div>

      {/* Win Rate Breakdown */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="text-xs text-gray-600 mb-2">Outcome Distribution:</div>
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-600 rounded-full mr-1"></div>
            <span>MOON {metrics.winRate.moon}%</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-400 rounded-full mr-1"></div>
            <span>PARTIAL {metrics.winRate.partialMoon}%</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-blue-500 rounded-full mr-1"></div>
            <span>WIN {metrics.winRate.win}%</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-gray-400 rounded-full mr-1"></div>
            <span>MISS {metrics.winRate.miss}%</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-red-500 rounded-full mr-1"></div>
            <span>RUG {metrics.winRate.rug}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
