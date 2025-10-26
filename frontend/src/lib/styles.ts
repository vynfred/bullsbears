/**
 * BullsBears Design System - Style Utilities
 * 
 * This file provides utilities for working with CSS modules and consistent styling
 * across the BullsBears application.
 */

/**
 * Combines multiple CSS class names, filtering out falsy values
 * Similar to the popular 'clsx' library but lightweight
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * Price change formatting utilities
 */
export const priceChangeUtils = {
  /**
   * Formats a price change value with appropriate sign and color class
   */
  formatChange: (value: number, includeSign: boolean = true): string => {
    if (value === 0) return '0.00';
    const formatted = Math.abs(value).toFixed(2);
    return includeSign ? (value > 0 ? `+${formatted}` : `-${formatted}`) : formatted;
  },

  /**
   * Formats a percentage change with appropriate sign and % symbol
   */
  formatPercentChange: (value: number, includeSign: boolean = true): string => {
    if (value === 0) return '0.00%';
    const formatted = Math.abs(value).toFixed(2);
    const sign = includeSign ? (value > 0 ? '+' : '-') : '';
    return `${sign}${formatted}%`;
  },

  /**
   * Gets the appropriate CSS class for price change styling
   */
  getChangeClass: (value: number): string => {
    if (value > 0) return 'price-change-positive';
    if (value < 0) return 'price-change-negative';
    return 'price-change-neutral';
  },

  /**
   * Gets the appropriate CSS module class for price change styling
   */
  getChangeModuleClass: (value: number, styles: Record<string, string>): string => {
    if (value > 0) return styles.priceChangePositive || '';
    if (value < 0) return styles.priceChangeNegative || '';
    return styles.priceChangeNeutral || '';
  }
};

/**
 * Number formatting utilities for financial data
 */
export const numberUtils = {
  /**
   * Formats a number as currency (USD)
   */
  formatCurrency: (value: number, decimals: number = 2): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  },

  /**
   * Formats a large number with appropriate suffixes (K, M, B)
   */
  formatLargeNumber: (value: number): string => {
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
    return value.toString();
  },

  /**
   * Formats a number with commas as thousands separators
   */
  formatWithCommas: (value: number): string => {
    return new Intl.NumberFormat('en-US').format(value);
  },

  /**
   * Formats a percentage value
   */
  formatPercentage: (value: number, decimals: number = 2): string => {
    return `${value.toFixed(decimals)}%`;
  }
};

/**
 * Date formatting utilities
 */
export const dateUtils = {
  /**
   * Formats a date for display in tables and cards
   */
  formatDate: (date: string | Date): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(d);
  },

  /**
   * Formats a date and time for timestamps
   */
  formatDateTime: (date: string | Date): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(d);
  },

  /**
   * Formats a relative time (e.g., "2 hours ago")
   */
  formatRelativeTime: (date: string | Date): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - d.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    
    return dateUtils.formatDate(d);
  }
};

/**
 * Responsive breakpoint utilities
 */
export const breakpoints = {
  sm: '480px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

/**
 * Common CSS module class combinations
 */
export const commonClasses = {
  /**
   * Standard card styling
   */
  card: (styles: Record<string, string>) => styles.card || 'clean-panel',

  /**
   * Primary button styling
   */
  buttonPrimary: (styles: Record<string, string>) => styles.button || 'clean-button',

  /**
   * Secondary button styling
   */
  buttonSecondary: (styles: Record<string, string>) => styles.buttonSecondary || 'clean-button-secondary',

  /**
   * Input field styling
   */
  input: (styles: Record<string, string>) => styles.input || 'clean-input',

  /**
   * Table styling
   */
  table: (styles: Record<string, string>) => styles.table || 'clean-table',

  /**
   * Loading state styling
   */
  loading: (styles: Record<string, string>) => cn(styles.loading, styles.flex, styles.itemsCenter, styles.justifyCenter),
};

/**
 * Theme-aware styling utilities
 */
export const themeUtils = {
  /**
   * Gets appropriate icon color based on theme
   */
  getIconColor: (isDark: boolean): string => {
    return isDark ? 'var(--text-primary)' : 'var(--text-primary)';
  },

  /**
   * Gets appropriate border color based on theme
   */
  getBorderColor: (isDark: boolean): string => {
    return isDark ? 'var(--border-color)' : 'var(--border-color)';
  },
};

/**
 * Animation utilities
 */
export const animations = {
  /**
   * Fade in animation
   */
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.2 }
  },

  /**
   * Slide up animation
   */
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.3 }
  },

  /**
   * Scale animation
   */
  scale: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    transition: { duration: 0.2 }
  }
};

/**
 * Validation utilities for form styling
 */
export const validationUtils = {
  /**
   * Gets appropriate input styling based on validation state
   */
  getInputClass: (
    isValid: boolean | null,
    styles: Record<string, string>
  ): string => {
    const baseClass = styles.input || 'clean-input';
    if (isValid === null) return baseClass;
    if (isValid) return cn(baseClass, styles.inputValid);
    return cn(baseClass, styles.inputInvalid);
  },

  /**
   * Gets appropriate message styling based on validation state
   */
  getMessageClass: (
    isValid: boolean,
    styles: Record<string, string>
  ): string => {
    return isValid ? styles.messageSuccess : styles.messageError;
  }
};
