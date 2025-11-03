import React from 'react';
import { Clock, Calendar } from 'lucide-react';

type TimelineFilter = '1d' | '3d' | '7d' | '14d' | '30d' | 'all';

interface TimelineSelectorProps {
  selectedTimeline: TimelineFilter;
  onTimelineChange: (timeline: TimelineFilter) => void;
  entryCount: number;
}

const TimelineSelector: React.FC<TimelineSelectorProps> = ({
  selectedTimeline,
  onTimelineChange,
  entryCount
}) => {
  const timelineOptions: { value: TimelineFilter; label: string; description: string }[] = [
    { value: '1d', label: '1 Day', description: 'Predictions within 1 day of target' },
    { value: '3d', label: '3 Days', description: 'Predictions within 3 days of target' },
    { value: '7d', label: '1 Week', description: 'Predictions within 1 week of target' },
    { value: '14d', label: '2 Weeks', description: 'Predictions within 2 weeks of target' },
    { value: '30d', label: '1 Month', description: 'Predictions within 1 month of target' },
    { value: 'all', label: 'All Time', description: 'All predictions regardless of timing' }
  ];

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-5 h-5 text-blue-400" />
        <h3 className="text-lg font-semibold text-white">Timeline Filter</h3>
        <div className="ml-auto text-sm text-gray-400">
          {entryCount} predictions shown
        </div>
      </div>

      {/* Timeline Options */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {timelineOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => onTimelineChange(option.value)}
            className={`relative p-3 rounded-lg text-sm font-medium transition-all duration-200 ${
              selectedTimeline === option.value
                ? 'bg-blue-600 text-white shadow-lg ring-2 ring-blue-400 ring-opacity-50'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
            }`}
          >
            <div className="flex flex-col items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span className="font-semibold">{option.label}</span>
            </div>
            
            {/* Tooltip on hover */}
            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 hover:opacity-100 transition-opacity pointer-events-none z-10">
              <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl border border-gray-600 whitespace-nowrap">
                {option.description}
                {/* Tooltip arrow */}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Description */}
      <div className="mt-4 p-3 bg-gray-700 rounded-lg">
        <div className="flex items-start gap-2">
          <div className="w-2 h-2 bg-blue-400 rounded-full mt-2 flex-shrink-0"></div>
          <div className="text-sm text-gray-300">
            <span className="font-medium text-white">Timeline Explanation:</span> This filter shows predictions based on how close the actual outcome was to the predicted timeframe. 
            For example, "3 Days" shows only predictions where the stock hit the target within 3 days of when we predicted it would spike.
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineSelector;
