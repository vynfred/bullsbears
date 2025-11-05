'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { DetailedPickCard } from './DetailedPickCard';
import { StickyHeader } from './StickyHeader';
import { MoonAlert } from '@/lib/api';

interface PulseProps {
  alerts: MoonAlert[];
  isLoading?: boolean;
  error?: string | null;
}

export function Pulse({ alerts, isLoading, error }: PulseProps) {
  const [sortBy, setSortBy] = useState<'confidence' | 'change' | 'time'>('confidence');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [sortOpen, setSortOpen] = useState(false);
  // All alerts are now visible without gut check requirement

  // Filter picks to last 7 days only (0-6 days old)
  const now = new Date();
  const recentAlerts = alerts.filter(alert => {
    const daysOld = Math.floor((now.getTime() - new Date(alert.timestamp).getTime()) / 86400000);
    return daysOld <= 6;
  });

  // Sort alerts
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

  const sortedAlerts = sortAlerts(recentAlerts);
  const liveCount = recentAlerts.filter(alert => {
    const daysOld = Math.floor((now.getTime() - new Date(alert.timestamp).getTime()) / 86400000);
    return daysOld === 0;
  }).length;

  // Future: Add to watchlist functionality
  const handleAddToWatchlist = (symbol: string) => {
    console.log('Adding to watchlist:', symbol);
    // TODO: Implement watchlist API call
  };
  return (
    <div className="space-y-4">
      <StickyHeader />

      <div className="px-4">
        {/* Loading State */}
        {isLoading && alerts.length === 0 && (
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{ borderColor: 'var(--color-primary)' }}></div>
            <p style={{ color: 'var(--text-muted)' }}>Loading live predictions...</p>
          </div>
        )}

        {/* Error State */}
        {error && alerts.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>Connection Error</h2>
            <p className="mb-6" style={{ color: 'var(--text-muted)' }}>{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 rounded-lg font-semibold transition-colors"
              style={{
                background: 'var(--color-primary)',
                color: 'var(--bg-primary)',
                border: '1px solid var(--color-primary)'
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Live Data Indicator */}
        {alerts.length > 0 && (
          <div className="flex items-center justify-center gap-2 mb-4">
            <div
              className={`w-2 h-2 rounded-full ${isLoading ? 'animate-pulse' : ''}`}
              style={{
                backgroundColor: isLoading ? 'var(--color-warning)' : 'var(--color-gain)'
              }}
            ></div>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {isLoading ? 'Updating...' : `Live data • ${alerts.length} alerts`}
            </span>
            {error && (
              <span className="text-sm ml-2" style={{ color: 'var(--color-loss)' }}>• Connection issues</span>
            )}
          </div>
        )}

        {/* AI Picks Header */}
        <div className="text-center mb-6">
          <div className="text-gray-400 text-lg">
            Monday, November 4th • 8:30 AM
          </div>
          <div className="flex items-center justify-center gap-2 text-green-400 mt-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">{liveCount} active picks</span>
          </div>
        </div>

        {sortedAlerts.length > 0 && (
          <div className="text-center">
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
                          setSortDirection(sort === 'time' ? 'desc' : 'desc');
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

        <div className="space-y-4">
          {sortedAlerts.length > 0 ? (
            sortedAlerts.map((alert) => (
              <DetailedPickCard
                key={alert.id}
                alert={alert}
                onDetails={(alertId) => console.log('Show details:', alertId)}
                onAddToWatchlist={(alertId) => console.log('Add to watchlist:', alertId)}
              />
            ))
          ) : (
            <div className="text-center py-16">
              <div className="w-20 h-20 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🚀</span>
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">
                No rockets yet — check back at 8:30 AM
              </h2>
              <p className="text-gray-400">
                Daily picks will appear here after screening
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
