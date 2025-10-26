# BullsBears Design System

A comprehensive CSS modules-based design system for the BullsBears stock analyzer application, featuring hard right angles, consistent table alignment, and proper stock price change color coding.

## Overview

This design system provides:
- **CSS Modules** for component isolation and consistency
- **Hard right angles** (minimal border radius) for a clean, professional look
- **Proper color coding** for stock price changes (green for gains, red for losses)
- **Aligned tables** with consistent spacing and typography
- **Mobile-first responsive design**
- **Accessibility-focused** components

## File Structure

```
src/styles/
├── components.module.css    # Reusable component styles
├── layout.module.css        # Layout and page structure styles
├── utilities.module.css     # Utility classes for spacing, typography, etc.
└── README.md               # This documentation
```

## Usage

### Importing Styles

```typescript
import styles from '../styles/components.module.css';
import layoutStyles from '../styles/layout.module.css';
import utilStyles from '../styles/utilities.module.css';
import { cn } from '../lib/styles';
```

### Basic Components

#### Cards
```tsx
<div className={styles.card}>
  <div className={styles.cardHeader}>
    <h2 className={styles.cardTitle}>Card Title</h2>
  </div>
  <div className={styles.cardContent}>
    Card content goes here
  </div>
</div>
```

#### Buttons
```tsx
<button className={styles.button}>Primary Button</button>
<button className={styles.buttonSecondary}>Secondary Button</button>
<button className={cn(styles.button, styles.buttonSmall)}>Small Button</button>
```

#### Tables with Proper Alignment
```tsx
<table className={styles.table}>
  <thead className={styles.tableHeader}>
    <tr>
      <th className={styles.tableHeaderCell}>Symbol</th>
      <th className={cn(styles.tableHeaderCell, styles.tableCellNumeric)}>Price</th>
    </tr>
  </thead>
  <tbody>
    <tr className={styles.tableRow}>
      <td className={styles.tableCell}>AAPL</td>
      <td className={cn(styles.tableCell, styles.tableCellNumeric)}>$175.50</td>
    </tr>
  </tbody>
</table>
```

### Stock Price Change Colors

The design system includes specialized classes for stock price changes:

```tsx
import { priceChangeUtils } from '../lib/styles';

// Automatic color coding based on value
<span className={priceChangeUtils.getChangeModuleClass(changeValue, styles)}>
  {priceChangeUtils.formatPercentChange(changeValue)}
</span>

// Manual color classes
<span className={styles.priceChangePositive}>+2.35%</span>
<span className={styles.priceChangeNegative}>-1.85%</span>
<span className={styles.priceChangeNeutral}>0.00%</span>
```

### Utility Classes

Use utility classes for common styling needs:

```tsx
// Spacing
<div className={cn(utilStyles.pLg, utilStyles.mbMd)}>Content</div>

// Typography
<h1 className={cn(utilStyles.text2xl, utilStyles.fontBold)}>Title</h1>

// Layout
<div className={cn(utilStyles.flex, utilStyles.itemsCenter, utilStyles.gapMd)}>
  <span>Item 1</span>
  <span>Item 2</span>
</div>
```

## Design Principles

### 1. Hard Right Angles
- All components use minimal border radius (`--radius-sm: 2px` or `--radius-none: 0px`)
- Creates a clean, professional appearance
- Consistent with financial application aesthetics

### 2. Stock Price Color Coding
- **Green (`--color-gain`)**: Positive price changes, gains
- **Red (`--color-loss`)**: Negative price changes, losses  
- **Gray (`--color-neutral`)**: No change, neutral states
- Automatic `+` prefix for positive values
- Consistent across all components

### 3. Table Alignment
- **Left align**: Text content (symbols, company names)
- **Right align**: Numeric data (prices, changes, volumes)
- **Center align**: Status indicators, badges
- Consistent padding and spacing
- Tabular numbers for numeric columns

### 4. Mobile-First Responsive
- Touch-friendly button sizes (min 44px height)
- Horizontal scrolling for tables on mobile
- Responsive grid layouts
- Optimized font sizes for small screens

## CSS Variables

The design system uses CSS custom properties for theming:

```css
:root {
  /* Colors */
  --color-gain: #00FF41;        /* Neon Green */
  --color-loss: #FF073A;        /* Red */
  --color-neutral: #808080;     /* Gray */
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  
  /* Border Radius - Hard Angles */
  --radius-none: 0px;
  --radius-sm: 2px;
  --radius-md: 4px;
  
  /* Typography */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
}
```

## Helper Functions

### Class Name Utility
```typescript
import { cn } from '../lib/styles';

// Combines classes, filters out falsy values
const className = cn(
  styles.button,
  isActive && styles.buttonActive,
  isDisabled && styles.buttonDisabled
);
```

### Price Change Utilities
```typescript
import { priceChangeUtils } from '../lib/styles';

// Format with automatic sign
priceChangeUtils.formatChange(2.35);        // "+2.35"
priceChangeUtils.formatPercentChange(-1.5); // "-1.50%"

// Get appropriate CSS class
priceChangeUtils.getChangeModuleClass(value, styles);
```

### Number Formatting
```typescript
import { numberUtils } from '../lib/styles';

numberUtils.formatCurrency(175.50);      // "$175.50"
numberUtils.formatLargeNumber(1500000);  // "1.5M"
numberUtils.formatWithCommas(1234567);   // "1,234,567"
```

## Best Practices

1. **Always use CSS modules** instead of global classes for components
2. **Combine utility classes** with component classes using `cn()`
3. **Use semantic HTML** with appropriate ARIA labels
4. **Test on mobile devices** to ensure touch targets are adequate
5. **Maintain consistent spacing** using the design system variables
6. **Follow color coding rules** for financial data display

## Migration Guide

When updating existing components:

1. Import the CSS modules and utility functions
2. Replace global classes with module classes
3. Update color coding to use the new price change utilities
4. Ensure tables use proper alignment classes
5. Test responsive behavior on mobile devices

## Future Enhancements

- Dark mode theme variables
- Animation utilities
- Form validation styling
- Chart component styles
- Print-specific styles
