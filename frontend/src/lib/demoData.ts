// Demo data for MVP Trading Co-Pilot
// This will be replaced with live data via a single switch

export interface BullishAlert {
  id: string;
  randomId: number; // Anonymous ID for gut check
  ticker: string; // Actual stock ticker (TSLA, NVDA, etc.)
  companyName: string; // Company name for display
  confidence: number; // AI/ML confidence percentage
  topReason: string; // Primary reason for the alert
  targetRange: {
    low: number; // Low target percentage
    avg: number; // Average target percentage
    high: number; // High target percentage
    estimatedDays: number; // Days to hit target
  };
  entryPrice: number; // Entry price
  currentPrice?: number; // Current price (for live tracking)
  timestamp: Date;
  gutVote?: 'BULLISH' | 'BEARISH' | 'PASS'; // User's gut vote
  finalConfidence?: number; // After gut vote boost
  isNew?: boolean; // For notification badges
  userStreak?: number; // User's current streak
  type: 'bullish' | 'bearish'; // Alert type
  daysToTarget: number; // Days to target
  direction?: 'LONG' | 'SHORT'; // Position direction
  sparklineData?: number[]; // Mini price history for sparkline
  status?: 'active' | 'completed' | 'expired'; // Alert status
}

// Legacy alias for backward compatibility
export type MoonAlert = BullishAlert;

export interface HistoryEntry {
  id: string;
  randomId?: number; // Anonymous ID for display
  ticker: string; // Actual stock ticker
  companyName: string; // Company name
  callTime: Date;
  aiConfidence: number;
  gutVote: 'BULLISH' | 'BEARISH' | 'PASS';
  targetPct: number;
  actualPct: number;
  maxGain: number; // Maximum gain during window
  daysToPeak: number; // Days to reach peak (renamed from timeToPeak)
  daysToHit: number;
  classification: 'MOON' | 'PARTIAL_MOON' | 'WIN' | 'MISS' | 'RUG' | 'NUCLEAR_RUG';
  postMoonRug: boolean; // Did it crash after hitting moon?
  entryPrice: number;
  currentPrice: number; // Current price for live tracking
  exitPrice: number;
  finalConfidence: number;
}

