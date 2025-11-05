'use client';

import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Trophy, Target, Zap } from 'lucide-react';
import { MoonAlert } from '@/lib/api';
import { LiveLinesChart, generateSamplePerformanceData } from './LiveLinesChart';
import { StickyHeader } from './StickyHeader';
import { pushService } from '@/lib/PushService';

interface PerformanceProps {
  alerts: MoonAlert[];
  isLoading?: boolean;
  error?: string | null;
}

interface PerformanceCardProps {
  alert: MoonAlert;
  onDetails: (alertId: string) => void;
  onAddToWatchlist: (alertId: string) => void;
}

function PerformanceCard({ alert, onDetails, onAddToWatchlist }: PerformanceCardProps) {
  // Calculate current performance
  const currentPrice = alert.currentPrice || alert.entryPrice;
  const changePercent = ((currentPrice - alert.entryPrice) / alert.entryPrice) * 100;
  const isPositive = changePercent >= 0;
  
  // Determine outcome classification with enhanced target hit detection
  const getOutcome = () => {
    if (alert.type === 'bullish') {
      if (changePercent >= 20) return {
        label: 'WIN',
        color: 'bg-green-500',
        icon: '🚀',
        description: 'Bullish target achieved!'
      };
      if (changePercent >= 10) return {
        label: 'PARTIAL',
        color: 'bg-yellow-500',
        icon: '📈',
        description: 'Partial bullish hit'
      };
      if (changePercent < -5) return {
        label: 'BEARISH',
        color: 'bg-red-500',
        icon: '💥',
        description: 'Unexpected bearish move'
      };
      return {
        label: 'PENDING',
        color: 'bg-gray-500',
        icon: '⏳',
        description: 'Tracking progress...'
      };
    } else {
      if (changePercent <= -20) return {
        label: 'WIN',
        color: 'bg-green-500',
        icon: '🎯',
        description: 'Bearish prediction hit!'
      };
      if (changePercent <= -10) return {
        label: 'PARTIAL',
        color: 'bg-yellow-500',
        icon: '📉',
        description: 'Partial bearish detected'
      };
      if (changePercent > 5) return {
        label: 'MISS',
        color: 'bg-gray-500',
        icon: '❌',
        description: 'Prediction missed'
      };
      return {
        label: 'PENDING',
        color: 'bg-blue-500',
        icon: '⏳',
        description: 'Monitoring for bearish...'
      };
    }
  };

  const outcome = getOutcome();
  
  // Mock gut weight (in production, this comes from ML SHAP analysis)
  const gutWeight = alert.gutVote === 'BULLISH' ? '+0.18' : alert.gutVote === 'BEARISH' ? '+0.03' : '+0.00';
  
  // Determine pick type
  const pickType = alert.type === 'bullish' ? 'BULLISH PICK' : 'BEARISH PICK';
  const pickTypeColor = alert.type === 'bullish' ? 'text-green-400' : 'text-red-400';
  
  // Format date and time
  const pickDate = new Date(alert.timestamp);
  const formattedDate = pickDate.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });
  const formattedTime = pickDate.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  });

  // Calculate price targets (actual prices, not percentages)
  const targetLowPct = alert.targetRange?.low || (alert.type === 'bullish' ? 18 : -18);
  const targetAvgPct = alert.targetRange?.avg || (alert.type === 'bullish' ? 23 : -23);
  const targetHighPct = alert.targetRange?.high || (alert.type === 'bullish' ? 31 : -31);
  
  const lowTarget = alert.entryPrice * (1 + targetLowPct / 100);
  const medTarget = alert.entryPrice * (1 + targetAvgPct / 100);
  const highTarget = alert.entryPrice * (1 + targetHighPct / 100);
  
  // Calculate stop loss 
  const stopLoss = alert.type === 'bullish'
    ? alert.entryPrice * 0.95
    : alert.entryPrice * 1.05;

  // Combined confidence (ML-learned, no manual boosts)
  const combinedConfidence = alert.finalConfidence || alert.confidence;

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border-2 border-gray-700 relative">
      {/* Enhanced Outcome Badge */}
      <div className={`absolute -top-3 -right-3 ${outcome.color} text-white px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1`}>
        <span>{outcome.icon}</span>
        <span>{outcome.label}</span>
      </div>

      {/* Outcome Description */}
      <div className="absolute -top-8 right-0 text-xs text-gray-400 italic">
        {outcome.description}
      </div>

      {/* Header Row - Pick Type and Confidence */}
      <div className="flex justify-between items-start mb-3">
        <div className={`text-xs font-bold ${pickTypeColor} bg-gray-700 px-2 py-1 rounded`}>
          {pickType}
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">{alert.confidence}%</div>
          <div className="text-xs text-gray-400">Confidence Score</div>
        </div>
      </div>

      {/* Stock Info Row */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-xl font-bold text-white">{alert.ticker}</h3>
          <div className="text-sm text-gray-300">${currentPrice.toFixed(2)}</div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">Final Result</div>
          <div className={`text-lg font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '+' : ''}{changePercent.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Price When Alerted with Date/Time */}
      <div className="flex justify-between items-center mb-4 text-sm">
        <div>
          <span className="text-gray-400">Price when alerted:</span>
          <div className="text-xs text-gray-500 mt-1">{formattedDate} • {formattedTime}</div>
        </div>
        <span className="text-white font-medium">${alert.entryPrice.toFixed(2)}</span>
      </div>

      {/* Price Targets & Stop Loss Box */}
      <div className="bg-gray-700 rounded-lg p-4 mb-4">
        <div className="mb-3">
          <div className="text-xs text-gray-400 mb-2">2-day window — {alert.type} possible</div>
          <div className="flex justify-between text-sm">
            <div className="text-center">
              <div className="text-yellow-400 font-semibold">${lowTarget.toFixed(2)}</div>
              <div className="text-xs text-gray-500">Low</div>
            </div>
            <div className="text-center">
              <div className="text-green-400 font-semibold">${medTarget.toFixed(2)}</div>
              <div className="text-xs text-gray-500">Med</div>
            </div>
            <div className="text-center">
              <div className="text-cyan-400 font-semibold">${highTarget.toFixed(2)}</div>
              <div className="text-xs text-gray-500">High</div>
            </div>
          </div>
        </div>
        
        <div className="border-t border-gray-600 pt-3">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-400">Recommended stop loss:</span>
            <span className="text-red-400 font-medium">${stopLoss.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Confidence Breakdown */}
      <div className="mb-4">
        <div className="text-xs text-gray-400 mb-2">Confidence Breakdown</div>
        <div className="flex justify-between items-center text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-400">AI:</span>
            <span className="text-cyan-400 font-semibold">{alert.confidence}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Your Gut:</span>
            <span className={`font-semibold flex items-center gap-1 ${
              alert.gutVote === 'BULLISH' ? 'text-green-400' :
              alert.gutVote === 'BEARISH' ? 'text-red-400' : 'text-gray-400'
            }`}>
              {alert.gutVote === 'BULLISH' && <TrendingUp className="w-3 h-3" />}
              {alert.gutVote === 'BEARISH' && <TrendingDown className="w-3 h-3" />}
              {alert.gutVote || 'PASS'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Combined:</span>
            <span className="text-white font-bold">{combinedConfidence}%</span>
          </div>
        </div>
      </div>

      {/* Gut Weight Badge */}
      <div className="mb-4">
        <div className="bg-cyan-600/20 border border-cyan-600/50 rounded-lg px-3 py-2 text-center">
          <div className="text-cyan-400 font-semibold text-sm">Your Gut Weight: {gutWeight}</div>
          <div className="text-xs text-gray-400 mt-1">ML-learned impact</div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => onDetails(alert.id)}
          className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          Details
        </button>
        <button
          onClick={() => onAddToWatchlist(alert.id)}
          className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          Add to Watchlist
        </button>
      </div>
    </div>
  );
}

export function Performance({ alerts, isLoading, error }: PerformanceProps) {
  const [sortBy, setSortBy] = useState<'confidence' | 'change' | 'time'>('time');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [sortOpen, setSortOpen] = useState(false);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'all'>('30d');
  const [activeFilter, setActiveFilter] = useState<'all' | 'watchlist' | 'ai-only' | 'gut-only'>('all');
  const [isLiveUpdating, setIsLiveUpdating] = useState(true);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());
  const [performanceData, setPerformanceData] = useState(generateSamplePerformanceData());

  // WebSocket simulation for real-time price updates
  useEffect(() => {
    if (!isLiveUpdating) return;

    const interval = setInterval(() => {
      // Simulate WebSocket price updates every 15 seconds
      setLastUpdateTime(new Date());

      // In production, this would update alert prices via WebSocket
      // For now, we simulate the live update indicator
    }, 15000);

    return () => clearInterval(interval);
  }, [isLiveUpdating]);

  // Filter picks to 7+ days old only (historical archive)
  const now = new Date();
  const historicalAlerts = alerts.filter(alert => {
    const daysOld = Math.floor((now.getTime() - new Date(alert.timestamp).getTime()) / 86400000);
    return daysOld > 6;
  });

  // Sort historical alerts
  const sortAlerts = (alertsToSort: MoonAlert[]) => {
    return [...alertsToSort].sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'confidence':
          comparison = (b.finalConfidence || b.confidence) - (a.finalConfidence || a.confidence);
          break;
        case 'change':
          const aChange = a.currentPrice ? ((a.currentPrice - a.entryPrice) / a.entryPrice) * 100 : 0;
          const bChange = b.currentPrice ? ((b.currentPrice - b.entryPrice) / b.entryPrice) * 100 : 0;
          comparison = bChange - aChange;
          break;
        case 'time':
          comparison = new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
          break;
        default:
          comparison = 0;
      }

      return sortDirection === 'desc' ? comparison : -comparison;
    });
  };

  const sortedAlerts = sortAlerts(historicalAlerts);

  // Calculate hero performance stats based on active filter
  const calculateHeroStats = () => {
    const filteredData = timeRange === 'all' ? performanceData :
      performanceData.filter(p => p.daysSincePick <= (timeRange === '7d' ? 7 : 30));

    if (filteredData.length === 0) return { beatAI: 0, highHits: 0, totalPicks: 0 };

    let primaryReturns: number[] = [];
    let aiReturns = filteredData.map(d => d.aiOnlyReturn).filter(r => r !== null);

    switch (activeFilter) {
      case 'watchlist':
        primaryReturns = filteredData.map(d => d.watchlistReturn).filter(r => r !== null);
        break;
      case 'gut-only':
        primaryReturns = filteredData.map(d => d.gutOnlyReturn).filter(r => r !== null);
        break;
      case 'ai-only':
        primaryReturns = aiReturns;
        aiReturns = []; // No comparison for AI-only
        break;
      default: // 'all'
        primaryReturns = filteredData.map(d => d.watchlistReturn).filter(r => r !== null);
    }

    const avgPrimaryReturn = primaryReturns.reduce((a, b) => a + b, 0) / primaryReturns.length;
    const avgAiReturn = aiReturns.length > 0 ? aiReturns.reduce((a, b) => a + b, 0) / aiReturns.length : 0;

    const beatAI = aiReturns.length > 0 ? avgPrimaryReturn - avgAiReturn : 0;
    const highHits = primaryReturns.filter(r => r >= 31).length;

    return { beatAI, highHits, totalPicks: primaryReturns.length };
  };

  const { beatAI, highHits, totalPicks } = calculateHeroStats();



  return (
    <div className="space-y-6">
      {/* Sticky Header */}
      <StickyHeader title="Performance" />

      <div className="px-4">


      {/* Live Performance Chart */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white">Live Performance Tracking</h2>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isLiveUpdating ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`}></div>
            <span className="text-gray-400 text-sm">
              {isLiveUpdating ? 'Live' : 'Paused'}
            </span>
          </div>
        </div>

        <LiveLinesChart
          data={performanceData}
          timeRange={timeRange}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
          totalPicks={totalPicks}
          className=""
        />
      </div>

      {/* Collapsible Sort - only show if we have historical picks */}
      {sortedAlerts.length > 0 && (
        <div className="text-center mb-6">
          <button
            onClick={() => setSortOpen(!sortOpen)}
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Sort by {sortBy === 'confidence' ? 'Confidence' : sortBy === 'change' ? '% Change' : 'Time'}
            {sortOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          
          {sortOpen && (
            <div className="mt-2 bg-gray-800 rounded-lg p-3 inline-block">
              <div className="flex gap-3">
                {(['confidence', 'change', 'time'] as const).map((sort) => (
                  <button
                    key={sort}
                    onClick={() => {
                      if (sortBy === sort) {
                        setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc');
                      } else {
                        setSortBy(sort);
                        setSortDirection('desc');
                      }
                      setSortOpen(false);
                    }}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      sortBy === sort 
                        ? 'bg-cyan-600 text-white' 
                        : 'text-gray-400 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    {sort === 'confidence' ? 'Confidence' : sort === 'change' ? '% Change' : 'Time'}
                    {sortBy === sort && (sortDirection === 'desc' ? ' ↓' : ' ↑')}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Performance Cards */}
      <div className="space-y-4">
        {sortedAlerts.length > 0 ? (
          sortedAlerts.map((alert) => (
            <PerformanceCard
              key={alert.id}
              alert={alert}
              onDetails={(alertId) => console.log('Show details:', alertId)}
              onAddToWatchlist={(alertId) => console.log('Add to watchlist:', alertId)}
            />
          ))
        ) : (
          /* Empty State */
          <div className="text-center py-16">
            <div className="w-20 h-20 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">📊</span>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              No historical picks yet
            </h2>
            <p className="text-gray-400">
              Picks older than 7 days will appear here
            </p>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
