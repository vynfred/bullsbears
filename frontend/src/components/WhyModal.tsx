'use client';

import React from 'react';
import { MoonAlert } from '@/lib/demoData';

interface WhyModalProps {
  alert: MoonAlert;
  onClose: () => void;
}

// Demo SHAP-style feature contributions
const getFeatureContributions = (alert: MoonAlert) => {
  // Simulate SHAP waterfall values based on the alert
  const baseContributions = [
    { feature: 'Volume surge', value: 31, color: 'text-green-600' },
    { feature: 'Grok AI technical', value: 24, color: 'text-green-600' },
    { feature: 'AI Confidence', value: Math.round((alert.confidence - 50) * 0.4), color: alert.confidence > 50 ? 'text-green-600' : 'text-red-600' },
    { feature: 'RSI oversold', value: 16, color: 'text-green-600' },
    { feature: 'DeepSeek sentiment', value: 14, color: 'text-green-600' },
    { feature: 'Options flow', value: 12, color: 'text-green-600' },
    { feature: 'Social buzz', value: 8, color: 'text-green-600' },
    { feature: 'Earnings whisper', value: 6, color: 'text-green-600' },
    { feature: 'Market conditions', value: -4, color: 'text-red-600' },
    { feature: 'Sector weakness', value: -7, color: 'text-red-600' },
  ];

  // Adjust contributions to match the alert's confidence
  const totalPositive = baseContributions.filter(c => c.value > 0).reduce((sum, c) => sum + c.value, 0);
  const totalNegative = baseContributions.filter(c => c.value < 0).reduce((sum, c) => sum + Math.abs(c.value), 0);
  
  return baseContributions.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
};

export default function WhyModal({ alert, onClose }: WhyModalProps) {
  const contributions = getFeatureContributions(alert);
  const displayConfidence = alert.finalConfidence || alert.confidence;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">
            Why {displayConfidence}% MOON?
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            ×
          </button>
        </div>

        {/* Stock Info */}
        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <div className="text-sm text-gray-600">Stock #{alert.randomId}</div>
          <div className="text-lg font-bold text-green-600">
            {displayConfidence}% MOON Confidence
          </div>
          {alert.finalConfidence && alert.finalConfidence !== alert.confidence && (
            <div className="text-xs text-blue-600">
              Boosted from {alert.confidence}% by gut check
            </div>
          )}
        </div>

        {/* Feature Contributions */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700 mb-3">
            Top Contributing Factors:
          </div>
          
          {contributions.slice(0, 8).map((contrib, index) => (
            <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
              <div className="text-sm text-gray-700">
                {contrib.feature}
              </div>
              <div className={`text-sm font-medium ${contrib.color}`}>
                {contrib.value > 0 ? '+' : ''}{contrib.value}%
              </div>
            </div>
          ))}
        </div>

        {/* Waterfall Visualization */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-600 mb-2">Confidence Breakdown:</div>
          <div className="flex items-center text-xs">
            <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded mr-2">
              Base: 45%
            </div>
            <div className="text-gray-400 mx-1">+</div>
            <div className="bg-green-100 text-green-800 px-2 py-1 rounded mr-2">
              Signals: +{alert.confidence - 45}%
            </div>
            {alert.gutVote && alert.finalConfidence && (
              <>
                <div className="text-gray-400 mx-1">+</div>
                <div className={`px-2 py-1 rounded ${
                  alert.finalConfidence > alert.confidence 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  Gut: {alert.finalConfidence > alert.confidence ? '+' : ''}{alert.finalConfidence - alert.confidence}%
                </div>
              </>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-xs text-yellow-800">
            <strong>Not Financial Advice:</strong> This analysis is based on patterns and may not predict future moves. Past performance ≠ future results.
          </div>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="w-full mt-4 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}
