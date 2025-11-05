import React, { useState } from 'react';
import { HistoryEntry, demoHistoryEntries } from '../lib/demoData';
import ScatterPlot from './ScatterPlot';
import PicksCarousel from './PicksCarousel';

type PulseFilter = 'all' | 'bullish' | 'bearish' | 'gut';

interface HistoryPulseProps {
  onEntrySelect?: (entry: HistoryEntry) => void;
}

const HistoryPulse: React.FC<HistoryPulseProps> = ({ onEntrySelect }) => {
  const [activeFilter, setActiveFilter] = useState<PulseFilter>('all');

  // Calculate "Your Edge" performance
  const calculateEdge = (entries: HistoryEntry[]) => {
    if (entries.length === 0) return { totalGain: 0, spyGain: 4 }; // Default SPY gain
    
    const totalGain = entries.reduce((sum, entry) => sum + entry.actualPct, 0);
    const spyGain = 4; // Mock SPY performance for demo
    
    return { totalGain: Math.round(totalGain), spyGain };
  };

  // Filter entries based on active filter
  const filteredEntries = demoHistoryEntries.filter(entry => {
    switch (activeFilter) {
      case 'bullish':
        return ['MOON', 'PARTIAL_MOON'].includes(entry.classification);
      case 'bearish':
        return ['RUG', 'NUCLEAR_RUG'].includes(entry.classification);
      case 'gut':
        return entry.gutVote && entry.gutVote !== 'PASS';
      default:
        return true;
    }
  });

  const { totalGain, spyGain } = calculateEdge(filteredEntries);

  const handleEntryClick = (entry: HistoryEntry) => {
    console.log('Selected entry:', entry.id);
    onEntrySelect?.(entry);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">Performance</h2>
        <p className="text-gray-400">
          Your personal P&L diary. Every pick you voted on → % gain, days to moon, streak flame, vs SPY.
        </p>
      </div>

      {/* Pulse Filter */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-4">PULSE FILTER</h3>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveFilter('all')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeFilter === 'all'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setActiveFilter('bullish')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeFilter === 'bullish'
                ? 'bg-green-600 text-white shadow-lg'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
            }`}
          >
            Bullish Picks
          </button>
          <button
            onClick={() => setActiveFilter('bearish')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeFilter === 'bearish'
                ? 'bg-red-600 text-white shadow-lg'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
            }`}
          >
            Bearish Picks
          </button>
          <button
            onClick={() => setActiveFilter('gut')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeFilter === 'gut'
                ? 'bg-orange-600 text-white shadow-lg'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
            }`}
          >
            Gut Only
          </button>
        </div>
      </div>

      {/* Your Edge Badge */}
      {filteredEntries.length > 0 && (
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-4 text-center">
          <div className="text-white text-lg font-bold">
            Your Edge: Gut + AI = {totalGain > 0 ? '+' : ''}{totalGain}% vs SPY +{spyGain}%
          </div>
          <div className="text-blue-100 text-sm mt-1">
            {filteredEntries.length} predictions • {Math.round((filteredEntries.filter(e => ['MOON', 'PARTIAL_MOON', 'WIN'].includes(e.classification)).length / filteredEntries.length) * 100)}% win rate
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredEntries.length === 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-400 text-xl mb-2">Your Pulse is quiet</div>
          <div className="text-gray-500 text-sm mb-6">Do a gut check to see your edge.</div>
          <button className="bg-orange-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-orange-600 transition-colors">
            Start Gut Check
          </button>
        </div>
      )}

      {/* Scatter Plot */}
      {filteredEntries.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">Performance Scatter</h3>
          <ScatterPlot
            entries={filteredEntries}
            onDotClick={handleEntryClick}
          />
        </div>
      )}

      {/* Picks Carousel */}
      {filteredEntries.length > 0 && (
        <div>
          <PicksCarousel
            entries={filteredEntries}
            onCardClick={handleEntryClick}
          />
        </div>
      )}
    </div>
  );
};

export default HistoryPulse;