// Demo bullish alerts for 8:30 AM pulse
export const demoBullishAlerts: BullishAlert[] = [
  {
    id: '1',
    randomId: 47291,
    ticker: 'TSLA',
    companyName: 'Tesla Inc',
    confidence: 89,
    topReason: 'Volume surge +31%',
    targetRange: {
      low: 18,
      avg: 23,
      high: 31,
      estimatedDays: 2
    },
    entryPrice: 247.80,
    currentPrice: 298.40,
    timestamp: new Date('2024-11-04T08:30:00'), // Today
    isNew: true,
    type: 'bullish',
    daysToTarget: 2,
    userStreak: 5,
    gutVote: 'BULLISH',
    finalConfidence: 94,
  },
  {
    id: '2',
    randomId: 83756,
    ticker: 'NVDA',
    companyName: 'NVIDIA Corp',
    confidence: 82,
    topReason: 'Grok AI technical +24%',
    targetRange: {
      low: 16,
      avg: 21,
      high: 28,
      estimatedDays: 3
    },
    entryPrice: 89.25,
    currentPrice: 95.40,
    timestamp: new Date('2024-11-03T08:30:00'), // 1 day old
    isNew: true,
    type: 'bullish',
    daysToTarget: 3,
    gutVote: 'BULLISH',
    finalConfidence: 87,
  },
  {
    id: '2b',
    randomId: 12345,
    ticker: 'AMZN',
    companyName: 'Amazon.com Inc',
    confidence: 75,
    topReason: 'Historical pattern match',
    targetRange: {
      low: 15,
      avg: 20,
      high: 28,
      estimatedDays: 2
    },
    entryPrice: 145.20,
    currentPrice: 162.80, // +12.1% gain
    timestamp: new Date('2024-10-25T08:30:00'), // 10 days old - should go to Performance
    isNew: false,
    type: 'bullish',
    daysToTarget: 2,
    gutVote: 'BULLISH',
    finalConfidence: 80,
  },
  {
    id: '3',
    randomId: 19384,
    ticker: 'AAPL',
    companyName: 'Apple Inc',
    confidence: 74,
    topReason: 'RSI oversold +16%',
    targetRange: {
      low: 15,
      avg: 20,
      high: 26,
      estimatedDays: 2
    },
    entryPrice: 234.75,
    currentPrice: 234.75,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: true,
    type: 'bullish',
    daysToTarget: 2,
    gutVote: 'BULLISH',
    finalConfidence: 74,
  },
  {
    id: '4',
    randomId: 62947,
    ticker: 'AMD',
    companyName: 'Advanced Micro Devices',
    confidence: 71,
    topReason: 'DeepSeek sentiment +19%',
    targetRange: {
      low: 14,
      avg: 19,
      high: 25,
      estimatedDays: 3
    },
    entryPrice: 67.80,
    currentPrice: 67.80,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: true,
    type: 'bullish',
    daysToTarget: 3,
    gutVote: 'BULLISH',
    finalConfidence: 71,
  },
  {
    id: '5',
    randomId: 51628,
    ticker: 'MSFT',
    companyName: 'Microsoft Corp',
    confidence: 68,
    topReason: 'Options flow +22%',
    targetRange: {
      low: 13,
      avg: 18,
      high: 24,
      estimatedDays: 2
    },
    entryPrice: 156.90,
    currentPrice: 156.90,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: true,
    type: 'bullish',
    daysToTarget: 2,
    gutVote: 'BULLISH',
    finalConfidence: 68,
  },
  {
    id: '6',
    randomId: 73492,
    ticker: 'GOOGL',
    companyName: 'Alphabet Inc',
    confidence: 65,
    topReason: 'Earnings whisper +17%',
    targetRange: {
      low: 12,
      avg: 17,
      high: 23,
      estimatedDays: 4
    },
    entryPrice: 98.45,
    currentPrice: 98.45,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: false,
    type: 'bullish',
    daysToTarget: 4,
    gutVote: 'BULLISH',
    finalConfidence: 65,
  },
  {
    id: '7',
    randomId: 38571,
    ticker: 'META',
    companyName: 'Meta Platforms',
    confidence: 62,
    topReason: 'Social buzz +15%',
    targetRange: {
      low: 11,
      avg: 16,
      high: 22,
      estimatedDays: 3
    },
    entryPrice: 203.20,
    currentPrice: 203.20,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: false,
    type: 'bullish',
    daysToTarget: 3,
    gutVote: 'BULLISH',
    finalConfidence: 62,
  },
  {
    id: '8',
    randomId: 94736,
    ticker: 'AMZN',
    companyName: 'Amazon.com Inc',
    confidence: 59,
    topReason: 'Momentum breakout +13%',
    targetRange: {
      low: 10,
      avg: 15,
      high: 21,
      estimatedDays: 2
    },
    entryPrice: 45.60,
    currentPrice: 45.60,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: false,
    type: 'bullish',
    daysToTarget: 2,
    gutVote: 'BULLISH',
    finalConfidence: 59,
  }
];

// Demo bearish alerts for bearish predictions
export const demoBearishAlerts: BullishAlert[] = [
  {
    id: 'r1',
    randomId: 73829,
    ticker: 'HOOD',
    companyName: 'Robinhood Markets Inc',
    confidence: 78,
    topReason: 'Overbought RSI +70, negative sentiment',
    targetRange: {
      low: -18,
      avg: -23,
      high: -31,
      estimatedDays: 2
    },
    entryPrice: 24.80,
    currentPrice: 19.20, // -22.6% drop
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: true,
    type: 'bearish',
    daysToTarget: 2,
    gutVote: 'BEARISH',
    finalConfidence: 83,
  },
  {
    id: 'r2',
    randomId: 58394,
    ticker: 'COIN',
    companyName: 'Coinbase Global Inc',
    confidence: 71,
    topReason: 'Volume decline, bearish news flow',
    targetRange: {
      low: -15,
      avg: -20,
      high: -28,
      estimatedDays: 3
    },
    entryPrice: 89.50,
    currentPrice: 89.50,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: true,
    type: 'bearish',
    daysToTarget: 3,
    gutVote: 'BEARISH',
    finalConfidence: 76,
  },
  {
    id: 'r3',
    randomId: 41627,
    ticker: 'PLTR',
    companyName: 'Palantir Technologies Inc',
    confidence: 65,
    topReason: 'Technical breakdown, weak momentum',
    targetRange: {
      low: -12,
      avg: -18,
      high: -25,
      estimatedDays: 2
    },
    entryPrice: 45.30,
    currentPrice: 45.30,
    timestamp: new Date('2024-11-03T08:30:00'),
    isNew: true,
    type: 'bearish',
    daysToTarget: 2,
    gutVote: 'PASS',
    finalConfidence: 65,
  }
];

// Legacy aliases for backward compatibility
export const demoMoonAlerts = demoBullishAlerts;
export const demoRugAlerts = demoBearishAlerts;

