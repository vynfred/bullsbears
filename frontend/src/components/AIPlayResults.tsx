'use client';

import React, { useState } from 'react';
import {
  TrendingUp, TrendingDown, Shield, Brain,
  ChevronDown, ChevronRight, Zap
} from 'lucide-react';
import { AIOptionPlay } from '@/lib/api';

interface AIPlayResultsProps {
  plays: AIOptionPlay[];
  onChooseOption?: (play: AIOptionPlay) => void;
}

export default function AIPlayResults({ plays, onChooseOption }: AIPlayResultsProps) {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  if (!plays || plays.length === 0) {
    return null;
  }

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'BUY':
        return 'text-[var(--text-primary)] bg-[var(--bg-tertiary)] border-[var(--text-primary)]';
      case 'SELL':
        return 'text-[var(--accent-red)] bg-[var(--bg-tertiary)] border-[var(--accent-red)]';
      default:
        return 'text-[var(--accent-yellow)] bg-[var(--bg-tertiary)] border-[var(--accent-yellow)]';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-[var(--text-primary)]';
    if (confidence >= 80) return 'text-[var(--accent-cyan)]';
    if (confidence >= 70) return 'text-[var(--accent-yellow)]';
    return 'text-[var(--text-muted)]';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded overflow-hidden">
      {/* Table Header */}
      <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] p-4">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-[var(--accent-cyan)]" />
          <h3 className="font-mono text-[var(--text-primary)] uppercase font-bold">
            AI OPTION PLAYS ({plays.length})
          </h3>
        </div>
      </div>

      {/* Options Table */}
      <div className="overflow-x-auto">
        <table className="w-full font-mono text-sm">
          <thead className="bg-[var(--bg-tertiary)] border-b border-[var(--border-color)]">
            <tr>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Symbol</th>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Type</th>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Strike</th>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Exp</th>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Premium</th>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Confidence</th>
              <th className="text-left p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Action</th>
              <th className="text-center p-3 text-[var(--text-muted)] uppercase text-xs font-bold">Details</th>
            </tr>
          </thead>
          <tbody>
            {plays.map((play, index) => (
              <React.Fragment key={index}>
                {/* Main Row */}
                <tr 
                  className="border-b border-[var(--border-color)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
                  onClick={() => toggleRow(index)}
                >
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      {play.ai_recommendation === 'BUY' ? (
                        <TrendingUp className="w-4 h-4 text-[var(--text-primary)]" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-[var(--accent-red)]" />
                      )}
                      <span className="text-[var(--text-primary)] font-bold">{play.symbol}</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold border ${getRecommendationColor(play.ai_recommendation)}`}>
                      {play.option_type}
                    </span>
                  </td>
                  <td className="p-3 text-[var(--text-primary)]">${play.strike}</td>
                  <td className="p-3 text-[var(--text-secondary)]">{play.expiration}</td>
                  <td className="p-3 text-[var(--accent-cyan)]">${play.entry_price.toFixed(2)}</td>
                  <td className="p-3">
                    <span className={`font-bold ${getConfidenceColor(play.confidence_score)}`}>
                      {play.confidence_score.toFixed(1)}%
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold border ${getRecommendationColor(play.ai_recommendation)}`}>
                      {play.ai_recommendation}
                    </span>
                  </td>
                  <td className="p-3 text-center">
                    {expandedRows.has(index) ? (
                      <ChevronDown className="w-4 h-4 text-[var(--accent-cyan)] mx-auto" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-[var(--text-muted)] mx-auto" />
                    )}
                  </td>
                </tr>

                {/* Expanded Details Row */}
                {expandedRows.has(index) && (
                  <tr className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)]">
                    <td colSpan={8} className="p-4">
                      <div className="space-y-4">
                        {/* AI Analysis */}
                        <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                          <div className="flex items-start gap-2 mb-2">
                            <Brain className="w-4 h-4 text-[var(--accent-cyan)] mt-0.5" />
                            <h4 className="font-bold text-[var(--accent-cyan)] uppercase text-xs">AI Analysis</h4>
                          </div>
                          <p className="text-[var(--text-secondary)] text-xs leading-relaxed">{play.summary}</p>
                        </div>

                        {/* Risk Metrics */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--text-primary)]">
                            <div className="flex items-center gap-2 mb-1">
                              <TrendingUp className="w-4 h-4 text-[var(--text-primary)]" />
                              <span className="text-xs font-bold text-[var(--text-muted)] uppercase">Max Profit</span>
                            </div>
                            <div className="text-lg font-bold text-[var(--text-primary)]">
                              {play.max_profit ? formatCurrency(play.max_profit) : '∞'}
                            </div>
                          </div>

                          <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--accent-red)]">
                            <div className="flex items-center gap-2 mb-1">
                              <TrendingDown className="w-4 h-4 text-[var(--accent-red)]" />
                              <span className="text-xs font-bold text-[var(--text-muted)] uppercase">Max Loss</span>
                            </div>
                            <div className="text-lg font-bold text-[var(--accent-red)]">
                              {formatCurrency(play.max_loss)}
                            </div>
                          </div>

                          <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--accent-yellow)]">
                            <div className="flex items-center gap-2 mb-1">
                              <Shield className="w-4 h-4 text-[var(--accent-yellow)]" />
                              <span className="text-xs font-bold text-[var(--text-muted)] uppercase">Risk/Reward</span>
                            </div>
                            <div className="text-lg font-bold text-[var(--accent-yellow)]">
                              {play.risk_reward_ratio ? play.risk_reward_ratio.toFixed(2) : 'N/A'}
                            </div>
                          </div>
                        </div>

                        {/* Position Details */}
                        <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                          <h4 className="font-bold text-[var(--accent-cyan)] uppercase text-xs mb-2">Position Details</h4>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                            <div>
                              <span className="text-[var(--text-muted)] uppercase">Target:</span>
                              <span className="ml-1 font-bold text-[var(--text-primary)]">${play.target_price.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="text-[var(--text-muted)] uppercase">Stop Loss:</span>
                              <span className="ml-1 font-bold text-[var(--accent-red)]">${play.stop_loss.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="text-[var(--text-muted)] uppercase">Contracts:</span>
                              <span className="ml-1 font-bold text-[var(--text-primary)]">{play.position_size}</span>
                            </div>
                            <div>
                              <span className="text-[var(--text-muted)] uppercase">Profit Prob:</span>
                              <span className="ml-1 font-bold text-[var(--accent-cyan)]">{formatPercent(play.probability_profit)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Key Factors */}
                        {play.key_factors && play.key_factors.length > 0 && (
                          <div className="bg-[var(--bg-tertiary)] p-3 rounded border border-[var(--border-color)]">
                            <h4 className="font-bold text-[var(--accent-cyan)] uppercase text-xs mb-2">Key Factors</h4>
                            <div className="flex flex-wrap gap-2">
                              {play.key_factors.map((factor, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-1 rounded text-xs font-bold bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-secondary)]"
                                >
                                  {factor}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Action Button */}
                        {onChooseOption && (
                          <div className="text-center">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onChooseOption(play);
                              }}
                              className="neon-button px-6 py-2 font-bold uppercase"
                            >
                              Execute Trade
                            </button>
                          </div>
                        )}

                        {/* Timestamp */}
                        <div className="text-center text-xs text-[var(--text-muted)] border-t border-[var(--border-color)] pt-2">
                          Generated: {new Date(play.generated_at).toLocaleString()}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
