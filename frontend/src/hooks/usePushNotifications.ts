/**
 * Hook for managing push notifications
 * - Requests permission on first load
 * - Monitors picks and watchlist for target hits
 * - Integrates with PushService
 */

import { useEffect, useCallback, useState } from 'react';
import { pushService } from '@/lib/PushService';
import { useAuth } from './useAuth';

interface UsePushNotificationsOptions {
  enabled?: boolean;
  watchlistOnly?: boolean;
}

export function usePushNotifications(options: UsePushNotificationsOptions = {}) {
  const { enabled = true, watchlistOnly = true } = options;
  const { userProfile, updateUserProfile } = useAuth();
  const [permissionStatus, setPermissionStatus] = useState<NotificationPermission>('default');
  const [isInitialized, setIsInitialized] = useState(false);

  // Request notification permission on first load
  useEffect(() => {
    if (!enabled || isInitialized) return;

    const requestPermission = async () => {
      if ('Notification' in window) {
        const currentPermission = Notification.permission;
        setPermissionStatus(currentPermission);

        // Only request if not already decided
        if (currentPermission === 'default') {
          try {
            const permission = await Notification.requestPermission();
            setPermissionStatus(permission);

            // Update user profile with notification preference
            if (userProfile && permission === 'granted') {
              await updateUserProfile({
                notificationSettings: {
                  pushEnabled: true,
                  emailEnabled: userProfile.notificationSettings?.emailEnabled ?? false,
                  morningPicks: userProfile.notificationSettings?.morningPicks ?? true,
                  targetHits: userProfile.notificationSettings?.targetHits ?? true,
                  watchlistAlerts: userProfile.notificationSettings?.watchlistAlerts ?? true,
                },
              });
            }

            console.log(`🔔 Notification permission: ${permission}`);
          } catch (error) {
            console.error('Failed to request notification permission:', error);
          }
        }
      }

      setIsInitialized(true);
    };

    // Request permission after a short delay to avoid blocking initial render
    const timer = setTimeout(requestPermission, 2000);
    return () => clearTimeout(timer);
  }, [enabled, isInitialized, userProfile, updateUserProfile]);

  // Update PushService config based on user settings
  useEffect(() => {
    if (!userProfile) return;

    const notificationSettings = userProfile.notificationSettings;
    if (notificationSettings) {
      pushService.updateConfig({
        enableBrowserNotifications: notificationSettings.pushEnabled,
        enableConfetti: true,
        watchlistOnly,
      });
    }
  }, [userProfile, watchlistOnly]);

  // Check target hit for a stock
  const checkTargetHit = useCallback(
    async (symbol: string, currentPrice: number, entryPrice: number, direction: 'LONG' | 'SHORT' = 'LONG') => {
      if (!enabled || permissionStatus !== 'granted') return;

      await pushService.checkTargetHit(symbol, currentPrice, entryPrice, direction);
    },
    [enabled, permissionStatus]
  );

  // Add stock to watchlist for notifications
  const addToWatchlist = useCallback((symbol: string) => {
    pushService.addToWatchlist(symbol);
  }, []);

  // Remove stock from watchlist
  const removeFromWatchlist = useCallback((symbol: string) => {
    pushService.removeFromWatchlist(symbol);
  }, []);

  // Trigger confetti manually
  const triggerConfetti = useCallback(() => {
    pushService.triggerConfetti();
  }, []);

  // Enable/disable notifications
  const toggleNotifications = useCallback(
    async (enable: boolean) => {
      if (!userProfile) return;

      await updateUserProfile({
        notificationSettings: {
          pushEnabled: enable,
          emailEnabled: userProfile.notificationSettings?.emailEnabled ?? false,
          morningPicks: userProfile.notificationSettings?.morningPicks ?? true,
          targetHits: userProfile.notificationSettings?.targetHits ?? true,
          watchlistAlerts: userProfile.notificationSettings?.watchlistAlerts ?? true,
        },
      });

      pushService.updateConfig({
        enableBrowserNotifications: enable,
      });
    },
    [userProfile, updateUserProfile]
  );

  return {
    permissionStatus,
    isEnabled: permissionStatus === 'granted' && userProfile?.notificationSettings?.pushEnabled !== false,
    checkTargetHit,
    addToWatchlist,
    removeFromWatchlist,
    triggerConfetti,
    toggleNotifications,
  };
}

// Hook for monitoring picks and watchlist for target hits
export function usePriceMonitoring(
  stocks: Array<{ symbol: string; entryPrice: number; currentPrice: number; direction?: 'LONG' | 'SHORT' }>,
  enabled: boolean = true
) {
  const { checkTargetHit } = usePushNotifications({ enabled });

  useEffect(() => {
    if (!enabled || stocks.length === 0) return;

    // Check each stock for target hits
    stocks.forEach((stock) => {
      checkTargetHit(stock.symbol, stock.currentPrice, stock.entryPrice, stock.direction || 'LONG');
    });
  }, [stocks, enabled, checkTargetHit]);
}

