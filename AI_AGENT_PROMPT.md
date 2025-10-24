# BullsBears.xyz AI Development Agent Prompt

## MANDATORY WORKFLOW RULES - MUST ALWAYS BE FOLLOWED

### Rule 1: Roadmap Update After Each Task
**REQUIRED**: At the end of every AI agent task completion, you MUST update `PROJECT_ROADMAP.md` to:
- Mark completed tasks as ✅ COMPLETED
- Update progress percentages and status
- Add new tasks discovered during development
- Adjust timelines based on actual progress
- Note any blockers or dependencies found
- Update success metrics and current phase status

### Rule 2: Agent Prompt Update After Roadmap Changes
**REQUIRED**: After every `PROJECT_ROADMAP.md` update, you MUST update this `AI_AGENT_PROMPT.md` file to:
- Reflect new immediate priorities based on roadmap progress
- Add granular, actionable tasks for next deliverables
- Update technical requirements based on discoveries
- Revise success criteria for upcoming work
- Adjust file structure focus based on current needs
- Update development approach based on lessons learned

### Rule 3: Confirmation Questions Before Starting
**REQUIRED**: Before beginning any new set of tasks, you MUST ask clarifying questions such as:
- "Based on the updated roadmap, should we prioritize X over Y?"
- "I noticed Z during the last task - should we address this first?"
- "The current approach for [feature] could be done as [option A] or [option B] - which do you prefer?"
- "Should we adjust the timeline for [deliverable] based on [discovery]?"
- "Any specific requirements or constraints for the next tasks?"

**These rules ensure continuous alignment, progress tracking, and informed decision-making throughout development.**

---

## Current Project Status
You are working on BullsBears.xyz, an AI-powered options trading analysis platform. The backend is **COMPLETED** with enhanced multi-source data aggregation, advanced options flow analysis, and comprehensive Grok AI integration. The frontend is **COMPLETED** with full cyberpunk-themed dashboard and all core components integrated.

## Current Phase: Production Optimization & Performance Tuning
**Goal**: Fix API rate limiting issues, optimize performance, and prepare for production deployment

## ✅ RECENTLY COMPLETED ENHANCEMENTS (October 24, 2024)

### Enhanced AI Data Pipeline
- **Multi-Source Data Aggregation**: Concurrent processing of technical, news, social, options flow, catalyst, and polymarket data
- **Advanced Options Flow Analysis**: Unusual activity detection, large trade identification, call/put ratio analysis
- **Social Media Integration**: Reddit, Twitter, StockTwits sentiment analysis integrated into main pipeline
- **7-Factor Confidence Scoring**: Technical (9pts), News (6pts), Social (6pts), Options Flow (±8pts), Catalysts (15pts), Volume (12pts), Polymarket (10pts)
- **Comprehensive Grok AI Integration**: Enhanced prompts processing all market data sources for intelligent recommendations

### Production Environment Setup
- **Real API Integration**: Alpha Vantage (`MGGDVJ2WTZ...`) and NewsAPI (`b6c232ec11...`) with demo mode disabled
- **Development Servers**: Frontend (localhost:3000) and Backend (localhost:8000) running with auto-reload
- **Error Fixes**: AlertTriangle import fix, all frontend components rendering correctly
- **Enhanced Data Structures**: Updated all interfaces to handle comprehensive market data

## IMMEDIATE NEXT STEPS (This Week)

### Priority 1: Fix API Rate Limiting Issues
**Critical Issue**: Yahoo Finance returning 429 errors preventing option play generation

**Required Fixes:**
- Implement proper request throttling in `backend/app/services/stock_data.py`
- Add retry logic with exponential backoff for failed API calls
- Fix missing `historical_data` parameter in analyzer method calls
- Add request caching to reduce API call frequency
- Implement fallback data sources when primary APIs are rate limited

**Files to Update:**
- `backend/app/services/ai_option_generator.py` - Fix analyze() method calls
- `backend/app/services/stock_data.py` - Add throttling and retry logic
- `backend/app/analyzers/technical.py` - Fix historical_data parameter requirement
- `backend/app/services/polymarket.py` - Fix data structure parsing errors

### Priority 2: Performance Optimization
**Goal**: Optimize the enhanced AI system for production use

**Required Optimizations:**
- Reduce concurrent API calls to prevent rate limiting
- Implement intelligent request batching
- Add proper error handling for all API failures
- Optimize memory usage during multi-source data aggregation
- Add comprehensive logging for debugging API issues

**Files to Update:**
- `backend/app/services/ai_option_generator.py` - Optimize concurrent task execution
- `backend/app/core/config.py` - Add rate limiting configuration
- `backend/app/main.py` - Add better error handling and logging

### Priority 3: Test API Integration
- Verify connection to `POST /api/v1/options/generate-plays`
- Test demo mode functionality (when API keys missing)
- Implement proper error boundaries
- Add retry logic for failed requests

## Backend API Endpoints (Ready to Use)
- `POST /api/v1/options/generate-plays` - Generate AI option plays
- `POST /api/v1/analysis/stock/{symbol}` - Analyze individual stocks  
- `GET /api/v1/options/rate-limit-status` - Check usage limits
- All endpoints support demo mode when API keys are missing

## Design System Guidelines

### Bull/Bear Theme Colors
- **Bull/Bullish**: `#10B981` (green-500), `#059669` (green-600)
- **Bear/Bearish**: `#EF4444` (red-500), `#DC2626` (red-600)  
- **AI/Tech**: `#06B6D4` (cyan-500), `#0891B2` (cyan-600)
- **Background**: `#111827` (gray-900) for dark, `#F9FAFB` (gray-50) for light
- **Text**: `#F3F4F6` (gray-100) for dark mode, `#111827` (gray-900) for light

