'use client';

import React from 'react';
import { Rocket, Brain, Trophy, TrendingUp, Star } from 'lucide-react';

export type TabType = 'pulse' | 'gutcheck' | 'performance' | 'trends' | 'watchlist';

interface BottomTabBarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  gutCheckBadgeCount?: number;
}

export function BottomTabBar({ activeTab, onTabChange, gutCheckBadgeCount = 0 }: BottomTabBarProps) {
  const tabs = [
    {
      id: 'pulse' as TabType,
      label: 'Pulse',
      icon: Rocket,
      color: 'blue'
    },
    {
      id: 'gutcheck' as TabType,
      label: 'Gut Check',
      icon: Brain,
      color: 'orange',
      badge: gutCheckBadgeCount
    },
    {
      id: 'performance' as TabType,
      label: 'Performance',
      icon: Trophy,
      color: 'green'
    },
    {
      id: 'trends' as TabType,
      label: 'Trends',
      icon: TrendingUp,
      color: 'purple'
    },
    {
      id: 'watchlist' as TabType,
      label: 'Watchlist',
      icon: Star,
      color: 'yellow'
    }
  ];

  const getTabStyles = (tab: typeof tabs[0], isActive: boolean) => {
    const baseStyles = "flex-1 flex flex-col items-center justify-center gap-1 py-3 px-2 text-xs font-medium transition-all duration-200 relative";
    
    if (isActive) {
      const colorMap = {
        blue: 'text-cyan-400 border-cyan-400',
        orange: 'text-orange-400 border-orange-400',
        green: 'text-green-400 border-green-400',
        purple: 'text-purple-400 border-purple-400',
        yellow: 'text-yellow-400 border-yellow-400'
      };
      
      return `${baseStyles} ${colorMap[tab.color]} border-b-2 bg-gray-700/50 shadow-lg`;
    }
    
    return `${baseStyles} text-gray-400 border-transparent border-b-2 hover:text-gray-300 hover:border-gray-600`;
  };

  const getGlowEffect = (tab: typeof tabs[0], isActive: boolean) => {
    if (!isActive) return '';
    
    const glowMap = {
      blue: 'shadow-cyan-400/50',
      orange: 'shadow-orange-400/50',
      green: 'shadow-green-400/50',
      purple: 'shadow-purple-400/50',
      yellow: 'shadow-yellow-400/50'
    };
    
    return `shadow-lg ${glowMap[tab.color]}`;
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-700 z-50" style={{ backgroundColor: '#111827' }}>
      <div className="flex">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 px-2 text-xs font-medium transition-all duration-200 relative ${
                isActive
                  ? 'text-white border-b-2 border-cyan-400'
                  : 'text-gray-400 border-b-2 border-transparent hover:text-gray-300'
              }`}
            >
              <div className="relative">
                <Icon className="w-5 h-5" />

                {/* Red Badge for Gut Check */}
                {tab.id === 'gutcheck' && tab.badge && tab.badge > 0 && (
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></div>
                )}
              </div>

              <span className="truncate max-w-full">
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Safe area padding for iOS */}
      <div className="h-safe-area-inset-bottom" style={{ backgroundColor: '#111827' }} />
    </div>
  );
}
