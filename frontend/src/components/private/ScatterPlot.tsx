// src/components/private/ScatterPlot.tsx
import React from 'react';
import { HistoryEntry } from '@/lib/types';

interface ScatterPlotProps {
  entries: HistoryEntry[];
  onEntryClick: (entry: HistoryEntry) => void;
}

const ScatterPlot: React.FC<ScatterPlotProps> = ({ entries, onEntryClick }) => {
  // Guard: no data
  if (!entries || entries.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 text-center">
        <p className="text-gray-400">No history data available</p>
      </div>
    );
  }

  // Chart dimensions
  const width = 600;
  const height = 400;
  const padding = 60;

  // Axis ranges (from backend)
  const xMin = -5;   // days_to_hit
  const xMax = 5;
  const yMin = -100; // actual_percent
  const yMax = 100;

  // Extract values
  const daysToHitValues = entries.map(e => e.days_to_hit ?? 0);
  const actualPercentValues = entries.map(e => e.actual_percent ?? 0);

  const xDomainMin = Math.min(xMin, ...daysToHitValues);
  const xDomainMax = Math.max(xMax, ...daysToHitValues);
  const yDomainMin = Math.min(yMin, ...actualPercentValues);
  const yDomainMax = Math.max(yMax, ...actualPercentValues);

  // Scale functions
  const scaleX = (days: number) => {
    const clamped = Math.max(xDomainMin, Math.min(xDomainMax, days));
    return padding + ((clamped - xDomainMin) / (xDomainMax - xDomainMin)) * (width - 2 * padding);
  };

  const scaleY = (percent: number) => {
    const clamped = Math.max(yDomainMin, Math.min(yDomainMax, percent));
    return height - padding - ((clamped - yDomainMin) / (yDomainMax - yDomainMin)) * (height - 2 * padding);
  };

  // Dot size: AI confidence (8–20px)
  const getDotSize = (confidence: number) => {
    return Math.max(8, Math.min(20, 8 + (confidence / 100) * 12));
  };

  // Dot color: AI confidence
  const getDotColor = (confidence: number) => {
    if (confidence >= 80) return '#10b981'; // emerald-500
    if (confidence >= 60) return '#3b82f6'; // blue-500
    if (confidence >= 40) return '#f59e0b'; // amber-500
    return '#ef4444'; // red-500
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">AI Performance Scatter</h3>

      <svg width={width} height={height} className="w-full">
        {/* Grid Lines - X */}
        {[-4, -2, 0, 2, 4].map(val => (
          <g key={`grid-x-${val}`}>
            <line
              x1={scaleX(val)}
              y1={padding}
              x2={scaleX(val)}
              y2={height - padding}
              stroke="#374151"
              strokeWidth="1"
              opacity="0.3"
            />
            <text
              x={scaleX(val)}
              y={height - padding + 20}
              fill="#9ca3af"
              fontSize="12"
              textAnchor="middle"
            >
              {val === 0 ? 'Target' : `${val > 0 ? '+' : ''}${val}d`}
            </text>
          </g>
        ))}

        {/* Grid Lines - Y */}
        {[-75, -50, -25, 0, 25, 50, 75].map(val => (
          <g key={`grid-y-${val}`}>
            <line
              x1={padding}
              y1={scaleY(val)}
              x2={width - padding}
              y2={scaleY(val)}
              stroke="#374151"
              strokeWidth="1"
              opacity="0.3"
            />
            <text
              x={padding - 10}
              y={scaleY(val)}
              fill="#9ca3af"
              fontSize="12"
              textAnchor="end"
              dominantBaseline="middle"
            >
              {val}%
            </text>
          </g>
        ))}

        {/* Center Lines */}
        <line x1={scaleX(0)} y1={padding} x2={scaleX(0)} y2={height - padding} stroke="#6b7280" strokeWidth="2" />
        <line x1={padding} y1={scaleY(0)} x2={width - padding} y2={scaleY(0)} stroke="#6b7280" strokeWidth="2" />

        {/* Data Points */}
        {entries.map((entry) => {
          const x = scaleX(entry.days_to_hit ?? 0);
          const y = scaleY(entry.actual_percent ?? 0);
          const size = getDotSize(entry.ai_confidence ?? 0);
          const color = getDotColor(entry.ai_confidence ?? 0);

          return (
            <g key={entry.id}>
              <circle
                cx={x}
                cy={y}
                r={size / 2}
                fill={color}
                stroke="#1f2937"
                strokeWidth="2"
                className="cursor-pointer hover:stroke-white transition-all"
                onClick={() => onEntryClick(entry)}
              />
              {/* Tooltip */}
              <g className="opacity-0 hover:opacity-100 pointer-events-none">
                <rect x={x - 60} y={y - 70} width="120" height="50" fill="#1f2937" rx="6" />
                <text x={x} y={y - 50} fill="white" fontSize="12" textAnchor="middle" fontWeight="bold">
                  {entry.ticker}
                </text>
                <text x={x} y={y - 35} fill="#10b981" fontSize="11" textAnchor="middle">
                  {entry.actual_percent?.toFixed(1)}%
                </text>
                <text x={x} y={y - 20} fill="#9ca3af" fontSize="10" textAnchor="middle">
                  Day {entry.days_to_hit} • AI {entry.ai_confidence}%
                </text>
              </g>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex justify-center gap-6 mt-4 text-xs text-gray-400">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span>&lt;40% Conf</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500"></div>
          <span>40–59%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span>60–79%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
          <span>≥80%</span>
        </div>
      </div>
    </div>
  );
};

export default ScatterPlot;