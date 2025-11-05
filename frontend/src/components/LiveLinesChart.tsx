'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from 'recharts';

interface PerformanceDataPoint {
  ts: number;
  price: number;
  locked: boolean;
  daysSincePick: number;
  watchlistReturn: number; // Your Watchlist Picks (yellow)
  aiOnlyReturn: number;    // AI-Only signals (blue)
  gutOnlyReturn: number;   // Gut Only picks (orange)
  communityReturn: number; // All Community (gray)
}

interface LiveLinesChartProps {
  data: PerformanceDataPoint[];
  timeRange: '7d' | '30d' | 'all';
  activeFilter: 'all' | 'watchlist' | 'ai-only' | 'gut-only';
  onFilterChange: (filter: 'all' | 'watchlist' | 'ai-only' | 'gut-only') => void;
  totalPicks: number;
  className?: string;
}

interface MiniCardProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

function MiniCard({ active, payload, label }: MiniCardProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
      <div className="text-xs text-gray-400 mb-2">Day {label}</div>

      {payload.map((entry, index) => {
        if (!entry.value) return null;

        let label = '';
        let color = '';

        switch (entry.dataKey) {
          case 'watchlistReturn':
            label = 'Your Watchlist';
            color = 'bg-yellow-400';
            break;
          case 'aiOnlyReturn':
            label = 'AI Only';
            color = 'bg-blue-400';
            break;
          case 'gutOnlyReturn':
            label = 'Gut Only';
            color = 'bg-orange-400';
            break;
          case 'communityReturn':
            label = 'Community';
            color = 'bg-gray-400';
            break;
          default:
            return null;
        }

        return (
          <div key={index} className="flex items-center gap-2 mb-1">
            <div className={`w-3 h-3 ${color} rounded-full`}></div>
            <span className="text-sm text-white">
              {label}: {entry.value > 0 ? '+' : ''}{entry.value.toFixed(1)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function LiveLinesChart({ data, timeRange, activeFilter, onFilterChange, totalPicks, className = '' }: LiveLinesChartProps) {
  // Filter data based on time range
  const filteredData = React.useMemo(() => {
    if (timeRange === 'all') return data;
    
    const maxDays = timeRange === '7d' ? 7 : 30;
    return data.filter(point => point.daysSincePick <= maxDays);
  }, [data, timeRange]);

  // Format X-axis labels
  const formatXAxisLabel = (tickItem: any) => {
    return `${tickItem}d`;
  };

  // Format Y-axis labels
  const formatYAxisLabel = (value: number) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(0)}%`;
  };

  return (
    <div className={`w-full ${className}`}>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={filteredData}
          margin={{
            top: 10,
            right: 15,
            left: 0,
            bottom: 10,
          }}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="#374151" 
            opacity={0.3}
          />
          
          <XAxis
            dataKey="daysSincePick"
            tickFormatter={formatXAxisLabel}
            stroke="#9CA3AF"
            fontSize={12}
            axisLine={false}
            tickLine={false}
          />
          
          <YAxis
            tickFormatter={formatYAxisLabel}
            stroke="#9CA3AF"
            fontSize={12}
            axisLine={false}
            tickLine={false}
            width={35}
          />
          
          {/* Zero reference line */}
          <ReferenceLine 
            y={0} 
            stroke="#6B7280" 
            strokeDasharray="2 2" 
            opacity={0.5}
          />
          

          
          <Tooltip
            content={<MiniCard />}
            cursor={{ stroke: '#6B7280', strokeWidth: 1, strokeDasharray: '3 3' }}
          />
          
          {/* Conditional Lines Based on Active Filter */}
          {(activeFilter === 'all' || activeFilter === 'watchlist') && (
            <Line
              type="monotone"
              dataKey="watchlistReturn"
              stroke="#EAB308"
              strokeWidth={3}
              dot={{ fill: '#EAB308', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: '#EAB308', strokeWidth: 2, fill: '#1F2937' }}
              name="Your Watchlist"
              connectNulls={false}
            />
          )}

          {(activeFilter === 'all' || activeFilter === 'ai-only') && (
            <Line
              type="monotone"
              dataKey="aiOnlyReturn"
              stroke="#3B82F6"
              strokeWidth={3}
              dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2, fill: '#1F2937' }}
              name="AI Only"
              connectNulls={false}
            />
          )}

          {(activeFilter === 'all' || activeFilter === 'gut-only') && (
            <Line
              type="monotone"
              dataKey="gutOnlyReturn"
              stroke="#F97316"
              strokeWidth={3}
              dot={{ fill: '#F97316', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: '#F97316', strokeWidth: 2, fill: '#1F2937' }}
              name="Gut Only"
              connectNulls={false}
            />
          )}

          {activeFilter === 'all' && (
            <Line
              type="monotone"
              dataKey="communityReturn"
              stroke="#9CA3AF"
              strokeWidth={2}
              dot={{ fill: '#9CA3AF', strokeWidth: 1, r: 3 }}
              activeDot={{ r: 5, stroke: '#9CA3AF', strokeWidth: 2, fill: '#1F2937' }}
              name="Community"
              connectNulls={false}
              opacity={0.6}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Interactive Legend/Filter Combined - Inline Style */}
      <div className="mt-4 flex items-center justify-center gap-4 text-sm overflow-x-auto">
        <div className="flex items-center gap-4 min-w-max">
          {[
            {
              id: 'all',
              label: 'ALL PICKS',
              count: totalPicks,
              lineColor: '#9CA3AF',
              textColor: 'text-gray-400'
            },
            {
              id: 'gut-only',
              label: 'YOUR GUT',
              count: Math.floor(totalPicks * 0.4),
              lineColor: '#F97316',
              textColor: 'text-orange-400'
            },
            {
              id: 'ai-only',
              label: 'AI-ONLY',
              count: Math.floor(totalPicks * 0.8),
              lineColor: '#3B82F6',
              textColor: 'text-blue-400'
            },
            {
              id: 'watchlist',
              label: 'WATCHLIST',
              count: Math.floor(totalPicks * 0.3),
              lineColor: '#EAB308',
              textColor: 'text-yellow-400'
            }
          ].map((filter) => (
            <button
              key={filter.id}
              onClick={() => onFilterChange(filter.id as any)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-all ${
                activeFilter === filter.id
                  ? `${filter.textColor} font-medium bg-gray-700/50 shadow-sm`
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
              }`}
            >
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: filter.lineColor }}
              ></div>
              <span className="whitespace-nowrap">{filter.count} {filter.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// Helper function to generate sample data for demo
export function generateSamplePerformanceData(): PerformanceDataPoint[] {
  const data: PerformanceDataPoint[] = [];

  // Generate 30 days of sample data
  for (let day = 0; day <= 30; day++) {
    const baseReturn = Math.sin(day * 0.2) * 15 + Math.random() * 10 - 5;
    const watchlistBoost = Math.random() * 6 - 1; // Watchlist picks slightly better
    const gutBoost = Math.random() * 8 - 2; // Gut picks variable performance
    const communityDrag = Math.random() * 4 - 2; // Community average

    data.push({
      ts: Date.now() - (30 - day) * 24 * 60 * 60 * 1000,
      price: 100 + baseReturn, // Mock price
      locked: day === 0,
      daysSincePick: day,
      watchlistReturn: Math.max(-25, Math.min(60, baseReturn + watchlistBoost)),
      aiOnlyReturn: Math.max(-20, Math.min(50, baseReturn)),
      gutOnlyReturn: Math.max(-30, Math.min(70, baseReturn + gutBoost)),
      communityReturn: Math.max(-15, Math.min(40, baseReturn + communityDrag))
    });
  }

  return data;
}
