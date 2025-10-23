'use client';

import React, { useState } from 'react';
import AIPlayGenerator from '@/components/AIPlayGenerator';
import AIPlayResults from '@/components/AIPlayResults';
import NotificationSystem from '@/components/NotificationSystem';
import HistoryTab from '@/components/HistoryTab';
import StockAnalyzer from '@/components/StockAnalyzer';
import ActivityTabs from '@/components/ActivityTabs';

import { api, AIOptionPlay } from '@/lib/api';
import { Terminal, Wifi, WifiOff, History, TrendingUp, Search, BarChart3, List, Menu, X } from 'lucide-react';
import { DirectionalBias } from '@/components/AIPlayGenerator';

type ActiveTool = 'ai-generator' | 'stock-analyzer' | 'portfolio' | 'unusual-options' | 'activity';

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
  const [backendStatus, setBackendStatus] = useState<boolean | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  // Legacy history state (will be integrated into tools)
  const [showHistory, setShowHistory] = useState(false);

  const checkBackendHealth = React.useCallback(async () => {
    if (isCheckingHealth) return; // Prevent multiple simultaneous checks

    setIsCheckingHealth(true);
    try {
      const isHealthy = await api.healthCheck();
      setBackendStatus(isHealthy);
    } catch (error) {
      console.log('Backend health check failed - this is normal if backend is not running');
      setBackendStatus(false);
    } finally {
      setIsCheckingHealth(false);
    }
  }, [isCheckingHealth]);

  // Check backend health on component mount (only once)
  React.useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  const getThemeClass = (bias: DirectionalBias) => {
    switch (bias) {
      case 'BULLISH': return 'theme-bullish';
      case 'BEARISH': return 'theme-bearish';
      case 'AI_DECIDES': return 'theme-ai-decides';
      default: return 'theme-ai-decides';
    }
  };

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
    { id: 'ai-generator' as ActiveTool, name: 'AI Options', icon: Terminal, description: 'Generate option plays' },
    { id: 'stock-analyzer' as ActiveTool, name: 'Stock Analyzer', icon: Search, description: 'Analyze individual stocks' },
    { id: 'portfolio' as ActiveTool, name: 'Portfolio', icon: BarChart3, description: 'Track your positions' },
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
    // Backend Offline Warning
    if (backendStatus === false) {
      return (
        <div className="mb-6 cyber-panel border-[var(--accent-red)]">
          <div className="flex items-center">
            <WifiOff className="h-5 w-5 status-error mr-3" />
            <div>
              <h3 className="font-mono text-[var(--accent-red)] font-bold uppercase">
                [ERROR] Backend Connection Failed
              </h3>
              <p className="text-sm text-[var(--text-muted)] mt-1 font-mono">
                &gt; FastAPI backend offline at http://localhost:8000
              </p>
              <button
                onClick={checkBackendHealth}
                className="mt-2 text-xs font-mono text-[var(--accent-red)] hover:text-[var(--text-primary)] underline"
              >
                [RETRY CONNECTION]
              </button>
            </div>
          </div>
        </div>
      );
    }

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
        return <ActivityTabs />;

      case 'ai-generator':
        return (
          <>
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

            {/* AI Play Results */}
            {aiPlays.length > 0 && (
              <div className="cyber-panel">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-2 h-2 bg-[var(--accent-yellow)] rounded-full animate-pulse"></div>
                  <h2 className="text-xl font-mono text-[var(--accent-yellow)] uppercase tracking-wider">
                    ANALYSIS RESULTS
                  </h2>
                </div>
                <AIPlayResults plays={aiPlays} onChooseOption={handleChooseOption} />
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
        return <StockAnalyzer />;

      case 'portfolio':
        return (
          <div className="cyber-panel text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <BarChart3 className="w-8 h-8 text-[var(--accent-cyan)]" />
              <h2 className="text-xl font-mono text-[var(--accent-cyan)] uppercase tracking-wider">
                Portfolio Tracker
              </h2>
            </div>
            <p className="font-mono text-[var(--text-secondary)] mb-4">
              &gt; Coming Soon - Track your trading performance
            </p>
            <button
              onClick={() => setShowHistory(true)}
              className="neon-button"
            >
              View Trading History
            </button>
          </div>
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
    <div className={`min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] ${getThemeClass(currentDirectionalBias)}`}>
      {/* Header with 90s aesthetic */}
      <header className="cyber-panel mb-0 rounded-none border-x-0 border-t-0 border-b">
        <div className="max-w-full px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 text-[var(--accent-cyan)] hover:bg-[var(--bg-secondary)] rounded"
              >
                {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
              <Terminal className="w-8 h-8 text-[var(--accent-cyan)]" />
              <div>
                <h1 className="glitch text-2xl md:text-3xl" data-text="BULLSBEARS">
                  BULLSBEARS
                </h1>
                <div className="font-mono text-xs text-[var(--text-muted)]">
                  v2.1.1
                </div>
              </div>
            </div>

            {/* System Status & Settings */}
            <div className="flex items-center gap-4">
              <button
                onClick={checkBackendHealth}
                disabled={isCheckingHealth}
                className="flex items-center gap-2 px-3 py-2 rounded font-mono text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
              >
                {backendStatus === null ? (
                  <div className="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-pulse"></div>
                ) : backendStatus ? (
                  <Wifi className="w-4 h-4 text-[var(--accent-cyan)]" />
                ) : (
                  <WifiOff className="w-4 h-4 text-[var(--accent-red)]" />
                )}
                {isCheckingHealth ? 'CHECKING...' : 'BACKEND'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-120px)]">
        {/* Left Sidebar */}
        <div className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 fixed lg:relative z-30 w-64 bg-[var(--bg-secondary)] border-r border-[var(--border-color)] transition-transform duration-300 ease-in-out h-full overflow-y-auto`}>
          <div className="p-4">
            <h2 className="text-sm font-mono text-[var(--accent-cyan)] uppercase tracking-wider mb-4">
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
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded font-mono text-sm transition-all ${
                      isActive
                        ? 'bg-[var(--accent-cyan)] text-[var(--bg-primary)] shadow-lg'
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
          </div>
        </div>

        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && (
          <div
            className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-20"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          <main className="p-4 sm:p-6 lg:p-8">{renderMainContent()}</main>
        </div>
      </div>

      {/* Notification System */}
      <NotificationSystem />
    </div>
  );
}
