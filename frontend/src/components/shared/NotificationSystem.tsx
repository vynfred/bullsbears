'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { X, Bell, AlertTriangle, TrendingUp, Zap } from 'lucide-react';

export interface Notification {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info' | 'signal';
  title: string;
  message: string;
  timestamp: Date;
  autoClose?: boolean;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationSystemProps {
  maxNotifications?: number;
  defaultDuration?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

const NotificationSystem: React.FC<NotificationSystemProps> = ({
  maxNotifications = 5,
  defaultDuration = 5000,
  position = 'top-right'
}) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      autoClose: notification.autoClose ?? true,
      duration: notification.duration ?? defaultDuration
    };

    setNotifications(prev => {
      const updated = [newNotification, ...prev];
      return updated.slice(0, maxNotifications);
    });

    // Auto-remove notification
    if (newNotification.autoClose) {
      setTimeout(() => {
        removeNotification(newNotification.id);
      }, newNotification.duration);
    }
  }, [maxNotifications, defaultDuration, removeNotification]);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  // Expose methods globally for use throughout the app
  useEffect(() => {
    (window as any).showNotification = addNotification;
    (window as any).clearNotifications = clearAll;
    
    return () => {
      delete (window as any).showNotification;
      delete (window as any).clearNotifications;
    };
  }, [addNotification, clearAll]);

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <TrendingUp className="w-5 h-5 text-[var(--text-primary)]" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-[var(--accent-yellow)]" />;
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-[var(--accent-red)]" />;
      case 'signal':
        return <Zap className="w-5 h-5 text-[var(--accent-cyan)] animate-pulse" />;
      default:
        return <Bell className="w-5 h-5 text-[var(--accent-cyan)]" />;
    }
  };

  const getNotificationStyles = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return 'border-[var(--text-primary)] bg-[var(--bg-tertiary)]';
      case 'warning':
        return 'border-[var(--accent-yellow)] bg-[var(--bg-secondary)]';
      case 'error':
        return 'border-[var(--accent-red)] bg-[var(--bg-secondary)]';
      case 'signal':
        return 'border-[var(--accent-cyan)] bg-[var(--bg-tertiary)] shadow-lg shadow-cyan-600/20';
      default:
        return 'border-[var(--border-color)] bg-[var(--bg-secondary)]';
    }
  };

  const getPositionStyles = () => {
    switch (position) {
      case 'top-left':
        return 'top-4 left-4';
      case 'bottom-right':
        return 'bottom-4 right-4';
      case 'bottom-left':
        return 'bottom-4 left-4';
      default:
        return 'top-4 right-4';
    }
  };

  if (notifications.length === 0) return null;

  return (
    <div className={`fixed ${getPositionStyles()} z-50 space-y-2 max-w-sm w-full`}>
      {notifications.map((notification, index) => (
        <div
          key={notification.id}
          className={`
            border rounded p-4 font-mono text-sm
            transform transition-all duration-300 ease-in-out
            ${getNotificationStyles(notification.type)}
            ${index === 0 ? 'scale-100 opacity-100' : 'scale-95 opacity-90'}
          `}
          style={{
            animation: `slideIn 0.3s ease-out ${index * 0.1}s both`
          }}
        >
          <div className="flex items-start gap-3">
            {getNotificationIcon(notification.type)}
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-bold text-[var(--text-primary)] uppercase text-xs">
                  {notification.title}
                </h4>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              
              <p className="text-[var(--text-secondary)] text-xs leading-relaxed">
                {notification.message}
              </p>
              
              {notification.action && (
                <button
                  onClick={notification.action.onClick}
                  className="mt-2 text-xs font-bold text-[var(--accent-cyan)] hover:text-[var(--text-primary)] underline uppercase"
                >
                  {notification.action.label}
                </button>
              )}
              
              <p className="text-[var(--text-muted)] text-xs mt-2">
                {notification.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
          
          {/* Progress bar for auto-close */}
          {notification.autoClose && (
            <div className="mt-2 h-1 bg-[var(--bg-primary)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--accent-cyan)] rounded-full"
                style={{
                  animation: `shrink ${notification.duration}ms linear`
                }}
              />
            </div>
          )}
        </div>
      ))}
      
      {notifications.length > 1 && (
        <button
          onClick={clearAll}
          className="w-full text-center text-xs font-mono text-[var(--text-muted)] hover:text-[var(--text-primary)] py-2 border border-[var(--border-color)] rounded bg-[var(--bg-secondary)] transition-colors"
        >
          CLEAR ALL ({notifications.length})
        </button>
      )}
      
      <style jsx>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        @keyframes shrink {
          from {
            width: 100%;
          }
          to {
            width: 0%;
          }
        }
      `}</style>
    </div>
  );
};

// Utility functions for easy notification creation
export const showNotification = (notification: Omit<Notification, 'id' | 'timestamp'>) => {
  if ((window as any).showNotification) {
    (window as any).showNotification(notification);
  }
};

export const showSuccessNotification = (title: string, message: string) => {
  showNotification({
    type: 'success',
    title,
    message
  });
};

export const showErrorNotification = (title: string, message: string) => {
  showNotification({
    type: 'error',
    title,
    message,
    autoClose: false
  });
};

export const showWarningNotification = (title: string, message: string) => {
  showNotification({
    type: 'warning',
    title,
    message
  });
};

export const showSignalNotification = (title: string, message: string, action?: { label: string; onClick: () => void }) => {
  showNotification({
    type: 'signal',
    title,
    message,
    action,
    autoClose: false
  });
};

export default NotificationSystem;
