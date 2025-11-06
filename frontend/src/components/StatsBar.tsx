import React from 'react';
import { TrendingUp, Brain } from 'lucide-react';
import { useStatsBarData } from '../hooks/useStatistics';

const StatsBar: React.FC = () => {
  // Get live statistics
  const { statsBarData, isLoading, error } = useStatsBarData({
    refreshInterval: 300000, // 5 minutes
    enabled: true,
    autoRefresh: true
  });

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-6">
      <div className="grid grid-cols-2 gap-4">
        {/* AI Bullish Accuracy */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-xs text-gray-400 uppercase tracking-wide">Bullish AI</span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {statsBarData?.bullish_win_rate ?? 52}%
          </div>
          <div className="text-xs text-gray-400">
            Win Rate
          </div>
        </div>

        {/* AI Bearish Accuracy */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Brain className="w-4 h-4 text-red-400" />
            <span className="text-xs text-gray-400 uppercase tracking-wide">Bearish AI</span>
          </div>
          <div className="text-2xl font-bold text-red-400">
            {statsBarData?.bearish_win_rate ?? 45}%
          </div>
          <div className="text-xs text-gray-400">
            Win Rate
          </div>
        </div>

      </div>

      {/* Bottom Stats Row - AI Performance */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="text-gray-400">
              Daily Scans: <span className="text-white font-medium">{statsBarData?.daily_scans ?? 888} stocks</span>
            </span>
            <span className="text-gray-400">
              Alert Rate: <span className="text-white font-medium">{statsBarData?.alert_rate ?? 1}%</span>
            </span>
          </div>

          <div className="text-gray-500 text-xs">
            AI-powered stock analysis
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsBar;
