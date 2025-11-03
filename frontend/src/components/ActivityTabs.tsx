'use client';

import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar, Newspaper, Filter, RefreshCw, ExternalLink, Zap } from 'lucide-react';
import { api, UnusualOptionsActivity, UnusualOptionContract, LargeOptionTrade } from '../lib/api';
import { cn, priceChangeUtils, numberUtils, dateUtils } from '../lib/styles';
import styles from '../styles/components.module.css';
import layoutStyles from '../styles/layout.module.css';
import utilStyles from '../styles/utilities.module.css';

type ActivityTab = 'trending' | 'earnings' | 'news' | 'unusual-options';

interface TrendingStock {
  symbol: string;
  company_name: string;
  current_price: number;
  price_change: number;
  price_change_percent: number;
  volume: number;
  analysis_count: number;
  sentiment_score: number;
  recommendation: string;
}

interface EarningsEvent {
  symbol: string;
  company_name: string;
  earnings_date: string;
  estimated_eps: number;
  actual_eps?: number;
  surprise_percent?: number;
  market_cap: number;
  last_quarter_eps?: number;
  last_quarter_surprise?: number;
  ai_sentiment?: string;
  ai_summary?: string;
  sector: string;
  time: 'BMO' | 'AMC' | 'TBD'; // Before Market Open, After Market Close, To Be Determined
  has_analysis?: boolean; // Whether analysis exists for this stock
  analysis_age_minutes?: number; // How old the analysis is in minutes
}

interface NewsItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  published_at: string;
  sentiment_score: number;
  related_symbols: string[];
  url: string;
}

interface ActivityTabsProps {
  onNavigateToAnalyzer?: (symbol: string, companyName: string) => void;
}

