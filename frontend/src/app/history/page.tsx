'use client';

import React, { useState } from 'react';
import { demoHistoryEntries, demoPersonalStats, getClassificationColor } from '@/lib/demoData';
import PerformanceHeader from '@/components/PerformanceHeader';
import HistoryCard from '@/components/HistoryCard';
import ShareableWinCard from '@/components/ShareableWinCard';

export default function HistoryPage() {
  const [selectedEntry, setSelectedEntry] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'wins' | 'losses'>('all');

  const filteredEntries = demoHistoryEntries.filter(entry => {
    if (filter === 'wins') {
      return ['MOON', 'PARTIAL_MOON', 'WIN'].includes(entry.classification);
    }
    if (filter === 'losses') {
      return ['MISS', 'RUG', 'NUCLEAR_RUG'].includes(entry.classification);
    }
    return true;
  });

  const winEntry = demoHistoryEntries.find(e => e.classification === 'MOON');

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {/* Performance Header */}
      <PerformanceHeader metrics={{
        totalCalls: demoPersonalStats.totalVotes,
        gutAccuracy: demoPersonalStats.yourGutAccuracy,
        aiAccuracy: 71, // From demoGlobalStats
        combinedAccuracy: demoPersonalStats.yourAiCombined,
        currentStreak: demoPersonalStats.currentStreak,
        bestStreak: demoPersonalStats.bestStreak,
        winRate: demoPersonalStats.winRate
      }} />

      {/* History Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">History Pulse</h1>
          <div className="text-sm text-gray-600">
            {filteredEntries.length} calls
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex bg-gray-100 rounded-lg p-1 mb-4">
          <button
            onClick={() => setFilter('all')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              filter === 'all' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            All ({demoHistoryEntries.length})
          </button>
          <button
            onClick={() => setFilter('wins')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              filter === 'wins' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Wins ({demoHistoryEntries.filter(e => ['MOON', 'PARTIAL_MOON', 'WIN'].includes(e.classification)).length})
          </button>
          <button
            onClick={() => setFilter('losses')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              filter === 'losses' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Losses ({demoHistoryEntries.filter(e => ['MISS', 'RUG', 'NUCLEAR_RUG'].includes(e.classification)).length})
          </button>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-white rounded-lg p-3 border">
            <div className="text-sm text-gray-600">Best Performance</div>
            <div className="text-lg font-bold text-green-600">+35% MOON</div>
            <div className="text-xs text-gray-500">Stock #28394 • 2 days</div>
          </div>
          <div className="bg-white rounded-lg p-3 border">
            <div className="text-sm text-gray-600">Worst Performance</div>
            <div className="text-lg font-bold text-red-600">-45% NUCLEAR RUG</div>
            <div className="text-xs text-gray-500">Stock #62819 • 1 day</div>
          </div>
        </div>
      </div>

      {/* History Entries */}
      <div className="space-y-3 mb-20">
        {filteredEntries.map((entry) => (
          <HistoryCard
            key={entry.id}
            entry={entry}
            onSelect={() => setSelectedEntry(entry.id)}
          />
        ))}
      </div>

      {/* Navigation */}
      <div className="fixed bottom-6 left-4 right-4">
        <div className="bg-white rounded-xl shadow-lg p-4 border">
          <div className="flex gap-3">
            <button
              onClick={() => window.location.href = '/pulse'}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              New Pulse
            </button>
            {winEntry && (
              <button
                onClick={() => setSelectedEntry('share')}
                className="bg-green-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-green-700 transition-colors"
              >
                Share Win
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Shareable Win Card Modal */}
      {selectedEntry === 'share' && winEntry && (
        <ShareableWinCard
          entry={winEntry}
          onClose={() => setSelectedEntry(null)}
        />
      )}
    </div>
  );
}
