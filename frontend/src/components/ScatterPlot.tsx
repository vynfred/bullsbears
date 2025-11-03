import React from 'react';
import { HistoryEntry } from '../lib/demoData';

interface ScatterPlotProps {
  entries: HistoryEntry[];
  onDotClick: (entry: HistoryEntry) => void;
}

const ScatterPlot: React.FC<ScatterPlotProps> = ({ entries, onDotClick }) => {
  // Chart dimensions - responsive
  const chartWidth = 400;
  const chartHeight = 300;
  const padding = 40;
  
  // Axis ranges
  const xMin = -5; // Days to Hit
  const xMax = 5;
  const yMin = -60; // % Gain
  const yMax = 60;
  
  // Scale functions
  const scaleX = (daysToHit: number) => {
    const clampedDays = Math.max(xMin, Math.min(xMax, daysToHit));
    return padding + ((clampedDays - xMin) / (xMax - xMin)) * (chartWidth - 2 * padding);
  };
  
  const scaleY = (percentGain: number) => {
    const clampedGain = Math.max(yMin, Math.min(yMax, percentGain));
    return chartHeight - padding - ((clampedGain - yMin) / (yMax - yMin)) * (chartHeight - 2 * padding);
  };
  
  // Get dot color based on gut vote
  const getDotColor = (gutVote: string) => {
    switch (gutVote) {
      case 'UP': return '#10b981'; // green-500
      case 'DOWN': return '#ef4444'; // red-500
      default: return '#6b7280'; // gray-500
    }
  };
  
  // Get dot size based on AI confidence (8-20px)
  const getDotSize = (aiConfidence: number) => {
    return Math.max(8, Math.min(20, 8 + (aiConfidence / 100) * 12));
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 overflow-x-auto">
      <div className="relative min-w-full">
        <svg width={chartWidth} height={chartHeight} className="w-full max-w-full overflow-visible">
          {/* Grid lines - Vertical (Days) */}
          {[-4, -2, 0, 2, 4].map(day => (
            <g key={`v-${day}`}>
              <line
                x1={scaleX(day)}
                y1={padding}
                x2={scaleX(day)}
                y2={chartHeight - padding}
                stroke="#374151"
                strokeWidth="1"
                opacity="0.3"
              />
              <text
                x={scaleX(day)}
                y={chartHeight - padding + 15}
                fill="#9ca3af"
                fontSize="10"
                textAnchor="middle"
              >
                {day === 0 ? 'Target' : `${day > 0 ? '+' : ''}${day}d`}
              </text>
            </g>
          ))}
          
          {/* Grid lines - Horizontal (%) */}
          {[-40, -20, 0, 20, 40].map(pct => (
            <g key={`h-${pct}`}>
              <line
                x1={padding}
                y1={scaleY(pct)}
                x2={chartWidth - padding}
                y2={scaleY(pct)}
                stroke="#374151"
                strokeWidth="1"
                opacity="0.3"
              />
              <text
                x={padding - 5}
                y={scaleY(pct)}
                fill="#9ca3af"
                fontSize="10"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {pct > 0 ? '+' : ''}{pct}%
              </text>
            </g>
          ))}
          
          {/* Center lines (target day and 0% gain) */}
          <line
            x1={scaleX(0)}
            y1={padding}
            x2={scaleX(0)}
            y2={chartHeight - padding}
            stroke="#6b7280"
            strokeWidth="2"
            opacity="0.5"
          />
          <line
            x1={padding}
            y1={scaleY(0)}
            x2={chartWidth - padding}
            y2={scaleY(0)}
            stroke="#6b7280"
            strokeWidth="2"
            opacity="0.5"
          />
          
          {/* Data points */}
          {entries.map((entry) => {
            const x = scaleX(entry.daysToHit);
            const y = scaleY(entry.actualPct);
            const size = getDotSize(entry.aiConfidence);
            const color = getDotColor(entry.gutVote);
            
            return (
              <g key={entry.id}>
                {/* Dot shadow */}
                <circle
                  cx={x + 1}
                  cy={y + 1}
                  r={size / 2}
                  fill="rgba(0,0,0,0.3)"
                />
                
                {/* Main dot */}
                <circle
                  cx={x}
                  cy={y}
                  r={size / 2}
                  fill={color}
                  stroke="#1f2937"
                  strokeWidth="2"
                  className="cursor-pointer hover:stroke-white hover:stroke-4 transition-all"
                  onClick={() => onDotClick(entry)}
                />
                
                {/* Hover tooltip */}
                <g className="opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
                  <rect
                    x={x - 40}
                    y={y - 50}
                    width="80"
                    height="35"
                    fill="#1f2937"
                    stroke="#374151"
                    rx="4"
                  />
                  <text
                    x={x}
                    y={y - 35}
                    fill="white"
                    fontSize="10"
                    textAnchor="middle"
                    fontWeight="bold"
                  >
                    {entry.ticker}
                  </text>
                  <text
                    x={x}
                    y={y - 25}
                    fill="#10b981"
                    fontSize="10"
                    textAnchor="middle"
                    fontWeight="bold"
                  >
                    {entry.actualPct > 0 ? '+' : ''}{entry.actualPct.toFixed(1)}%
                  </text>
                  <text
                    x={x}
                    y={y - 15}
                    fill="#9ca3af"
                    fontSize="9"
                    textAnchor="middle"
                  >
                    Day {entry.daysToHit} | AI {entry.aiConfidence}%
                  </text>
                </g>
              </g>
            );
          })}
        </svg>
        
        {/* Axis labels */}
        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-xs text-gray-400 mt-2">
          Days to Hit Target
        </div>
        <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -rotate-90 text-xs text-gray-400">
          % Gain/Loss
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-gray-300">Gut: UP</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <span className="text-gray-300">Gut: DOWN</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
          <span className="text-gray-300">Gut: SKIP</span>
        </div>
        <div className="text-gray-400">
          Size = AI Confidence
        </div>
      </div>
    </div>
  );
};

export default ScatterPlot;
