'use client';

import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const themes = [
    { value: 'light', icon: Sun, label: 'Light' },
    { value: 'dark', icon: Moon, label: 'Dark' },
    { value: 'system', icon: Monitor, label: 'System' },
  ] as const;

  return (
    <div className="flex items-center space-x-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg p-1">
      {themes.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`
            flex items-center justify-center w-8 h-8 rounded-md transition-colors
            ${theme === value 
              ? 'bg-white dark:bg-neutral-700 shadow-sm' 
              : 'hover:bg-neutral-200 dark:hover:bg-neutral-700'
            }
          `}
          title={label}
        >
          <Icon className="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
        </button>
      ))}
    </div>
  );
}
