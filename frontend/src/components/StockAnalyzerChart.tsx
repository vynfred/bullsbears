'use client';

import React, { useRef, useEffect, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { TrendingUp, TrendingDown, Target, Zap } from 'lucide-react';

interface OHLCData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface StockAnalyzerChartProps {
  ticker: string;
  className?: string;
}

interface DrawingTool {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
}

const StockAnalyzerChart: React.FC<StockAnalyzerChartProps> = ({ ticker, className = '' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<OHLCData[]>([]);
  const [activeDrawingTool, setActiveDrawingTool] = useState<string | null>(null);

  const drawingTools: DrawingTool[] = [
    { id: 'support', name: 'Auto Support', icon: TrendingUp, description: 'Detect support levels' },
    { id: 'resistance', name: 'Auto Resistance', icon: TrendingDown, description: 'Detect resistance levels' },
    { id: 'fibonacci', name: 'Fibonacci', icon: Target, description: 'Fibonacci retracement' },
    { id: 'breakout', name: 'Breakout', icon: Zap, description: 'Breakout detection' },
  ];

  // Fetch OHLC data
  const fetchStockData = async (symbol: string): Promise<OHLCData[]> => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/stock/${symbol}/ohlc?period=1y&interval=1d`);
      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching stock data:', error);
      throw error;
    }
  };

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    try {
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { color: 'transparent' },
          textColor: 'var(--text-primary)',
        },
        grid: {
          vertLines: { color: 'var(--border-color)' },
          horzLines: { color: 'var(--border-color)' },
        },
        crosshair: {
          mode: 1,
        },
        rightPriceScale: {
          borderColor: 'var(--border-color)',
        },
        timeScale: {
          borderColor: 'var(--border-color)',
          timeVisible: true,
          secondsVisible: false,
        },
        width: chartContainerRef.current.clientWidth,
        height: 400,
      });

      const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#00FF41', // Neon green for gains
        downColor: '#FF073A', // Red for losses
        borderDownColor: '#FF073A',
        borderUpColor: '#00FF41',
        wickDownColor: '#FF073A',
        wickUpColor: '#00FF41',
      });

      chartRef.current = chart;
      candlestickSeriesRef.current = candlestickSeries;

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chart) {
          chart.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
      };
    } catch (error) {
      console.error('Error initializing chart:', error);
      setError('Failed to initialize chart');
    }
  }, []);

  // Load data
  useEffect(() => {
    const loadData = async () => {
      if (!ticker || !candlestickSeriesRef.current) return;

      setIsLoading(true);
      setError(null);

      try {
        const ohlcData = await fetchStockData(ticker);
        
        // Convert to TradingView format
        const chartData: CandlestickData[] = ohlcData.map(item => ({
          time: item.time as Time,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
        }));

        candlestickSeriesRef.current.setData(chartData);
        setData(ohlcData);

        // Fit content to show all data
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }

      } catch (error) {
        console.error('Error loading chart data:', error);
        setError('Failed to load chart data. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [ticker]);

  // Auto-drawing functions
  const autoDrawSupport = async () => {
    if (!data.length || !chartRef.current) return;

    try {
      // Simple support detection - find recent lows
      const recentData = data.slice(-50); // Last 50 data points
      const lows = recentData.map(d => d.low);
      const minLow = Math.min(...lows);
      
      // Add horizontal line at support level
      candlestickSeriesRef.current?.createPriceLine({
        price: minLow,
        color: '#00FF41',
        lineWidth: 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: 'Support',
      });

      setActiveDrawingTool(null);
    } catch (error) {
      console.error('Error drawing support:', error);
    }
  };

  const autoDrawResistance = async () => {
    if (!data.length || !chartRef.current) return;

    try {
      // Simple resistance detection - find recent highs
      const recentData = data.slice(-50); // Last 50 data points
      const highs = recentData.map(d => d.high);
      const maxHigh = Math.max(...highs);
      
      // Add horizontal line at resistance level
      candlestickSeriesRef.current?.createPriceLine({
        price: maxHigh,
        color: '#FF073A',
        lineWidth: 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: 'Resistance',
      });

      setActiveDrawingTool(null);
    } catch (error) {
      console.error('Error drawing resistance:', error);
    }
  };

  const autoDrawFibonacci = async () => {
    if (!data.length || !chartRef.current) return;

    try {
      // Find swing high and low for Fibonacci
      const recentData = data.slice(-100);
      const highs = recentData.map(d => d.high);
      const lows = recentData.map(d => d.low);
      const swingHigh = Math.max(...highs);
      const swingLow = Math.min(...lows);
      
      const diff = swingHigh - swingLow;
      const fibLevels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
      
      // Draw Fibonacci levels
      fibLevels.forEach((level, index) => {
        const price = swingHigh - (diff * level);
        candlestickSeriesRef.current?.createPriceLine({
          price,
          color: `hsl(${180 + index * 30}, 70%, 60%)`,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `Fib ${(level * 100).toFixed(1)}%`,
        });
      });

      setActiveDrawingTool(null);
    } catch (error) {
      console.error('Error drawing Fibonacci:', error);
    }
  };

  const detectBreakout = async () => {
    if (!data.length) return;

    try {
      const response = await fetch(`http://localhost:8000/api/v1/analyzers/breakout?symbol=${ticker}`);
      if (response.ok) {
        const breakoutData = await response.json();
        // Handle breakout detection results
        console.log('Breakout analysis:', breakoutData);
      }
      setActiveDrawingTool(null);
    } catch (error) {
      console.error('Error detecting breakout:', error);
      setActiveDrawingTool(null);
    }
  };

  const handleDrawingTool = (toolId: string) => {
    setActiveDrawingTool(toolId);
    
    switch (toolId) {
      case 'support':
        autoDrawSupport();
        break;
      case 'resistance':
        autoDrawResistance();
        break;
      case 'fibonacci':
        autoDrawFibonacci();
        break;
      case 'breakout':
        detectBreakout();
        break;
    }
  };

  if (error) {
    return (
      <div className={`clean-panel ${className}`}>
        <div className="text-center py-8">
          <div className="status-loss mb-2">Chart Error</div>
          <p className="text-sm text-[var(--text-muted)]">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 clean-button-secondary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`clean-panel ${className}`}>
      {/* Chart Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">
            {ticker.toUpperCase()} Chart
          </h3>
          <p className="text-sm text-[var(--text-muted)]">Interactive candlestick chart with drawing tools</p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 text-[var(--text-muted)]">
            <div className="w-4 h-4 border-2 border-[var(--text-muted)] border-t-transparent rounded-full animate-spin"></div>
            Loading...
          </div>
        )}
      </div>

      {/* Drawing Tools */}
      <div className="flex flex-wrap gap-2 mb-4">
        {drawingTools.map((tool) => {
          const Icon = tool.icon;
          return (
            <button
              key={tool.id}
              onClick={() => handleDrawingTool(tool.id)}
              disabled={isLoading || activeDrawingTool === tool.id}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                activeDrawingTool === tool.id
                  ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]'
                  : 'clean-button-secondary'
              }`}
              title={tool.description}
            >
              <Icon className="w-4 h-4" />
              {tool.name}
            </button>
          );
        })}
      </div>

      {/* Chart Container */}
      <div className="relative">
        <div
          ref={chartContainerRef}
          className="w-full h-[400px] sm:h-[500px] rounded-lg overflow-hidden"
          style={{ minHeight: '400px' }}
        />
        
        {/* Disclaimer */}
        <div className="mt-2 text-xs text-[var(--text-muted)] text-center">
          Not financial advice. Educational tool only. Do your own research.
        </div>
      </div>
    </div>
  );
};

export default StockAnalyzerChart;
