# BullsBears Live Data Integration Mapping 🔌

## Overview
This document maps frontend components to backend APIs and data structures for live data integration.

## 📊 **PICKS TAB** → Backend Integration

### Data Source: `/api/v1/bullish_alerts` & `/api/v1/bearish_alerts`

#### Frontend Hook: `useLivePicks()`
```typescript
// Usage in PicksTab.tsx
const { picks, bullishPicks, bearishPicks, isLoading, refresh } = useLivePicks({
  bullishLimit: 25,
  bearishLimit: 25,
  minConfidence: 0.48, // 48% threshold
  refreshInterval: 5 * 60 * 1000 // 5 minutes
});
```

#### Backend Response → Frontend Transformation:
```typescript
BullishAlertResponse {
  id: number                    → LivePick.id (string)
  symbol: string               → LivePick.symbol
  company_name?: string        → LivePick.name
  confidence: number           → LivePick.confidence (×100 for percentage)
  reasons: string[]            → LivePick.reasoning (first reason)
  technical_score: number      → Used in aiSummary
  sentiment_score: number      → Used in aiSummary
  social_score: number         → Used in aiSummary
  earnings_score: number       → Used in aiSummary
  timestamp: string            → LivePick.timestamp
  target_timeframe: string     → Used for target calculations
  risk_factors: string[]       → Used in aiSummary
  alert_outcome?: string       → LivePick.targetHit
  actual_move_percent?: number → LivePick.change
  days_to_move?: number        → LivePick.timeToTargetHours (×24)
}
```

#### Key Features:
- **Real-time Updates**: Auto-refresh every 5 minutes
- **Confidence Filtering**: Only show picks >48% confidence
- **Sorting**: By confidence desc, then timestamp desc
- **Sentiment Detection**: Bullish vs Bearish classification
- **Target Calculations**: Dynamic price targets based on confidence

---

## 👁️ **WATCHLIST TAB** → Backend Integration

### Data Source: `/api/v1/watchlist`

#### Frontend Hook: `useLiveWatchlist()`
```typescript
// Usage in WatchlistTab.tsx
const { 
  stocks, 
  isLoading, 
  addStock, 
  updateStock, 
  removeStock, 
  totalGainLoss,
  winnersCount 
} = useLiveWatchlist({
  refreshInterval: 5 * 60 * 1000 // 5 minutes
});
```

#### Backend Response → Frontend Transformation:
```typescript
WatchlistEntryResponse {
  id: number                      → LiveWatchlistStock.id (string)
  symbol: string                  → LiveWatchlistStock.symbol
  company_name?: string           → LiveWatchlistStock.name
  entry_price: number             → LiveWatchlistStock.addedAt
  target_price: number            → LiveWatchlistStock.targetPrice
  stop_loss_price?: number        → LiveWatchlistStock.stopLoss
  current_price?: number          → LiveWatchlistStock.currentPrice
  current_return_percent?: number → LiveWatchlistStock.changePercent
  current_return_dollars?: number → LiveWatchlistStock.changeSince
  ai_confidence_score: number     → LiveWatchlistStock.aiConfidence (×100)
  ai_recommendation: string       → LiveWatchlistStock.aiRecommendation
  status: string                  → LiveWatchlistStock.status
  is_winner?: boolean             → LiveWatchlistStock.isWinner
  days_held: number               → LiveWatchlistStock.daysHeld
  entry_date: string              → LiveWatchlistStock.entryDate
}
```

#### CRUD Operations:
- **GET** `/api/v1/watchlist/` → Fetch all entries
- **POST** `/api/v1/watchlist/add` → Add new stock
- **PUT** `/api/v1/watchlist/:id` → Update entry (editable prices)
- **DELETE** `/api/v1/watchlist/:id` → Remove stock

#### Key Features:
- **Editable Prices**: Users can edit "added at" price inline
- **Performance Tracking**: Real-time P&L calculations
- **Chart Data**: 30-day performance history for line charts
- **Notes System**: AI recommendations and user notes

---

## 📈 **ANALYTICS TAB** → Backend Integration

### Data Sources: Multiple Analytics Endpoints

