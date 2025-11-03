import React from 'react';
import { HistoryEntry } from '../lib/demoData';

interface HistorySpectrumProps {
  entries: HistoryEntry[];
  onEntryClick: (entry: HistoryEntry) => void;
}

const HistorySpectrum: React.FC<HistorySpectrumProps> = ({ entries, onEntryClick }) => {
  // Sort entries by actual percentage change for positioning
  const sortedEntries = [...entries].sort((a, b) => a.actualPct - b.actualPct);
  
  // Find min and max for scaling
  const minPct = Math.min(...entries.map(e => e.actualPct));
  const maxPct = Math.max(...entries.map(e => e.actualPct));
  const range = maxPct - minPct;
  
  // Position calculation (0-100% across the spectrum)
  const getPosition = (actualPct: number): number => {
    if (range === 0) return 50; // Center if all same
    return ((actualPct - minPct) / range) * 100;
  };
  
  // Get color based on classification
  const getColor = (classification: HistoryEntry['classification']): string => {
    switch (classification) {
      case 'NUCLEAR_RUG': return '#dc2626'; // red-600
      case 'RUG': return '#ef4444'; // red-500
      case 'MISS': return '#6b7280'; // gray-500
      case 'WIN': return '#3b82f6'; // blue-500
      case 'PARTIAL_MOON': return '#10b981'; // emerald-500
      case 'MOON': return '#059669'; // emerald-600
      default: return '#6b7280';
    }
  };
  
  // Get size based on confidence/importance
  const getSize = (entry: HistoryEntry): number => {
    const baseSize = 12;
    const confidenceMultiplier = entry.finalConfidence / 100;
    return Math.max(8, Math.min(20, baseSize + (confidenceMultiplier * 8)));
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
      {/* Spectrum Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span className="text-sm text-gray-400">Rugs</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
            <span className="text-sm text-gray-400">Neutral</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-400">Moons</span>
          </div>
        </div>
        <div className="text-sm text-gray-500">
          {entries.length} predictions
        </div>
      </div>

      {/* Spectrum Visualization */}
      <div className="relative h-32 mb-4">
        {/* Background gradient bar */}
        <div className="absolute top-12 left-0 right-0 h-8 rounded-full bg-gradient-to-r from-red-600 via-gray-600 to-green-600 opacity-20"></div>
        
        {/* Center line */}
        <div className="absolute top-12 left-1/2 w-0.5 h-8 bg-gray-400 opacity-50"></div>
        
        {/* Percentage labels */}
        <div className="absolute top-2 left-0 text-xs text-red-400 font-medium">
          {minPct.toFixed(1)}%
        </div>
        <div className="absolute top-2 left-1/2 transform -translate-x-1/2 text-xs text-gray-400 font-medium">
          0%
        </div>
        <div className="absolute top-2 right-0 text-xs text-green-400 font-medium">
          {maxPct.toFixed(1)}%
        </div>
        
        {/* Data points */}
        {entries.map((entry) => {
          const position = getPosition(entry.actualPct);
          const size = getSize(entry);
          const color = getColor(entry.classification);
          
          return (
            <div
              key={entry.id}
              className="absolute cursor-pointer transform -translate-x-1/2 hover:scale-125 transition-transform group"
              style={{
                left: `${position}%`,
                top: '48px',
                transform: `translateX(-50%) translateY(-${size/2}px)`
              }}
              onClick={() => onEntryClick(entry)}
            >
              {/* Data point circle */}
              <div
                className="rounded-full border-2 border-gray-800 shadow-lg"
                style={{
                  width: `${size}px`,
                  height: `${size}px`,
                  backgroundColor: color
                }}
              ></div>
              
              {/* Hover tooltip */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl border border-gray-600 whitespace-nowrap">
                  <div className="font-semibold">{entry.ticker}</div>
                  <div className="text-gray-300">{entry.actualPct.toFixed(1)}% in {entry.daysToHit}d</div>
                  <div className="text-gray-400 capitalize">{entry.classification.toLowerCase().replace('_', ' ')}</div>
                </div>
                {/* Tooltip arrow */}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 text-center text-sm">
        <div>
          <div className="text-red-400 font-semibold text-lg">
            {entries.filter(e => ['RUG', 'NUCLEAR_RUG'].includes(e.classification)).length}
          </div>
          <div className="text-gray-400">Rugs</div>
        </div>
        <div>
          <div className="text-gray-400 font-semibold text-lg">
            {entries.filter(e => ['MISS', 'WIN'].includes(e.classification)).length}
          </div>
          <div className="text-gray-400">Neutral</div>
        </div>
        <div>
          <div className="text-green-400 font-semibold text-lg">
            {entries.filter(e => ['MOON', 'PARTIAL_MOON'].includes(e.classification)).length}
          </div>
          <div className="text-gray-400">Moons</div>
        </div>
      </div>
    </div>
  );
};

export default HistorySpectrum;
