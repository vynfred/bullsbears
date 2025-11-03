import React from 'react';
import { PersonalPulseEntry } from '../lib/demoData';
import { TrendingUp, TrendingDown, Clock, Target } from 'lucide-react';

interface PersonalPulseCardProps {
  entry: PersonalPulseEntry;
  rank: number;
}

const PersonalPulseCard: React.FC<PersonalPulseCardProps> = ({ entry, rank }) => {
  const getClassificationBadge = (classification: PersonalPulseEntry['classification']) => {
    switch (classification) {
      case 'MOON':
        return 'bg-green-900 text-green-300 border-green-700';
      case 'PARTIAL_MOON':
        return 'bg-green-800 text-green-200 border-green-600';
      case 'WIN':
        return 'bg-blue-900 text-blue-300 border-blue-700';
      case 'MISS':
        return 'bg-gray-700 text-gray-300 border-gray-600';
      case 'RUG':
        return 'bg-red-900 text-red-300 border-red-700';
      case 'NUCLEAR_RUG':
        return 'bg-red-800 text-red-200 border-red-600';
      case 'WATCH':
        return 'bg-yellow-900 text-yellow-300 border-yellow-700';
      default:
        return 'bg-gray-700 text-gray-300 border-gray-600';
    }
  };

  const getGutVoteBadge = (vote: 'UP' | 'DOWN' | 'PASS') => {
    switch (vote) {
      case 'UP':
        return 'bg-green-900 text-green-300';
      case 'DOWN':
        return 'bg-red-900 text-red-300';
      case 'PASS':
        return 'bg-gray-700 text-gray-300';
    }
  };

  const getPercentChangeColor = (change: number) => {
    if (change > 0) return 'text-green-400';
    if (change < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  const getRankColor = (rank: number) => {
    if (rank === 1) return 'text-yellow-400'; // Gold
    if (rank === 2) return 'text-gray-300'; // Silver
    if (rank === 3) return 'text-orange-400'; // Bronze
    return 'text-gray-400';
  };

  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-lg p-4 ${entry.isStale ? 'opacity-60' : ''}`}>
      <div className="flex items-center justify-between mb-3">
        {/* Rank and Anonymous ID */}
        <div className="flex items-center gap-3">
          <div className={`text-2xl font-bold ${getRankColor(rank)}`}>
            #{rank}
          </div>
          <div className="text-lg font-semibold text-white">
            {entry.anonymousId}
          </div>
          {entry.isStale && (
            <span className="px-2 py-1 text-xs font-medium bg-yellow-900 text-yellow-300 border border-yellow-700 rounded">
              STALE
            </span>
          )}
        </div>

        {/* Classification Badge */}
        <span className={`px-3 py-1 text-sm font-medium border rounded-full ${getClassificationBadge(entry.classification)}`}>
          {entry.classification}
        </span>
      </div>

      {/* Performance Stats */}
      <div className="grid grid-cols-4 gap-4 mb-3">
        {/* Percent Change - BIG */}
        <div className="col-span-2">
          <div className="text-xs text-gray-400 mb-1">% Change</div>
          <div className={`text-3xl font-bold ${getPercentChangeColor(entry.percentChange)}`}>
            {entry.percentChange > 0 ? '+' : ''}{entry.percentChange.toFixed(1)}%
          </div>
        </div>

        {/* Confidence */}
        <div>
          <div className="text-xs text-gray-400 mb-1">Confidence</div>
          <div className="text-xl font-semibold text-white">
            {entry.confidence}%
          </div>
        </div>

        {/* Days Elapsed */}
        <div>
          <div className="text-xs text-gray-400 mb-1">Time</div>
          <div className="text-lg font-medium text-gray-300 flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {entry.daysElapsed}d
          </div>
        </div>
      </div>

      {/* Bottom Row - Gut Vote and Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Gut Vote Badge */}
          <span className={`px-2 py-1 text-xs font-medium rounded ${getGutVoteBadge(entry.gutVote)}`}>
            GUT: {entry.gutVote}
          </span>

          {/* Trend Icon */}
          {entry.percentChange > 0 ? (
            <TrendingUp className="w-4 h-4 text-green-400" />
          ) : entry.percentChange < 0 ? (
            <TrendingDown className="w-4 h-4 text-red-400" />
          ) : (
            <div className="w-4 h-4" />
          )}
        </div>

        {/* Days to Moon (for WATCH status) */}
        {entry.classification === 'WATCH' && entry.estimatedDaysToMoon && (
          <div className="flex items-center gap-1 text-xs text-yellow-400">
            <Target className="w-3 h-3" />
            {entry.estimatedDaysToMoon}d to moon
          </div>
        )}

        {/* Vote Time */}
        <div className="text-xs text-gray-500">
          {entry.voteTime.toLocaleDateString()}
        </div>
      </div>
    </div>
  );
};

export default PersonalPulseCard;
