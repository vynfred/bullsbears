'use client';

import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar, Newspaper, Filter, RefreshCw, ExternalLink } from 'lucide-react';

type ActivityTab = 'trending' | 'earnings' | 'news';

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

export default function ActivityTabs() {
  const [activeTab, setActiveTab] = useState<ActivityTab>('trending');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Data states
  const [trendingStocks, setTrendingStocks] = useState<TrendingStock[]>([]);
  const [earningsEvents, setEarningsEvents] = useState<EarningsEvent[]>([]);
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  
  // Filter states
  const [newsFilter, setNewsFilter] = useState<'all' | 'portfolio'>('all');

  const tabs = [
    { id: 'trending' as ActivityTab, name: 'Trending Stocks', icon: TrendingUp },
    { id: 'earnings' as ActivityTab, name: 'Earnings', icon: Calendar },
    { id: 'news' as ActivityTab, name: 'News', icon: Newspaper },
  ];

  const fetchTrendingStocks = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/recommendations/trending?limit=20&time_range=24h');
      if (!response.ok) throw new Error('Failed to fetch trending stocks');

      const data = await response.json();
      if (data.success) {
        setTrendingStocks(data.data.trending_stocks || []);
      } else {
        // Fallback to mock data if API returns no data
        setTrendingStocks(getMockTrendingStocks());
      }
    } catch (err) {
      console.error('Error fetching trending stocks:', err);
      // Use mock data as fallback
      setTrendingStocks(getMockTrendingStocks());
      setError('Backend API temporarily unavailable - showing demo data');
    }
  };

  const fetchEarningsCalendar = async () => {
    try {
      // TODO: Implement earnings calendar endpoint
      // For now, using mock data
      const mockEarnings: EarningsEvent[] = [
        {
          symbol: 'AAPL',
          company_name: 'Apple Inc.',
          earnings_date: '2024-01-25T16:30:00Z',
          estimated_eps: 2.10,
          market_cap: 3000000000000,
        },
        {
          symbol: 'MSFT',
          company_name: 'Microsoft Corporation',
          earnings_date: '2024-01-24T16:30:00Z',
          estimated_eps: 2.78,
          actual_eps: 2.93,
          surprise_percent: 5.4,
          market_cap: 2800000000000,
        },
      ];
      setEarningsEvents(mockEarnings);
    } catch (err) {
      console.error('Error fetching earnings calendar:', err);
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
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, [activeTab]);

  const formatPrice = (price: number) => `$${price.toFixed(2)}`;
  const formatPercent = (percent: number) => `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`;
  const formatVolume = (volume: number) => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  const formatMarketCap = (marketCap: number) => {
    if (marketCap >= 1000000000000) return `$${(marketCap / 1000000000000).toFixed(1)}T`;
    if (marketCap >= 1000000000) return `$${(marketCap / 1000000000).toFixed(1)}B`;
    return `$${(marketCap / 1000000).toFixed(1)}M`;
  };

  const getSentimentColor = (score: number) => {
    if (score >= 0.6) return 'text-[var(--accent-cyan)]';
    if (score >= 0.4) return 'text-[var(--accent-yellow)]';
    return 'text-[var(--accent-red)]';
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-[var(--accent-cyan)]';
    if (change < 0) return 'text-[var(--accent-red)]';
    return 'text-[var(--text-secondary)]';
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
    <div className="space-y-3">
      {trendingStocks.length === 0 ? (
        <div className="text-center py-8">
          <TrendingUp className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <p className="font-mono text-[var(--text-secondary)]">No trending stocks data available</p>
        </div>
      ) : (
        trendingStocks.map((stock, index) => (
          <div key={stock.symbol} className="bg-[var(--bg-secondary)] p-4 rounded border border-[var(--border-color)] hover:border-[var(--accent-cyan)] transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-[var(--accent-cyan)] font-mono text-sm font-bold">
                  #{index + 1}
                </div>
                <div>
                  <div className="font-mono font-bold text-[var(--text-primary)]">
                    {stock.symbol}
                  </div>
                  <div className="text-xs text-[var(--text-secondary)]">
                    {stock.company_name}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono font-bold text-[var(--text-primary)]">
                  {formatPrice(stock.current_price)}
                </div>
                <div className={`text-sm font-mono ${getChangeColor(stock.price_change)}`}>
                  {formatPercent(stock.price_change_percent)}
                </div>
              </div>
              <div className="text-right text-xs text-[var(--text-muted)]">
                <div>Vol: {formatVolume(stock.volume)}</div>
                <div className={getSentimentColor(stock.sentiment_score)}>
                  Sentiment: {(stock.sentiment_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderEarningsCalendar = () => (
    <div className="space-y-3">
      {earningsEvents.length === 0 ? (
        <div className="text-center py-8">
          <Calendar className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <p className="font-mono text-[var(--text-secondary)]">No earnings events scheduled</p>
        </div>
      ) : (
        earningsEvents.map((event) => (
          <div key={event.symbol} className="bg-[var(--bg-secondary)] p-4 rounded border border-[var(--border-color)] hover:border-[var(--accent-yellow)] transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-mono font-bold text-[var(--text-primary)]">
                  {event.symbol}
                </div>
                <div className="text-xs text-[var(--text-secondary)]">
                  {event.company_name}
                </div>
                <div className="text-xs text-[var(--text-muted)] mt-1">
                  {formatMarketCap(event.market_cap)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono text-[var(--accent-yellow)]">
                  {new Date(event.earnings_date).toLocaleDateString()}
                </div>
                <div className="text-xs text-[var(--text-muted)]">
                  Est EPS: ${event.estimated_eps.toFixed(2)}
                </div>
                {event.actual_eps && (
                  <div className={`text-xs font-mono ${event.surprise_percent && event.surprise_percent > 0 ? 'text-[var(--accent-cyan)]' : 'text-[var(--accent-red)]'}`}>
                    Actual: ${event.actual_eps.toFixed(2)}
                    {event.surprise_percent && ` (${formatPercent(event.surprise_percent)})`}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );

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
                    Sentiment: {(news.sentiment_score * 100).toFixed(0)}%
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

  return (
    <div className="space-y-6">
      {/* Header with Tabs */}
      <div className="cyber-panel">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-[var(--accent-cyan)]" />
            <h2 className="text-xl font-mono text-[var(--accent-cyan)] uppercase tracking-wider">
              Market Activity
            </h2>
          </div>
          <button
            onClick={refreshData}
            disabled={isLoading}
            className="neon-button-secondary p-2"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-4">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded font-mono text-sm transition-all ${
                  isActive
                    ? 'bg-[var(--accent-cyan)] text-[var(--bg-primary)] shadow-lg'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.name}
              </button>
            );
          })}
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-[var(--bg-tertiary)] border border-[var(--accent-red)] rounded">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[var(--accent-red)] text-sm">{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Tab Content */}
      <div className="cyber-panel">
        {isLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border border-[var(--accent-cyan)] border-t-transparent mx-auto mb-4"></div>
            <p className="font-mono text-[var(--text-secondary)]">Loading {tabs.find(t => t.id === activeTab)?.name.toLowerCase()}...</p>
          </div>
        ) : (
          <>
            {activeTab === 'trending' && renderTrendingStocks()}
            {activeTab === 'earnings' && renderEarningsCalendar()}
            {activeTab === 'news' && renderNews()}
          </>
        )}
      </div>
    </div>
  );
}
