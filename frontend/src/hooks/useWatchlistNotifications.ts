/**
 * Custom hook for managing watchlist notifications
 * Handles target hits, stop losses, and performance milestones
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

export interface WatchlistNotification {
  id: string;
  entry_id: number;
  symbol: string;
  type: 'target_hit' | 'stop_loss_hit' | 'price_alert' | 'performance_milestone' | 'daily_summary';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  current_price: number;
  entry_price: number;
  target_price?: number;
  stop_loss_price?: number;
  gain_percent: number;
  gain_dollars: number;
  timestamp: string;
  metadata: Record<string, any>;
}

export interface DailySummary {
  id: string;
  title: string;
  message: string;
  gain_percent: number;
  gain_dollars: number;
  timestamp: string;
  metadata: {
    total_entries: number;
    winners: number;
    losers: number;
    neutral: number;
  };
}

interface UseWatchlistNotificationsReturn {
  notifications: WatchlistNotification[];
  dailySummary: DailySummary | null;
  isLoading: boolean;
  error: string | null;
  unreadCount: number;
  checkNotifications: () => Promise<void>;
  getDailySummary: () => Promise<void>;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
  testNotifications: (entryId: number) => Promise<any>;
}

export function useWatchlistNotifications(): UseWatchlistNotificationsReturn {
  const [notifications, setNotifications] = useState<WatchlistNotification[]>([]);
  const [dailySummary, setDailySummary] = useState<DailySummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [readNotifications, setReadNotifications] = useState<Set<string>>(new Set());

  const checkNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('🔔 Checking watchlist notifications...');
      const response = await api.checkNotifications();
      
      if (response && Array.isArray(response)) {
        setNotifications(response);
        console.log(`📬 Found ${response.length} notifications`);
        
        // Show browser notifications for high/critical severity
        response.forEach(notification => {
          if (notification.severity === 'high' || notification.severity === 'critical') {
            showBrowserNotification(notification);
          }
        });
      } else {
        setNotifications([]);
      }
    } catch (err) {
      console.error('Error checking notifications:', err);
      setError(err instanceof Error ? err.message : 'Failed to check notifications');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getDailySummary = useCallback(async () => {
    try {
      console.log('📊 Getting daily summary...');
      const response = await api.getDailySummary();
      
      if (response && response.title) {
        setDailySummary(response);
        console.log('📈 Daily summary loaded:', response.message);
      } else {
        setDailySummary(null);
      }
    } catch (err) {
      console.error('Error getting daily summary:', err);
      // Don't set error for daily summary failures
    }
  }, []);

  const markAsRead = useCallback((notificationId: string) => {
    setReadNotifications(prev => new Set(prev).add(notificationId));
  }, []);

  const markAllAsRead = useCallback(() => {
    const allIds = notifications.map(n => n.id);
    setReadNotifications(new Set(allIds));
  }, [notifications]);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
    setReadNotifications(new Set());
  }, []);

  const testNotifications = useCallback(async (entryId: number) => {
    try {
      console.log(`🧪 Testing notifications for entry ${entryId}...`);
      const response = await api.testNotifications(entryId);
      console.log('Test notifications result:', response);
      return response;
    } catch (err) {
      console.error('Error testing notifications:', err);
      throw err;
    }
  }, []);

  // Show browser notification
  const showBrowserNotification = useCallback((notification: WatchlistNotification) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      const browserNotification = new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico',
        tag: `watchlist-${notification.symbol}`,
        requireInteraction: notification.severity === 'critical'
      });

      browserNotification.onclick = () => {
        window.focus();
        // Navigate to performance tab
        window.location.hash = '#performance';
        browserNotification.close();
      };

      // Auto-close after 10 seconds for non-critical notifications
      if (notification.severity !== 'critical') {
        setTimeout(() => {
          browserNotification.close();
        }, 10000);
      }
    }
  }, []);

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        console.log('Notification permission:', permission);
      });
    }
  }, []);

  // Auto-check notifications every 5 minutes during market hours
  useEffect(() => {
    const checkInterval = setInterval(() => {
      const now = new Date();
      const hour = now.getHours();
      const day = now.getDay();
      
      // Check if it's market hours (9 AM - 4 PM, Mon-Fri)
      const isMarketHours = day >= 1 && day <= 5 && hour >= 9 && hour <= 16;
      
      if (isMarketHours) {
        checkNotifications();
      }
    }, 5 * 60 * 1000); // 5 minutes

    // Initial check
    checkNotifications();
    getDailySummary();

    return () => clearInterval(checkInterval);
  }, [checkNotifications, getDailySummary]);

  const unreadCount = notifications.filter(n => !readNotifications.has(n.id)).length;

  return {
    notifications,
    dailySummary,
    isLoading,
    error,
    unreadCount,
    checkNotifications,
    getDailySummary,
    markAsRead,
    markAllAsRead,
    clearNotifications,
    testNotifications
  };
}

// Utility functions for notification formatting
export const getNotificationIcon = (type: WatchlistNotification['type']): string => {
  switch (type) {
    case 'target_hit':
      return '🎯';
    case 'stop_loss_hit':
      return '🛑';
    case 'performance_milestone':
      return '🚀';
    case 'price_alert':
      return '📈';
    case 'daily_summary':
      return '📊';
    default:
      return '🔔';
  }
};

export const getNotificationColor = (severity: WatchlistNotification['severity']): string => {
  switch (severity) {
    case 'critical':
      return 'text-red-400 border-red-500';
    case 'high':
      return 'text-yellow-400 border-yellow-500';
    case 'medium':
      return 'text-blue-400 border-blue-500';
    case 'low':
      return 'text-gray-400 border-gray-500';
    default:
      return 'text-gray-400 border-gray-500';
  }
};

export const formatNotificationTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString();
};