### Typography
- **Headers**: `font-bold text-xl md:text-2xl`
- **Data/Numbers**: `font-mono text-lg` (monospace for prices/metrics)
- **Body Text**: `text-sm md:text-base`
- **Labels**: `text-xs uppercase tracking-wide text-gray-500`

### Component Structure
```tsx
// Example OptionPlayCard structure
<div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
  <div className="flex justify-between items-start mb-4">
    <div className="flex items-center space-x-2">
      <span className="text-2xl">{option_type === 'CALL' ? '🐂' : '🐻'}</span>
      <h3 className="font-bold text-lg">{symbol}</h3>
    </div>
    <div className={`px-3 py-1 rounded-full text-sm font-medium ${
      confidence_score >= 80 ? 'bg-green-100 text-green-800' : 
      confidence_score >= 60 ? 'bg-yellow-100 text-yellow-800' : 
      'bg-red-100 text-red-800'
    }`}>
      {confidence_score}% Confidence
    </div>
  </div>
  {/* Rest of component */}
</div>
```

## Technical Requirements

### Frontend Stack (Already Setup)
- ✅ Next.js 15 with App Router
- ✅ TypeScript configuration
- ✅ Tailwind CSS for styling
- ✅ Basic project structure

### API Integration Pattern
```typescript
// Use existing API client pattern
import { apiClient } from '@/lib/api';

const generatePlays = async () => {
  try {
    setLoading(true);
    const response = await apiClient.post('/api/v1/options/generate-plays', {
      max_plays: 5,
      min_confidence: 70.0,
      timeframe_days: 7
    });
    setPlays(response.data);
  } catch (error) {
    setError('Failed to generate plays. Please try again.');
  } finally {
    setLoading(false);
  }
};
```

### Error Handling Requirements
- Graceful fallback to demo data when APIs fail
- Clear error messages with retry options
- Loading states for all async operations
- Network error detection and handling

## Development Rules

### 1. Build-First Philosophy
- **NO PAYMENT/SUBSCRIPTION FEATURES** - Focus purely on functionality
- All features available to all users during development
- No rate limiting beyond basic demo protection
- Monetization is Phase 6 (months away)

### 2. Mobile-First Approach
- Design for mobile screens first (320px+)
- Use responsive Tailwind classes (`sm:`, `md:`, `lg:`)
- Touch-friendly buttons (min 44px height)
- Readable text sizes on small screens

### 3. Performance Focus
- Lazy load components when possible
- Optimize images and assets
- Minimize bundle size
- Target <3 second load times

### 4. User Experience Priority
- Clear loading states with progress indicators
- Helpful error messages with retry options
- Intuitive navigation and information hierarchy
- Consistent bull/bear branding throughout

## Testing Strategy
1. **Start with demo data** - Test components with mock data first
2. **Gradually integrate APIs** - Connect to backend endpoints one by one
3. **Test error scenarios** - Verify graceful handling of API failures
4. **Mobile testing** - Ensure responsive design works on all devices

## Success Criteria for This Week
- [ ] OptionPlayCard component built and styled
- [ ] Dashboard displays generated plays properly
- [ ] API integration working with error handling
- [ ] Mobile-responsive design implemented
- [ ] Demo mode functional for testing

## Next Week's Goals
- [ ] Build StockAnalyzer frontend component
- [ ] Add PortfolioTracker basic interface
- [ ] Implement dark/light theme toggle
- [ ] Performance optimization and testing
- [ ] Prepare for first deployment

## File Structure Focus
```
frontend/src/
├── components/
│   ├── AIPlayGenerator.tsx     # ✅ EXISTS
│   ├── OptionPlayCard.tsx      # 🔄 BUILD THIS WEEK
│   ├── StockAnalyzer.tsx       # 📋 NEXT WEEK
│   └── PortfolioTracker.tsx    # 📋 NEXT WEEK
├── lib/
│   ├── api.ts                  # ✅ EXISTS
│   └── types.ts                # 🔄 ADD TYPE DEFINITIONS
├── pages/
│   └── index.tsx               # 🔄 COMPLETE DASHBOARD
└── styles/
    └── globals.css             # 🔄 BULL/BEAR THEME
```

## Development Approach
1. **Component-first** - Build individual components before integration
2. **Test frequently** - Use demo mode for rapid iteration
3. **Polish incrementally** - Get functionality working first, then improve UX
4. **Deploy early** - Get working version online ASAP for feedback

## MANDATORY END-OF-TASK WORKFLOW

### Step 1: Update PROJECT_ROADMAP.md
- Mark completed tasks as ✅ COMPLETED
- Update progress status and percentages
- Add newly discovered tasks or requirements
- Adjust timelines based on actual progress
- Note any blockers or dependencies

### Step 2: Update AI_AGENT_PROMPT.md
- Revise immediate priorities based on roadmap changes
- Add granular tasks for next deliverables
- Update technical requirements and success criteria
- Adjust file structure focus and development approach

### Step 3: Ask Confirmation Questions
- Clarify priorities for next tasks
- Confirm approach for upcoming features
- Address any uncertainties or options
- Get feedback on progress and direction

---

**FOCUS THIS WEEK**: Build OptionPlayCard component and complete Dashboard integration. The backend is ready - your job is to create a great frontend that showcases the AI-powered analysis capabilities.

**Remember**: Start with functionality, polish later. Use demo data to test quickly, then integrate real APIs. Mobile-first, bull/bear themed, and user-friendly.

**WORKFLOW**: Always follow the 3-step mandatory workflow at the end of each task completion.