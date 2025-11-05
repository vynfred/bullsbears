'use client';

import React, { useState } from 'react';
import { StickyHeader } from '@/components/StickyHeader';
import { AIVsWatchlistDashboard } from '@/components/AIVsWatchlistDashboard';
import { BarChart3, TrendingUp, Target, Trophy, Star, Activity } from 'lucide-react';

type PerformanceTab = 'overview' | 'ai-vs-watchlist' | 'detailed-analytics';

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<PerformanceTab>('overview');

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: BarChart3 },
    { id: 'ai-vs-watchlist' as const, label: 'AI vs Watchlist', icon: Trophy },
    { id: 'detailed-analytics' as const, label: 'Detailed Analytics', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-black">
      {/* Sticky Header */}
      <StickyHeader title="Analytics" />

      <div className="px-4 py-6 space-y-6">
        {/* Page Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-4">AI/ML Analytics</h1>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Track AI accuracy, win ratios, and confidence-to-outcome correlations across different timeframes.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex justify-center">
          <div className="bg-gray-900 rounded-lg p-1 flex space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="max-w-7xl mx-auto">
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'ai-vs-watchlist' && <AIVsWatchlistTab />}
          {activeTab === 'detailed-analytics' && <DetailedAnalyticsTab />}
        </div>
      </div>
    </div>
  );
}

function OverviewTab() {
  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Return</p>
              <p className="text-2xl font-bold text-green-400">+12.5%</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-400" />
          </div>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Win Rate</p>
              <p className="text-2xl font-bold text-white">68%</p>
            </div>
            <Target className="w-8 h-8 text-blue-400" />
          </div>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Active Positions</p>
              <p className="text-2xl font-bold text-white">7</p>
            </div>
            <Star className="w-8 h-8 text-yellow-400" />
          </div>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Best Trade</p>
              <p className="text-2xl font-bold text-green-400">+24.8%</p>
            </div>
            <Trophy className="w-8 h-8 text-green-400" />
          </div>
        </div>
      </div>

      {/* Performance Chart Placeholder */}
      <div className="bg-gray-900 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Performance Over Time</h3>
        <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-700 rounded-lg">
          <div className="text-center">
            <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-2" />
            <p className="text-gray-400">Performance chart coming soon</p>
            <p className="text-sm text-gray-500">Track your returns over time with interactive charts</p>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-gray-900 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {[
            { symbol: 'TSLA', action: 'Added to watchlist', return: '+5.2%', time: '2 hours ago' },
            { symbol: 'NVDA', action: 'Position closed', return: '+18.7%', time: '1 day ago' },
            { symbol: 'AAPL', action: 'Stop loss hit', return: '-3.1%', time: '3 days ago' },
          ].map((activity, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-semibold text-sm">{activity.symbol.slice(0, 2)}</span>
                </div>
                <div>
                  <p className="text-white font-medium">{activity.symbol}</p>
                  <p className="text-gray-400 text-sm">{activity.action}</p>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-semibold ${activity.return.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
                  {activity.return}
                </p>
                <p className="text-gray-400 text-sm">{activity.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AIVsWatchlistTab() {
  return (
    <div>
      <AIVsWatchlistDashboard />
    </div>
  );
}

function DetailedAnalyticsTab() {
  return (
    <div className="space-y-6">
      {/* Detailed Analytics Placeholder */}
      <div className="bg-gray-900 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Advanced Analytics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Risk Metrics */}
          <div className="space-y-4">
            <h4 className="font-medium text-white">Risk Metrics</h4>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Sharpe Ratio</span>
                <span className="text-white">1.24</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Max Drawdown</span>
                <span className="text-red-400">-8.3%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Volatility</span>
                <span className="text-white">15.2%</span>
              </div>
            </div>
          </div>

          {/* Sector Performance */}
          <div className="space-y-4">
            <h4 className="font-medium text-white">Sector Performance</h4>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Technology</span>
                <span className="text-green-400">+15.8%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Healthcare</span>
                <span className="text-green-400">+8.2%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Energy</span>
                <span className="text-red-400">-2.1%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trade Analysis */}
      <div className="bg-gray-900 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Trade Analysis</h3>
        <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-700 rounded-lg">
          <div className="text-center">
            <Activity className="w-12 h-12 text-gray-600 mx-auto mb-2" />
            <p className="text-gray-400">Detailed trade analysis coming soon</p>
            <p className="text-sm text-gray-500">Analyze your trading patterns and identify improvement opportunities</p>
          </div>
        </div>
      </div>
    </div>
  );
}
