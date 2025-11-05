'use client';

import React, { useState, useEffect } from 'react';
import {
  demoHistoryEntries,
  demoPersonalPulse,
  demoGlobalStats,
  demoPersonalStats,
  hasVotedToday,
  getFreshEntries,
  getStaleEntries,
  PersonalPulseEntry,
  HistoryEntry
} from '@/lib/demoData';
import { MoonAlert } from '@/lib/api';
import { useLiveAlerts } from '@/hooks/useLiveAlerts';
import AlertCard from '@/components/AlertCard';

import PersonalPulseCard from '@/components/PersonalPulseCard';
import HistoryPulse from '@/components/HistoryPulse';
import { Rocket, Brain, Trophy, TrendingUp, Star, Filter } from 'lucide-react';
import { Pulse } from '@/components/Pulse';
import { Analytics } from '@/components/Analytics';
import { Watchlist } from '@/components/Watchlist';
import { ConfettiWrapper } from '@/components/ConfettiWrapper';
import { BottomTabBar, TabType } from '@/components/BottomTabBar';

type PulseSortBy = 'confidence' | 'change' | 'toMoon' | 'ticker';

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('pulse');

  // Handle navigation from Analytics to Pulse tab
  useEffect(() => {
    const handleNavigateToPulse = () => {
      setActiveTab('pulse');
    };

    window.addEventListener('navigate-to-pulse', handleNavigateToPulse);
    return () => window.removeEventListener('navigate-to-pulse', handleNavigateToPulse);
  }, []);

  // Live alerts from backend
  const {
    alerts: allAlerts,
    moonAlerts,
    rugAlerts,
    isLoading: alertsLoading,
    error: alertsError,
    refresh: refreshAlerts
  } = useLiveAlerts({
    moonLimit: 15,
    rugLimit: 15,
    refreshInterval: 5 * 60 * 1000, // 5 minutes
    enabled: true
  });

  // User ID for future watchlist functionality
  const userId = 'demo-user-123'; // In production, get from auth context

  // State for watchlist functionality (future implementation)
  const [watchlistItems, setWatchlistItems] = useState<string[]>([]);


  // Personal Pulse state
  const [personalPulse, setPersonalPulse] = useState<PersonalPulseEntry[]>(demoPersonalPulse);
  const [pulseSortBy, setPulseSortBy] = useState<PulseSortBy>('change');
  const [isFirstTimeUser, setIsFirstTimeUser] = useState(false); // Set to true for empty state demo

  // Helper function to sort personal pulse entries
  const sortPersonalPulse = (entries: PersonalPulseEntry[], sortBy: PulseSortBy): PersonalPulseEntry[] => {
    return [...entries].sort((a, b) => {
      switch (sortBy) {
        case 'confidence':
          return a.confidence - b.confidence; // Least to greatest (short top to bottom)
        case 'change':
          return a.percentChange - b.percentChange; // Least to greatest (short top to bottom)
        case 'toMoon':
          if (a.classification === 'WATCH' && b.classification === 'WATCH') {
            return (a.estimatedDaysToMoon || 999) - (b.estimatedDaysToMoon || 999); // Least to greatest
          }
          if (a.classification === 'WATCH') return -1;
          if (b.classification === 'WATCH') return 1;
          return a.percentChange - b.percentChange; // Least to greatest
        case 'ticker':
          return a.anonymousId.localeCompare(b.anonymousId); // A to Z
        default:
          return a.percentChange - b.percentChange; // Least to greatest (short top to bottom)
      }
    });
  };

  // Get sorted personal pulse entries
  const sortedPersonalPulse = sortPersonalPulse(personalPulse, pulseSortBy);
  const freshEntries = sortedPersonalPulse.filter(entry => !entry.isStale);
  const staleEntries = sortedPersonalPulse.filter(entry => entry.isStale);

  // All alerts are now visible without filtering



  // Future: Add to watchlist functionality
  const addToWatchlist = (symbol: string) => {
    setWatchlistItems(prev => [...prev, symbol]);
    // TODO: Call API to save to user's watchlist
  };





  // Show loading state while fetching initial data
  if (alertsLoading && allAlerts.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary)' }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{ borderColor: 'var(--color-primary)' }}></div>
          <p style={{ color: 'var(--text-muted)' }}>Loading live alerts...</p>
        </div>
      </div>
    );
  }

  // Show error state if alerts failed to load
  if (alertsError && allAlerts.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary)' }}>
        <div className="text-center max-w-md mx-auto px-4">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>Connection Error</h2>
          <p className="mb-6" style={{ color: 'var(--text-muted)' }}>{alertsError}</p>
          <button
            onClick={refreshAlerts}
            className="px-6 py-3 rounded-lg font-semibold transition-colors"
            style={{
              background: 'var(--color-primary)',
              color: 'var(--bg-primary)',
              border: '1px solid var(--color-primary)'
            }}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <ConfettiWrapper>
      <div className="min-h-screen overflow-x-hidden" style={{ background: 'var(--bg-primary)' }}>

      {/* Connection Status Indicator */}
      {alertsError && (
        <div className="border-b px-4 py-2" style={{
          background: 'var(--color-loss-bg)',
          borderColor: 'var(--color-loss-border)'
        }}>
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--color-loss)' }}>⚠️ Connection issues - showing cached data</span>
            <button
              onClick={refreshAlerts}
              className="text-sm underline hover:opacity-80 transition-opacity"
              style={{ color: 'var(--color-loss)' }}
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Tab Content */}
      <div className="max-w-full overflow-x-hidden pb-20">
        {activeTab === 'pulse' && (
          <Pulse
            alerts={allAlerts}
            isLoading={alertsLoading}
            error={alertsError}
          />
        )}

        {activeTab === 'watchlist' && (
          <Watchlist />
        )}

        {activeTab === 'analytics' && (
          <Analytics
            alerts={allAlerts}
            isLoading={alertsLoading}
            error={alertsError}
          />
        )}
      </div>



      {/* Bottom Tab Bar */}
      <BottomTabBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      </div>
    </ConfettiWrapper>
  );
}
