'use client';

import React, { useState } from 'react';
import { AIOptionPlay } from '@/lib/api';
import ShareableContent from './ShareableContent';

interface OptionPlayCardProps {
  play: AIOptionPlay;
  onChoosePlay?: (play: AIOptionPlay) => void;
  onSharePlay?: (play: AIOptionPlay) => void;
}

export default function OptionPlayCard({ play, onChoosePlay, onSharePlay }: OptionPlayCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showShareContent, setShowShareContent] = useState(false);

  // Determine colors based on option type and confidence
  const isBullish = play.option_type === 'CALL';
  const isHighConfidence = play.confidence_score >= 80;
  const isMediumConfidence = play.confidence_score >= 60;

  const confidenceColor = isHighConfidence 
    ? 'text-green-400 bg-green-900/20 border-green-500/30' 
    : isMediumConfidence 
    ? 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
    : 'text-red-400 bg-red-900/20 border-red-500/30';

  const typeColor = isBullish 
    ? 'text-green-400 bg-green-900/20' 
    : 'text-red-400 bg-red-900/20';

  const formatCurrency = (value: number) => `$${value.toFixed(2)}`;
  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

  return (
    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700/50 rounded-lg p-6 hover:border-cyan-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3">
          <div className="text-2xl">
            {isBullish ? '🐂' : '🐻'}
          </div>
          <div>
            <h3 className="text-xl font-bold text-white font-mono">{play.symbol}</h3>
            <p className="text-sm text-gray-400">{play.company_name}</p>
          </div>
        </div>
        
        <div className={`px-3 py-1 rounded-full text-sm font-medium border ${confidenceColor}`}>
          {play.confidence_score.toFixed(1)}% Confidence
        </div>
      </div>

      {/* Option Details */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className={`px-3 py-2 rounded-lg ${typeColor}`}>
          <div className="text-xs uppercase tracking-wide opacity-70">Option Type</div>
          <div className="font-bold font-mono">{play.option_type}</div>
        </div>
        
        <div className="bg-gray-800/50 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Strike</div>
          <div className="font-bold font-mono text-white">{formatCurrency(play.strike)}</div>
        </div>
        
        <div className="bg-gray-800/50 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Expiration</div>
          <div className="font-bold font-mono text-white">{play.expiration}</div>
        </div>
        
        <div className="bg-gray-800/50 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Position Size</div>
          <div className="font-bold font-mono text-white">{play.position_size} contracts</div>
        </div>
      </div>

      {/* Price Targets */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-blue-900/20 border border-blue-500/30 px-3 py-2 rounded-lg text-center">
          <div className="text-xs uppercase tracking-wide text-blue-400">Entry</div>
          <div className="font-bold font-mono text-blue-300">{formatCurrency(play.entry_price)}</div>
        </div>
        
        <div className="bg-green-900/20 border border-green-500/30 px-3 py-2 rounded-lg text-center">
          <div className="text-xs uppercase tracking-wide text-green-400">Target</div>
          <div className="font-bold font-mono text-green-300">{formatCurrency(play.target_price)}</div>
        </div>
        
        <div className="bg-red-900/20 border border-red-500/30 px-3 py-2 rounded-lg text-center">
          <div className="text-xs uppercase tracking-wide text-red-400">Stop Loss</div>
          <div className="font-bold font-mono text-red-300">{formatCurrency(play.stop_loss)}</div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Max Profit</div>
          <div className="font-bold font-mono text-green-400">{formatCurrency(play.max_profit)}</div>
        </div>
        
        <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Max Loss</div>
          <div className="font-bold font-mono text-red-400">{formatCurrency(play.max_loss)}</div>
        </div>
        
        <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Risk/Reward</div>
          <div className="font-bold font-mono text-cyan-400">{play.risk_reward_ratio.toFixed(2)}:1</div>
        </div>
        
        <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
          <div className="text-xs uppercase tracking-wide text-gray-400">Win Probability</div>
          <div className="font-bold font-mono text-cyan-400">{formatPercent(play.probability_profit)}</div>
        </div>
      </div>

      {/* AI Summary */}
      <div className="mb-4">
        <div className="text-sm text-gray-300 leading-relaxed">
          {play.summary}
        </div>
      </div>

      {/* Expandable Details */}
      <div className="border-t border-gray-700/50 pt-4">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-between w-full text-left text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          <span>AI Analysis Details</span>
          <span className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>

        {isExpanded && (
          <div className="mt-4 space-y-4 animate-in slide-in-from-top-2 duration-200">
            {/* Analysis Scores */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
                <div className="text-xs uppercase tracking-wide text-gray-400">Technical Score</div>
                <div className="font-bold font-mono text-white">{play.technical_score.toFixed(1)}/100</div>
              </div>
              
              <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
                <div className="text-xs uppercase tracking-wide text-gray-400">Volume Score</div>
                <div className="font-bold font-mono text-white">{play.volume_score.toFixed(1)}/10</div>
              </div>
              
              <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
                <div className="text-xs uppercase tracking-wide text-gray-400">News Sentiment</div>
                <div className={`font-bold font-mono ${play.news_sentiment >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {play.news_sentiment >= 0 ? '+' : ''}{(play.news_sentiment * 100).toFixed(1)}%
                </div>
              </div>
              
              <div className="bg-gray-800/30 px-3 py-2 rounded-lg">
                <div className="text-xs uppercase tracking-wide text-gray-400">Catalyst Impact</div>
                <div className="font-bold font-mono text-white">{play.catalyst_impact.toFixed(1)}/10</div>
              </div>
            </div>

            {/* Key Factors */}
            {play.key_factors && play.key_factors.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-300 mb-2">Key Factors:</div>
                <ul className="space-y-1">
                  {play.key_factors.map((factor, index) => (
                    <li key={index} className="text-sm text-gray-400 flex items-start">
                      <span className="text-cyan-400 mr-2">•</span>
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI Recommendation */}
            <div className="bg-cyan-900/20 border border-cyan-500/30 p-3 rounded-lg">
              <div className="text-sm font-medium text-cyan-400 mb-1">AI Recommendation:</div>
              <div className="text-sm text-gray-300">{play.ai_recommendation}</div>
            </div>

            {/* Risk Warning */}
            {play.risk_warning && (
              <div className="bg-red-900/20 border border-red-500/30 p-3 rounded-lg">
                <div className="text-sm font-medium text-red-400 mb-1">⚠️ Risk Warning:</div>
                <div className="text-sm text-gray-300">{play.risk_warning}</div>
              </div>
            )}

            {/* Shareable Content */}
            {showShareContent && (
              <div className="mt-4">
                <ShareableContent
                  play={play}
                  type="prediction"
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mt-6">
        {onChoosePlay && (
          <button
            onClick={() => onChoosePlay(play)}
            className="flex-1 bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 hover:shadow-lg hover:shadow-green-500/25"
          >
            Choose This Play
          </button>
        )}
        
        <button
          onClick={() => setShowShareContent(!showShareContent)}
          className="bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white font-medium py-2 px-4 rounded-lg transition-all duration-200"
        >
          {showShareContent ? 'Hide Share' : 'Share'}
        </button>
      </div>
    </div>
  );
}
