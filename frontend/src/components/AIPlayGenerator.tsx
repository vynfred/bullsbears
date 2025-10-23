'use client';

import React, { useState } from 'react';
import { Zap, Settings, DollarSign, Clock, TrendingUp, AlertTriangle, Target, Shield, Timer } from 'lucide-react';
import { api, AIOptionPlay, GeneratePlaysParams, RateLimitStatus } from '@/lib/api';

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
    max_plays: 3,
    min_confidence: 70,
    timeframe_days: 7,
    position_size: 1000,
    risk_tolerance: 'MODERATE'
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

  const handleGenerate = async () => {
    onLoadingChange(true);
    onError(null);

    try {
      const response = await api.generateOptionPlays({
        ...params,
        directional_bias: directionalBias
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Position Size */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <DollarSign className="h-3 w-3 inline mr-1" />
              Position Size
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[var(--text-muted)] font-mono text-xs">$</span>
              <input
                type="number"
                value={params.position_size}
                onChange={(e) => setParams({...params, position_size: parseInt(e.target.value) || 1000})}
                min={100}
                max={50000}
                step={100}
                className="terminal-input w-full pl-6 pr-3 py-2 text-sm"
                placeholder="1000"
              />
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              Min Confidence
            </label>
            <div className="relative">
              <select
                value={params.min_confidence}
                onChange={(e) => setParams({...params, min_confidence: parseInt(e.target.value)})}
                className="terminal-input w-full px-3 py-2 text-sm appearance-none"
              >
                <option value={60}>60%</option>
                <option value={65}>65%</option>
                <option value={70}>70%</option>
                <option value={75}>75%</option>
                <option value={80}>80%</option>
                <option value={85}>85%</option>
                <option value={90}>90%</option>
              </select>
              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[var(--text-muted)] font-mono">%</span>
            </div>
          </div>

          {/* Directional Bias */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              Directional Bias
            </label>
            <div className="flex bg-[var(--bg-secondary)] rounded border border-[var(--border-color)] p-1">
              {/* Bullish */}
              <button
                onClick={() => handleDirectionalBiasChange('BULLISH')}
                className={`flex-1 px-2 py-1 rounded text-xs font-mono uppercase transition-all duration-200 ${
                  directionalBias === 'BULLISH'
                    ? 'bg-green-600 text-white shadow-lg shadow-green-600/30'
                    : 'text-[var(--text-muted)] hover:text-green-400'
                }`}
              >
                🐂 Bull
              </button>
              {/* AI Decides */}
              <button
                onClick={() => handleDirectionalBiasChange('AI_DECIDES')}
                className={`flex-1 px-2 py-1 rounded text-xs font-mono uppercase transition-all duration-200 ${
                  directionalBias === 'AI_DECIDES'
                    ? 'bg-[var(--accent-cyan)] text-black shadow-lg shadow-cyan-600/30'
                    : 'text-[var(--text-muted)] hover:text-[var(--accent-cyan)]'
                }`}
              >
                👽 AI
              </button>
              {/* Bearish */}
              <button
                onClick={() => handleDirectionalBiasChange('BEARISH')}
                className={`flex-1 px-2 py-1 rounded text-xs font-mono uppercase transition-all duration-200 ${
                  directionalBias === 'BEARISH'
                    ? 'bg-red-600 text-white shadow-lg shadow-red-600/30'
                    : 'text-[var(--text-muted)] hover:text-red-400'
                }`}
              >
                🐻 Bear
              </button>
            </div>
          </div>

          {/* Expiration Date */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <Clock className="h-3 w-3 inline mr-1" />
              Expiration Date
            </label>
            <select
              value={params.timeframe_days}
              onChange={(e) => setParams({...params, timeframe_days: parseInt(e.target.value)})}
              className="terminal-input w-full px-3 py-2 text-sm"
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

          {/* Risk Tolerance */}
          <div>
            <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
              <Shield className="h-3 w-3 inline mr-1" />
              Risk Level
            </label>
            <select
              value={params.risk_tolerance}
              onChange={(e) => setParams({...params, risk_tolerance: e.target.value as 'LOW' | 'MODERATE' | 'HIGH'})}
              className="terminal-input w-full px-3 py-2 text-sm"
            >
              <option value="LOW">Conservative</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">Aggressive</option>
            </select>
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
            {/* Max Plays */}
            <div>
              <label className="block text-xs font-mono text-[var(--text-secondary)] mb-2 uppercase">
                <Target className="h-3 w-3 inline mr-1" />
                Maximum Plays
              </label>
              <select
                value={params.max_plays}
                onChange={(e) => setParams({...params, max_plays: parseInt(e.target.value)})}
                className="terminal-input w-full px-3 py-2 text-sm"
              >
                <option value={1}>1 Play</option>
                <option value={2}>2 Plays</option>
                <option value={3}>3 Plays</option>
                <option value={4}>4 Plays</option>
                <option value={5}>5 Plays</option>
              </select>
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
