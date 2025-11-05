'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, WatchlistEntry, AddToWatchlistRequest, UpdateWatchlistEntryRequest, BulkWatchlistOperation, WatchlistPerformanceMetrics } from '@/lib/api';

export interface UseWatchlistReturn {
  // Data
  entries: WatchlistEntry[];
  performanceMetrics: WatchlistPerformanceMetrics | null;
  summary: any;
  
  // Loading states
  isLoading: boolean;
  isUpdating: boolean;
  isAdding: boolean;
  
  // Error handling
  error: string | null;
  
  // Actions
  addToWatchlist: (request: AddToWatchlistRequest) => Promise<boolean>;
  updateEntry: (entryId: number, request: UpdateWatchlistEntryRequest) => Promise<boolean>;
  removeEntry: (entryId: number) => Promise<boolean>;
  bulkOperation: (request: BulkWatchlistOperation) => Promise<boolean>;
  updatePrices: () => Promise<boolean>;
  refreshData: () => Promise<void>;
  
  // Filters
  filteredEntries: WatchlistEntry[];
  setStatusFilter: (status: string | null) => void;
  setTypeFilter: (type: string | null) => void;
  statusFilter: string | null;
  typeFilter: string | null;
}

export function useWatchlist(): UseWatchlistReturn {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<WatchlistPerformanceMetrics | null>(null);
  const [summary, setSummary] = useState<any>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  // Filter entries based on current filters
  const filteredEntries = entries.filter(entry => {
    if (statusFilter && entry.status !== statusFilter) return false;
    if (typeFilter && entry.entry_type !== typeFilter) return false;
    return true;
  });

  // Fetch all watchlist data
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [entriesData, metricsData, summaryData] = await Promise.all([
        api.getWatchlistEntries(),
        api.getWatchlistPerformance().catch(() => null), // Don't fail if metrics unavailable
        api.getWatchlistSummary().catch(() => null) // Don't fail if summary unavailable
      ]);
      
      setEntries(entriesData);
      setPerformanceMetrics(metricsData);
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch watchlist data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Refresh data
  const refreshData = useCallback(async () => {
    setIsUpdating(true);
    await fetchData();
    setIsUpdating(false);
  }, [fetchData]);

  // Add to watchlist
  const addToWatchlist = useCallback(async (request: AddToWatchlistRequest): Promise<boolean> => {
    try {
      setIsAdding(true);
      setError(null);
      
      const result = await api.addToWatchlist(request);
      
      if (result.success) {
        await refreshData(); // Refresh to get the new entry
        return true;
      }
      
      setError(result.message || 'Failed to add to watchlist');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add to watchlist');
      return false;
    } finally {
      setIsAdding(false);
    }
  }, [refreshData]);

  // Update entry
  const updateEntry = useCallback(async (entryId: number, request: UpdateWatchlistEntryRequest): Promise<boolean> => {
    try {
      setError(null);
      
      const result = await api.updateWatchlistEntry(entryId, request);
      
      if (result.success) {
        await refreshData(); // Refresh to get updated data
        return true;
      }
      
      setError(result.message || 'Failed to update entry');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update entry');
      return false;
    }
  }, [refreshData]);

  // Remove entry
  const removeEntry = useCallback(async (entryId: number): Promise<boolean> => {
    try {
      setError(null);
      
      const result = await api.removeFromWatchlist(entryId);
      
      if (result.success) {
        // Optimistically update the UI
        setEntries(prev => prev.filter(entry => entry.id !== entryId));
        await refreshData(); // Refresh to ensure consistency
        return true;
      }
      
      setError(result.message || 'Failed to remove entry');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove entry');
      return false;
    }
  }, [refreshData]);

  // Bulk operation
  const bulkOperation = useCallback(async (request: BulkWatchlistOperation): Promise<boolean> => {
    try {
      setError(null);
      
      const result = await api.bulkWatchlistOperation(request);
      
      if (result.success) {
        await refreshData(); // Refresh to get updated data
        return true;
      }
      
      setError(result.message || 'Bulk operation failed');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk operation failed');
      return false;
    }
  }, [refreshData]);

  // Update prices
  const updatePrices = useCallback(async (): Promise<boolean> => {
    try {
      setIsUpdating(true);
      setError(null);
      
      const result = await api.updateWatchlistPrices();
      
      if (result.success) {
        await refreshData(); // Refresh to get updated prices
        return true;
      }
      
      setError(result.message || 'Failed to update prices');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update prices');
      return false;
    } finally {
      setIsUpdating(false);
    }
  }, [refreshData]);

  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    // Data
    entries,
    performanceMetrics,
    summary,
    
    // Loading states
    isLoading,
    isUpdating,
    isAdding,
    
    // Error handling
    error,
    
    // Actions
    addToWatchlist,
    updateEntry,
    removeEntry,
    bulkOperation,
    updatePrices,
    refreshData,
    
    // Filters
    filteredEntries,
    setStatusFilter,
    setTypeFilter,
    statusFilter,
    typeFilter,
  };
}
