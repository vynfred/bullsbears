# BullsBears.xyz AI Agent Prompt - Updated Nov 3, 2024

## 🎯 IMMEDIATE PRIORITIES (Post Pulse Stock Card Completion)

### Current Status: Pulse Stock Card Component ✅ COMPLETED
- **Pulse Stock Card Component**: ✅ COMPLETED with comprehensive design
- **Real-time Price Tracking**: ✅ COMPLETED with Polygon.io WebSocket integration (test mode)
- **AI Confidence Display**: ✅ COMPLETED with 82-feature system integration
- **Gut Check Modal**: ✅ COMPLETED with 5-second timer and anonymous IDs
- **Demo Environment**: ✅ COMPLETED at http://localhost:3001/pulse-demo

### Workflow Corrections Applied ✅ COMPLETED
- **Removed Gut Check Buttons**: From Pulse cards (gut check completed during screening)
- **Removed Streak References**: Multiple daily gut checks, no daily streaks
- **Added Moon/Rug Tabs**: Directional predictions with sorting options
- **Updated Confidence Display**: AI + Gut + Overall confidence breakdown
- **Real Ticker Display**: Show TSLA, NVDA (bias eliminated in screening process)

### Next Immediate Deliverables (Priority Order)

#### 1. Complete MVP Frontend Development ⚠️ NEXT PRIORITY
**Goal**: Build complete trading co-pilot experience with push notifications
**Timeline**: 2-3 days
**Components Needed**:
- [ ] **Push Notification System**: 8:30 AM alerts with WebSocket integration
- [ ] **Screening Process Interface**: Anonymous gut check workflow before Pulse
- [ ] **History Pulse System**: Win/loss tracking with 6-tier classification
- [ ] **Mobile-First PWA**: Touch-friendly interface with swipe gestures (left=BEARISH, right=BULLISH)

#### 2. Backend Automation System ⚠️ CRITICAL BACKEND
**Goal**: Automated scanning, outcome tracking, and data pipeline
**Timeline**: 2-3 days
**Components Needed**:
- [ ] **8:30 AM Celery Beat Schedule**: Pre-market pulse scanning
- [ ] **Target Range Prediction**: ML confidence intervals × volatility multiplier
- [ ] **Automated Outcome Tracking**: 3-day post-alert validation
- [ ] **WebSocket Infrastructure**: Real-time notifications and updates

## 🔄 CORRECTED WORKFLOW UNDERSTANDING

### Screening Process (Pre-Pulse)
1. **AI/ML Identification**: System identifies potential moon/rug candidates
2. **Anonymous Gut Check**: User votes on stocks with random IDs (#47291, #83756)
3. **Confidence Boosting**: Gut votes adjust AI confidence scores
4. **Qualification**: Only stocks completing this process appear on Pulse

### Pulse Page (Post-Screening)
1. **Completed Picks Display**: Show actual tickers (TSLA, NVDA) since bias eliminated
2. **Moon/Rug Tabs**: Directional predictions with sorting options
3. **No Gut Check Buttons**: Gut check already completed during screening
4. **Performance Tracking**: Real-time price updates and target progress
5. **Multiple Daily Cycles**: No daily streak concept, multiple gut checks per day

### Sorting Options for Pulse
- **Overall Confidence**: AI confidence + gut vote boost (default)
- **AI Confidence**: Pure AI/ML model confidence
- **Gut Vote**: BULLISH > BEARISH > PASS ranking
- **Actual Performance**: % change since identification

## 📱 TECHNICAL REQUIREMENTS

### Mobile-First UX Requirements
- **PWA-Ready**: Service worker, manifest, offline capability
- **Touch Optimization**: 44px minimum touch targets, swipe gestures (left=BEARISH, right=BULLISH)
- **Real-time Updates**: WebSocket connections for live price tracking
- **Push Notifications**: Browser notifications for 8:30 AM alerts

### Backend Integration Requirements
- **82-Feature AI System**: Connect to existing production models
- **Celery Scheduling**: 8:30 AM automated scans, 15-minute updates
- **PostgreSQL Schema**: history_pulse, gut_votes, target_predictions tables
- **Redis Caching**: AI features (5min), prices (30sec), alerts (5min)

## 🎯 SUCCESS CRITERIA

### MVP Trading Co-Pilot Experience
- ⚠️ **8:30 AM Push Notifications**: "MOON PULSE: 3 stocks ready"
- ⚠️ **Anonymous Screening**: 5-second gut check with random IDs
- ⚠️ **Real-time Pulse**: Moon/Rug tabs with sorting and live prices
- ⚠️ **Target Tracking**: ML-based price ranges with estimated days
- ⚠️ **History System**: 6-tier classification (MOON/PARTIAL/WIN/MISS/RUG/NUCLEAR)

### Technical Performance Targets
- **API Response**: <200ms average, <500ms for AI analysis
- **Real-time Updates**: 15-minute price intervals, instant notifications
- **Database Queries**: <50ms average query time
- **WebSocket Latency**: <100ms for real-time updates

## 📋 IMMEDIATE ACTION ITEMS

1. **Build Screening Interface**: Anonymous gut check workflow with 5-second timer
2. **Implement Push Notifications**: WebSocket server and browser notification API
3. **Create History System**: Win/loss tracking with 6-tier classification
4. **Add Celery Scheduling**: 8:30 AM automated scans and 15-minute updates
5. **Connect Real AI System**: Switch from test data to 82-feature production models

**Target**: Complete MVP trading co-pilot experience within 1 week