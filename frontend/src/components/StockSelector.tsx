'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, TrendingUp, Star, AlertCircle, Check, Loader2 } from 'lucide-react';
import styles from '@/styles/components.module.css';
import { api } from '../lib/api';

export interface StockSelection {
  symbol: string;
  companyName: string;
  currentPrice?: number;
  isValid: boolean;
}

interface StockSelectorProps {
  onStockSelected: (selection: StockSelection) => void;
  selectedStock: StockSelection | null;
  disabled?: boolean;
}

// Popular stocks and ETFs for quick selection
const POPULAR_STOCKS = [
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'TSLA', name: 'Tesla, Inc.' },
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'META', name: 'Meta Platforms Inc.' },
  { symbol: 'AMD', name: 'Advanced Micro Devices' },
];

const POPULAR_ETFS = [
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust' },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust' },
  { symbol: 'IWM', name: 'iShares Russell 2000 ETF' },
  { symbol: 'VIX', name: 'CBOE Volatility Index' },
];

export default function StockSelector({ onStockSelected, selectedStock, disabled = false }: StockSelectorProps) {
  const [inputValue, setInputValue] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const validationTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize with selected stock if provided
  useEffect(() => {
    if (selectedStock) {
      setInputValue(selectedStock.symbol);
    }
  }, [selectedStock]);

  // Debounced validation
  useEffect(() => {
    if (validationTimeoutRef.current) {
      clearTimeout(validationTimeoutRef.current);
    }

    if (inputValue.trim() && inputValue.length >= 1) {
      validationTimeoutRef.current = setTimeout(() => {
        validateStock(inputValue.trim().toUpperCase());
      }, 500);
    } else {
      setValidationError(null);
      setIsValidating(false);
    }

    return () => {
      if (validationTimeoutRef.current) {
        clearTimeout(validationTimeoutRef.current);
      }
    };
  }, [inputValue]);

  const validateStock = async (symbol: string) => {
    if (symbol.length > 10 || !/^[A-Z]+$/.test(symbol)) {
      setValidationError('Invalid ticker format');
      setIsValidating(false);
      return;
    }

    setIsValidating(true);
    setValidationError(null);

    try {
      const response = await api.validateStockSymbol(symbol);

      if (response.success && response.is_valid) {
        const stockSelection: StockSelection = {
          symbol: response.symbol,
          companyName: response.company_name || `${symbol} Corporation`,
          isValid: true
        };

        onStockSelected(stockSelection);
      } else {
        setValidationError(response.error_message || 'Invalid ticker symbol');
      }
    } catch (error) {
      console.error('Error validating stock:', error);
      setValidationError('Unable to validate ticker');
    } finally {
      setIsValidating(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase();
    setInputValue(value);
    setShowSuggestions(false);
  };

  const handleQuickSelect = (stock: { symbol: string; name: string }) => {
    setInputValue(stock.symbol);
    setShowSuggestions(false);
    
    const stockSelection: StockSelection = {
      symbol: stock.symbol,
      companyName: stock.name,
      isValid: true
    };
    
    onStockSelected(stockSelection);
  };

  const handleInputFocus = () => {
    setShowSuggestions(true);
  };

  const handleInputBlur = () => {
    // Delay hiding suggestions to allow clicks
    setTimeout(() => setShowSuggestions(false), 200);
  };

  return (
    <div className={styles.formGroup}>
      <label className={styles.label}>
        <Search className="h-4 w-4 mr-2" />
        Select Stock Symbol
      </label>
      
      <div className="relative">
        {/* Stock Input */}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            placeholder="Enter ticker symbol (e.g., NVDA)"
            disabled={disabled}
            className={`${styles.input} pr-10 ${
              selectedStock?.isValid ? 'border-green-500' : 
              validationError ? 'border-red-500' : ''
            }`}
            maxLength={10}
          />
          
          {/* Validation Status Icon */}
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            {isValidating && (
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--accent-primary)] border-t-transparent"></div>
            )}
            {selectedStock?.isValid && !isValidating && (
              <Check className="h-4 w-4 text-green-500" />
            )}
            {validationError && !isValidating && (
              <AlertCircle className="h-4 w-4 text-red-500" />
            )}
          </div>
        </div>

        {/* Validation Error */}
        {validationError && (
          <p className="text-red-500 text-sm mt-1 flex items-center">
            <AlertCircle className="h-3 w-3 mr-1" />
            {validationError}
          </p>
        )}

        {/* Selected Stock Info */}
        {selectedStock?.isValid && (
          <div className="mt-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-green-800 dark:text-green-200">
                  {selectedStock.symbol}
                </p>
                <p className="text-sm text-green-600 dark:text-green-300">
                  {selectedStock.companyName}
                </p>
              </div>
              {selectedStock.currentPrice && (
                <div className="text-right">
                  <p className="font-semibold text-green-800 dark:text-green-200">
                    ${selectedStock.currentPrice.toFixed(2)}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quick Selection Suggestions */}
        {showSuggestions && !disabled && (
          <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-80 overflow-y-auto">
            {/* Popular Stocks */}
            <div className="p-3 border-b border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center">
                <TrendingUp className="h-3 w-3 mr-1" />
                Popular Stocks
              </h4>
              <div className="grid grid-cols-2 gap-1">
                {POPULAR_STOCKS.map((stock) => (
                  <button
                    key={stock.symbol}
                    onClick={() => handleQuickSelect(stock)}
                    className="text-left p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm transition-colors"
                  >
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {stock.symbol}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {stock.name}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Popular ETFs */}
            <div className="p-3">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center">
                <Star className="h-3 w-3 mr-1" />
                Popular ETFs
              </h4>
              <div className="grid grid-cols-2 gap-1">
                {POPULAR_ETFS.map((etf) => (
                  <button
                    key={etf.symbol}
                    onClick={() => handleQuickSelect(etf)}
                    className="text-left p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm transition-colors"
                  >
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {etf.symbol}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {etf.name}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Help Text */}
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
        Enter a stock ticker symbol or select from popular options above
      </p>
    </div>
  );
}
