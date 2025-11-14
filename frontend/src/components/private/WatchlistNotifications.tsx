// src/components/private/WatchlistNotifications.tsx
'use client';

import React from 'react';
import { Bell, Target, AlertTriangle, TrendingUp } from 'lucide-react';
import { useWatchlistNotifications } from '@/hooks/useWatchlistNotifications';
import { WatchlistNotification } from '@/lib/types';

const getIcon = (type: string) => {
  switch (type) {
    case 'target_hit': return <Target className="w-4 h-4 text-emerald-400" />;
    case 'stop_loss_hit': return <AlertTriangle className="w-4 h-4 text-red-400" />;
    case 'performance_milestone': return <TrendingUp className="w-4 h-4 text-yellow-400" />;
    default: return <Bell className="w-4 h-4 text-blue-400" />;
  }
};

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

export default function WatchlistNotifications() {
  const { notifications, isLoading } = useWatchlistNotifications();

  const recent = notifications.slice(0, 10);

  if (isLoading) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
        <div className="animate-pulse flex items-center gap-2">
          <Bell className="w-5 h-5 text-gray-500" />
          <span className="text-gray-500">Loading notifications...</span>
        </div>
      </div>
    );
  }

  if (recent.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-center">
        <Bell className="w-12 h-12 mx-auto mb-2 text-gray-600" />
        <p className="text-gray-400">No new notifications</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <Bell className="w-5 h-5 text-blue-400" />
        <h3 className="text-lg font-semibold text-white">Watchlist Updates</h3>
        <span className="text-xs text-gray-400">Last 10</span>
      </div>

      {recent.map(notif => (
        <div
          key={notif.id}
          className="flex items-start gap-3 p-2 rounded hover:bg-gray-800 transition-colors"
        >
          <span className="mt-0.5">{getIcon(notif.type)}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{notif.title}</p>
            <p className="text-xs text-gray-400">{notif.message}</p>
            <p className="text-xs text-gray-500 mt-1">{formatTime(notif.timestamp)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}