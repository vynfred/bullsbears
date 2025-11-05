'use client';

import React, { useState, useMemo } from 'react';
import { Star, TrendingUp, TrendingDown, Edit3, Trash2, Plus, RefreshCw, Filter, MoreHorizontal, BarChart3, PieChart, Target } from 'lucide-react';
import { StickyHeader } from './StickyHeader';
import { useWatchlist } from '@/hooks/useWatchlist';
import { WatchlistEntry as APIWatchlistEntry, UpdateWatchlistEntryRequest } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface WatchlistProps {
  entries?: APIWatchlistEntry[];
}

// Demo data for watchlist entries (keeping for backward compatibility during transition)
const demoWatchlistEntries: any[] = [
  {
    id: '1',
    ticker: 'TSLA',
    companyName: 'Tesla Inc.',
    entryPrice: 247.80,
    entryDate: '2024-11-03T08:30:00Z',
    currentPrice: 298.40,
    exitPrice: 298.40, // Default to current price
    isActive: true,
    userSetEntry: false,
    userSetExit: false
  },
  {
    id: '2',
    ticker: 'NVDA',
    companyName: 'NVIDIA Corporation',
    entryPrice: 142.50,
    entryDate: '2024-11-02T14:20:00Z',
    currentPrice: 145.80,
    exitPrice: 145.80, // Default to current price
    isActive: true,
    userSetEntry: true, // User manually set this entry price
    userSetExit: false
  },
  {
    id: '3',
    ticker: 'AAPL',
    companyName: 'Apple Inc.',
    entryPrice: 225.00,
    entryDate: '2024-11-01T09:15:00Z',
    currentPrice: 224.80,
    exitPrice: 230.50,
    exitDate: '2024-11-03T15:45:00Z',
    isActive: false,
    userSetEntry: false,
    userSetExit: true // User manually set exit price to lock profits
  }
];

