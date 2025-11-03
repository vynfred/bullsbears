import React from 'react';
import { Trophy, TrendingUp, Brain, Zap } from 'lucide-react';
import { demoGlobalStats, demoPersonalStats } from '../lib/demoData';
import AccuracyTrendChart from './AccuracyTrendChart';

const StatsBar: React.FC = () => {
  const beatsGlobal = demoPersonalStats.yourGutAccuracy > demoGlobalStats.globalGutWinRate;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Global Gut Win Rate */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-gray-400 uppercase tracking-wide">Global Gut</span>
          </div>
          <div className="text-2xl font-bold text-blue-400">
            {demoGlobalStats.globalGutWinRate}%
          </div>
        </div>

        {/* Your Gut Accuracy */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Zap className="w-4 h-4 text-orange-400" />
            <span className="text-xs text-gray-400 uppercase tracking-wide">Your Gut</span>
            {beatsGlobal && (
              <Trophy className="w-3 h-3 text-yellow-400" />
            )}
          </div>
          <div className={`text-2xl font-bold ${beatsGlobal ? 'text-yellow-400' : 'text-orange-400'}`}>
            {demoPersonalStats.yourGutAccuracy}%
          </div>
          {beatsGlobal && (
            <div className="text-xs text-yellow-400 font-medium">
              Beat the crowd!
            </div>
          )}
        </div>

        {/* AI Accuracy */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-gray-400 uppercase tracking-wide">AI Only</span>
          </div>
          <div className="text-2xl font-bold text-purple-400">
            {demoGlobalStats.aiAccuracy}%
          </div>
        </div>

        {/* You + AI Combined */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <div className="flex items-center gap-1">
              <Zap className="w-3 h-3 text-orange-400" />
              <span className="text-xs text-gray-400">+</span>
              <Brain className="w-3 h-3 text-purple-400" />
            </div>
            <span className="text-xs text-gray-400 uppercase tracking-wide ml-1">Combined</span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {demoPersonalStats.yourAiCombined}%
          </div>
        </div>
      </div>

      {/* Bottom Stats Row - Trending Accuracy */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="text-gray-400">
              Your Votes: <span className="text-white font-medium">{demoPersonalStats.totalVotes}</span>
            </span>

            {/* Trending Accuracy Chart - Mini Version */}
            <div className="flex items-center gap-2">
              <span className="text-gray-400">Accuracy Trend:</span>
              <AccuracyTrendChart showMiniVersion={true} />
            </div>
          </div>

          <div className="text-gray-500 text-xs">
            {demoGlobalStats.totalUsers.toLocaleString()} users • {demoGlobalStats.totalVotes.toLocaleString()} votes
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsBar;
