'use client';

import React, { useState } from 'react';
import { SortBar } from './SortBar';
import { CleanStockCard } from './CleanStockCard';
import { MoonAlert } from '@/lib/demoData';

interface PulseProps {
  alerts: MoonAlert[];
  onGutVote: (alertId: string, vote: 'UP' | 'DOWN' | 'PASS') => void;
}

export function Pulse({ alerts, onGutVote }: PulseProps) {
  const [sortBy, setSortBy] = useState<'confidence' | 'change' | 'time'>('confidence');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

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

  const sortedAlerts = sortAlerts(alerts);
  const liveCount = alerts.filter(alert => alert.status === 'active').length;
  return (
    <div className="space-y-4">
      {/* Header with Live Counter */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">PULSE</h1>
          <p className="text-gray-400">Today's picks • 8:30 AM</p>
        </div>
        <div className="flex items-center gap-2 text-green-400">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span className="text-sm font-medium">{liveCount} live</span>
        </div>
      </div>

      {/* Sort Bar */}
      <SortBar
        sortBy={sortBy}
        sortDirection={sortDirection}
        onSortChange={setSortBy}
        onDirectionChange={setSortDirection}
      />

      {/* Alert Cards */}
      <div className="space-y-4">
        {sortedAlerts.length > 0 ? (
          sortedAlerts.map((alert) => (
            <CleanStockCard
              key={alert.id}
              alert={alert}
              onAnalysisDetails={(alertId) => console.log('Analysis details:', alertId)}
              onTrackProgress={(alertId) => console.log('Track progress:', alertId)}
            />
          ))
        ) : (
          /* Empty State */
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
  );
}