export function Watchlist({ entries }: WatchlistProps) {
  const {
    entries: watchlistEntries,
    filteredEntries,
    isLoading,
    isUpdating,
    error,
    updateEntry,
    removeEntry,
    updatePrices,
    setStatusFilter,
    setTypeFilter,
    statusFilter,
    typeFilter
  } = useWatchlist();

  const [editingEntry, setEditingEntry] = useState<number | null>(null);
  const [editPrice, setEditPrice] = useState<string>('');
  const [editingField, setEditingField] = useState<'entry_price' | 'target_price' | 'stop_loss_price' | 'exit_price' | null>(null);
  const [showRemoveDialog, setShowRemoveDialog] = useState<number | null>(null);
  const [selectedEntries, setSelectedEntries] = useState<number[]>([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'portfolio' | 'individual'>('portfolio');
  const [positionType, setPositionType] = useState<'long' | 'short' | 'both'>('both');

  const calculateReturn = (entry: APIWatchlistEntry) => {
    const currentPrice = entry.current_price || entry.entry_price;
    const returnPercent = ((currentPrice - entry.entry_price) / entry.entry_price) * 100;
    const returnDollar = (currentPrice - entry.entry_price);
    return { returnPercent, returnDollar };
  };

  // Portfolio performance calculations
  const portfolioMetrics = useMemo(() => {
    const filteredBySelection = selectedStocks.size > 0
      ? filteredEntries.filter(entry => selectedStocks.has(entry.symbol))
      : filteredEntries;

    const filteredByPosition = positionType === 'both'
      ? filteredBySelection
      : filteredBySelection.filter(entry => {
          const { returnPercent } = calculateReturn(entry);
          return positionType === 'long' ? returnPercent >= 0 : returnPercent < 0;
        });

    const totalInvested = filteredByPosition.reduce((sum, entry) => sum + entry.entry_price, 0);
    const currentValue = filteredByPosition.reduce((sum, entry) => sum + (entry.current_price || entry.entry_price), 0);
    const totalReturn = currentValue - totalInvested;
    const totalReturnPercent = totalInvested > 0 ? (totalReturn / totalInvested) * 100 : 0;

    // Generate historical performance data (mock for now)
    const performanceData = Array.from({ length: 30 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (29 - i));
      const baseReturn = totalReturnPercent;
      const variance = Math.sin(i * 0.2) * 2; // Add some realistic variance
      return {
        date: date.toISOString().split('T')[0],
        portfolio: baseReturn + variance,
        individual: filteredByPosition.map(entry => {
          const { returnPercent } = calculateReturn(entry);
          return returnPercent + Math.random() * 4 - 2; // Add variance
        })
      };
    });

    return {
      totalInvested,
      currentValue,
      totalReturn,
      totalReturnPercent,
      stockCount: filteredByPosition.length,
      performanceData
    };
  }, [filteredEntries, selectedStocks, positionType]);

  const handleEditEntry = (entryId: number, price: number, field: 'entry_price' | 'target_price' | 'stop_loss_price' | 'exit_price') => {
    setEditingEntry(entryId);
    setEditingField(field);
    setEditPrice(price.toString());
  };

  const toggleStockSelection = (symbol: string) => {
    const newSelection = new Set(selectedStocks);
    if (newSelection.has(symbol)) {
      newSelection.delete(symbol);
    } else {
      newSelection.add(symbol);
    }
    setSelectedStocks(newSelection);
  };

  const handleSaveEdit = async (entryId: number) => {
    const newPrice = parseFloat(editPrice);
    if (isNaN(newPrice) || newPrice <= 0) return;

    const updateRequest: UpdateWatchlistEntryRequest = {};
    if (editingField === 'entry_price') {
      updateRequest.entry_price = newPrice;
    } else if (editingField === 'target_price') {
      updateRequest.target_price = newPrice;
    } else if (editingField === 'stop_loss_price') {
      updateRequest.stop_loss_price = newPrice;
    } else if (editingField === 'exit_price') {
      updateRequest.exit_price = newPrice;
    }

    const success = await updateEntry(entryId, updateRequest);

    if (success) {
      setEditingEntry(null);
      setEditingField(null);
      setEditPrice('');
    }
  };

  const handleRemoveFromWatchlist = (entryId: number) => {
    setShowRemoveDialog(entryId);
  };

  const handleConfirmRemove = async (entryId: number, setExitPrice: boolean) => {
    if (setExitPrice) {
      // Update entry to closed status with current price as exit price
      const entry = watchlistEntries.find(e => e.id === entryId);
      if (entry && entry.current_price) {
        await updateEntry(entryId, {
          status: 'CLOSED',
          exit_price: entry.current_price,
          exit_reason: 'Manual close'
        });
      }
    } else {
      // Remove completely from watchlist
      await removeEntry(entryId);
    }
    setShowRemoveDialog(null);
  };

  const handleCancelRemove = () => {
    setShowRemoveDialog(null);
  };

  const activeEntries = filteredEntries.filter(e => e.status === 'ACTIVE');
  const closedEntries = filteredEntries.filter(e => e.status === 'CLOSED');

  return (
    <div className="space-y-6">
      {/* Sticky Header */}
      <StickyHeader title="Watchlist" />

      <div className="px-4">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-white mb-4">Your Watchlist</h1>
          <p className="text-gray-400">
            Track portfolio performance, select stocks to see combined strategies, and analyze both long and short positions.
          </p>
        </div>

        {/* Portfolio Performance Dashboard */}
        <div className="mb-8 space-y-4">
          {/* Controls */}
          <div className="flex flex-wrap gap-4 items-center justify-between">
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('portfolio')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'portfolio'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                <BarChart3 className="w-4 h-4 inline mr-2" />
                Portfolio View
              </button>
              <button
                onClick={() => setViewMode('individual')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'individual'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                <PieChart className="w-4 h-4 inline mr-2" />
                Individual Stocks
              </button>
            </div>

            <div className="flex gap-2">
              <select
                value={positionType}
                onChange={(e) => setPositionType(e.target.value as 'long' | 'short' | 'both')}
                className="bg-gray-700 text-white px-3 py-2 rounded-lg text-sm border border-gray-600"
              >
                <option value="both">All Positions</option>
                <option value="long">Long Only</option>
                <option value="short">Short Only</option>
              </select>
            </div>
          </div>

          {/* Portfolio Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Total Invested</div>
              <div className="text-white text-xl font-bold">${portfolioMetrics.totalInvested.toFixed(2)}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Current Value</div>
              <div className="text-white text-xl font-bold">${portfolioMetrics.currentValue.toFixed(2)}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Total Return</div>
              <div className={`text-xl font-bold ${portfolioMetrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {portfolioMetrics.totalReturn >= 0 ? '+' : ''}${portfolioMetrics.totalReturn.toFixed(2)}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Return %</div>
              <div className={`text-xl font-bold ${portfolioMetrics.totalReturnPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {portfolioMetrics.totalReturnPercent >= 0 ? '+' : ''}{portfolioMetrics.totalReturnPercent.toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Performance Chart */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h3 className="text-white text-lg font-bold mb-4">
              {selectedStocks.size > 0 ? `Selected Stocks Performance (${selectedStocks.size})` : 'Portfolio Performance (30 days)'}
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={portfolioMetrics.performanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="portfolio"
                    stroke="#10B981"
                    strokeWidth={2}
                    name="Portfolio Return (%)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Active Positions */}
        {activeEntries.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              Active Positions ({activeEntries.length})
            </h2>
            
            <div className="space-y-4">
              {activeEntries.map((entry) => {
                const { returnPercent, returnDollar } = calculateReturn(entry);
                const isPositive = returnPercent >= 0;
                
                return (
                  <div key={entry.id} className={`bg-gray-800 border rounded-lg p-4 transition-all ${
                    selectedStocks.has(entry.symbol)
                      ? 'border-blue-500 bg-blue-900/20'
                      : 'border-gray-700'
                  }`}>
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={selectedStocks.has(entry.symbol)}
                          onChange={() => toggleStockSelection(entry.symbol)}
                          className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-lg font-bold text-white">{entry.symbol}</span>
                            <Star className="w-4 h-4 text-yellow-400 fill-current" />
                          </div>
                          <div className="text-sm text-gray-400">{entry.company_name}</div>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className={`text-lg font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                          {isPositive ? '+' : ''}{returnPercent.toFixed(1)}%
                        </div>
                        <div className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                          {isPositive ? '+' : ''}${returnDollar.toFixed(2)}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-gray-400">Entry Price</div>
                        <div className="flex items-center gap-2">
                          {editingEntry === entry.id && editingField === 'entry_price' ? (
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                value={editPrice}
                                onChange={(e) => setEditPrice(e.target.value)}
                                className="w-20 bg-gray-700 text-white px-2 py-1 rounded text-sm"
                                step="0.01"
                              />
                              <button
                                onClick={() => handleSaveEdit(entry.id)}
                                className="text-green-400 hover:text-green-300"
                              >
                                ✓
                              </button>
                            </div>
                          ) : (
                            <>
                              <span className="text-white font-medium">${entry.entry_price.toFixed(2)}</span>
                              <button
                                onClick={() => handleEditEntry(entry.id, entry.entry_price, 'entry_price')}
                                className="text-gray-400 hover:text-white"
                              >
                                <Edit3 className="w-3 h-3" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      <div>
                        <div className="text-gray-400">Exit Price</div>
                        <div className="flex items-center gap-2">
                          {editingEntry === entry.id && editingField === 'exit_price' ? (
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                value={editPrice}
                                onChange={(e) => setEditPrice(e.target.value)}
                                className="w-20 bg-gray-700 text-white px-2 py-1 rounded text-sm"
                                step="0.01"
                              />
                              <button
                                onClick={() => handleSaveEdit(entry.id)}
                                className="text-green-400 hover:text-green-300"
                              >
                                ✓
                              </button>
                            </div>
                          ) : (
                            <>
                              <span className="text-white font-medium">${entry.exit_price?.toFixed(2) || 'N/A'}</span>
                              <button
                                onClick={() => handleEditEntry(entry.id, entry.exit_price || 0, 'exit_price')}
                                className="text-gray-400 hover:text-white"
                              >
                                <Edit3 className="w-3 h-3" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      <div>
                        <div className="text-gray-400">Current Price</div>
                        <div className="text-white font-medium">${entry.current_price?.toFixed(2) || 'N/A'}</div>
                      </div>
                    </div>

                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => handleEditEntry(entry.id, entry.current_price || 0, 'exit_price')}
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors"
                      >
                        Lock Profits
                      </button>
                      <button
                        onClick={() => handleRemoveFromWatchlist(entry.id)}
                        className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Closed Positions */}
        {closedEntries.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-gray-400" />
              Closed Positions ({closedEntries.length})
            </h2>
            
            <div className="space-y-4">
              {closedEntries.map((entry) => {
                const { returnPercent, returnDollar } = calculateReturn(entry);
                const isPositive = returnPercent >= 0;
                
                return (
                  <div key={entry.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 opacity-75">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold text-white">{entry.symbol}</span>
                          <span className="text-xs bg-gray-600 text-gray-300 px-2 py-1 rounded">CLOSED</span>
                        </div>
                        <div className="text-sm text-gray-400">{entry.company_name}</div>
                      </div>
                      
                      <div className="text-right">
                        <div className={`text-lg font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                          {isPositive ? '+' : ''}{returnPercent.toFixed(1)}%
                        </div>
                        <div className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                          {isPositive ? '+' : ''}${returnDollar.toFixed(2)}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-gray-400">Entry</div>
                        <div className="text-white">${entry.entry_price.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Exit</div>
                        <div className="flex items-center gap-1">
                          <span className="text-white">${entry.exit_price?.toFixed(2) || 'N/A'}</span>
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400">Days Held</div>
                        <div className="text-white">
                          {entry.days_held}d
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {activeEntries.length === 0 && closedEntries.length === 0 && (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 text-center">
            <Star className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <div className="text-gray-400 text-xl mb-2">Your watchlist is empty</div>
            <div className="text-gray-500 text-sm mb-6">Add stocks by voting on gut checks or from the Pulse tab</div>
            <button className="bg-yellow-500 text-black px-6 py-3 rounded-lg font-semibold hover:bg-yellow-400 transition-colors">
              Browse Today's Picks
            </button>
          </div>
        )}
      </div>

      {/* Remove Confirmation Dialog */}
      {showRemoveDialog && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-xl font-bold text-white mb-4">Remove from Watchlist</h3>
            <p className="text-gray-300 mb-6">
              What would you like to do with this position's performance data?
            </p>

            <div className="space-y-3">
              <button
                onClick={() => handleConfirmRemove(showRemoveDialog, true)}
                className="w-full bg-green-600 hover:bg-green-700 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
              >
                Set Exit Price & Keep Performance Data
              </button>
              <button
                onClick={() => handleConfirmRemove(showRemoveDialog, false)}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
              >
                Remove Completely (Delete Performance Data)
              </button>
              <button
                onClick={handleCancelRemove}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
