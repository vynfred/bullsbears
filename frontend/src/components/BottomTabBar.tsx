'use client';

import React from 'react';
import { Rocket, Brain, Trophy, TrendingUp, Star } from 'lucide-react';

export type TabType = 'pulse' | 'watchlist' | 'analytics';

interface BottomTabBarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export function BottomTabBar({ activeTab, onTabChange }: BottomTabBarProps) {
  const tabs = [
    {
      id: 'pulse' as TabType,
      label: 'Picks',
      icon: Rocket,
      color: 'blue'
    },
    {
      id: 'watchlist' as TabType,
      label: 'Watchlist',
      icon: Star,
      color: 'yellow'
    },
    {
      id: 'analytics' as TabType,
      label: 'Analytics',
      icon: Trophy,
      color: 'green'
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
      
      return `${baseStyles} ${colorMap[tab.color as keyof typeof colorMap]} border-b-2 bg-gray-700/50 shadow-lg`;
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
    
    return `shadow-lg ${glowMap[tab.color as keyof typeof glowMap]}`;
  };

  return (
    <div
      className="fixed bottom-0 left-0 right-0 border-t z-50"
      style={{
        backgroundColor: 'var(--bg-primary)', // Use dark background for contrast
        borderColor: 'var(--border-color)',
        boxShadow: 'var(--shadow-lg)'
      }}
    >
      <div className="flex">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className="flex-1 flex flex-col items-center justify-center gap-1 py-3 px-2 text-xs font-medium transition-all duration-200 relative border-b-2"
              style={{
                color: isActive ? 'var(--color-primary)' : 'var(--text-primary)', // Use primary text color for visibility
                borderBottomColor: isActive ? 'var(--color-primary)' : 'transparent',
                backgroundColor: isActive ? 'rgba(119, 228, 200, 0.1)' : 'transparent' // Subtle active background
              }}
            >
              <div className="relative">
                <Icon className="w-5 h-5" />


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