// Combined alerts for demo
export const demoAllAlerts: BullishAlert[] = [...demoBullishAlerts, ...demoBearishAlerts];

// Demo history data showing various outcomes
export const demoHistoryEntries: HistoryEntry[] = [
  {
    id: 'h1',
    randomId: 47291,
    ticker: 'NVDA',
    companyName: 'NVIDIA Corp',
    callTime: new Date('2024-10-31T08:30:00'),
    aiConfidence: 87,
    gutVote: 'BULLISH',
    targetPct: 20,
    actualPct: 35,
    maxGain: 38,
    daysToPeak: 2,
    daysToHit: 2,
    classification: 'MOON',
    postMoonRug: false,
    entryPrice: 125.40,
    currentPrice: 169.29,
    exitPrice: 169.29,
    finalConfidence: 92, // Boosted by gut vote
  },
  {
    id: 'h2',
    randomId: 83756,
    ticker: 'TSLA',
    companyName: 'Tesla Inc',
    callTime: new Date('2024-10-30T08:30:00'),
    aiConfidence: 76,
    gutVote: 'BEARISH',
    targetPct: 20,
    actualPct: 19,
    maxGain: 22,
    daysToPeak: 1,
    daysToHit: 3,
    classification: 'PARTIAL_MOON',
    postMoonRug: true, // Hit 22% then crashed
    entryPrice: 89.75,
    currentPrice: 106.80,
    exitPrice: 106.80,
    finalConfidence: 71, // Reduced by gut vote disagreement
  },
  {
    id: 'h3',
    randomId: 92847,
    ticker: 'AAPL',
    companyName: 'Apple Inc',
    callTime: new Date('2024-10-29T08:30:00'),
    aiConfidence: 82,
    gutVote: 'BULLISH',
    targetPct: 20,
    actualPct: 8,
    maxGain: 12,
    daysToPeak: 1,
    daysToHit: 0,
    classification: 'WIN',
    postMoonRug: false,
    entryPrice: 156.20,
    currentPrice: 168.70,
    exitPrice: 168.70,
    finalConfidence: 87,
  },
  {
    id: 'h4',
    randomId: 15639,
    ticker: 'AMD',
    companyName: 'Advanced Micro Devices',
    callTime: new Date('2024-10-28T08:30:00'),
    aiConfidence: 69,
    gutVote: 'PASS',
    targetPct: 20,
    actualPct: -5,
    maxGain: 3,
    daysToPeak: 0,
    daysToHit: 0,
    classification: 'MISS',
    postMoonRug: false,
    entryPrice: 78.90,
    currentPrice: 74.96,
    exitPrice: 74.96,
    finalConfidence: 69, // No gut vote boost
  },
  {
    id: 'h5',
    ticker: 'META',
    companyName: 'Meta Platforms',
    callTime: new Date('2024-10-27T08:30:00'),
    aiConfidence: 71,
    gutVote: 'BULLISH',
    targetPct: 20,
    actualPct: -22,
    maxGain: -2,
    daysToPeak: 0,
    daysToHit: 0,
    classification: 'RUG',
    postMoonRug: false,
    entryPrice: 134.50,
    currentPrice: 104.91,
    exitPrice: 104.91,
    finalConfidence: 76,
  },
  {
    id: 'h6',
    ticker: 'GOOGL',
    companyName: 'Alphabet Inc',
    callTime: new Date('2024-10-26T08:30:00'),
    aiConfidence: 85,
    gutVote: 'BEARISH',
    targetPct: 20,
    actualPct: -45,
    maxGain: -8,
    daysToPeak: 0,
    daysToHit: 0,
    classification: 'NUCLEAR_RUG',
    postMoonRug: false,
    entryPrice: 198.75,
    currentPrice: 109.31,
    exitPrice: 109.31,
    finalConfidence: 80, // Gut vote was right to disagree
  }
];

// Global vs Personal Performance Stats
export const demoGlobalStats = {
  globalGutWinRate: 78, // Global community gut accuracy
  aiAccuracy: 71, // AI-only accuracy
  totalUsers: 12847, // Total users in community
  totalVotes: 89234, // Total gut votes cast
};

export const demoPersonalStats = {
  yourGutAccuracy: 83, // User's personal gut accuracy
  yourAiCombined: 89, // User + AI combined accuracy
  totalVotes: 24, // User's total votes
  currentStreak: 5, // Current winning streak
  bestStreak: 8, // Best streak ever
  beatsGlobal: true, // User beats global average
  winRate: {
    moon: 42, // % of calls that hit MOON
    partialMoon: 25, // % that hit PARTIAL_MOON
    win: 17, // % that hit WIN (directional)
    miss: 12, // % that were MISS
    rug: 4, // % that were RUG
  }
};

