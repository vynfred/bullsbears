'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { BarChart3, TrendingUp, Target, Trophy, Calendar, Zap, Brain, Activity, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { StickyHeader } from './StickyHeader';
import { MoonAlert } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from 'recharts';

interface AnalyticsProps {
  alerts: MoonAlert[];
  isLoading?: boolean;
  error?: string | null;
}

type TimeFrame = '1d' | '3d' | '5d' | '7d' | '1m' | '3m' | '6m' | '1y';

export function Analytics({ alerts, isLoading, error }: AnalyticsProps) {
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [nextRetrainCountdown, setNextRetrainCountdown] = useState('6h 12m 03s');

  // Live countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const nextRetrain = new Date(now.getTime() + 6 * 60 * 60 * 1000 + 12 * 60 * 1000 + 3 * 1000); // 6h 12m 03s from now
      const diff = nextRetrain.getTime() - now.getTime();

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setNextRetrainCountdown(`${hours}h ${minutes}m ${seconds.toString().padStart(2, '0')}s`);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Calculate analytics metrics
  const analyticsData = useMemo(() => {
    // 90-day rolling accuracy data
    const accuracyData = Array.from({ length: 90 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (89 - i));
      const baseAccuracy = 68 + (i / 89) * 4.4; // Climbs from 68% to 72.4%
      const variance = Math.sin(i * 0.1) * 1.5; // Add realistic variance
      return {
        date: date.toISOString().split('T')[0],
        accuracy: Math.min(92, Math.max(50, baseAccuracy + variance)),
        picks: Math.floor(Math.random() * 8) + 1,
        moonHits: Math.floor(Math.random() * 15) + 5
      };
    });

    // Confidence tiers with relative scaling
    const todaysMaxConfidence = 92; // NVDA example
    const confidenceTiers = [
      {
        tier: 'High',
        range: '80–92%',
        hitRate: 88,
        hits: 12,
        total: 14,
        bars: 8,
        maxBars: 10
      },
      {
        tier: 'Med',
        range: '65–79%',
        hitRate: 71,
        hits: 22,
        total: 31,
        bars: 6,
        maxBars: 10
      },
      {
        tier: 'Low',
        range: '55–64%',
        hitRate: 52,
        hits: 18,
        total: 35,
        bars: 3,
        maxBars: 10
      }
    ];

    // 24H Wins & Misses rotating cards
    const recentResults = [
      { symbol: 'NVDA', change: '+31%', timeframe: '36h', confidence: 92, type: 'moon', color: 'green' },
      { symbol: 'COIN', change: '–28%', timeframe: '24h', confidence: 68, type: 'rug', color: 'red' },
      { symbol: 'TSLA', change: '+24%', timeframe: '18h', confidence: 85, type: 'moon', color: 'green' },
      { symbol: 'AMD', change: '–19%', timeframe: '42h', confidence: 73, type: 'rug', color: 'red' },
      { symbol: 'AAPL', change: '+16%', timeframe: '28h', confidence: 79, type: 'moon', color: 'green' }
    ];

    // Global Hot Bets leaderboard
    const globalHotBets = [
      { rank: 1, symbol: 'NVDA', change: '+18.2%', users: 2847, confidence: 92, type: 'moon' },
      { rank: 2, symbol: 'TSLA', change: '+14.7%', users: 2103, confidence: 85, type: 'moon' },
      { rank: 3, symbol: 'AMD', change: '+11.3%', users: 1789, confidence: 78, type: 'moon' },
      { rank: 4, symbol: 'COIN', change: '–9.4%', users: 1204, confidence: 68, type: 'rug' },
      { rank: 5, symbol: 'HOOD', change: '+8.1%', users: 987, confidence: 74, type: 'moon' }
    ];

    return {
      accuracyData,
      confidenceTiers,
      recentResults,
      globalHotBets,
      todaysMaxConfidence,
      currentAccuracy: 72.4,
      accuracyChange: 0.8,
      totalPicks: 145,
      lastRetrain: '2h 14m ago',
      totalStocksToday: 888,
      targetStocksByDec: 3000,
      moonEvents: 2076,
      rugEvents: 1020,
      totalActiveTraders: 12430
    };
  }, []);

  // Auto-rotate cards every 3 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentCardIndex((prev) => (prev + 1) % analyticsData.recentResults.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [analyticsData.recentResults.length]);

  return (
    <div className="space-y-6">
      {/* Sticky Header */}
      <StickyHeader title="Analytics" />

      <div className="px-4">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-white mb-4">AI/ML Analytics</h1>
          <p className="text-gray-400">
            Real-time model performance, confidence analysis, and global trading insights.
          </p>
        </div>

        {/* 1. Model Accuracy Badge */}
        <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 border border-blue-500/30 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <Brain className="w-6 h-6 text-blue-400" />
              <span className="text-2xl font-bold text-white">MODEL ACCURACY {analyticsData.currentAccuracy}%</span>
              <div className="flex items-center gap-1 text-green-400">
                <ArrowUp className="w-4 h-4" />
                <span className="font-medium">+{analyticsData.accuracyChange}%</span>
              </div>
              <span className="text-gray-400">({analyticsData.totalPicks} picks)</span>
            </div>
          </div>
          <div className="text-gray-300 text-sm">
            Last retrain {analyticsData.lastRetrain}
          </div>
          <div className="text-gray-300 text-sm">
            Next retrain in <span className="text-cyan-400 font-mono">{nextRetrainCountdown}</span>
          </div>
        </div>

        {/* 2. Accuracy Over Time */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h3 className="text-white text-xl font-bold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-400" />
            ACCURACY OVER TIME
          </h3>
          <p className="text-gray-400 text-sm mb-4">90-day rolling line chart</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analyticsData.accuracyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  stroke="#9CA3AF"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis stroke="#9CA3AF" domain={[65, 75]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  formatter={(value: any, name: string) => [
                    `${value.toFixed(1)}%`,
                    name === 'accuracy' ? 'Accuracy' : name
                  ]}
                  labelFormatter={(label) => {
                    const date = new Date(label);
                    const moonHits = analyticsData.accuracyData.find(d => d.date === label)?.moonHits || 0;
                    return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}: ${moonHits} moon hits in 24h`;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#3B82F6"
                  strokeWidth={3}
                  dot={false}
                  name="Model Accuracy"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="text-center text-gray-400 text-sm mt-2">
            Blue line climbs 68% → 72.4%
          </div>
        </div>

        {/* 3. Confidence Tiers */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h3 className="text-white text-xl font-bold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-purple-400" />
            CONFIDENCE TIERS (relative scale)
          </h3>

          <div className="space-y-4 mb-6">
            {analyticsData.confidenceTiers.map((tier, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1">
                  <div className="w-12 text-white font-medium">{tier.tier}</div>
                  <div className="w-20 text-gray-400 text-sm">{tier.range}</div>
                  <div className="flex-1 flex items-center gap-2">
                    <div className="flex">
                      {Array.from({ length: tier.maxBars }, (_, i) => (
                        <div
                          key={i}
                          className={`w-3 h-4 mr-1 ${
                            i < tier.bars
                              ? tier.tier === 'High' ? 'bg-green-500' : tier.tier === 'Med' ? 'bg-yellow-500' : 'bg-red-500'
                              : 'bg-gray-600'
                          }`}
                        />
                      ))}
                    </div>
                    <span className="text-white font-bold">{tier.hitRate}% hit</span>
                    <span className="text-gray-400">({tier.hits}/{tier.total})</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-gray-700 pt-4">
            <div className="text-gray-400 text-sm mb-2">
              Relative scale • Today's ceiling = {analyticsData.todaysMaxConfidence}% (NVDA)
            </div>
            <div className="text-gray-400 text-sm mb-4">
              Yesterday's max was 89%. We never show 100%.
            </div>

            <div className="relative">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-bold">{analyticsData.todaysMaxConfidence}%</span>
                <span className="text-gray-400 text-sm">← today's max</span>
              </div>
              <div className="w-full bg-gray-700 h-6 rounded-lg overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-600 to-pink-600 relative"
                  style={{ width: `${(analyticsData.todaysMaxConfidence / 100) * 100}%` }}
                >
                  <div className="absolute right-0 top-0 h-full w-2 bg-white/30 animate-pulse" />
                </div>
              </div>
              <div className="text-gray-400 text-xs mt-1">
                moves up when hotter signals hit
              </div>
            </div>
          </div>
        </div>

        {/* 4. What We Track */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h3 className="text-white text-xl font-bold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            WHAT WE TRACK
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <div className="text-blue-400 font-bold">TECHNICAL</div>
              <div className="text-gray-300 text-sm">42 indicators • volume surge • RSI</div>
            </div>
            <div className="space-y-2">
              <div className="text-green-400 font-bold">SOCIAL</div>
              <div className="text-gray-300 text-sm">1.2M X posts • Grok+DeepSeek • CEO spikes</div>
            </div>
            <div className="space-y-2">
              <div className="text-yellow-400 font-bold">ECONOMIC</div>
              <div className="text-gray-300 text-sm">Fed • CPI • yield curve • VIX pops</div>
            </div>
          </div>
        </div>

        {/* 5. Screening Scale */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h3 className="text-white text-xl font-bold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-orange-400" />
            SCREENING SCALE
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-300">{analyticsData.totalStocksToday} stocks today</span>
                <span className="text-white font-bold">→ {analyticsData.targetStocksByDec.toLocaleString()} by Dec 31</span>
              </div>
              <div className="w-full bg-gray-700 h-2 rounded-full">
                <div
                  className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full"
                  style={{ width: `${(analyticsData.totalStocksToday / analyticsData.targetStocksByDec) * 100}%` }}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-green-400">{analyticsData.moonEvents.toLocaleString()} moon events</span>
                <span className="text-red-400">{analyticsData.rugEvents.toLocaleString()} rug events</span>
              </div>
            </div>
          </div>
        </div>

        {/* 6. 24H Wins & Misses (auto-rotating cards) */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h3 className="text-white text-xl font-bold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            24H WINS & MISSES (auto-rotating cards)
          </h3>

          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setCurrentCardIndex((prev) => (prev - 1 + analyticsData.recentResults.length) % analyticsData.recentResults.length)}
                className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-white" />
              </button>

              <div className="flex-1 mx-4">
                {analyticsData.recentResults.map((result, index) => (
                  <div
                    key={index}
                    className={`transition-all duration-500 ${
                      index === currentCardIndex ? 'opacity-100 scale-100' : 'opacity-0 scale-95 absolute'
                    }`}
                  >
                    {index === currentCardIndex && (
                      <div className={`text-center p-6 rounded-lg border-2 ${
                        result.type === 'moon'
                          ? 'border-green-500 bg-green-900/20'
                          : 'border-red-500 bg-red-900/20'
                      }`}>
                        <div className="text-3xl font-bold text-white mb-2">{result.symbol}</div>
                        <div className={`text-2xl font-bold mb-2 ${
                          result.type === 'moon' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {result.change} in {result.timeframe}
                        </div>
                        <div className="text-gray-400">{result.confidence}% confidence</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={() => setCurrentCardIndex((prev) => (prev + 1) % analyticsData.recentResults.length)}
                className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-white" />
              </button>
            </div>

            <div className="flex justify-center gap-2">
              {analyticsData.recentResults.map((_, index) => (
                <div
                  key={index}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    index === currentCardIndex ? 'bg-blue-400' : 'bg-gray-600'
                  }`}
                />
              ))}
            </div>

            <div className="text-center text-gray-400 text-sm mt-4">
              ← swipe for more →
            </div>
          </div>
        </div>

        {/* 7. Global Hot Bets (neon leaderboard) */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h3 className="text-white text-xl font-bold mb-4 flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-400" />
            GLOBAL HOT BETS (neon leaderboard)
          </h3>

          <div className="space-y-3 mb-4">
            {analyticsData.globalHotBets.map((bet, index) => (
              <div
                key={index}
                className={`flex items-center justify-between p-4 rounded-lg border ${
                  bet.type === 'moon'
                    ? 'border-green-500/30 bg-green-900/10'
                    : 'border-red-500/30 bg-red-900/10'
                } hover:border-opacity-60 transition-all`}
              >
                <div className="flex items-center gap-4">
                  <div className="text-2xl font-bold text-white w-8">{bet.rank}</div>
                  <div className="text-xl font-bold text-white">{bet.symbol}</div>
                  <div className={`text-lg font-bold ${
                    bet.type === 'moon' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {bet.change}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-gray-300">
                    {bet.users.toLocaleString()} {bet.type === 'rug' ? 'rugs' : 'users'}
                  </div>
                  <div className="text-purple-400 font-bold">{bet.confidence}%</div>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center text-cyan-400 font-medium">
            "{analyticsData.totalActiveTraders.toLocaleString()} traders are riding these right now."
          </div>
        </div>

        {/* 8. One-Tap Footer */}
        <div className="text-center mb-8">
          <button
            onClick={() => {
              // Navigate to Pulse tab - this would be handled by parent component
              window.dispatchEvent(new CustomEvent('navigate-to-pulse'));
            }}
            className="bg-gradient-to-r from-lime-500 to-green-500 hover:from-lime-400 hover:to-green-400 text-black font-bold py-4 px-8 rounded-lg text-lg transition-all duration-300 animate-pulse hover:animate-none transform hover:scale-105"
          >
            <Eye className="w-5 h-5 inline mr-2" />
            SEE RECENT PICKS
          </button>
          <div className="text-gray-400 text-sm mt-2">
            jumps straight to Pulse tab
          </div>
        </div>
      </div>
    </div>
  );
}
