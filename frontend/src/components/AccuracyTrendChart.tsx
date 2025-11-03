import React from 'react';
import { TrendingUp, TrendingDown, Minus, Target, Brain, Zap } from 'lucide-react';
import { demoAccuracyTrend, getCurrentTrend, getTrendStreak, AccuracyTrendPoint } from '../lib/demoData';

interface AccuracyTrendChartProps {
  showMiniVersion?: boolean; // For compact display in StatsBar
}

const AccuracyTrendChart: React.FC<AccuracyTrendChartProps> = ({ showMiniVersion = false }) => {
  const currentTrend = getCurrentTrend();
  const trendStreak = getTrendStreak();
  const latestPoint = demoAccuracyTrend[demoAccuracyTrend.length - 1];
  
  // Calculate chart dimensions
  const chartWidth = showMiniVersion ? 120 : 400;
  const chartHeight = showMiniVersion ? 40 : 200;
  const padding = showMiniVersion ? 5 : 20;
  
  // Find min/max values for scaling
  const allAccuracies = demoAccuracyTrend.flatMap(point => [
    point.gutAccuracy,
    point.aiAccuracy,
    point.combinedAccuracy
  ]);
  const minAccuracy = Math.min(...allAccuracies) - 5;
  const maxAccuracy = Math.max(...allAccuracies) + 5;
  
  // Scale functions
  const scaleX = (index: number) => 
    padding + (index / (demoAccuracyTrend.length - 1)) * (chartWidth - 2 * padding);
  
  const scaleY = (accuracy: number) => 
    chartHeight - padding - ((accuracy - minAccuracy) / (maxAccuracy - minAccuracy)) * (chartHeight - 2 * padding);
  
  // Generate path strings for each line
  const generatePath = (dataKey: keyof Pick<AccuracyTrendPoint, 'gutAccuracy' | 'aiAccuracy' | 'combinedAccuracy'>) => {
    return demoAccuracyTrend
      .map((point, index) => {
        const x = scaleX(index);
        const y = scaleY(point[dataKey]);
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      })
      .join(' ');
  };
  
  const getTrendIcon = () => {
    switch (currentTrend) {
      case 'UP':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'DOWN':
        return <TrendingDown className="w-4 h-4 text-red-400" />;
      default:
        return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };
  
  const getTrendColor = () => {
    switch (currentTrend) {
      case 'UP':
        return 'text-green-400';
      case 'DOWN':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  if (showMiniVersion) {
    // Mini version for StatsBar
    return (
      <div className="flex items-center gap-2">
        <div className="relative">
          <svg width={chartWidth} height={chartHeight} className="overflow-visible">
            {/* Combined accuracy line (main line) */}
            <path
              d={generatePath('combinedAccuracy')}
              stroke="#10b981"
              strokeWidth="2"
              fill="none"
              className="drop-shadow-sm"
            />
            
            {/* Gut accuracy line */}
            <path
              d={generatePath('gutAccuracy')}
              stroke="#f59e0b"
              strokeWidth="1.5"
              fill="none"
              opacity="0.7"
            />
            
            {/* Data points for latest */}
            {demoAccuracyTrend.map((point, index) => {
              if (index === demoAccuracyTrend.length - 1) {
                return (
                  <circle
                    key={index}
                    cx={scaleX(index)}
                    cy={scaleY(point.combinedAccuracy)}
                    r="3"
                    fill="#10b981"
                    stroke="#1f2937"
                    strokeWidth="1"
                  />
                );
              }
              return null;
            })}
          </svg>
        </div>
        
        <div className="flex items-center gap-1">
          {getTrendIcon()}
          <span className={`text-sm font-medium ${getTrendColor()}`}>
            {trendStreak}
          </span>
        </div>
      </div>
    );
  }

  // Full version for detailed view
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Accuracy Trend</h3>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            {getTrendIcon()}
            <span className={`text-sm font-medium ${getTrendColor()}`}>
              {currentTrend} {trendStreak}
            </span>
          </div>
          <div className="text-sm text-gray-400">
            {latestPoint.confidenceLevel} confidence
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="relative mb-4">
        <svg width={chartWidth} height={chartHeight} className="w-full overflow-visible">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map(value => (
            <g key={value}>
              <line
                x1={padding}
                y1={scaleY(value)}
                x2={chartWidth - padding}
                y2={scaleY(value)}
                stroke="#374151"
                strokeWidth="1"
                opacity="0.3"
              />
              <text
                x={padding - 5}
                y={scaleY(value)}
                fill="#9ca3af"
                fontSize="10"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {value}%
              </text>
            </g>
          ))}
          
          {/* Combined accuracy line */}
          <path
            d={generatePath('combinedAccuracy')}
            stroke="#10b981"
            strokeWidth="3"
            fill="none"
            className="drop-shadow-sm"
          />
          
          {/* Gut accuracy line */}
          <path
            d={generatePath('gutAccuracy')}
            stroke="#f59e0b"
            strokeWidth="2"
            fill="none"
          />
          
          {/* AI accuracy line */}
          <path
            d={generatePath('aiAccuracy')}
            stroke="#8b5cf6"
            strokeWidth="2"
            fill="none"
          />
          
          {/* Data points */}
          {demoAccuracyTrend.map((point, index) => (
            <g key={index}>
              {/* Combined accuracy point */}
              <circle
                cx={scaleX(index)}
                cy={scaleY(point.combinedAccuracy)}
                r="4"
                fill="#10b981"
                stroke="#1f2937"
                strokeWidth="2"
              />
              
              {/* Gut accuracy point */}
              <circle
                cx={scaleX(index)}
                cy={scaleY(point.gutAccuracy)}
                r="3"
                fill="#f59e0b"
                stroke="#1f2937"
                strokeWidth="1"
              />
              
              {/* AI accuracy point */}
              <circle
                cx={scaleX(index)}
                cy={scaleY(point.aiAccuracy)}
                r="3"
                fill="#8b5cf6"
                stroke="#1f2937"
                strokeWidth="1"
              />
            </g>
          ))}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-gray-300">Combined</span>
          <span className="text-green-400 font-medium">{latestPoint.combinedAccuracy}%</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Zap className="w-3 h-3 text-orange-400" />
          <span className="text-gray-300">Your Gut</span>
          <span className="text-orange-400 font-medium">{latestPoint.gutAccuracy}%</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Brain className="w-3 h-3 text-purple-400" />
          <span className="text-gray-300">AI Only</span>
          <span className="text-purple-400 font-medium">{latestPoint.aiAccuracy}%</span>
        </div>
      </div>
      
      {/* Trend Summary */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="text-center">
          <div className="text-sm text-gray-400 mb-1">
            Trending {currentTrend.toLowerCase()} for {trendStreak} period{trendStreak !== 1 ? 's' : ''}
          </div>
          <div className="text-xs text-gray-500">
            Based on {latestPoint.totalVotes} total votes • {latestPoint.confidenceLevel.toLowerCase()} confidence level
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccuracyTrendChart;
