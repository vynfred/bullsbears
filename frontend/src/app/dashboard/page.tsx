'use client';

import React, { useState, useEffect } from 'react';
import {
  demoMoonAlerts,
  demoHistoryEntries,
  demoPersonalPulse,
  demoGlobalStats,
  demoPersonalStats,
  hasVotedToday,
  getFreshEntries,
  getStaleEntries,
  PersonalPulseEntry,
  MoonAlert,
  HistoryEntry
} from '@/lib/demoData';
import AlertCard from '@/components/AlertCard';
import GutVoteModal from '@/components/GutVoteModal';

import PersonalPulseCard from '@/components/PersonalPulseCard';
import StatsBar from '@/components/StatsBar';
import AccuracyTrendChart from '@/components/AccuracyTrendChart';
import HistoryPulse from '@/components/HistoryPulse';
import { Rocket, Brain, Trophy, TrendingUp, Star, Bell, Filter } from 'lucide-react';
import { Pulse } from '@/components/Pulse';
import { BottomTabBar, TabType } from '@/components/BottomTabBar';

type PulseSortBy = 'confidence' | 'change' | 'toMoon' | 'ticker';

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('pulse');

  // Demo alerts with rug alerts added
  const rugAlerts = demoMoonAlerts.map(alert => ({
    ...alert,
    id: alert.id + '_rug',
    type: 'rug' as const,
    confidence: Math.max(60, alert.confidence - 15),
  }));

  const allAlerts = [...demoMoonAlerts, ...rugAlerts];
  const [alerts, setAlerts] = useState<MoonAlert[]>([]);
  const [currentVoteIndex, setCurrentVoteIndex] = useState<number | null>(null);
  const [votingComplete, setVotingComplete] = useState(false);


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

  // Load alerts on mount
  useEffect(() => {
    // Filter to top alerts (55%+ threshold) and take top 8
    const topAlerts = demoMoonAlerts
      .filter(alert => alert.confidence >= 55)
      .slice(0, 8);
    setAlerts(topAlerts);
  }, []);

  // Handle gut vote completion
  const handleVoteComplete = (alertId: string, vote: 'UP' | 'DOWN' | 'PASS') => {
    const votedAlert = alerts.find(alert => alert.id === alertId);

    setAlerts(prev => prev.map(alert => {
      if (alert.id === alertId) {
        // Simulate adaptive confidence boosting
        let boost = 0;
        if (vote === 'UP') boost = 3; // User agrees with AI
        if (vote === 'DOWN') boost = -2; // User disagrees
        // PASS = no boost

        return {
          ...alert,
          gutVote: vote,
          finalConfidence: alert.confidence + boost
        };
      }
      return alert;
    }));

    // Add voted stock to personal pulse
    if (votedAlert) {
      const newPulseEntry: PersonalPulseEntry = {
        id: `p_${alertId}`,
        anonymousId: `#${Math.random().toString(36).substr(2, 4).toUpperCase()}`,
        ticker: votedAlert.ticker,
        companyName: votedAlert.companyName,
        gutVote: vote,
        voteTime: new Date(),
        confidence: votedAlert.confidence + (vote === 'UP' ? 3 : vote === 'DOWN' ? -2 : 0),
        entryPrice: votedAlert.entryPrice,
        currentPrice: votedAlert.currentPrice || votedAlert.entryPrice,
        percentChange: 0, // Will be updated with live data
        daysElapsed: 0,
        classification: 'WATCH',
        isStale: false,
      };

      setPersonalPulse(prev => [newPulseEntry, ...prev]);
      setIsFirstTimeUser(false); // User now has entries
    }

    setCurrentVoteIndex(null);

    // Check if all votes are complete
    const updatedAlerts = alerts.map(alert =>
      alert.id === alertId ? { ...alert, gutVote: vote } : alert
    );

    if (updatedAlerts.every(alert => alert.gutVote)) {
      setVotingComplete(true);
    }
  };

  // Start gut check process
  const startGutCheck = () => {
    const firstUnvoted = alerts.findIndex(alert => !alert.gutVote);
    if (firstUnvoted !== -1) {
      setCurrentVoteIndex(firstUnvoted);
    }
  };

  // Get new alerts count for notification badge
  const newAlertsCount = alerts.filter(alert => alert.isNew).length;



  return (
    <div className="min-h-screen bg-gray-900 overflow-x-hidden">


      {/* Tab Content */}
      <div className="p-4 max-w-full overflow-x-hidden pb-20">
        {activeTab === 'pulse' && (
          <Pulse
            alerts={allAlerts}
            onGutVote={handleVoteComplete}
          />
        )}

        {activeTab === 'gutcheck' && (
          <div className="text-center py-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">Gut Check</h2>
              <p className="text-gray-400">
                Your live quantum timer. Feel the ping → swipe → watch your gut score climb.
              </p>
              <p className="text-sm text-yellow-400 mt-2 font-medium">
                🔒 COMPLETELY ANONYMOUS - No stock names shown
              </p>
            </div>

            {newAlertsCount > 0 && (
              <div className="bg-orange-900 border border-orange-700 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Bell className="w-5 h-5 text-orange-400" />
                  <span className="font-semibold text-orange-300">
                    {newAlertsCount} New Anonymous Alerts Ready
                  </span>
                </div>
                <p className="text-sm text-orange-400">
                  Swipe right for UP, left for DOWN
                </p>
              </div>
            )}

            {!votingComplete ? (
              <button
                onClick={startGutCheck}
                className="bg-orange-500 text-white px-8 py-4 rounded-lg font-semibold text-lg shadow-lg hover:bg-orange-600 transition-colors"
              >
                Start Anonymous Gut Check ⚡
              </button>
            ) : (
              <div className="bg-green-900 border border-green-700 rounded-lg p-6">
                <div className="text-green-300 font-semibold mb-2">
                  ✅ Gut Check Complete!
                </div>
                <div className="text-sm text-green-400">
                  All anonymous votes recorded. Check the Pulse tab for updated rankings.
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'performance' && (
          <HistoryPulse
            onEntrySelect={(entry) => {
              console.log('Selected history entry:', entry.id);
              // Could open a detailed modal here
            }}
          />
        )}

        {activeTab === 'watchlist' && (
          <div className="space-y-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">Your Watchlist</h2>
              <p className="text-gray-400">
                Your portfolio tracker. Entry/exit prices, live P&L, "MOON HIT" confetti, one-tap share.
              </p>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 text-center">
              <Star className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <div className="text-gray-400 text-xl mb-2">Your watchlist is empty</div>
              <div className="text-gray-500 text-sm mb-6">Add stocks by voting on gut checks</div>
              <button className="bg-yellow-500 text-black px-6 py-3 rounded-lg font-semibold hover:bg-yellow-400 transition-colors">
                Start Gut Check
              </button>
            </div>
          </div>
        )}

        {activeTab === 'trends' && (
          <div>
            {/* Trends Header */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">Trends</h2>
              <p className="text-gray-400">
                Global vs You. 30-day win-rate sparkline, "You beat 94% of traders" badge, top gut leaderboard.
              </p>
            </div>

            {/* Global vs Personal Stats Bar */}
            <StatsBar />

            {/* Full Accuracy Trend Chart */}
            <AccuracyTrendChart showMiniVersion={false} />

            {/* Additional Trend Insights */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Trend Performance Card */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-3">Performance Insights</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Best Accuracy:</span>
                    <span className="text-green-400 font-medium">91%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Worst Accuracy:</span>
                    <span className="text-red-400 font-medium">71%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Volatility:</span>
                    <span className="text-yellow-400 font-medium">±8.5%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Improvement:</span>
                    <span className="text-blue-400 font-medium">+8% (30d)</span>
                  </div>
                </div>
              </div>

              {/* Confidence Level Card */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-3">Confidence Level</h3>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-400 mb-2">HIGH</div>
                  <div className="text-sm text-gray-400 mb-3">Based on 24+ votes</div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className="bg-green-400 h-2 rounded-full" style={{ width: '85%' }}></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">85% confidence</div>
                </div>
              </div>

              {/* Next Milestone Card */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-3">Next Milestone</h3>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-400 mb-2">90%</div>
                  <div className="text-sm text-gray-400 mb-3">Target Accuracy</div>
                  <div className="text-xs text-gray-500">
                    Need 7% improvement to reach elite tier
                  </div>
                  <div className="mt-3 w-full bg-gray-700 rounded-full h-2">
                    <div className="bg-purple-400 h-2 rounded-full" style={{ width: '92%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Gut Vote Modal */}
      {currentVoteIndex !== null && (
        <GutVoteModal
          alert={alerts[currentVoteIndex]}
          onVote={(vote) => handleVoteComplete(alerts[currentVoteIndex].id, vote)}
          onClose={() => {
            const nextIndex = alerts.findIndex((alert, idx) =>
              idx > currentVoteIndex && !alert.gutVote
            );
            setCurrentVoteIndex(nextIndex !== -1 ? nextIndex : null);
          }}
        />
      )}

      {/* Bottom Tab Bar */}
      <BottomTabBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        gutCheckBadgeCount={newAlertsCount}
      />
    </div>
  );
}
