'use client';

import React from 'react';
import { HistoryEntry } from '@/lib/demoData';

interface ShareableWinCardProps {
  entry: HistoryEntry;
  onClose: () => void;
}

export default function ShareableWinCard({ entry, onClose }: ShareableWinCardProps) {
  const shareText = `MOON HIT: +${entry.actualPct}% in ${entry.daysToHit} days. My gut said ${entry.gutVote}. AI said ${entry.aiConfidence}%. We won. 🚀🌙`;

  const handleShare = async (platform: 'twitter' | 'copy') => {
    if (platform === 'twitter') {
      const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
      window.open(twitterUrl, '_blank');
    } else if (platform === 'copy') {
      try {
        await navigator.clipboard.writeText(shareText);
        alert('Copied to clipboard!');
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-6 max-w-sm w-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">Share Your Win</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            ×
          </button>
        </div>

        {/* Win Card Preview */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4 mb-6 border border-green-200">
          <div className="text-center">
            {/* Moon Emoji */}
            <div className="text-4xl mb-2">🚀🌙</div>
            
            {/* Main Message */}
            <div className="text-lg font-bold text-green-800 mb-2">
              MOON HIT!
            </div>
            
            {/* Performance */}
            <div className="text-2xl font-bold text-green-600 mb-1">
              +{entry.actualPct}%
            </div>
            <div className="text-sm text-green-700 mb-3">
              in {entry.daysToHit} days
            </div>
            
            {/* Prediction Details */}
            <div className="bg-white/50 rounded-lg p-3 text-sm">
              <div className="flex justify-between items-center mb-1">
                <span className="text-gray-600">My gut said:</span>
                <span className={`font-medium ${
                  entry.gutVote === 'UP' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {entry.gutVote}
                </span>
              </div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-gray-600">AI said:</span>
                <span className="font-medium text-blue-600">{entry.aiConfidence}%</span>
              </div>
              <div className="text-xs text-gray-500 mt-2">
                We won together! 🎯
              </div>
            </div>
          </div>
        </div>

        {/* Share Text Preview */}
        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <div className="text-xs text-gray-600 mb-1">Share text:</div>
          <div className="text-sm text-gray-800 font-mono">
            {shareText}
          </div>
        </div>

        {/* Share Buttons */}
        <div className="space-y-3">
          <button
            onClick={() => handleShare('twitter')}
            className="w-full bg-blue-500 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-600 transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
              <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
            </svg>
            Share to X (Twitter)
          </button>
          
          <button
            onClick={() => handleShare('copy')}
            className="w-full bg-gray-100 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Copy to Clipboard
          </button>
        </div>

        {/* Disclaimer */}
        <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-xs text-yellow-800">
            Remember: This is not financial advice. Past performance doesn't guarantee future results.
          </div>
        </div>
      </div>
    </div>
  );
}
