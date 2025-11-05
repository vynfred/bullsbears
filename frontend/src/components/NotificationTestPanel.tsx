/**
 * Notification Test Panel
 * Development component for testing the notification system
 */

import React, { useState } from 'react';
import { Bell, TestTube, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';

interface NotificationTestPanelProps {
  className?: string;
}

export function NotificationTestPanel({ className = '' }: NotificationTestPanelProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [testResults, setTestResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const runNotificationTest = async () => {
    setIsLoading(true);
    setError(null);
    setTestResults([]);

    try {
      console.log('🧪 Running notification system test...');
      
      // Test 1: Check notifications endpoint
      const notifications = await api.checkNotifications();
      setTestResults(prev => [...prev, {
        test: 'Check Notifications',
        status: 'success',
        data: notifications,
        message: `Found ${notifications.length} notifications`
      }]);

      // Test 2: Get daily summary
      const summary = await api.getDailySummary();
      setTestResults(prev => [...prev, {
        test: 'Daily Summary',
        status: 'success',
        data: summary,
        message: 'Daily summary retrieved successfully'
      }]);

      // Test 3: Test notifications for first watchlist entry (if any exist)
      // This would require getting watchlist entries first
      try {
        const watchlistEntries = await api.getWatchlistEntries();
        if (watchlistEntries.length > 0) {
          const testResult = await api.testNotifications(watchlistEntries[0].id);
          setTestResults(prev => [...prev, {
            test: 'Test Notifications',
            status: 'success',
            data: testResult,
            message: `Test notifications for entry ${watchlistEntries[0].id}`
          }]);
        } else {
          setTestResults(prev => [...prev, {
            test: 'Test Notifications',
            status: 'warning',
            data: null,
            message: 'No watchlist entries found to test'
          }]);
        }
      } catch (testError) {
        setTestResults(prev => [...prev, {
          test: 'Test Notifications',
          status: 'error',
          data: testError,
          message: 'Failed to test notifications'
        }]);
      }

    } catch (err: any) {
      setError(err.message || 'Test failed');
      setTestResults(prev => [...prev, {
        test: 'Overall Test',
        status: 'error',
        data: err,
        message: err.message || 'Unknown error'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Bell className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'border-green-500';
      case 'warning':
        return 'border-yellow-500';
      case 'error':
        return 'border-red-500';
      default:
        return 'border-gray-500';
    }
  };

  return (
    <div className={`bg-gray-900 border border-gray-700 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TestTube className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Notification System Test</h3>
        </div>
        
        <button
          onClick={runNotificationTest}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:opacity-50 text-white rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Testing...' : 'Run Test'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span className="text-red-300 text-sm">Error: {error}</span>
          </div>
        </div>
      )}

      {testResults.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-300">Test Results:</h4>
          
          {testResults.map((result, index) => (
            <div
              key={index}
              className={`p-3 border-l-2 ${getStatusColor(result.status)} bg-gray-800/50 rounded-r-lg`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {getStatusIcon(result.status)}
                  <span className="text-sm font-medium text-white">{result.test}</span>
                </div>
                <span className={`text-xs px-2 py-1 rounded ${
                  result.status === 'success' ? 'bg-green-900 text-green-300' :
                  result.status === 'warning' ? 'bg-yellow-900 text-yellow-300' :
                  'bg-red-900 text-red-300'
                }`}>
                  {result.status.toUpperCase()}
                </span>
              </div>
              
              <p className="text-sm text-gray-300 mb-2">{result.message}</p>
              
              {result.data && (
                <details className="text-xs">
                  <summary className="text-gray-400 cursor-pointer hover:text-gray-300">
                    View Data
                  </summary>
                  <pre className="mt-2 p-2 bg-gray-900 rounded text-gray-300 overflow-x-auto">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 p-3 bg-gray-800/30 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Test Coverage:</h4>
        <ul className="text-xs text-gray-400 space-y-1">
          <li>• API endpoint connectivity</li>
          <li>• Notification checking functionality</li>
          <li>• Daily summary generation</li>
          <li>• Test notification triggers</li>
          <li>• Error handling and fallbacks</li>
        </ul>
      </div>
    </div>
  );
}
