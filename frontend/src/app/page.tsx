'use client';

import React, { useState } from 'react';
import AIPlayGenerator from '@/components/AIPlayGenerator';
import AIPlayResults from '@/components/AIPlayResults';
import OptionPlayCard from '@/components/OptionPlayCard';
import NotificationSystem from '@/components/NotificationSystem';
import HistoryTab from '@/components/HistoryTab';
import StockAnalyzer from '@/components/StockAnalyzer';
import ActivityTabs from '@/components/ActivityTabs';
import PortfolioTracker from '@/components/PortfolioTracker';
import PerformanceDashboard from '@/components/PerformanceDashboard';

import ThemeToggle from '@/components/ThemeToggle';

import { api, AIOptionPlay } from '@/lib/api';
import { History, TrendingUp, Search, BarChart3, List, Menu, X, AlertTriangle, Zap } from 'lucide-react';
import { DirectionalBias } from '@/components/AIPlayGenerator';

type ActiveTool = 'ai-generator' | 'stock-analyzer' | 'portfolio' | 'unusual-options' | 'activity' | 'performance';

export default function Home() {
  // Navigation state
  const [activeTool, setActiveTool] = useState<ActiveTool>('activity');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // AI Play Generator state
  const [aiPlays, setAiPlays] = useState<AIOptionPlay[]>([]);
  const [isGeneratingPlays, setIsGeneratingPlays] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [currentDirectionalBias, setCurrentDirectionalBias] = useState<DirectionalBias>('AI_DECIDES');

  // System state
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Legacy history state (will be integrated into tools)
  const [showHistory, setShowHistory] = useState(false);

  // Navigation state for earnings -> analyzer flow
  const [pendingAnalysis, setPendingAnalysis] = useState<{symbol: string, companyName: string} | null>(null);

  // Navigation handler for earnings -> analyzer
  const handleNavigateToAnalyzer = (symbol: string, companyName: string) => {
    setPendingAnalysis({ symbol, companyName });
    setActiveTool('stock-analyzer');
  };

  // Check demo mode on component mount (only once)
  React.useEffect(() => {
    const checkDemoMode = async () => {
      try {
        const response = await fetch('http://localhost:8000/');
        const text = await response.text();
        setIsDemoMode(text.includes('DEMO MODE') || text.includes('demo'));
      } catch (error) {
        // Backend not available - assume not demo mode
        setIsDemoMode(false);
      }
    };

    checkDemoMode();
  }, []); // Empty dependency array to run only once on mount

  // Clean design - no theme classes needed

  const handlePlaysGenerated = (plays: AIOptionPlay[]) => {
    setAiPlays(plays);
  };

  const handleLoadingChange = (loading: boolean) => {
    setIsGeneratingPlays(loading);
  };

  const handleError = (error: string | null) => {
    setAiError(error);
  };

  const handleChooseOption = async (play: AIOptionPlay) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/choose-option', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: play.symbol,
          company_name: play.company_name,
          option_type: play.option_type,
          strike: play.strike,
          expiration: play.expiration,
          entry_price: play.entry_price,
          target_price: play.target_price,
          stop_loss: play.stop_loss,
          confidence_score: play.confidence_score,
          ai_recommendation: play.ai_recommendation,
          position_size: play.position_size,
          max_profit: play.max_profit,
          max_loss: play.max_loss,
          risk_reward_ratio: play.risk_reward_ratio,
          summary: play.summary,
          key_factors: play.key_factors,
        }),
      });

      if (response.ok) {
        // Show success message or redirect to history
        alert('Option play saved to history!');
      } else {
        throw new Error('Failed to save option play');
      }
    } catch (error) {
      console.error('Error saving option play:', error);
      alert('Failed to save option play. Please try again.');
    }
  };

  // Navigation helpers
  const tools = [
    { id: 'activity' as ActiveTool, name: 'Activity', icon: TrendingUp, description: 'Market trends & news' },
    { id: 'ai-generator' as ActiveTool, name: 'AI Options', icon: Zap, description: 'Generate option plays' },
    { id: 'stock-analyzer' as ActiveTool, name: 'Stock Analyzer', icon: Search, description: 'Analyze individual stocks' },
    { id: 'portfolio' as ActiveTool, name: 'Portfolio', icon: BarChart3, description: 'Track your positions' },
    { id: 'performance' as ActiveTool, name: 'Performance', icon: History, description: 'Track watchlist performance' },
    { id: 'unusual-options' as ActiveTool, name: 'Unusual Options', icon: List, description: 'Daily unusual activity' },
  ];

  const handleToolChange = (toolId: ActiveTool) => {
    setActiveTool(toolId);
    setSidebarOpen(false); // Close sidebar on mobile after selection

    // Remember last selected tool
    localStorage.setItem('bullsbears-active-tool', toolId);
  };

  // Load last selected tool on mount
  React.useEffect(() => {
    const savedTool = localStorage.getItem('bullsbears-active-tool') as ActiveTool;
    if (savedTool && tools.find(t => t.id === savedTool)) {
      setActiveTool(savedTool);
    }
  }, []);

  // Render main content based on active tool
  const renderMainContent = () => {

    // Demo Mode Warning
    const demoModeWarning = isDemoMode && (
      <div className="mb-6 clean-panel border-[var(--color-neutral)]">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 status-neutral mr-3" />
          <div>
            <h3 className="status-neutral font-semibold">
              Demo Mode - Using Simulated Data
            </h3>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              API keys not configured - showing demo data for testing purposes
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Configure Alpha Vantage and News API keys in backend/.env for real market data
            </p>
          </div>
        </div>
      </div>
    );

    // Legacy history view
    if (showHistory) {
      return (
        <div className="cyber-panel">
          <HistoryTab onBack={() => setShowHistory(false)} />
        </div>
      );
    }

    // Main tool content
    switch (activeTool) {
      case 'activity':
        return (
          <>
            {demoModeWarning}
            <ActivityTabs onNavigateToAnalyzer={handleNavigateToAnalyzer} />
          </>
        );

      case 'ai-generator':
        return (
          <>
            {demoModeWarning}
            {/* AI Play Generator */}
            <div className="cyber-panel mb-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 bg-[var(--text-primary)] rounded-full animate-pulse"></div>
                <h2 className="text-xl font-mono text-[var(--accent-cyan)] uppercase tracking-wider">
                  AI NEURAL NETWORK
                </h2>
              </div>
              <AIPlayGenerator
                onPlaysGenerated={handlePlaysGenerated}
                isLoading={isGeneratingPlays}
                error={aiError}
                onLoadingChange={handleLoadingChange}
                onError={handleError}
                onDirectionalBiasChange={setCurrentDirectionalBias}
              />
            </div>

            {/* AI Play Results - Card Layout */}
            {aiPlays.length > 0 && (
              <div className="cyber-panel">
                <div className="flex items-center gap-2 mb-6">
                  <div className="w-2 h-2 bg-[var(--accent-yellow)] rounded-full animate-pulse"></div>
                  <h2 className="text-xl font-mono text-[var(--accent-yellow)] uppercase tracking-wider">
                    ANALYSIS RESULTS ({aiPlays.length})
                  </h2>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {aiPlays.map((play, index) => (
                    <OptionPlayCard
                      key={index}
                      play={play}
                      onChoosePlay={handleChooseOption}
                      onSharePlay={(play) => {
                        // TODO: Implement share functionality
                        console.log('Share play:', play.symbol);
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* No Results Message */}
            {!isGeneratingPlays && aiPlays.length === 0 && !aiError && (
              <div className="cyber-panel text-center">
                <div className="flex items-center justify-center gap-2 mb-4">
                  <div className="w-2 h-2 bg-[var(--text-muted)] rounded-full"></div>
                  <h2 className="text-xl font-mono text-[var(--text-muted)] uppercase tracking-wider">
                    NO PLAYS GENERATED
                  </h2>
                </div>
                <p className="font-mono text-[var(--text-secondary)] mb-2">
                  &gt; No options met the confidence threshold
                </p>
                <p className="font-mono text-xs text-[var(--text-muted)]">
                  Try lowering the confidence threshold or adjusting parameters
                </p>
              </div>
            )}
          </>
        );

      case 'stock-analyzer':
        return (
          <>
            {demoModeWarning}
            <StockAnalyzer
              initialSymbol={pendingAnalysis?.symbol}
              initialCompanyName={pendingAnalysis?.companyName}
              onAnalysisStart={() => setPendingAnalysis(null)}
            />
          </>
        );

      case 'portfolio':
        return (
          <>
            {demoModeWarning}
            <PortfolioTracker />
          </>
        );

      case 'performance':
        return (
          <>
            {demoModeWarning}
            <PerformanceDashboard />
          </>
        );

      case 'unusual-options':
        return (
          <div className="cyber-panel text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <List className="w-8 h-8 text-[var(--accent-yellow)]" />
              <h2 className="text-xl font-mono text-[var(--accent-yellow)] uppercase tracking-wider">
                Unusual Options Activity
              </h2>
            </div>
            <p className="font-mono text-[var(--text-secondary)]">
              &gt; Coming Soon - Daily unusual volume detection
            </p>
          </div>
        );

      default:
        return <ActivityTabs />;
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Clean Header */}
      <header className="sticky top-0 z-40 bg-[var(--bg-secondary)] border-b-[1.5px] border-[var(--border-color)]">
        <div className="max-w-full px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] rounded-lg"
              >
                {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
              <TrendingUp className="w-8 h-8 text-[var(--color-gain)]" />
              <div>
                <h1 className="clean-header text-2xl md:text-3xl font-bold">
                  BullsBears
                </h1>
                <div className="text-xs text-[var(--text-muted)]">
                  AI Stock & Options Analysis
                </div>
              </div>
            </div>

            {/* Header Actions */}
            <div className="flex items-center gap-4">
              {/* Theme toggle moved to sidebar */}
            </div>
          </div>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-80px)]">
        {/* Left Sidebar */}
        <div className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 fixed lg:sticky top-[80px] lg:top-[80px] z-30 w-64 bg-[var(--bg-tertiary)] border-r-[1.5px] border-[var(--border-color)] transition-transform duration-300 ease-in-out h-[calc(100vh-80px)]`}>
          <div className="p-4">
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
              Trading Tools
            </h2>
            <nav className="space-y-2">
              {tools.map((tool) => {
                const Icon = tool.icon;
                const isActive = activeTool === tool.id;
                return (
                  <button
                    key={tool.id}
                    onClick={() => handleToolChange(tool.id)}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm transition-all ${
                      isActive
                        ? 'bg-[var(--text-primary)] text-[var(--bg-primary)] shadow-sm'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <div className="text-left">
                      <div className="font-bold">{tool.name}</div>
                      <div className="text-xs opacity-75">{tool.description}</div>
                    </div>
                  </button>
                );
              })}
            </nav>

            {/* Theme Toggle at Bottom */}
            <div className="absolute bottom-4 left-4">
              <ThemeToggle />
            </div>
          </div>
        </div>

        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && (
          <div
            className="lg:hidden fixed top-[80px] left-0 right-0 bottom-0 bg-black bg-opacity-50 z-20"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <div className="flex-1 w-full lg:w-auto">
          <main className="p-4 sm:p-6 lg:p-8 w-full">{renderMainContent()}</main>
        </div>
      </div>

      {/* Notification System */}
      <NotificationSystem />
    </div>
  );
}
