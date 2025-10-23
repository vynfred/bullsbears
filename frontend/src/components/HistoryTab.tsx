'use client';

import React, { useState, useEffect } from 'react';
import {
  Target, AlertTriangle,
  BarChart3, ArrowLeft, RefreshCw
} from 'lucide-react';

interface ChosenOption {
  id: number;
  symbol: string;
  company_name: string;
  option_type: string;
  strike: number;
  expiration: string;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  confidence_score: number;
  ai_recommendation: string;
  chosen_at: string;
  position_size: number;
  max_profit: number;
  max_loss: number;
  risk_reward_ratio: number;
  summary: string;
  key_factors: string[];
  is_expired: boolean;
  final_price?: number;
  actual_profit_loss?: number;
}

interface OptionPricePoint {
  timestamp: string;
  price: number;
  underlying_price?: number;
}

interface OptionChartData {
  chosen_option: ChosenOption;
  price_history: OptionPricePoint[];
  current_price?: number;
  current_profit_loss?: number;
}

interface BacktestResults {
  total_plays: number;
  profitable_plays: number;
  losing_plays: number;
  win_rate: number;
  total_profit_loss: number;
  average_profit_loss: number;
}

interface HistoryTabProps {
  onBack: () => void;
}

export default function HistoryTab({ onBack }: HistoryTabProps) {
  const [chosenOptions, setChosenOptions] = useState<ChosenOption[]>([]);
  const [selectedOption, setSelectedOption] = useState<OptionChartData | null>(null);
  const [backtestResults, setBacktestResults] = useState<BacktestResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchChosenOptions();
  }, []);

  const fetchChosenOptions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/v1/chosen-options');
      if (!response.ok) {
        throw new Error('Failed to fetch chosen options');
      }
      const data = await response.json();
      setChosenOptions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOptionChart = async (optionId: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/option-chart/${optionId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch option chart');
      }
      const data = await response.json();
      setSelectedOption(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch chart data');
    } finally {
      setIsLoading(false);
    }
  };

  const runBacktest = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/v1/backtest', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to run backtest');
      }
      const data = await response.json();
      setBacktestResults(data.backtest_results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run backtest');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getOptionTypeColor = (type: string) => {
    return type === 'CALL' ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100';
  };

  const getProfitLossColor = (value: number) => {
    if (value > 0) return 'text-green-600';
    if (value < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  if (selectedOption) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setSelectedOption(null)}
            className="flex items-center text-gray-600 hover:text-gray-800"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Back to History
          </button>
          <h2 className="text-xl font-bold text-gray-900">Option Chart</h2>
        </div>

        {/* Option Details */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900">
                {selectedOption.chosen_option.symbol} {selectedOption.chosen_option.company_name}
              </h3>
              <div className="flex items-center space-x-4 mt-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getOptionTypeColor(selectedOption.chosen_option.option_type)}`}>
                  {selectedOption.chosen_option.option_type}
                </span>
                <span className="text-sm text-gray-600">
                  Strike: ${selectedOption.chosen_option.strike}
                </span>
                <span className="text-sm text-gray-600">
                  Exp: {selectedOption.chosen_option.expiration}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600">Chosen: {formatDate(selectedOption.chosen_option.chosen_at)}</div>
              <div className="text-lg font-bold text-gray-900">
                Entry: ${selectedOption.chosen_option.entry_price.toFixed(2)}
              </div>
              {selectedOption.current_price && (
                <div className="text-lg font-bold">
                  Current: ${selectedOption.current_price.toFixed(2)}
                </div>
              )}
            </div>
          </div>

          {/* P&L Display */}
          {selectedOption.current_profit_loss !== undefined && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Current P&L:</span>
                <span className={`text-lg font-bold ${getProfitLossColor(selectedOption.current_profit_loss)}`}>
                  ${selectedOption.current_profit_loss.toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {/* Simple Chart Placeholder */}
          <div className="bg-gray-100 rounded-lg p-8 text-center">
            <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">
              Chart showing {selectedOption.price_history.length} price points
            </p>
            <p className="text-sm text-gray-500 mt-2">
              From {formatDate(selectedOption.price_history[0]?.timestamp)} to{' '}
              {formatDate(selectedOption.price_history[selectedOption.price_history.length - 1]?.timestamp)}
            </p>
          </div>

          {/* Option Summary */}
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">AI Analysis Summary</h4>
            <p className="text-sm text-blue-800">{selectedOption.chosen_option.summary}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="h-5 w-5 mr-2" />
          Back to Scanner
        </button>
        <div className="flex items-center space-x-4">
          <button
            onClick={runBacktest}
            disabled={isLoading || chosenOptions.length === 0}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg flex items-center"
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            {isLoading ? 'Running...' : 'Back Test'}
          </button>
          <button
            onClick={fetchChosenOptions}
            disabled={isLoading}
            className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg flex items-center"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Backtest Results */}
      {backtestResults && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Backtest Results</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{backtestResults.total_plays}</div>
              <div className="text-sm text-gray-600">Total Plays</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{backtestResults.profitable_plays}</div>
              <div className="text-sm text-gray-600">Profitable</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{backtestResults.losing_plays}</div>
              <div className="text-sm text-gray-600">Losing</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{backtestResults.win_rate.toFixed(1)}%</div>
              <div className="text-sm text-gray-600">Win Rate</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${getProfitLossColor(backtestResults.total_profit_loss)}`}>
                ${backtestResults.total_profit_loss.toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">Total P&L</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${getProfitLossColor(backtestResults.average_profit_loss)}`}>
                ${backtestResults.average_profit_loss.toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">Avg P&L</div>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-gray-600">Loading...</p>
        </div>
      )}

      {/* Options History */}
      {chosenOptions.length === 0 && !isLoading ? (
        <div className="text-center py-12">
          <Target className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Options Chosen Yet</h3>
          <p className="text-gray-600">
            Choose option plays from the scanner to track their performance here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {chosenOptions.map((option) => (
            <div key={option.id} className="bg-white rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">
                    {option.symbol} {option.company_name}
                  </h3>
                  <div className="flex items-center space-x-4 mt-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getOptionTypeColor(option.option_type)}`}>
                      {option.option_type}
                    </span>
                    <span className="text-sm text-gray-600">Strike: ${option.strike}</span>
                    <span className="text-sm text-gray-600">Exp: {option.expiration}</span>
                    <span className="text-sm text-gray-600">Entry: ${option.entry_price.toFixed(2)}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-600">
                    {formatDate(option.chosen_at)}
                  </div>
                  <div className="text-lg font-bold text-purple-600">
                    {option.confidence_score.toFixed(1)}% Confidence
                  </div>
                  {option.actual_profit_loss !== undefined && (
                    <div className={`text-lg font-bold ${getProfitLossColor(option.actual_profit_loss)}`}>
                      P&L: ${option.actual_profit_loss.toFixed(2)}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  {option.summary.substring(0, 100)}...
                </div>
                <button
                  onClick={() => fetchOptionChart(option.id)}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center"
                >
                  <BarChart3 className="h-4 w-4 mr-2" />
                  View Chart
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
