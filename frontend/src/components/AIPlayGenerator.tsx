'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { Zap, Settings, DollarSign, Clock, TrendingUp, AlertTriangle, Target, Shield, Timer, RotateCcw } from 'lucide-react';
import { api, AIOptionPlay, GeneratePlaysParams, RateLimitStatus } from '@/lib/api';
import styles from '@/styles/components.module.css';

export type DirectionalBias = 'BULLISH' | 'BEARISH' | 'AI_DECIDES';

interface AIPlayGeneratorProps {
  onPlaysGenerated: (plays: AIOptionPlay[]) => void;
  isLoading: boolean;
  error: string | null;
  onLoadingChange: (loading: boolean) => void;
  onError: (error: string | null) => void;
  onDirectionalBiasChange?: (bias: DirectionalBias) => void;
}

export default function AIPlayGenerator({ onPlaysGenerated, isLoading, error, onLoadingChange, onError, onDirectionalBiasChange }: AIPlayGeneratorProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [rateLimitStatus, setRateLimitStatus] = useState<RateLimitStatus | null>(null);
  const [directionalBias, setDirectionalBias] = useState<DirectionalBias>('AI_DECIDES');
  const [params, setParams] = useState<GeneratePlaysParams>({
    symbol: '',
    max_plays: 3,
    min_confidence: 70,
    timeframe_days: 7,
    position_size: 1000,
    risk_tolerance: 'MODERATE'
  });

  // Advanced settings state
  const [advancedSettings, setAdvancedSettings] = useState({
    shares_owned: {} as Record<string, number>,
    iv_threshold: 50,
    earnings_alert: true,
    insight_style: 'professional_trader'
  });

  // Fetch rate limit status (only when needed, not on mount)
  const fetchRateLimitStatus = async () => {
    try {
      const status = await api.getRateLimitStatus();
      setRateLimitStatus(status);
    } catch (error) {
      console.log('Rate limit status unavailable - this is normal if backend is not running');
      // Don't set error state, just silently fail
    }
  };

  const handleDirectionalBiasChange = (bias: DirectionalBias) => {
    setDirectionalBias(bias);
    onDirectionalBiasChange?.(bias);
  };

  const formatNumberWithCommas = (num: number): string => {
    return num.toLocaleString();
  };

  const handlePositionSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/,/g, ''); // Remove commas for parsing
    const numValue = parseInt(value) || 1000;
    setParams({...params, position_size: numValue});
  };

  const handleGenerate = async () => {
    onLoadingChange(true);
    onError(null);

    try {
      const response = await api.generateOptionPlays({
        ...params,
        directional_bias: directionalBias,
        // Include advanced settings
        insight_style: advancedSettings.insight_style,
        iv_threshold: advancedSettings.iv_threshold,
        earnings_alert: advancedSettings.earnings_alert,
        shares_owned: advancedSettings.shares_owned
      });

      if (response.success) {
        onPlaysGenerated(response.plays);
        // Update rate limit status after successful generation
        if (response.rate_limit_info) {
          setRateLimitStatus(prev => prev ? {
            ...prev,
            current_usage: response.rate_limit_info!.current_usage,
            remaining: response.rate_limit_info!.remaining
          } : null);
        } else {
          // Refresh rate limit status
          fetchRateLimitStatus();
        }
      } else if (response.rate_limit_exceeded) {
        // Update rate limit status when limit is exceeded
        fetchRateLimitStatus();
        throw new Error(response.error || 'Rate limit exceeded');
      } else {
        throw new Error(response.error || 'Failed to generate plays');
      }
    } catch (err: unknown) {
      console.error('Error generating plays:', err);
      onError(err instanceof Error ? err.message : 'Failed to generate option plays');
    } finally {
      onLoadingChange(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Rate Limit Status */}
      {rateLimitStatus && (
        <div className="flex items-center justify-between p-3 border border-[var(--border-color)] rounded bg-[var(--bg-tertiary)]">
          <div className="flex items-center gap-2">
            <Timer className="w-4 h-4 text-[var(--accent-cyan)]" />
            <span className="font-mono text-xs text-[var(--text-secondary)] uppercase">
              Daily Usage Limit
            </span>
          </div>
          <div className="text-right font-mono text-xs">
            <div className={`${rateLimitStatus.remaining > 0 ? 'status-online' : 'status-error'}`}>
              {rateLimitStatus.current_usage}/{rateLimitStatus.daily_limit} USED
            </div>
            <div className="text-[var(--text-muted)]">
              {rateLimitStatus.remaining} REMAINING
              {rateLimitStatus.reset_time_est && (
                <div className="text-[var(--accent-yellow)]">
                  RESET: {rateLimitStatus.reset_time_est}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Settings Panel */}
      <div className="border border-[var(--border-color)] rounded p-4 bg-[var(--bg-tertiary)]">
        <h3 className="font-mono text-[var(--accent-cyan)] text-sm mb-4 uppercase tracking-wider">
          [TRADING PARAMETERS]
        </h3>

        {/* Symbol Selection Section */}
        <div className="mb-6 p-4 border border-[var(--border-color)] rounded bg-[var(--bg-secondary)]">
          <label className="block text-xs font-mono text-[var(--text-secondary)] mb-3 uppercase">
            <DollarSign className="h-3 w-3 inline mr-1" />
            Stock/ETF Symbol
          </label>

          <div className="space-y-4">
            {/* Manual Input */}
            <input
              type="text"
              value={params.symbol || ''}
              onChange={(e) => setParams({...params, symbol: e.target.value.toUpperCase()})}
              placeholder="Enter symbol (e.g., AAPL) or select below"
              className="clean-input w-full text-sm font-mono uppercase"
            />

            {/* Popular Stocks */}
            <div>
              <p className="text-xs font-mono text-[var(--text-muted)] mb-2">&gt; Popular Options Stocks:</p>
              <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
                {['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX'].map((symbol) => (
                  <button
                    key={symbol}
                    onClick={() => setParams({...params, symbol})}
                    className={`px-2 py-1 text-xs font-mono border rounded transition-colors ${
                      params.symbol === symbol
                        ? 'bg-[var(--accent-cyan)] border-[var(--accent-cyan)] text-[var(--bg-primary)]'
                        : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]'
                    }`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>

            {/* Popular ETFs */}
            <div>
              <p className="text-xs font-mono text-[var(--text-muted)] mb-2">&gt; Popular Options ETFs:</p>
              <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
                {['SPY', 'QQQ', 'IWM', 'EEM', 'GLD', 'TLT', 'XLF', 'EWZ'].map((symbol) => (
                  <button
                    key={symbol}
                    onClick={() => setParams({...params, symbol})}
                    className={`px-2 py-1 text-xs font-mono border rounded transition-colors ${
                      params.symbol === symbol
                        ? 'bg-[var(--accent-cyan)] border-[var(--accent-cyan)] text-[var(--bg-primary)]'
                        : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]'
                    }`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>

            {/* AI Wildcards */}
            <div>
              <p className="text-xs font-mono text-[var(--text-muted)] mb-2">&gt; AI Wildcards:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <button
                  onClick={() => setParams({...params, symbol: 'AI_SURPRISE'})}
                  className={`px-3 py-2 text-xs font-mono border rounded transition-colors ${
                    params.symbol === 'AI_SURPRISE'
                      ? 'bg-[var(--accent-yellow)] border-[var(--accent-yellow)] text-[var(--bg-primary)]'
                      : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]'
                  }`}
                >
                  🎲 AI SURPRISE ME
                </button>
                <button
                  onClick={() => setParams({...params, symbol: 'TRENDING_NOW'})}
                  className={`px-3 py-2 text-xs font-mono border rounded transition-colors ${
                    params.symbol === 'TRENDING_NOW'
                      ? 'bg-[var(--accent-red)] border-[var(--accent-red)] text-[var(--bg-primary)]'
                      : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]'
                  }`}
                >
                  🔥 TRENDING NOW
                </button>
              </div>
            </div>
          </div>

          <p className="text-xs font-mono text-[var(--text-muted)] mt-3">
            &gt; Manual entry, popular picks, or let AI choose trending stocks
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Position Size */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <DollarSign className="h-3 w-3 inline mr-1" />
              Position Size
            </label>
            <div className={styles.selectorContainer}>
              <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[var(--text-muted)] font-mono text-sm pointer-events-none z-10">$</span>
              <input
                type="text"
                value={formatNumberWithCommas(params.position_size || 0)}
                onChange={handlePositionSizeChange}
                className={`${styles.selectorInput}`}
                style={{ paddingLeft: '24px' }}
                placeholder="1,000"
              />
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              Min Confidence
            </label>
            <div className={styles.selectorContainer}>
              <select
                value={params.min_confidence}
                onChange={(e) => setParams({...params, min_confidence: parseInt(e.target.value)})}
                className={styles.selectorSelect}
              >
                <option value={60}>60%</option>
                <option value={65}>65%</option>
                <option value={70}>70%</option>
                <option value={75}>75%</option>
                <option value={80}>80%</option>
                <option value={85}>85%</option>
                <option value={90}>90%</option>
              </select>
              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[var(--text-muted)] font-mono text-sm">%</span>
            </div>
          </div>

          {/* Directional Bias */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              Directional Bias
            </label>
            <div className={styles.directionalBiasContainer}>
              {/* Bullish */}
              <button
                onClick={() => handleDirectionalBiasChange('BULLISH')}
                className={`${styles.directionalBiasButton} ${styles.bullish} ${
                  directionalBias === 'BULLISH' ? styles.active : ''
                }`}
              >
                <Image
                  src="/bull-icon.png"
                  alt="Bull"
                  width={20}
                  height={20}
                  className={`transition-all duration-200 ${
                    directionalBias === 'BULLISH'
                      ? 'brightness-0' // Black when selected
                      : 'brightness-0 dark:invert' // Black in light mode, white in dark mode
                  }`}
                />
                {/* Tooltip */}
                <div className={styles.tooltip}>
                  Bullish - Favor upward price movements
                </div>
              </button>

              {/* AI Decides */}
              <button
                onClick={() => handleDirectionalBiasChange('AI_DECIDES')}
                className={`${styles.directionalBiasButton} ${styles.ai} ${
                  directionalBias === 'AI_DECIDES' ? styles.active : ''
                }`}
              >
                <Image
                  src="/robot-icon.png"
                  alt="AI Robot"
                  width={20}
                  height={20}
                  className={`transition-all duration-200 ${
                    directionalBias === 'AI_DECIDES'
                      ? 'brightness-0' // Black when selected
                      : 'brightness-0 dark:invert' // Black in light mode, white in dark mode
                  }`}
                />
                {/* Tooltip */}
                <div className={styles.tooltip}>
                  AI Decides - Let AI analyze and choose optimal direction
                </div>
              </button>

              {/* Bearish */}
              <button
                onClick={() => handleDirectionalBiasChange('BEARISH')}
                className={`${styles.directionalBiasButton} ${styles.bearish} ${
                  directionalBias === 'BEARISH' ? styles.active : ''
                }`}
              >
                <Image
                  src="/bear-icon.png"
                  alt="Bear"
                  width={20}
                  height={20}
                  className={`transition-all duration-200 ${
                    directionalBias === 'BEARISH'
                      ? 'brightness-0' // Black when selected
                      : 'brightness-0 dark:invert' // Black in light mode, white in dark mode
                  }`}
                />
                {/* Tooltip */}
                <div className={styles.tooltip}>
                  Bearish - Favor downward price movements
                </div>
              </button>
            </div>
          </div>

          {/* Expiration Date */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <Clock className="h-3 w-3 inline mr-1" />
              Expiration Date
            </label>
            <div className={styles.selectorContainer}>
              <select
                value={params.timeframe_days}
                onChange={(e) => setParams({...params, timeframe_days: parseInt(e.target.value)})}
                className={styles.selectorSelect}
              >
                <option value={1}>1 Day (±2 days)</option>
                <option value={2}>2 Days (±2 days)</option>
                <option value={3}>3 Days (±2 days)</option>
                <option value={7}>1 Week (±2 days)</option>
                <option value={14}>2 Weeks (±2 days)</option>
                <option value={21}>3 Weeks (±2 days)</option>
                <option value={30}>1 Month (±2 days)</option>
              </select>
            </div>
          </div>

          {/* Risk Tolerance */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <Shield className="h-3 w-3 inline mr-1" />
              Insight Style
            </label>
            <div className={styles.selectorContainer}>
              <select
                value={params.risk_tolerance}
                onChange={(e) => setParams({...params, risk_tolerance: e.target.value as 'LOW' | 'MODERATE' | 'HIGH'})}
                className={styles.selectorSelect}
              >
                <option value="LOW">Conservative</option>
                <option value="MODERATE">Moderate</option>
                <option value="HIGH">Aggressive</option>
              </select>
            </div>
          </div>
        </div>

        {/* Advanced Settings Toggle */}
        <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center text-xs font-mono text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors uppercase"
          >
            <Settings className="h-3 w-3 mr-1" />
            {showAdvanced ? '[HIDE]' : '[SHOW]'} Advanced Settings
          </button>
        </div>
      </div>

      {/* Advanced Settings Panel */}
      {showAdvanced && (
        <div className="border border-[var(--accent-cyan)] rounded p-4 bg-[var(--bg-secondary)] mb-6">
          <h3 className="font-mono text-[var(--accent-cyan)] text-sm mb-4 uppercase tracking-wider">
            [ADVANCED OPTIONS]
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Insight Style */}
            <div className="relative group">
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <Shield className="h-3 w-3 inline mr-1" />
                Insight Style
                <span className="ml-1 text-[var(--text-muted)] cursor-help">ⓘ</span>
              </label>
              <div className={styles.selectorContainer}>
                <select
                  value={advancedSettings.insight_style}
                  onChange={(e) => setAdvancedSettings({...advancedSettings, insight_style: e.target.value})}
                  className={styles.selectorSelect}
                >
                  <option value="cautious_trader">Cautious Trader (Low Risk: Defined, Income-Focused)</option>
                  <option value="professional_trader">Professional Trader (Medium Risk: Balanced, Structured)</option>
                  <option value="degenerate_gambler">Degenerate Gambler (High Risk: Aggressive, High-Reward)</option>
                </select>
              </div>

              {/* Tooltip */}
              <div className="absolute left-0 top-full mt-2 w-96 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg p-3 text-xs font-mono opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 shadow-lg">
                <div className="space-y-3">
                  <div className="text-[var(--accent-cyan)] font-bold text-center border-b border-[var(--border-color)] pb-2">Insight Style Strategies</div>

                  <div>
                    <div className="text-[var(--accent-cyan)] font-bold">Cautious Trader (Low Risk):</div>
                    <div className="text-[var(--text-secondary)] ml-2 mt-1">
                      • <strong>Bullish:</strong> Bull Put Spread (credit; delta -0.2 to -0.4)<br/>
                      • <strong>Bearish:</strong> Bear Call Spread (credit; delta 0.2 to 0.4)<br/>
                      • <strong>Neutral:</strong> Short Strangle (credit; wings ±20%)
                    </div>
                  </div>

                  <div>
                    <div className="text-[var(--accent-yellow)] font-bold">Professional Trader (Medium Risk):</div>
                    <div className="text-[var(--text-secondary)] ml-2 mt-1">
                      • <strong>Bullish:</strong> Bull Call Spread (debit; delta 0.4-0.6)<br/>
                      • <strong>Bearish:</strong> Bear Put Spread (debit; delta -0.4 to -0.6)<br/>
                      • <strong>Neutral:</strong> Iron Condor (credit; breakeven ±10%)
                    </div>
                  </div>

                  <div>
                    <div className="text-[var(--accent-red)] font-bold">Degenerate Gambler (High Risk):</div>
                    <div className="text-[var(--text-secondary)] ml-2 mt-1">
                      • <strong>Bullish:</strong> Naked Call (long OTM; delta &gt;0.7)<br/>
                      • <strong>Bearish:</strong> Naked Put (long OTM; delta &lt; -0.7)<br/>
                      • <strong>Neutral:</strong> Long Straddle (debit; vega &gt;0.5 volatility bet)
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* IV Threshold */}
            <div className="relative group">
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <TrendingUp className="h-3 w-3 inline mr-1" />
                IV Threshold: {advancedSettings.iv_threshold}%
                <span className="ml-1 text-[var(--text-muted)] cursor-help">ⓘ</span>
              </label>
              <div className="relative">
                <input
                  type="range"
                  min="20"
                  max="80"
                  value={advancedSettings.iv_threshold}
                  onChange={(e) => setAdvancedSettings({...advancedSettings, iv_threshold: parseInt(e.target.value)})}
                  className="w-full h-2 bg-[var(--bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs font-mono text-[var(--text-muted)] mt-1">
                  <span>20%</span>
                  <span>50%</span>
                  <span>80%</span>
                </div>
              </div>

              {/* IV Tooltip */}
              <div className="absolute left-0 top-full mt-2 w-72 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg p-3 text-xs font-mono opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 shadow-lg">
                <div className="space-y-1">
                  <div className="text-[var(--accent-cyan)] font-bold">Implied Volatility Filter</div>
                  <div className="text-[var(--text-secondary)]">Maximum IV% to consider for trades.</div>
                  <div className="text-[var(--text-muted)]">
                    • Low (20-40%): Conservative, stable stocks<br/>
                    • Medium (40-60%): Balanced risk/reward<br/>
                    • High (60-80%): Volatile, high-premium options
                  </div>
                </div>
              </div>
            </div>

            {/* Max Plays */}
            <div>
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <Target className="h-3 w-3 inline mr-1" />
                Maximum Plays
              </label>
              <div className={styles.selectorContainer}>
                <select
                  value={params.max_plays}
                  onChange={(e) => setParams({...params, max_plays: parseInt(e.target.value)})}
                  className={styles.selectorSelect}
                >
                  <option value={1}>1 Play</option>
                  <option value={2}>2 Plays</option>
                  <option value={3}>3 Plays</option>
                  <option value={4}>4 Plays</option>
                  <option value={5}>5 Plays</option>
                </select>
              </div>
              <p className="text-xs font-mono text-[var(--text-muted)] mt-1">
                &gt; Limit analysis output
              </p>
            </div>

            {/* Daily Limit Info */}
            <div>
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <Timer className="h-3 w-3 inline mr-1" />
                Usage Status
              </label>
              <div className={`px-3 py-2 border rounded font-mono text-xs ${
                rateLimitStatus?.remaining === 0
                  ? 'bg-[var(--bg-primary)] border-[var(--accent-red)] text-[var(--accent-red)]'
                  : rateLimitStatus && rateLimitStatus.remaining <= 2
                  ? 'bg-[var(--bg-primary)] border-[var(--accent-yellow)] text-[var(--accent-yellow)]'
                  : 'bg-[var(--bg-primary)] border-[var(--text-primary)] text-[var(--text-primary)]'
              }`}>
                {rateLimitStatus ? (
                  <>
                    <p className="font-bold">
                      {rateLimitStatus.current_usage} / {rateLimitStatus.daily_limit} USED
                    </p>
                    <p className="mt-1 text-[var(--text-muted)]">
                      {rateLimitStatus.remaining} REMAINING • RESET: MIDNIGHT EST
                    </p>
                  </>
                ) : (
                  <p className="text-[var(--text-muted)]">LOADING STATUS...</p>
                )}
              </div>
            </div>

            {/* Earnings Alert Toggle */}
            <div className="relative group">
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <AlertTriangle className="h-3 w-3 inline mr-1" />
                Earnings Alert
                <span className="ml-1 text-[var(--text-muted)] cursor-help">ⓘ</span>
              </label>
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setAdvancedSettings({...advancedSettings, earnings_alert: !advancedSettings.earnings_alert})}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    advancedSettings.earnings_alert
                      ? 'bg-[var(--accent-cyan)]'
                      : 'bg-[var(--bg-tertiary)]'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      advancedSettings.earnings_alert ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <span className="text-xs font-mono text-[var(--text-secondary)]">
                  {advancedSettings.earnings_alert ? 'AVOID EARNINGS' : 'IGNORE EARNINGS'}
                </span>
              </div>
              <p className="text-xs font-mono text-[var(--text-muted)] mt-1">
                &gt; {advancedSettings.earnings_alert ? 'Reduce position size near earnings' : 'Trade normally near earnings'}
              </p>

              {/* Earnings Tooltip */}
              <div className="absolute left-0 top-full mt-2 w-64 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg p-3 text-xs font-mono opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 shadow-lg">
                <div className="space-y-1">
                  <div className="text-[var(--accent-yellow)] font-bold">Earnings Proximity Alert</div>
                  <div className="text-[var(--text-secondary)]">Control trading behavior near earnings dates.</div>
                  <div className="text-[var(--text-muted)]">
                    • ON: Avoid/reduce positions 1-2 weeks before earnings<br/>
                    • OFF: Trade normally regardless of earnings timing
                  </div>
                </div>
              </div>
            </div>

            {/* Reset to Defaults Button */}
            <div className="col-span-2 flex justify-end">
              <button
                onClick={() => {
                  setAdvancedSettings({
                    insight_style: 'professional_trader',
                    iv_threshold: 50,
                    earnings_alert: true,
                    shares_owned: {}
                  });
                }}
                className="neon-button-secondary px-4 py-2 text-xs font-mono flex items-center gap-2"
              >
                <RotateCcw className="h-3 w-3" />
                RESET TO DEFAULTS
              </button>
            </div>

            {/* Shares Owned */}
            <div className="col-span-2">
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <DollarSign className="h-3 w-3 inline mr-1" />
                Shares Owned (for Covered Calls)
              </label>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="SYMBOL"
                    className="clean-input flex-1 text-xs font-mono uppercase"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const target = e.target as HTMLInputElement;
                        const symbol = target.value.toUpperCase();
                        const sharesInput = target.parentElement?.querySelector('input[placeholder="SHARES"]') as HTMLInputElement;
                        const shares = parseInt(sharesInput?.value || '0');

                        if (symbol && shares > 0) {
                          setAdvancedSettings({
                            ...advancedSettings,
                            shares_owned: {
                              ...advancedSettings.shares_owned,
                              [symbol]: shares
                            }
                          });
                          target.value = '';
                          if (sharesInput) sharesInput.value = '';
                        }
                      }
                    }}
                  />
                  <input
                    type="number"
                    placeholder="SHARES"
                    min="0"
                    step="100"
                    className="clean-input w-24 text-xs font-mono"
                  />
                  <button
                    onClick={(e) => {
                      const container = e.currentTarget.parentElement;
                      const symbolInput = container?.querySelector('input[placeholder="SYMBOL"]') as HTMLInputElement;
                      const sharesInput = container?.querySelector('input[placeholder="SHARES"]') as HTMLInputElement;
                      const symbol = symbolInput?.value.toUpperCase();
                      const shares = parseInt(sharesInput?.value || '0');

                      if (symbol && shares > 0) {
                        setAdvancedSettings({
                          ...advancedSettings,
                          shares_owned: {
                            ...advancedSettings.shares_owned,
                            [symbol]: shares
                          }
                        });
                        if (symbolInput) symbolInput.value = '';
                        if (sharesInput) sharesInput.value = '';
                      }
                    }}
                    className="neon-button-secondary px-3 py-1 text-xs font-mono"
                  >
                    ADD
                  </button>
                </div>

                {/* Display current shares */}
                {Object.keys(advancedSettings.shares_owned).length > 0 && (
                  <div className="space-y-1">
                    {Object.entries(advancedSettings.shares_owned).map(([symbol, shares]) => (
                      <div key={symbol} className="flex items-center justify-between bg-[var(--bg-tertiary)] px-2 py-1 rounded text-xs font-mono">
                        <span className="text-[var(--text-primary)]">{symbol}: {shares} shares</span>
                        <button
                          onClick={() => {
                            const newShares = {...advancedSettings.shares_owned};
                            delete newShares[symbol];
                            setAdvancedSettings({...advancedSettings, shares_owned: newShares});
                          }}
                          className="text-[var(--accent-red)] hover:text-[var(--accent-red)] ml-2"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <p className="text-xs font-mono text-[var(--text-muted)]">
                  &gt; Enable covered call strategies (requires 100+ shares)
                </p>
              </div>
            </div>
          </div>
        </div>
      )}



      {/* Error Display */}
      {error && (
        <div className="border border-[var(--accent-red)] rounded p-4 mb-4 bg-[var(--bg-secondary)]">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 status-error mr-2" />
            <div>
              <h3 className="font-mono text-[var(--accent-red)] font-bold uppercase">
                [ERROR] Generation Failed
              </h3>
              <p className="text-sm font-mono text-[var(--text-muted)] mt-1">&gt; {error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Generate Button */}
      <div className="text-center">
        <button
          onClick={handleGenerate}
          disabled={isLoading || (rateLimitStatus?.can_generate === false)}
          className={`neon-button w-full max-w-md mx-auto flex items-center justify-center px-8 py-4 text-lg transition-all ${
            isLoading || (rateLimitStatus?.can_generate === false)
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
          }`}
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-[var(--text-primary)] border-t-transparent mr-3"></div>
              ANALYZING... (2-3 MIN)
            </>
          ) : rateLimitStatus && !rateLimitStatus.can_generate ? (
            <>
              <AlertTriangle className="h-5 w-5 mr-3" />
              LIMIT REACHED
            </>
          ) : (
            <>
              <Zap className="h-5 w-5 mr-3" />
              EXECUTE BULLSBEARS SCAN
            </>
          )}
        </button>

        {/* Current Settings Summary */}
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <span className="inline-flex items-center px-3 py-1 border border-[var(--text-primary)] rounded text-xs font-mono text-[var(--text-primary)]">
            ${(params.position_size || 1000).toLocaleString()}
          </span>
          <span className="inline-flex items-center px-3 py-1 border border-[var(--accent-cyan)] rounded text-xs font-mono text-[var(--accent-cyan)]">
            {params.min_confidence}% CONF
          </span>
          <span className="inline-flex items-center px-3 py-1 border border-[var(--accent-yellow)] rounded text-xs font-mono text-[var(--accent-yellow)]">
            {params.timeframe_days}D (±2)
          </span>
          <span className="inline-flex items-center px-3 py-1 border border-[var(--text-secondary)] rounded text-xs font-mono text-[var(--text-secondary)]">
            {params.risk_tolerance}
          </span>
        </div>

        {/* System Info */}
        <div className="mt-4 text-xs font-mono text-[var(--text-muted)] text-center space-y-1">

          <p className="text-[var(--accent-red)]">
            [LIMIT] 5 GENERATIONS/DAY • [EXPIRE] MARKET CLOSE
          </p>

        </div>
      </div>
    </div>
  );
}
