'use client';

import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import styles from '../styles/components.module.css';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const themes = [
    { value: 'light', icon: Sun, label: 'Light Mode' },
    { value: 'dark', icon: Moon, label: 'Dark Mode' },
    { value: 'system', icon: Monitor, label: 'System' },
  ] as const;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-xs)',
        background: 'var(--bg-tertiary)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--spacing-xs)',
        border: '1px solid var(--border-color)'
      }}
    >
      {themes.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={theme === value ? styles.buttonSmall : styles.buttonSecondary}
          style={{
            width: '36px',
            height: '36px',
            padding: '0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: theme === value ? 'var(--color-primary)' : 'transparent',
            color: theme === value ? 'white' : 'var(--text-secondary)',
            border: theme === value ? '1px solid var(--color-primary)' : '1px solid transparent',
            borderRadius: 'var(--radius-sm)',
            transition: 'all var(--transition-normal)'
          }}
          title={label}
          aria-label={label}
        >
          <Icon size={16} />
        </button>
      ))}
    </div>
  );
}