// Accuracy Trend Data - Track accuracy over time for charting
export interface AccuracyTrendPoint {
  date: Date;
  gutAccuracy: number; // User's gut accuracy at this point
  aiAccuracy: number; // AI accuracy at this point
  combinedAccuracy: number; // Combined accuracy
  totalVotes: number; // Cumulative votes at this point
  trendDirection: 'UP' | 'DOWN' | 'FLAT'; // Trending direction
  confidenceLevel: 'HIGH' | 'MEDIUM' | 'LOW'; // Based on sample size
}

// Demo accuracy trend data - 30 days of accuracy tracking
export const demoAccuracyTrend: AccuracyTrendPoint[] = [
  {
    date: new Date('2024-10-04'),
    gutAccuracy: 75,
    aiAccuracy: 68,
    combinedAccuracy: 82,
    totalVotes: 5,
    trendDirection: 'FLAT',
    confidenceLevel: 'LOW'
  },
  {
    date: new Date('2024-10-07'),
    gutAccuracy: 71,
    aiAccuracy: 69,
    combinedAccuracy: 79,
    totalVotes: 7,
    trendDirection: 'DOWN',
    confidenceLevel: 'LOW'
  },
  {
    date: new Date('2024-10-10'),
    gutAccuracy: 78,
    aiAccuracy: 70,
    combinedAccuracy: 84,
    totalVotes: 9,
    trendDirection: 'UP',
    confidenceLevel: 'MEDIUM'
  },
  {
    date: new Date('2024-10-13'),
    gutAccuracy: 82,
    aiAccuracy: 71,
    combinedAccuracy: 87,
    totalVotes: 11,
    trendDirection: 'UP',
    confidenceLevel: 'MEDIUM'
  },
  {
    date: new Date('2024-10-16'),
    gutAccuracy: 79,
    aiAccuracy: 70,
    combinedAccuracy: 85,
    totalVotes: 14,
    trendDirection: 'DOWN',
    confidenceLevel: 'MEDIUM'
  },
  {
    date: new Date('2024-10-19'),
    gutAccuracy: 85,
    aiAccuracy: 72,
    combinedAccuracy: 89,
    totalVotes: 16,
    trendDirection: 'UP',
    confidenceLevel: 'MEDIUM'
  },
  {
    date: new Date('2024-10-22'),
    gutAccuracy: 88,
    aiAccuracy: 71,
    combinedAccuracy: 91,
    totalVotes: 18,
    trendDirection: 'UP',
    confidenceLevel: 'HIGH'
  },
  {
    date: new Date('2024-10-25'),
    gutAccuracy: 84,
    aiAccuracy: 70,
    combinedAccuracy: 88,
    totalVotes: 20,
    trendDirection: 'DOWN',
    confidenceLevel: 'HIGH'
  },
  {
    date: new Date('2024-10-28'),
    gutAccuracy: 86,
    aiAccuracy: 71,
    combinedAccuracy: 90,
    totalVotes: 22,
    trendDirection: 'UP',
    confidenceLevel: 'HIGH'
  },
  {
    date: new Date('2024-11-01'),
    gutAccuracy: 83,
    aiAccuracy: 71,
    combinedAccuracy: 89,
    totalVotes: 24,
    trendDirection: 'DOWN',
    confidenceLevel: 'HIGH'
  }
];

// Helper function to get current trend direction
export const getCurrentTrend = (): 'UP' | 'DOWN' | 'FLAT' => {
  if (demoAccuracyTrend.length < 2) return 'FLAT';
  const latest = demoAccuracyTrend[demoAccuracyTrend.length - 1];
  return latest.trendDirection;
};

// Helper function to get trend streak (how many consecutive periods trending in same direction)
export const getTrendStreak = (): number => {
  if (demoAccuracyTrend.length < 2) return 0;

  const currentDirection = getCurrentTrend();
  let streak = 1;

  for (let i = demoAccuracyTrend.length - 2; i >= 0; i--) {
    if (demoAccuracyTrend[i].trendDirection === currentDirection) {
      streak++;
    } else {
      break;
    }
  }

  return streak;
};

