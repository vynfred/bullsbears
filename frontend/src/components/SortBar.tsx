'use client';

import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface SortBarProps {
  sortBy: 'confidence' | 'change' | 'time';
  sortDirection: 'asc' | 'desc';
  onSortChange: (sortBy: 'confidence' | 'change' | 'time') => void;
  onDirectionChange: (direction: 'asc' | 'desc') => void;
}

export function SortBar({ sortBy, sortDirection, onSortChange, onDirectionChange }: SortBarProps) {
  const handleSortClick = (newSortBy: 'confidence' | 'change' | 'time') => {
    if (sortBy === newSortBy) {
      // Same sort field - flip direction
      onDirectionChange(sortDirection === 'desc' ? 'asc' : 'desc');
    } else {
      // New sort field - use default direction
      onSortChange(newSortBy);
      onDirectionChange(newSortBy === 'time' ? 'desc' : 'desc'); // newest first for time, highest first for others
    }
  };

  const getSortLabel = (sort: string) => {
    switch (sort) {
      case 'confidence': return 'Confidence';
      case 'change': return '% Change';
      case 'time': return 'Time';
      default: return sort;
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg px-4 py-3 mb-4">
      <div className="flex items-center gap-4">
        <span className="text-gray-400 text-sm font-medium">Sort:</span>
        
        {(['confidence', 'change', 'time'] as const).map((sort) => (
          <button
            key={sort}
            onClick={() => handleSortClick(sort)}
            className={`flex items-center gap-1 px-3 py-1 rounded-md text-sm font-medium transition-all ${
              sortBy === sort
                ? 'text-white bg-gray-700'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            {getSortLabel(sort)}
            {sortBy === sort && (
              sortDirection === 'desc' ? 
                <ChevronDown className="w-4 h-4" /> : 
                <ChevronUp className="w-4 h-4" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
