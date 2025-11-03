'use client';

import React, { useState, useEffect } from 'react';
import { Calendar, AlertTriangle, Clock, TrendingUp, Loader2 } from 'lucide-react';
import { api } from '../lib/api';
import styles from '@/styles/components.module.css';

export interface ExpirationDate {
  date: string; // YYYY-MM-DD format
  displayDate: string; // Human readable format
  daysToExpiry: number;
  isWeekly: boolean;
  isMonthly: boolean;
  isQuarterly: boolean;
  hasEarnings?: boolean;
  earningsDate?: string;
}

interface ExpirationSelectorProps {
  symbol: string | null;
  onExpirationSelected: (expiration: ExpirationDate) => void;
  selectedExpiration: ExpirationDate | null;
  disabled?: boolean;
}

export default function ExpirationSelector({ 
  symbol, 
  onExpirationSelected, 
  selectedExpiration, 
  disabled = false 
}: ExpirationSelectorProps) {
  const [availableExpirations, setAvailableExpirations] = useState<ExpirationDate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available expiration dates when symbol changes
  useEffect(() => {
    if (symbol) {
      fetchExpirationDates(symbol);
    } else {
      setAvailableExpirations([]);
      setError(null);
    }
  }, [symbol]);

  const fetchExpirationDates = async (stockSymbol: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.getExpirationDates(stockSymbol);

      if (response.success && response.expirations) {
        // Convert API response to ExpirationDate format
        const formattedExpirations: ExpirationDate[] = response.expirations.map(exp => ({
          date: exp.date,
          displayDate: exp.display_date,
          daysToExpiry: exp.days_to_expiry,
          isWeekly: exp.is_weekly,
          isMonthly: exp.is_monthly,
          isQuarterly: exp.is_quarterly,
          hasEarnings: exp.has_earnings,
          earningsDate: exp.earnings_date
        }));

        setAvailableExpirations(formattedExpirations);
      } else {
        setError(response.error_message || 'No expiration dates available');
        setAvailableExpirations([]);
      }
    } catch (err) {
      console.error('Error loading expirations:', err);
      setError('Failed to load expiration dates');
      setAvailableExpirations([]);
    } finally {
      setIsLoading(false);
    }
  };



  const handleExpirationSelect = (expiration: ExpirationDate) => {
    onExpirationSelected(expiration);
  };

  const getExpirationTypeLabel = (expiration: ExpirationDate) => {
    if (expiration.isQuarterly) return 'Quarterly';
    if (expiration.isMonthly) return 'Monthly';
    if (expiration.isWeekly) return 'Weekly';
    return 'Standard';
  };

  const getExpirationTypeColor = (expiration: ExpirationDate) => {
    if (expiration.isQuarterly) return 'text-purple-600 dark:text-purple-400';
    if (expiration.isMonthly) return 'text-blue-600 dark:text-blue-400';
    if (expiration.isWeekly) return 'text-green-600 dark:text-green-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  if (!symbol) {
    return (
      <div className={styles.formGroup}>
        <label className={styles.label}>
          <Calendar className="h-4 w-4 mr-2" />
          Select Expiration Date
        </label>
        <div className="p-4 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
          Select a stock symbol first
        </div>
      </div>
    );
  }

  return (
    <div className={styles.formGroup}>
      <label className={styles.label}>
        <Calendar className="h-4 w-4 mr-2" />
        Select Expiration Date
      </label>

      {isLoading && (
        <div className="flex items-center justify-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-[var(--accent-primary)] border-t-transparent mr-3"></div>
          Loading expiration dates for {symbol}...
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center text-red-700 dark:text-red-300">
            <AlertTriangle className="h-4 w-4 mr-2" />
            {error}
          </div>
        </div>
      )}

      {!isLoading && !error && availableExpirations.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {availableExpirations.map((expiration) => (
            <button
              key={expiration.date}
              onClick={() => handleExpirationSelect(expiration)}
              disabled={disabled}
              className={`w-full p-3 text-left border rounded-lg transition-all hover:shadow-md ${
                selectedExpiration?.date === expiration.date
                  ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
                  : 'border-gray-200 dark:border-gray-700 hover:border-[var(--accent-primary)]/50'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-gray-900 dark:text-gray-100">
                      {expiration.displayDate}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${getExpirationTypeColor(expiration)} bg-current/10`}>
                      {getExpirationTypeLabel(expiration)}
                    </span>
                  </div>
                  
                  <div className="flex items-center mt-1 space-x-4">
                    <span className="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                      <Clock className="h-3 w-3 mr-1" />
                      {expiration.daysToExpiry} days
                    </span>
                    
                    {expiration.hasEarnings && (
                      <span className="text-sm text-orange-600 dark:text-orange-400 flex items-center">
                        <TrendingUp className="h-3 w-3 mr-1" />
                        Earnings nearby
                      </span>
                    )}
                  </div>
                </div>
                
                {selectedExpiration?.date === expiration.date && (
                  <div className="ml-2">
                    <div className="w-2 h-2 bg-[var(--accent-primary)] rounded-full"></div>
                  </div>
                )}
              </div>

              {expiration.hasEarnings && expiration.earningsDate && (
                <div className="mt-2 p-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded text-xs">
                  <div className="flex items-center text-orange-700 dark:text-orange-300">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Earnings expected around {new Date(expiration.earningsDate).toLocaleDateString()}
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {!isLoading && !error && availableExpirations.length === 0 && (
        <div className="p-4 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg">
          No expiration dates available for {symbol}
        </div>
      )}

      {/* Help Text */}
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
        Weekly options expire every Friday, monthly options on the third Friday of each month
      </p>
    </div>
  );
}