export default function ActivityTabs({ onNavigateToAnalyzer }: ActivityTabsProps = {}) {
  const [activeTab, setActiveTab] = useState<ActivityTab>('trending');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [trendingStocks, setTrendingStocks] = useState<TrendingStock[]>([]);
  const [earningsEvents, setEarningsEvents] = useState<EarningsEvent[]>([]);
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [unusualOptionsData, setUnusualOptionsData] = useState<UnusualOptionsActivity | null>(null);

  // Filter states
  const [newsFilter, setNewsFilter] = useState<'all' | 'portfolio'>('all');

  const tabs = [
    { id: 'trending' as ActivityTab, name: 'Trending Stocks', icon: TrendingUp },
    { id: 'earnings' as ActivityTab, name: 'Earnings', icon: Calendar },
    { id: 'news' as ActivityTab, name: 'News', icon: Newspaper },
    { id: 'unusual-options' as ActivityTab, name: 'Unusual Options', icon: Zap },
  ];

  const fetchTrendingStocks = async () => {
    try {
      // Skip API call for now - use mock data directly
      // const response = await fetch('http://localhost:8000/api/v1/recommendations/trending?limit=20&time_range=24h');
      // if (!response.ok) throw new Error('Failed to fetch trending stocks');

      // const data = await response.json();
      // if (data.success) {
      //   setTrendingStocks(data.data.trending_stocks || []);
      // } else {
      //   // Fallback to mock data if API returns no data
      //   setTrendingStocks(getMockTrendingStocks());
      // }

      // Use mock data directly (backend not running)
      setTrendingStocks(getMockTrendingStocks());
    } catch (err) {
      console.error('Error fetching trending stocks:', err);
      // Use mock data as fallback
      setTrendingStocks(getMockTrendingStocks());
      setError('Backend API temporarily unavailable - showing demo data');
    }
  };

  const fetchEarningsCalendar = async () => {
    try {
      // Skip API call for now - use mock data directly
      // const response = await fetch('http://localhost:8000/api/v1/earnings/calendar?days_ahead=7&include_analysis_status=true');

      // if (!response.ok) {
      //   throw new Error(`Failed to fetch earnings calendar: ${response.statusText}`);
      // }

      // const data = await response.json();

      // Transform backend data to match frontend interface
      const transformedEarnings: EarningsEvent[] = data.events.map((event: any) => ({
        symbol: event.symbol,
        company_name: event.company_name,
        earnings_date: event.earnings_date,
        estimated_eps: event.estimated_eps || 0,
        actual_eps: event.actual_eps,
        surprise_percent: event.surprise_percent,
        market_cap: event.market_cap || 1000000000,
        last_quarter_eps: event.last_quarter_eps,
        last_quarter_surprise: event.last_quarter_surprise,
        ai_sentiment: event.ai_sentiment,
        ai_summary: event.ai_summary,
        sector: event.sector,
        time: event.time,
        has_analysis: event.has_analysis,
        analysis_age_minutes: event.analysis_age_minutes
      }));

      // setEarningsEvents(transformedEarnings);

      // If no real data available, fall back to mock data
      // if (transformedEarnings.length === 0) {
      //   await fetchMockEarningsData();
      // }

      // Use mock data directly (backend not running)
      await fetchMockEarningsData();

    } catch (err) {
      console.error('Error fetching earnings calendar:', err);
      // Fall back to mock data on error
      await fetchMockEarningsData();
    }
  };

  const fetchMockEarningsData = async () => {
    try {
      // Helper function to get next market days
      const getNextMarketDays = () => {
        const days = [];
        const today = new Date();
        let currentDate = new Date(today);

        while (days.length < 7) {
          const dayOfWeek = currentDate.getDay();
          // Skip weekends (0 = Sunday, 6 = Saturday)
          if (dayOfWeek !== 0 && dayOfWeek !== 6) {
            days.push(new Date(currentDate));
          }
          currentDate.setDate(currentDate.getDate() + 1);
        }
        return days;
      };

      const marketDays = getNextMarketDays();
      const mockEarnings: EarningsEvent[] = [
        // Day 1
        {
          symbol: 'AAPL',
          company_name: 'Apple Inc.',
          earnings_date: marketDays[0].toISOString(),
          estimated_eps: 2.10,
          last_quarter_eps: 1.95,
          last_quarter_surprise: 7.7,
          market_cap: 3000000000000,
          sector: 'Technology',
          time: 'AMC',
          ai_sentiment: 'Bullish',
          ai_summary: 'Strong iPhone 15 sales and services growth expected. AI integration narrative driving optimism.'
        },
        {
          symbol: 'MSFT',
          company_name: 'Microsoft Corporation',
          earnings_date: marketDays[0].toISOString(),
          estimated_eps: 2.78,
          last_quarter_eps: 2.69,
          last_quarter_surprise: 3.3,
          market_cap: 2800000000000,
          sector: 'Technology',
          time: 'AMC',
          ai_sentiment: 'Bullish',
          ai_summary: 'Azure cloud growth and AI Copilot adoption driving revenue. Strong enterprise demand expected.'
        },
        // Day 2
        {
          symbol: 'GOOGL',
          company_name: 'Alphabet Inc.',
          earnings_date: marketDays[1].toISOString(),
          estimated_eps: 1.45,
          last_quarter_eps: 1.55,
          last_quarter_surprise: -6.5,
          market_cap: 1700000000000,
          sector: 'Technology',
          time: 'AMC',
          ai_sentiment: 'Neutral',
          ai_summary: 'Ad revenue recovery uncertain. Cloud growth positive but competitive pressure from AI costs.'
        },
        // Day 3
        {
          symbol: 'TSLA',
          company_name: 'Tesla Inc.',
          earnings_date: marketDays[2].toISOString(),
          estimated_eps: 0.85,
          last_quarter_eps: 0.91,
          last_quarter_surprise: -6.6,
          market_cap: 800000000000,
          sector: 'Consumer Discretionary',
          time: 'AMC',
          ai_sentiment: 'Bearish',
          ai_summary: 'Delivery concerns and margin pressure from price cuts. Cybertruck ramp uncertainty.'
        },
        {
          symbol: 'NFLX',
          company_name: 'Netflix Inc.',
          earnings_date: marketDays[2].toISOString(),
          estimated_eps: 2.15,
          last_quarter_eps: 3.73,
          last_quarter_surprise: 15.2,
          market_cap: 180000000000,
          sector: 'Communication Services',
          time: 'AMC',
          ai_sentiment: 'Bullish',
          ai_summary: 'Password sharing crackdown boosting subscribers. Ad-tier growth accelerating globally.'
        },
        // Day 4
        {
          symbol: 'NVDA',
          company_name: 'NVIDIA Corporation',
          earnings_date: marketDays[3].toISOString(),
          estimated_eps: 5.15,
          last_quarter_eps: 4.02,
          last_quarter_surprise: 28.1,
          market_cap: 1800000000000,
          sector: 'Technology',
          time: 'AMC',
          ai_sentiment: 'Bullish',
          ai_summary: 'AI chip demand remains robust. Data center revenue expected to exceed guidance significantly.'
        },
        // Day 5
        {
          symbol: 'META',
          company_name: 'Meta Platforms Inc.',
          earnings_date: marketDays[4].toISOString(),
          estimated_eps: 3.85,
          last_quarter_eps: 4.39,
          last_quarter_surprise: 12.5,
          market_cap: 850000000000,
          sector: 'Communication Services',
          time: 'AMC',
          ai_sentiment: 'Neutral',
          ai_summary: 'Reality Labs losses concerning investors. Ad recovery solid but metaverse spending high.'
        },
        // Day 6
        {
          symbol: 'AMZN',
          company_name: 'Amazon.com Inc.',
          earnings_date: marketDays[5].toISOString(),
          estimated_eps: 0.75,
          last_quarter_eps: 0.94,
          last_quarter_surprise: 25.3,
          market_cap: 1500000000000,
          sector: 'Consumer Discretionary',
          time: 'AMC',
          ai_sentiment: 'Bullish',
          ai_summary: 'AWS growth stabilizing. Prime Day and holiday season driving retail momentum.'
        },
        // Day 7
        {
          symbol: 'JPM',
          company_name: 'JPMorgan Chase & Co.',
          earnings_date: marketDays[6].toISOString(),
          estimated_eps: 4.15,
          last_quarter_eps: 4.32,
          last_quarter_surprise: 4.1,
          market_cap: 450000000000,
          sector: 'Financial Services',
          time: 'BMO',
          ai_sentiment: 'Neutral',
          ai_summary: 'Net interest income under pressure. Credit quality remains stable but provisions may increase.'
        }
      ];
      setEarningsEvents(mockEarnings);
    } catch (err) {
      console.error('Error fetching mock earnings data:', err);
      setError('Failed to load earnings calendar');
    }
  };

  const fetchNews = async () => {
    try {
      // TODO: Implement news aggregation endpoint
      // For now, using mock data
      const mockNews: NewsItem[] = [
        {
          id: '1',
          title: 'Tech Stocks Rally on AI Optimism',
          summary: 'Major technology companies see significant gains as investors remain bullish on artificial intelligence developments...',
          source: 'MarketWatch',
          published_at: '2024-01-23T14:30:00Z',
          sentiment_score: 0.8,
          related_symbols: ['NVDA', 'MSFT', 'GOOGL'],
          url: 'https://example.com/news/1',
        },
        {
          id: '2',
          title: 'Federal Reserve Signals Potential Rate Cuts',
          summary: 'Fed officials hint at possible interest rate reductions in upcoming meetings, boosting market sentiment...',
          source: 'Reuters',
          published_at: '2024-01-23T12:15:00Z',
          sentiment_score: 0.6,
          related_symbols: ['SPY', 'QQQ'],
          url: 'https://example.com/news/2',
        },
      ];
      setNewsItems(mockNews);
    } catch (err) {
      console.error('Error fetching news:', err);
      setError('Failed to load news');
    }
  };

  const fetchUnusualOptions = async () => {
    try {
      // Skip API call for now - use mock data directly
      // const data = await api.getUnusualOptionsActivity(50, 2.0, 10000, '1d');
      // setUnusualOptionsData(data);

      // Use mock data directly (backend not running)
      setUnusualOptionsData({
        success: true,
        data: {
          timestamp: new Date().toISOString(),
          time_range: '1d',
          filter_criteria: {
            min_volume_ratio: 2.0,
            min_premium: 10000,
            symbols_analyzed: 24
          },
          ai_summary: {
            summary: "Elevated options activity detected in tech sector with unusual call volume in NVDA and TSLA. Large premium flows suggest institutional positioning ahead of earnings.",
            key_trends: [
              "Tech sector showing 3x normal call volume",
              "NVDA unusual activity: 15.2x volume/OI ratio",
              "Large premium flows: $2.3M in TSLA calls"
            ],
            market_sentiment: "BULLISH",
            confidence: 0.85,
            last_updated: new Date().toISOString()
          },
          unusual_options: [],
          large_trades: [],
          sector_activity: {},
          market_metrics: {
            total_unusual_contracts: 47,
            total_large_trades: 12,
            total_premium_flow: 5420000,
            call_put_ratio: 2.3
          }
        },
        disclaimer: "Demo data - unusual options analysis for educational purposes only."
      });
    }
  };

  const refreshData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      switch (activeTab) {
        case 'trending':
          await fetchTrendingStocks();
          break;
        case 'earnings':
          await fetchEarningsCalendar();
          break;
        case 'news':
          await fetchNews();
          break;
        case 'unusual-options':
          await fetchUnusualOptions();
          break;
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, [activeTab]);

  // Auto-refresh for unusual options every 3 minutes
  useEffect(() => {
    if (activeTab === 'unusual-options') {
      const interval = setInterval(() => {
        fetchUnusualOptions();
      }, 3 * 60 * 1000); // 3 minutes

      return () => clearInterval(interval);
    }
  }, [activeTab]);

  // Use design system utilities instead of custom formatters
  const formatPrice = (price: number | undefined | null) => {
    if (price == null || isNaN(price)) return '$--';
    return numberUtils.formatCurrency(price);
  };

  const formatPercent = (percent: number | undefined | null) => {
    if (percent == null || isNaN(percent)) return '--';
    return priceChangeUtils.formatPercentChange(percent);
  };

  const formatVolume = (volume: number | undefined | null) => {
    if (volume == null || isNaN(volume)) return '--';
    return numberUtils.formatLargeNumber(volume);
  };

  const formatMarketCap = (marketCap: number | undefined | null) => {
    if (marketCap == null || isNaN(marketCap)) return '$--';
    return numberUtils.formatCurrency(marketCap, 1);
  };

  const getSentimentColor = (score: number | undefined | null) => {
    if (score == null || isNaN(score)) return utilStyles.textSecondary;
    if (score >= 0.6) return utilStyles.textGain;
    if (score >= 0.4) return utilStyles.textNeutral;
    return utilStyles.textLoss;
  };

  const getChangeColor = (change: number | undefined | null) => {
    if (change == null || isNaN(change)) return utilStyles.textSecondary;
    return priceChangeUtils.getChangeModuleClass(change, utilStyles);
  };

  const getMockTrendingStocks = (): TrendingStock[] => {
    const mockStocks = [
      { symbol: "AAPL", name: "Apple Inc.", base_price: 175.50 },
      { symbol: "MSFT", name: "Microsoft Corporation", base_price: 378.85 },
      { symbol: "NVDA", name: "NVIDIA Corporation", base_price: 875.30 },
      { symbol: "GOOGL", name: "Alphabet Inc.", base_price: 138.75 },
      { symbol: "AMZN", name: "Amazon.com Inc.", base_price: 145.20 },
      { symbol: "TSLA", name: "Tesla Inc.", base_price: 248.50 },
      { symbol: "META", name: "Meta Platforms Inc.", base_price: 485.75 },
      { symbol: "NFLX", name: "Netflix Inc.", base_price: 485.30 },
      { symbol: "AMD", name: "Advanced Micro Devices", base_price: 142.85 },
      { symbol: "CRM", name: "Salesforce Inc.", base_price: 285.40 },
    ];

    return mockStocks.map((stock, index) => {
      const priceChange = (Math.random() - 0.5) * 10; // Random change between -5 and +5
      const priceChangePercent = (priceChange / stock.base_price) * 100;
      const volume = Math.floor(Math.random() * 50000000) + 1000000; // 1M to 50M
      const sentimentScore = Math.random() * 0.6 + 0.2; // 0.2 to 0.8
      const recommendations = ["BUY", "STRONG_BUY", "HOLD", "SELL"];

      return {
        symbol: stock.symbol,
        company_name: stock.name,
        current_price: Number((stock.base_price + priceChange).toFixed(2)),
        price_change: Number(priceChange.toFixed(2)),
        price_change_percent: Number(priceChangePercent.toFixed(2)),
        volume: volume,
        analysis_count: Math.floor(Math.random() * 10) + 3, // 3 to 12
        sentiment_score: Number(sentimentScore.toFixed(2)),
        recommendation: recommendations[Math.floor(Math.random() * recommendations.length)]
      };
    });
  };

  const renderTrendingStocks = () => (
    <div className={utilStyles.wFull}>
      {trendingStocks.length === 0 ? (
        <div className={cn(styles.loading, utilStyles.ptXl, utilStyles.pbXl)}>
          <TrendingUp className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <p className={cn(utilStyles.textSecondary, utilStyles.textCenter)}>No trending stocks data available</p>
        </div>
      ) : (
        <div className="table-container">
          <table className={styles.table}>
            <thead className={styles.tableHeader}>
              <tr>
                <th className={styles.tableHeaderCell}>#</th>
                <th className={styles.tableHeaderCell}>Symbol</th>
                <th className={styles.tableHeaderCell}>Company</th>
                <th className={cn(styles.tableHeaderCell, styles.tableCellNumeric)}>Price</th>
                <th className={cn(styles.tableHeaderCell, styles.tableCellNumeric)}>Change</th>
                <th className={cn(styles.tableHeaderCell, styles.tableCellNumeric)}>Volume</th>
                <th className={cn(styles.tableHeaderCell, styles.tableCellCenter)}>Sentiment</th>
                <th className={cn(styles.tableHeaderCell, styles.tableCellCenter)}>Rec.</th>
              </tr>
            </thead>
            <tbody>
              {trendingStocks.map((stock, index) => (
                <tr key={stock.symbol} className={styles.tableRow}>
                  <td className={styles.tableCell}>
                    <span className={cn(utilStyles.textGain, utilStyles.fontSemibold, utilStyles.textSm)}>
                      #{index + 1}
                    </span>
                  </td>
                  <td className={styles.tableCell}>
                    <span className={cn(utilStyles.fontSemibold, utilStyles.textPrimary)}>
                      {stock.symbol}
                    </span>
                  </td>
                  <td className={styles.tableCell}>
                    <span className={cn(utilStyles.textSecondary, utilStyles.textSm)}>
                      {stock.company_name}
                    </span>
                  </td>
                  <td className={cn(styles.tableCell, styles.tableCellNumeric)}>
                    <span className={cn(utilStyles.fontSemibold, utilStyles.textPrimary)}>
                      {formatPrice(stock.current_price)}
                    </span>
                  </td>
                  <td className={cn(styles.tableCell, styles.tableCellNumeric)}>
                    <span className={cn(getChangeColor(stock.price_change), utilStyles.fontSemibold)}>
                      {formatPercent(stock.price_change_percent)}
                    </span>
                  </td>
                  <td className={cn(styles.tableCell, styles.tableCellNumeric)}>
                    <span className={utilStyles.textSecondary}>
                      {formatVolume(stock.volume)}
                    </span>
                  </td>
                  <td className={cn(styles.tableCell, styles.tableCellCenter)}>
                    <span className={getSentimentColor(stock.sentiment_score)}>
                      {stock.sentiment_score != null && !isNaN(stock.sentiment_score)
                        ? `${(stock.sentiment_score * 100).toFixed(0)}%`
                        : '--'}
                    </span>
                  </td>
                  <td className={cn(styles.tableCell, styles.tableCellCenter)}>
                    <span className={cn(
                      styles.badge,
                      stock.recommendation === 'BUY' || stock.recommendation === 'STRONG_BUY'
                        ? styles.badgeGain
                        : stock.recommendation === 'SELL'
                        ? styles.badgeLoss
                        : styles.badgeNeutral,
                      utilStyles.textXs
                    )}>
                      {stock.recommendation}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  // Add navigation handler for earnings stocks
  const handleEarningsStockClick = async (symbol: string, companyName: string, hasAnalysis?: boolean) => {
    // If no analysis exists, trigger it in the background
    if (!hasAnalysis) {
      try {
        // Skip API call for now (backend not running)
        // await fetch(`http://localhost:8000/api/v1/earnings/trigger-analysis/${symbol}`, {
        //   method: 'POST'
        // });
        console.log(`Would trigger analysis for ${symbol} (backend not running)`);
      } catch (error) {
        console.warn(`Failed to trigger analysis for ${symbol}:`, error);
        // Continue anyway - the stock analyzer will handle the analysis
      }
    }

    // Call the parent callback to navigate to stock analyzer
    if (onNavigateToAnalyzer) {
      onNavigateToAnalyzer(symbol, companyName);
    }
  };

  const renderEarningsCalendar = () => {
    // Group earnings by date
    const earningsByDate = earningsEvents.reduce((acc, event) => {
      const dateKey = new Date(event.earnings_date).toDateString();
      if (!acc[dateKey]) {
        acc[dateKey] = [];
      }
      acc[dateKey].push(event);
      return acc;
    }, {} as Record<string, EarningsEvent[]>);

    const sortedDates = Object.keys(earningsByDate).sort((a, b) =>
      new Date(a).getTime() - new Date(b).getTime()
    );

    if (earningsEvents.length === 0) {
      return (
        <div className="text-center py-8">
          <Calendar className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <p className="font-mono text-[var(--text-secondary)]">No earnings events scheduled</p>
        </div>
      );
    }

    return (
      <div className="space-y-8">
        {sortedDates.map((dateKey) => {
          const events = earningsByDate[dateKey];
          const date = new Date(dateKey);
          const isToday = date.toDateString() === new Date().toDateString();

          return (
            <div key={dateKey}>
              {/* Day Header with Line */}
              <div className="flex items-center gap-4 mb-6">
                <h3 className={cn(
                  'text-lg font-semibold whitespace-nowrap',
                  isToday ? utilStyles.textGain : utilStyles.textPrimary
                )}>
                  {date.toLocaleDateString('en-US', {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric'
                  })}
                  {isToday && <span className="ml-2 text-sm font-normal">(Today)</span>}
                </h3>
                <div className="flex-1 h-[1.5px] bg-[var(--border-color)]"></div>
                <div className="text-sm text-[var(--text-muted)] whitespace-nowrap">
                  {events.length} earnings report{events.length !== 1 ? 's' : ''}
                </div>
              </div>

              {/* Table without card wrapper */}
              <div className="table-container mb-8">
                <table className={styles.table}>
                  <thead className={styles.tableHeader}>
                    <tr>
                      <th className={styles.tableHeaderCell}>Company</th>
                      <th className={styles.tableHeaderCell}>Time</th>
                      <th className={styles.tableHeaderCell}>Est EPS</th>
                      <th className={styles.tableHeaderCell}>Last EPS</th>
                      <th className={styles.tableHeaderCell}>Last Surprise</th>
                      <th className={styles.tableHeaderCell}>Sentiment</th>
                      <th className={styles.tableHeaderCell}>AI Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((event) => (
                      <tr
                        key={event.symbol}
                        className={cn(styles.tableRow, 'cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors')}
                        onClick={() => handleEarningsStockClick(event.symbol, event.company_name, event.has_analysis)}
                        title={`Click to analyze ${event.symbol}${event.has_analysis ? ' (Analysis available)' : ' (Will trigger analysis)'}`}
                      >
                        <td className={styles.tableCell}>
                          <div>
                            <div className="font-mono font-bold text-[var(--text-primary)] flex items-center gap-2">
                              {event.symbol}
                              {event.has_analysis ? (
                                <span className="text-xs text-green-500">✓ Ready</span>
                              ) : (
                                <span className="text-xs text-[var(--text-muted)]">→ Analyze</span>
                              )}
                            </div>
                            <div className="text-sm text-[var(--text-secondary)]">
                              {event.company_name}
                            </div>
                            <div className="text-xs text-[var(--text-muted)]">
                              {event.sector}
                            </div>
                          </div>
                        </td>
                        <td className={styles.tableCell}>
                          <div className="text-center">
                            <div className={cn(
                              'px-2 py-1 rounded text-xs font-mono',
                              event.time === 'BMO' ? 'bg-blue-100 text-blue-800' :
                              event.time === 'AMC' ? 'bg-purple-100 text-purple-800' :
                              'bg-gray-100 text-gray-800'
                            )}>
                              {event.time}
                            </div>
                          </div>
                        </td>
                        <td className={styles.tableCell}>
                          <div className="text-right font-mono">
                            ${event.estimated_eps.toFixed(2)}
                          </div>
                        </td>
                        <td className={styles.tableCell}>
                          <div className="text-right font-mono">
                            {event.last_quarter_eps ? `$${event.last_quarter_eps.toFixed(2)}` : '--'}
                          </div>
                        </td>
                        <td className={styles.tableCell}>
                          <div className="text-right">
                            {event.last_quarter_surprise ? (
                              <span className={cn(
                                'font-mono',
                                event.last_quarter_surprise > 0 ? utilStyles.textGain : utilStyles.textLoss
                              )}>
                                {event.last_quarter_surprise > 0 ? '+' : ''}{event.last_quarter_surprise.toFixed(1)}%
                              </span>
                            ) : '--'}
                          </div>
                        </td>
                        <td className={styles.tableCell}>
                          <div className="text-center">
                            {event.ai_sentiment && (
                              <span className={cn(
                                'px-2 py-1 rounded text-xs font-medium',
                                event.ai_sentiment === 'Bullish' ? 'bg-green-100 text-green-800' :
                                event.ai_sentiment === 'Bearish' ? 'bg-red-100 text-red-800' :
                                'bg-yellow-100 text-yellow-800'
                              )}>
                                {event.ai_sentiment}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className={styles.tableCell}>
                          <div className="text-sm text-[var(--text-secondary)] max-w-xs">
                            {event.ai_summary || '--'}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderNews = () => (
    <div className="space-y-4">
      {/* News Filter */}
      <div className="flex items-center gap-4 mb-4">
        <Filter className="w-4 h-4 text-[var(--text-muted)]" />
        <div className="flex gap-2">
          <button
            onClick={() => setNewsFilter('all')}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
              newsFilter === 'all'
                ? 'bg-[var(--accent-cyan)] text-[var(--bg-primary)]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            All News
          </button>
          <button
            onClick={() => setNewsFilter('portfolio')}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
              newsFilter === 'portfolio'
                ? 'bg-[var(--accent-cyan)] text-[var(--bg-primary)]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Portfolio Related
          </button>
        </div>
      </div>

      {newsItems.length === 0 ? (
        <div className="text-center py-8">
          <Newspaper className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <p className="font-mono text-[var(--text-secondary)]">No news items available</p>
        </div>
      ) : (
        newsItems.map((news) => (
          <div key={news.id} className="bg-[var(--bg-secondary)] p-4 rounded border border-[var(--border-color)] hover:border-[var(--accent-yellow)] transition-colors">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <h4 className="font-mono font-bold text-[var(--text-primary)] mb-2">
                  {news.title}
                </h4>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed mb-3">
                  {news.summary}
                </p>
                <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
                  <span>{news.source}</span>
                  <span>{new Date(news.published_at).toLocaleString()}</span>
                  <span className={getSentimentColor(news.sentiment_score)}>
                    Sentiment: {news.sentiment_score != null && !isNaN(news.sentiment_score)
                      ? `${(news.sentiment_score * 100).toFixed(0)}%`
                      : '--'}
                  </span>
                </div>
                {news.related_symbols.length > 0 && (
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-[var(--text-muted)]">Related:</span>
                    {news.related_symbols.map((symbol) => (
                      <span key={symbol} className="px-2 py-1 bg-[var(--bg-tertiary)] text-[var(--accent-cyan)] text-xs font-mono rounded">
                        {symbol}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <a
                href={news.url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-4 p-2 text-[var(--text-muted)] hover:text-[var(--accent-cyan)] transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderUnusualOptions = () => (
    <div className="space-y-4">
      {/* AI Summary Section */}
      {unusualOptionsData?.data.ai_summary && (
        <div className="clean-panel border-2 border-[var(--color-gain)]">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-5 h-5 text-[var(--color-gain)]" />
            <h3 className="clean-header text-lg text-[var(--color-gain)]">
              AI Market Summary
            </h3>
            <span className={`px-2 py-1 rounded text-xs font-mono ${
              unusualOptionsData.data.ai_summary.market_sentiment === 'BULLISH'
                ? 'bg-gain text-[var(--color-gain)]'
                : unusualOptionsData.data.ai_summary.market_sentiment === 'BEARISH'
                ? 'bg-loss text-[var(--color-loss)]'
                : 'bg-neutral text-[var(--color-neutral)]'
            }`}>
              {unusualOptionsData.data.ai_summary.market_sentiment}
            </span>
          </div>

          <p className="text-[var(--text-primary)] mb-3 leading-relaxed">
            {unusualOptionsData.data.ai_summary.summary}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {unusualOptionsData.data.ai_summary.key_trends.map((trend, index) => (
              <div key={index} className="clean-panel p-3">
                <span className="text-sm text-[var(--text-secondary)]">
                  • {trend}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between mt-3 text-xs text-[var(--text-muted)]">
            <span>Confidence: {(unusualOptionsData.data.ai_summary.confidence * 100).toFixed(0)}%</span>
            <span>Updated: {new Date(unusualOptionsData.data.ai_summary.last_updated).toLocaleTimeString()}</span>
          </div>
        </div>
      )}

      {/* Market Metrics */}
      {unusualOptionsData?.data.market_metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="clean-panel">
            <div className="text-2xl font-bold text-[var(--color-gain)]">
              {unusualOptionsData.data.market_metrics.total_unusual_contracts}
            </div>
            <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
              Unusual Contracts
            </div>
          </div>

          <div className="clean-panel">
            <div className="text-2xl font-bold text-[var(--color-gain)]">
              {unusualOptionsData.data.market_metrics.total_large_trades}
            </div>
            <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
              Large Trades
            </div>
          </div>

          <div className="clean-panel">
            <div className="text-2xl font-bold text-[var(--color-loss)]">
              ${(unusualOptionsData.data.market_metrics.total_premium_flow / 1000000).toFixed(1)}M
            </div>
            <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
              Premium Flow
            </div>
          </div>

          <div className="clean-panel">
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {unusualOptionsData.data.market_metrics.call_put_ratio}
            </div>
            <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
              Call/Put Ratio
            </div>
          </div>
        </div>
      )}

      {/* Placeholder for actual data - will be populated when backend is working */}
      <div className="clean-panel text-center">
        <Zap className="w-12 h-12 text-[var(--color-gain)] mx-auto mb-4" />
        <h3 className="clean-header text-lg text-[var(--color-gain)] mb-2">Real-time Unusual Options Activity</h3>
        <p className="text-[var(--text-secondary)] mb-4">
          Monitoring {unusualOptionsData?.data.filter_criteria.symbols_analyzed || 24} symbols for unusual activity
        </p>
        <div className="text-sm text-[var(--text-muted)] space-y-1">
          <p>• Volume/OI ratio threshold: {unusualOptionsData?.data.filter_criteria.min_volume_ratio || 2.0}x</p>
          <p>• Minimum premium: ${(unusualOptionsData?.data.filter_criteria.min_premium || 10000).toLocaleString()}</p>
          <p>• Auto-refresh: Every 3 minutes</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className={cn(utilStyles.flex, utilStyles.flexCol, utilStyles.gapLg)}>
      {/* Header with Tabs */}
      <div className={styles.card}>
        <div className={cn(styles.cardHeader, utilStyles.mbMd)}>
          <div className={cn(utilStyles.flex, utilStyles.itemsCenter, utilStyles.gapSm)}>
            <TrendingUp className="w-6 h-6 text-[var(--text-primary)]" />
            <h2 className={cn(styles.cardTitle, utilStyles.textXl, utilStyles.textPrimary)}>
              Market Activity
            </h2>
          </div>
          <button
            onClick={refreshData}
            disabled={isLoading}
            className={cn(styles.buttonSecondary, styles.buttonSmall)}
            title="Refresh Data"
          >
            <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className={layoutStyles.tabContainer}>
          <div className={layoutStyles.tabList}>
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    layoutStyles.tab,
                    isActive && layoutStyles.tabActive
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {tab.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className={cn(
            utilStyles.mbMd,
            utilStyles.pMd,
            styles.bgLoss,
            utilStyles.border,
            utilStyles.roundedSm
          )}>
            <div className={cn(utilStyles.flex, utilStyles.itemsCenter, utilStyles.gapSm)}>
              <span className={cn(utilStyles.textLoss, utilStyles.textSm)}>{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Tab Content */}
      <div className={styles.card}>
        {isLoading ? (
          <div className={styles.loading}>
            <div className={styles.spinner}></div>
            <p className={utilStyles.textSecondary}>
              Loading {tabs.find(t => t.id === activeTab)?.name.toLowerCase()}...
            </p>
          </div>
        ) : (
          <div className={layoutStyles.tabContent}>
            {activeTab === 'trending' && renderTrendingStocks()}
            {activeTab === 'earnings' && renderEarningsCalendar()}
            {activeTab === 'news' && renderNews()}
            {activeTab === 'unusual-options' && renderUnusualOptions()}
          </div>
        )}
      </div>
    </div>
  );
}