// User's Personal Pulse - Only stocks they've gut-voted on
export interface PersonalPulseEntry {
  id: string;
  anonymousId: string; // e.g., "#X9K2"
  ticker: string; // For internal tracking (not shown in pulse)
  companyName: string; // For internal tracking
  gutVote: 'BULLISH' | 'BEARISH' | 'PASS';
  voteTime: Date;
  confidence: number; // Final confidence after gut boost
  entryPrice: number;
  currentPrice: number;
  percentChange: number;
  daysElapsed: number;
  classification: 'MOON' | 'PARTIAL_MOON' | 'WIN' | 'MISS' | 'RUG' | 'NUCLEAR_RUG' | 'WATCH';
  isStale: boolean; // Older than 24h with no new vote
  estimatedDaysToMoon?: number; // For WATCH status
}

// Demo personal pulse - user's gut-voted stocks (7-day leaderboard)
export const demoPersonalPulse: PersonalPulseEntry[] = [
  {
    id: 'p1',
    anonymousId: '#X9K2',
    ticker: 'NVDA',
    companyName: 'NVIDIA Corp',
    gutVote: 'BULLISH',
    voteTime: new Date('2024-11-01T08:35:00'),
    confidence: 93,
    entryPrice: 125.40,
    currentPrice: 155.67,
    percentChange: 24.1,
    daysElapsed: 2,
    classification: 'MOON',
    isStale: false,
  },
  {
    id: 'p2',
    anonymousId: '#M8J3',
    ticker: 'TSLA',
    companyName: 'Tesla Inc',
    gutVote: 'BULLISH',
    voteTime: new Date('2024-11-02T08:35:00'),
    confidence: 87,
    entryPrice: 89.75,
    currentPrice: 106.53,
    percentChange: 18.7,
    daysElapsed: 1,
    classification: 'MOON',
    isStale: false,
  },
  {
    id: 'p3',
    anonymousId: '#P1M9',
    ticker: 'AAPL',
    companyName: 'Apple Inc',
    gutVote: 'BULLISH',
    voteTime: new Date('2024-10-31T08:35:00'),
    confidence: 74,
    entryPrice: 156.20,
    currentPrice: 174.94,
    percentChange: 12.0,
    daysElapsed: 3,
    classification: 'PARTIAL_MOON',
    isStale: false,
  },
  {
    id: 'p4',
    anonymousId: '#K4N1',
    ticker: 'AMD',
    companyName: 'Advanced Micro Devices',
    gutVote: 'PASS',
    voteTime: new Date('2024-10-30T08:35:00'),
    confidence: 58,
    entryPrice: 78.90,
    currentPrice: 74.16,
    percentChange: -6.0,
    daysElapsed: 4,
    classification: 'WATCH',
    isStale: true, // Older than 24h
    estimatedDaysToMoon: 2,
  },
  {
    id: 'p5',
    anonymousId: '#R7Q4',
    ticker: 'META',
    companyName: 'Meta Platforms',
    gutVote: 'BEARISH',
    voteTime: new Date('2024-10-29T08:35:00'),
    confidence: 76,
    entryPrice: 134.50,
    currentPrice: 104.91,
    percentChange: -22.0,
    daysElapsed: 5,
    classification: 'RUG',
    isStale: true,
  }
];

// Helper function to check if user has voted today
export const hasVotedToday = (): boolean => {
  const today = new Date().toDateString();
  return demoPersonalPulse.some(entry =>
    entry.voteTime.toDateString() === today
  );
};

// Helper function to get fresh vs stale entries
export const getFreshEntries = (): PersonalPulseEntry[] => {
  return demoPersonalPulse.filter(entry => !entry.isStale);
};

export const getStaleEntries = (): PersonalPulseEntry[] => {
  return demoPersonalPulse.filter(entry => entry.isStale);
};

// Switch for demo vs live data
export const USE_DEMO_DATA = false; // Set to false for live data

// Helper functions
export const getRandomNumericId = (): number => {
  return Math.floor(Math.random() * 90000) + 10000; // 5-digit random number
};

export const formatConfidence = (confidence: number): string => {
  return `${confidence}%`;
};

export const formatTargetRange = (range: MoonAlert['targetRange']): string => {
  return `${range.low}-${range.high}% in ${range.estimatedDays}d`;
};

export const getClassificationColor = (classification: HistoryEntry['classification']): string => {
  switch (classification) {
    case 'MOON': return 'text-green-600 bg-green-100';
    case 'PARTIAL_MOON': return 'text-green-500 bg-green-50';
    case 'WIN': return 'text-blue-600 bg-blue-100';
    case 'MISS': return 'text-gray-600 bg-gray-100';
    case 'RUG': return 'text-red-600 bg-red-100';
    case 'NUCLEAR_RUG': return 'text-red-800 bg-red-200';
    default: return 'text-gray-600 bg-gray-100';
  }
};
