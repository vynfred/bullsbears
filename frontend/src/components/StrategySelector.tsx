'use client';

import React from 'react';
import { Shield, Target, Zap, TrendingUp, Info } from 'lucide-react';
import styles from '@/styles/components.module.css';

export type StrategyType = 'cautious_trader' | 'professional_trader' | 'degenerate_gambler' | 'speculation';

export interface StrategyProfile {
  id: StrategyType;
  name: string;
  description: string;
  riskLevel: 'Low' | 'Medium' | 'High' | 'Very High';
  deltaRange: string;
  strategies: {
    bullish: string;
    bearish: string;
    neutral: string;
  };
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  borderColor: string;
}

const STRATEGY_PROFILES: StrategyProfile[] = [
  {
    id: 'cautious_trader',
    name: 'Cautious Trader',
    description: 'Conservative approach with limited risk and steady income focus',
    riskLevel: 'Low',
    deltaRange: '-0.2 to 0.4',
    strategies: {
      bullish: 'Bull Put Spread (credit)',
      bearish: 'Bear Call Spread (credit)',
      neutral: 'Short Strangle (credit; wings ±20%)'
    },
    icon: Shield,
    color: 'text-green-700 dark:text-green-300',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800'
  },
  {
    id: 'professional_trader',
    name: 'Professional Trader',
    description: 'Balanced risk-reward with defined risk spreads',
    riskLevel: 'Medium',
    deltaRange: '0.4 to 0.6',
    strategies: {
      bullish: 'Bull Call Spread (debit)',
      bearish: 'Bear Put Spread (debit)',
      neutral: 'Iron Condor (credit; breakeven ±10%)'
    },
    icon: Target,
    color: 'text-blue-700 dark:text-blue-300',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800'
  },
  {
    id: 'degenerate_gambler',
    name: 'Degenerate Gambler',
    description: 'High-risk, high-reward directional bets',
    riskLevel: 'High',
    deltaRange: '>0.7 or <-0.7',
    strategies: {
      bullish: 'Naked Call (long OTM)',
      bearish: 'Naked Put (long OTM)',
      neutral: 'Long Straddle (debit; vega >0.5)'
    },
    icon: Zap,
    color: 'text-red-700 dark:text-red-300',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800'
  },
  {
    id: 'speculation',
    name: 'Speculation',
    description: 'Maximum leverage directional plays with extreme risk',
    riskLevel: 'Very High',
    deltaRange: 'Maximum leverage',
    strategies: {
      bullish: 'Deep OTM Calls (0DTE-7DTE)',
      bearish: 'Deep OTM Puts (0DTE-7DTE)',
      neutral: 'Gamma Scalping (high vega plays)'
    },
    icon: TrendingUp,
    color: 'text-purple-700 dark:text-purple-300',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    borderColor: 'border-purple-200 dark:border-purple-800'
  }
];

interface StrategySelectorProps {
  onStrategySelected: (strategy: StrategyProfile) => void;
  selectedStrategy: StrategyProfile | null;
  disabled?: boolean;
}

export default function StrategySelector({ 
  onStrategySelected, 
  selectedStrategy, 
  disabled = false 
}: StrategySelectorProps) {
  const [showAdvanced, setShowAdvanced] = React.useState(false);

  const handleStrategySelect = (strategy: StrategyProfile) => {
    onStrategySelected(strategy);
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'Low': return 'text-green-600 dark:text-green-400';
      case 'Medium': return 'text-blue-600 dark:text-blue-400';
      case 'High': return 'text-red-600 dark:text-red-400';
      case 'Very High': return 'text-purple-600 dark:text-purple-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  // Show first 3 strategies by default, 4th (Speculation) only when advanced is toggled
  const visibleStrategies = showAdvanced ? STRATEGY_PROFILES : STRATEGY_PROFILES.slice(0, 3);

  return (
    <div className={styles.formGroup}>
      <div className="flex items-center justify-between mb-3">
        <label className={styles.label}>
          <Target className="h-4 w-4 mr-2" />
          Select Trading Strategy
        </label>
        
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-[var(--accent-primary)] hover:text-[var(--accent-primary)]/80 transition-colors"
          disabled={disabled}
        >
          {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
        </button>
      </div>

      <div className="space-y-3">
        {visibleStrategies.map((strategy) => {
          const Icon = strategy.icon;
          const isSelected = selectedStrategy?.id === strategy.id;
          
          return (
            <button
              key={strategy.id}
              onClick={() => handleStrategySelect(strategy)}
              disabled={disabled}
              className={`w-full p-4 text-left border-2 rounded-lg transition-all hover:shadow-md ${
                isSelected
                  ? `${strategy.borderColor} ${strategy.bgColor}`
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="flex items-start space-x-3">
                <div className={`p-2 rounded-lg ${strategy.bgColor}`}>
                  <Icon className={`h-5 w-5 ${strategy.color}`} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className={`font-semibold ${strategy.color}`}>
                      {strategy.name}
                    </h3>
                    <span className={`text-xs px-2 py-1 rounded-full ${getRiskLevelColor(strategy.riskLevel)} bg-current/10`}>
                      {strategy.riskLevel} Risk
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    {strategy.description}
                  </p>
                  
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      <strong>Delta Range:</strong> {strategy.deltaRange}
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
                        <div className="font-medium text-green-700 dark:text-green-300">Bullish</div>
                        <div className="text-green-600 dark:text-green-400">{strategy.strategies.bullish}</div>
                      </div>
                      
                      <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                        <div className="font-medium text-red-700 dark:text-red-300">Bearish</div>
                        <div className="text-red-600 dark:text-red-400">{strategy.strategies.bearish}</div>
                      </div>
                      
                      <div className="p-2 bg-gray-50 dark:bg-gray-900/20 rounded border border-gray-200 dark:border-gray-800">
                        <div className="font-medium text-gray-700 dark:text-gray-300">Neutral</div>
                        <div className="text-gray-600 dark:text-gray-400">{strategy.strategies.neutral}</div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {isSelected && (
                  <div className="ml-2 mt-1">
                    <div className={`w-3 h-3 rounded-full ${strategy.color.replace('text-', 'bg-')}`}></div>
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Risk Warning */}
      <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <div className="flex items-start space-x-2">
          <Info className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-yellow-700 dark:text-yellow-300">
            <strong>Risk Disclaimer:</strong> Higher risk strategies can result in significant losses. 
            Only trade with capital you can afford to lose. This tool provides analysis, not financial advice.
          </div>
        </div>
      </div>

      {/* Help Text */}
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
        Each strategy targets different risk-reward profiles and market conditions
      </p>
    </div>
  );
}
