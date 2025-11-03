'use client';

import React, { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, AlertTriangle, Info, Calculator } from 'lucide-react';
import styles from '@/styles/components.module.css';

export interface PositionSize {
  maxPositionSize: number;
  sharesOwned: number;
  riskPercentage: number;
  accountSize?: number;
}

interface PositionSizerProps {
  onPositionChanged: (position: PositionSize) => void;
  selectedPosition: PositionSize | null;
  disabled?: boolean;
  currentStockPrice?: number;
}

const PRESET_AMOUNTS = [1000, 2500, 5000, 10000, 25000, 50000];

export default function PositionSizer({ 
  onPositionChanged, 
  selectedPosition, 
  disabled = false,
  currentStockPrice = 100 // Default price for calculations
}: PositionSizerProps) {
  const [maxPositionSize, setMaxPositionSize] = useState(selectedPosition?.maxPositionSize || 10000);
  const [sharesOwned, setSharesOwned] = useState(selectedPosition?.sharesOwned || 0);
  const [accountSize, setAccountSize] = useState(selectedPosition?.accountSize || 100000);
  const [showAccountSize, setShowAccountSize] = useState(false);

  // Calculate risk percentage
  const riskPercentage = accountSize > 0 ? (maxPositionSize / accountSize) * 100 : 0;

  // Update parent component when values change
  useEffect(() => {
    const position: PositionSize = {
      maxPositionSize,
      sharesOwned,
      riskPercentage,
      accountSize: showAccountSize ? accountSize : undefined
    };
    onPositionChanged(position);
  }, [maxPositionSize, sharesOwned, riskPercentage, accountSize, showAccountSize, onPositionChanged]);

  const handleMaxPositionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[^0-9]/g, '');
    const numValue = parseInt(value) || 0;
    setMaxPositionSize(Math.min(numValue, 1000000)); // Cap at $1M
  };

  const handleSharesOwnedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[^0-9]/g, '');
    const numValue = parseInt(value) || 0;
    setSharesOwned(Math.min(numValue, 100000)); // Cap at 100k shares
  };

  const handleAccountSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[^0-9]/g, '');
    const numValue = parseInt(value) || 0;
    setAccountSize(Math.min(numValue, 10000000)); // Cap at $10M
  };

  const handlePresetSelect = (amount: number) => {
    setMaxPositionSize(amount);
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const getRiskLevelColor = (percentage: number) => {
    if (percentage <= 2) return 'text-green-600 dark:text-green-400';
    if (percentage <= 5) return 'text-yellow-600 dark:text-yellow-400';
    if (percentage <= 10) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getRiskLevelLabel = (percentage: number) => {
    if (percentage <= 2) return 'Conservative';
    if (percentage <= 5) return 'Moderate';
    if (percentage <= 10) return 'Aggressive';
    return 'Very High Risk';
  };

  const getSharesValue = () => {
    return sharesOwned * currentStockPrice;
  };

  const canUseCoveredStrategies = () => {
    return sharesOwned >= 100; // Need at least 100 shares for covered calls
  };

  return (
    <div className={styles.formGroup}>
      <label className={styles.label}>
        <DollarSign className="h-4 w-4 mr-2" />
        Position Sizing
      </label>

      {/* Max Position Size */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Maximum Position Size
          </label>
          
          {/* Preset Amounts */}
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
            {PRESET_AMOUNTS.map((amount) => (
              <button
                key={amount}
                onClick={() => handlePresetSelect(amount)}
                disabled={disabled}
                className={`px-3 py-2 text-sm rounded border transition-colors ${
                  maxPositionSize === amount
                    ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                    : 'border-gray-300 dark:border-gray-600 hover:border-[var(--accent-primary)]/50'
                } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                {formatCurrency(amount)}
              </button>
            ))}
          </div>

          {/* Custom Amount Input */}
          <div className="relative">
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
              $
            </div>
            <input
              type="text"
              value={formatNumber(maxPositionSize)}
              onChange={handleMaxPositionChange}
              disabled={disabled}
              className={`${styles.input} pl-8`}
              placeholder="Enter custom amount"
            />
          </div>
        </div>

        {/* Shares Owned */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Shares Currently Owned
            <span className="text-xs text-gray-500 ml-1">(for covered call strategies)</span>
          </label>
          
          <div className="relative">
            <input
              type="text"
              value={formatNumber(sharesOwned)}
              onChange={handleSharesOwnedChange}
              disabled={disabled}
              className={styles.input}
              placeholder="0"
            />
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500">
              shares
            </div>
          </div>

          {sharesOwned > 0 && (
            <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded text-sm">
              <div className="flex items-center justify-between">
                <span className="text-blue-700 dark:text-blue-300">
                  Portfolio Value: {formatCurrency(getSharesValue())}
                </span>
                {canUseCoveredStrategies() && (
                  <span className="text-green-600 dark:text-green-400 flex items-center">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    Covered strategies available
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Account Size (Optional) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Account Size
              <span className="text-xs text-gray-500 ml-1">(optional, for risk calculation)</span>
            </label>
            <button
              onClick={() => setShowAccountSize(!showAccountSize)}
              className="text-sm text-[var(--accent-primary)] hover:text-[var(--accent-primary)]/80 transition-colors"
              disabled={disabled}
            >
              {showAccountSize ? 'Hide' : 'Show'}
            </button>
          </div>

          {showAccountSize && (
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                $
              </div>
              <input
                type="text"
                value={formatNumber(accountSize)}
                onChange={handleAccountSizeChange}
                disabled={disabled}
                className={`${styles.input} pl-8`}
                placeholder="Total account value"
              />
            </div>
          )}
        </div>

        {/* Risk Analysis */}
        {showAccountSize && accountSize > 0 && (
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center mb-2">
              <Calculator className="h-4 w-4 mr-2 text-gray-600 dark:text-gray-400" />
              <span className="font-medium text-gray-700 dark:text-gray-300">Risk Analysis</span>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600 dark:text-gray-400">Position Size</div>
                <div className="font-semibold">{formatCurrency(maxPositionSize)}</div>
              </div>
              
              <div>
                <div className="text-gray-600 dark:text-gray-400">Account Risk</div>
                <div className={`font-semibold ${getRiskLevelColor(riskPercentage)}`}>
                  {riskPercentage.toFixed(1)}% ({getRiskLevelLabel(riskPercentage)})
                </div>
              </div>
            </div>

            {riskPercentage > 10 && (
              <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
                <div className="flex items-center text-red-700 dark:text-red-300 text-xs">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  High risk: Consider reducing position size to &lt;10% of account
                </div>
              </div>
            )}
          </div>
        )}

        {/* Position Summary */}
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-center mb-2">
            <Info className="h-4 w-4 mr-2 text-blue-600 dark:text-blue-400" />
            <span className="font-medium text-blue-700 dark:text-blue-300">Position Summary</span>
          </div>
          
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-blue-600 dark:text-blue-400">Max Position:</span>
              <span className="font-semibold text-blue-700 dark:text-blue-300">
                {formatCurrency(maxPositionSize)}
              </span>
            </div>
            
            <div className="flex justify-between">
              <span className="text-blue-600 dark:text-blue-400">Shares Owned:</span>
              <span className="font-semibold text-blue-700 dark:text-blue-300">
                {formatNumber(sharesOwned)} shares
              </span>
            </div>
            
            {showAccountSize && (
              <div className="flex justify-between">
                <span className="text-blue-600 dark:text-blue-400">Account Risk:</span>
                <span className={`font-semibold ${getRiskLevelColor(riskPercentage)}`}>
                  {riskPercentage.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Help Text */}
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
        Position size determines your maximum risk. Shares owned enables covered call strategies (requires 100+ shares).
      </p>
    </div>
  );
}
