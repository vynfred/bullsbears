/**
 * Watchlist Notifications Component
 * Displays target hits, stop losses, and performance milestones
 */

import React, { useState } from 'react';
import { Bell, X, Target, AlertTriangle, TrendingUp, BarChart3, RefreshCw } from 'lucide-react';
import { 
  useWatchlistNotifications, 
  WatchlistNotification,
  getNotificationIcon,
  getNotificationColor,
  formatNotificationTime
} from '../hooks/useWatchlistNotifications';

interface WatchlistNotificationsProps {
  className?: string;
}

export function WatchlistNotifications({ className = '' }: WatchlistNotificationsProps) {
  const {
    notifications,
    dailySummary,
    isLoading,
    error,
    unreadCount,
    checkNotifications,
    getDailySummary,
    markAsRead,
    markAllAsRead,
    clearNotifications
  } = useWatchlistNotifications();

  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedType, setSelectedType] = useState<string>('all');

  const filteredNotifications = notifications.filter(notification => {
    if (selectedType === 'all') return true;
    return notification.type === selectedType;
  });

  const notificationTypes = [
    { value: 'all', label: 'All', icon: Bell },
    { value: 'target_hit', label: 'Targets', icon: Target },
    { value: 'stop_loss_hit', label: 'Stop Loss', icon: AlertTriangle },
    { value: 'performance_milestone', label: 'Milestones', icon: TrendingUp },
    { value: 'daily_summary', label: 'Summary', icon: BarChart3 }
  ];

  const handleNotificationClick = (notification: WatchlistNotification) => {
    markAsRead(notification.id);
    // Could navigate to specific watchlist entry or performance page
  };

  const handleRefresh = async () => {
    await checkNotifications();
    await getDailySummary();
  };

  return (
    <div className={`bg-gray-900 border border-gray-700 rounded-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Notifications</h3>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="p-2 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
            title="Refresh notifications"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            {isExpanded ? <X className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Daily Summary */}
      {dailySummary && (
        <div className="p-4 border-b border-gray-700 bg-gray-800/50">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">{dailySummary.title}</span>
          </div>
          <p className="text-sm text-gray-300 mb-2">{dailySummary.message}</p>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>W: {dailySummary.metadata.winners}</span>
            <span>L: {dailySummary.metadata.losers}</span>
            <span>Total: {dailySummary.metadata.total_entries}</span>
          </div>
        </div>
      )}

      {isExpanded && (
        <>
          {/* Filter Tabs */}
          <div className="flex items-center gap-1 p-2 border-b border-gray-700 bg-gray-800/30">
            {notificationTypes.map(type => {
              const Icon = type.icon;
              const count = type.value === 'all' 
                ? notifications.length 
                : notifications.filter(n => n.type === type.value).length;
              
              return (
                <button
                  key={type.value}
                  onClick={() => setSelectedType(type.value)}
                  className={`flex items-center gap-1 px-3 py-1 rounded text-xs transition-colors ${
                    selectedType === type.value
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
                >
                  <Icon className="w-3 h-3" />
                  {type.label}
                  {count > 0 && (
                    <span className="bg-gray-600 text-white px-1 rounded">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Notifications List */}
          <div className="max-h-96 overflow-y-auto">
            {error && (
              <div className="p-4 text-red-400 text-sm">
                Error: {error}
              </div>
            )}

            {filteredNotifications.length === 0 ? (
              <div className="p-4 text-center text-gray-400">
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Checking notifications...
                  </div>
                ) : (
                  'No notifications'
                )}
              </div>
            ) : (
              <div className="divide-y divide-gray-700">
                {filteredNotifications.map(notification => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onClick={() => handleNotificationClick(notification)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          {notifications.length > 0 && (
            <div className="flex items-center justify-between p-3 border-t border-gray-700 bg-gray-800/30">
              <button
                onClick={markAllAsRead}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                Mark all as read
              </button>
              <button
                onClick={clearNotifications}
                className="text-xs text-red-400 hover:text-red-300 transition-colors"
              >
                Clear all
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface NotificationItemProps {
  notification: WatchlistNotification;
  onClick: () => void;
}

function NotificationItem({ notification, onClick }: NotificationItemProps) {
  const icon = getNotificationIcon(notification.type);
  const colorClass = getNotificationColor(notification.severity);
  const timeAgo = formatNotificationTime(notification.timestamp);

  return (
    <div
      onClick={onClick}
      className={`p-4 hover:bg-gray-800/50 cursor-pointer transition-colors border-l-2 ${colorClass}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg">{icon}</span>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-sm font-medium text-white truncate">
              {notification.title}
            </h4>
            <span className="text-xs text-gray-400 ml-2">
              {timeAgo}
            </span>
          </div>
          
          <p className="text-sm text-gray-300 mb-2">
            {notification.message}
          </p>
          
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>
              {notification.gain_percent >= 0 ? '+' : ''}{notification.gain_percent.toFixed(1)}%
            </span>
            <span>
              ${notification.current_price.toFixed(2)}
            </span>
            {notification.metadata.days_held && (
              <span>
                {notification.metadata.days_held}d held
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
