'use client';

import React, { useState } from 'react';
import { MoonAlert } from '@/lib/demoData';
import WhyModal from './WhyModal';

interface AlertCardProps {
  alert: MoonAlert;
  rank?: number;
  onGutVote: () => void;
  showFinalConfidence?: boolean;
}

export default function AlertCard({ alert, rank, onGutVote, showFinalConfidence }: AlertCardProps) {
  const [showWhy, setShowWhy] = useState(false);

  const displayConfidence = showFinalConfidence && alert.finalConfidence 
    ? alert.finalConfidence 
    : alert.confidence;

  const hasVoted = alert.gutVote && alert.gutVote !== 'PASS';
  const confidenceBoosted = alert.finalConfidence && alert.finalConfidence !== alert.confidence;

  return (
    <>
      <div className="bg-white rounded-xl p-4 shadow-sm border hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            {/* Rank (if final ranking) */}
            {rank && (
              <div className="flex items-center mb-2">
                <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold mr-2">
                  {rank}
                </div>
                <div className="text-xs text-gray-500">Final Ranking</div>
              </div>
            )}

            {/* Anonymous Stock ID */}
            <div className="text-lg font-mono text-gray-700 mb-1">
              Stock #{alert.randomId}
            </div>

            {/* Confidence Score */}
            <div className="flex items-center mb-2">
              <div className="text-3xl font-bold text-green-600 mr-2">
                {displayConfidence}% MOON
              </div>
              {confidenceBoosted && (
                <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                  {alert.finalConfidence! > alert.confidence ? '+' : ''}
                  {alert.finalConfidence! - alert.confidence}% gut boost
                </div>
              )}
            </div>

            {/* Top Reason */}
            <div className="text-sm text-gray-600 mb-3">
              {alert.topReason}
            </div>

            {/* Target Range */}
            <div className="bg-gray-50 rounded-lg p-3 mb-3">
              <div className="text-xs text-gray-500 mb-1">Target Range</div>
              <div className="flex items-center justify-between text-sm">
                <div>
                  <span className="text-gray-600">Low:</span>
                  <span className="font-medium ml-1">+{alert.targetRange.low}%</span>
                </div>
                <div>
                  <span className="text-gray-600">Avg:</span>
                  <span className="font-medium ml-1">+{alert.targetRange.avg}%</span>
                </div>
                <div>
                  <span className="text-gray-600">High:</span>
                  <span className="font-medium ml-1">+{alert.targetRange.high}%</span>
                </div>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Est. {alert.targetRange.estimatedDays} days to hit • Entry: ${alert.entryPrice}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => setShowWhy(true)}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                Why this alert?
              </button>

              {/* Gut Vote Status */}
              {alert.gutVote ? (
                <div className="flex items-center text-xs">
                  <div className={`px-2 py-1 rounded text-white text-xs font-medium ${
                    alert.gutVote === 'BULLISH' ? 'bg-green-500' :
                    alert.gutVote === 'BEARISH' ? 'bg-red-500' : 'bg-gray-500'
                  }`}>
                    {alert.gutVote === 'PASS' ? 'PASSED' : alert.gutVote}
                  </div>
                </div>
              ) : (
                <button
                  onClick={onGutVote}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                >
                  Gut Check
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Why Modal */}
      {showWhy && (
        <WhyModal
          alert={alert}
          onClose={() => setShowWhy(false)}
        />
      )}
    </>
  );
}
