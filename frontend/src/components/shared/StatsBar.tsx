// src/components/shared/StatsBar.tsx
'use client';

import React from 'react';
import { TrendingUp, Brain, Zap, Trophy } from 'lucide-react';
import { useStatsBarData } from '@/hooks/useStatistics';

export default function StatsBar() {
  const { statsBarData, isLoading, error } = useStatsBarData();

  if (isLoading) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <div className="animate-pulse">Loading stats...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-center text-red-400 text-sm">
        {error}
      </div>
    );
  }

  if (!statsBarData) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-center text-gray-400">
        No stats available
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div className="flex justify-center mb-1">
            <Brain className="w-5 h-5 text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-white">{statsBarData.daily_scans}</p>
          <p className="text-xs text-gray-400">Daily Scans</p>
        </div>

        <div>
          <div className="flex justify-center mb-1">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">{statsBarData.bullish_win_rate.toFixed(1)}%</p>
          <p className="text-xs text-gray-400">Bullish Win Rate</p>
        </div>

        <div>
          <div className="flex justify-center mb-1">
            <Zap className="w-5 h-5 text-yellow-400" />
          </div>
          <p className="text-2xl font-bold text-white">{statsBarData.bearish_win_rate.toFixed(1)}%</p>
          <p className="text-xs text-gray-400">Bearish Win Rate</p>
        </div>

        <div>
          <div className="flex justify-center mb-1">
            <Trophy className="w-5 h-5 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-white">{statsBarData.alert_rate.toFixed(1)}%</p>
          <p className="text-xs text-gray-400">Alert Rate</p>
        </div>
      </div>
    </div>
  );
}