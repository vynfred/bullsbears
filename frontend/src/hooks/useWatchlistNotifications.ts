// src/hooks/useWatchlistNotifications.ts
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { WatchlistNotification } from '@/lib/types';

export function useWatchlistNotifications() {
  const [notifications, setNotifications] = useState<WatchlistNotification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.getWatchlistNotifications();
        setNotifications(data);
      } catch (err) {
        console.error('Failed to load notifications');
      } finally {
        setIsLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 24 * 60 * 60 * 1000); // daily
    return () => clearInterval(interval);
  }, []);

  return { notifications, isLoading };
}