#### Current Implementation:
- **Accuracy Chart**: Uses `demoAccuracyTrend` mock data
- **Recent Picks**: Uses `demoHistoryEntries` mock data
- **Performance Metrics**: Calculated from mock data

#### Required Backend Endpoints:
```typescript
// New endpoints needed:
GET /api/v1/analytics/accuracy?days=90    → AccuracyOverTime[]
GET /api/v1/analytics/recent-picks?days=7 → RecentPicksWithOutcomes[]
GET /api/v1/analytics/performance-summary → PerformanceSummary
```

#### Data Structures Needed:
```typescript
interface AccuracyOverTime {
  date: string;
  accuracy: number;
  total_picks: number;
  correct_picks: number;
}

interface RecentPicksWithOutcomes {
  symbol: string;
  sentiment: 'bullish' | 'bearish';
  confidence: number;
  outcome: 'WIN' | 'LOSS' | 'PENDING';
  actual_move_percent: number;
  days_to_outcome: number;
  target_hit: 'low' | 'mid' | 'high' | null;
}

interface PerformanceSummary {
  total_picks: number;
  win_rate: number;
  avg_confidence: number;
  best_streak: number;
  current_streak: number;
}
```

---

## 🔄 **DATA FLOW ARCHITECTURE**

### 1. **Frontend State Management**
```
Component → Hook → API Client → Backend
    ↓         ↓         ↓          ↓
  UI State → Cache → HTTP → Database
```

### 2. **Error Handling Strategy**
- **Graceful Degradation**: Fall back to mock data if APIs fail
- **Loading States**: Show spinners during data fetching
- **Error Messages**: User-friendly error notifications
- **Retry Logic**: Automatic retry with exponential backoff

### 3. **Caching Strategy**
- **Frontend**: React state + localStorage for persistence
- **Backend**: Redis caching (5-minute TTL for live data)
- **API Client**: Axios interceptors for request/response caching

### 4. **Real-time Updates**
- **Polling**: 5-minute intervals for picks and watchlist
- **Manual Refresh**: Pull-to-refresh functionality
- **Background Updates**: Service worker for offline support

---

## 🚀 **IMPLEMENTATION CHECKLIST**

### Phase 1: Core Integration ✅
- [x] Create `useLivePicks` hook
- [x] Create `useLiveWatchlist` hook  
- [x] Update API client with new endpoints
- [x] Remove legacy components
- [x] Update PROJECT_ROADMAP.md

### Phase 2: Component Integration 🚧
- [ ] Update PicksTab to use `useLivePicks`
- [ ] Update WatchlistTab to use `useLiveWatchlist`
- [ ] Add loading states and error handling
- [ ] Test CRUD operations for watchlist

### Phase 3: Analytics Integration 📊
- [ ] Create analytics endpoints in backend
- [ ] Create `useLiveAnalytics` hook
- [ ] Update AnalyticsTab with live data
- [ ] Add performance tracking

### Phase 4: Testing & Polish 🧪
- [ ] End-to-end testing with live backend
- [ ] Performance optimization
- [ ] Error handling refinement
- [ ] User experience polish

---

## 🔧 **DEVELOPMENT NOTES**

### Environment Setup:
```bash
# Backend (Terminal 1)
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)  
cd frontend && npm run dev

# Test API Connection
curl http://localhost:8000/api/v1/bullish_alerts/
```

### Key Configuration:
- **API Base URL**: `http://127.0.0.1:8000`
- **Timeout**: 120 seconds (for AI generation)
- **Refresh Interval**: 5 minutes
- **Confidence Threshold**: 48%
- **Cache TTL**: 5 minutes

### Testing Strategy:
1. **Mock Data First**: Ensure UI works with mock data
2. **API Integration**: Connect to live backend gradually
3. **Error Scenarios**: Test network failures and API errors
4. **Performance**: Monitor loading times and memory usage
5. **User Experience**: Test on mobile and desktop

---

## 📱 **MOBILE-FIRST CONSIDERATIONS**

- **Touch Interactions**: Swipe to refresh, tap to expand
- **Loading States**: Skeleton screens for better UX
- **Offline Support**: Cache data for offline viewing
- **Performance**: Lazy loading and virtualization
- **Responsive Design**: Optimized for 320px+ screens

This mapping ensures seamless integration between the polished frontend and the production-ready backend system.
