// src/app/admin-control/bb-admin/page.tsx
"use client";

import { useState, useEffect } from "react";
import { Power, AlertTriangle, Database, Users, TrendingUp, ListChecks, Clock, RefreshCw, Activity, Zap, Target, BarChart3 } from "lucide-react";

interface Stats {
  stocks: number;
  shortlist: number;
  picks: number;
  users: number;
}

interface ActivityEntry {
  timestamp: string;
  step: string;
  action: string;
  details: Record<string, unknown> | null;
  tier_counts: Record<string, number> | null;
  duration_seconds: number | null;
  success: boolean;
  error_message: string | null;
}

interface TierCounts {
  all: number;
  active: number;
  shortlist: number;
  picks: number;
}

interface Freshness {
  ohlc: { latest_date: string; oldest_date: string; total_rows: number };
  shortlist: { latest_date: string; today_count: number };
  picks: { latest_created: string | null; today_count: number };
  server_time: string;
}

export default function AdminControlPanel() {
  const [systemOn, setSystemOn] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats>({ stocks: 0, shortlist: 0, picks: 0, users: 0 });
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [tierCounts, setTierCounts] = useState<TierCounts>({ all: 0, active: 0, shortlist: 0, picks: 0 });
  const [freshness, setFreshness] = useState<Freshness | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>("");
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/internal/system/status`);
      const data = await res.json();
      setSystemOn(data.system_on);
    } catch (e) {
      console.error("Failed to fetch status:", e);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/data/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats({
          stocks: data.stocks?.total_symbols || 0,
          shortlist: data.shortlist?.today || 0,
          picks: data.picks?.today || 0,
          users: data.users?.total || 0,
        });
      }
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    }
  };

  const fetchActivity = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/data/activity`);
      if (res.ok) {
        const data = await res.json();
        setActivity(data.activity || []);
        setTierCounts(data.tier_counts || { all: 0, active: 0, shortlist: 0, picks: 0 });
      }
    } catch (e) {
      console.error("Failed to fetch activity:", e);
    }
  };

  const fetchFreshness = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/data/freshness`);
      if (res.ok) {
        const data = await res.json();
        setFreshness(data);
      }
    } catch (e) {
      console.error("Failed to fetch freshness:", e);
    }
    setLastRefresh(new Date().toLocaleTimeString());
  };

  const triggerPipeline = async () => {
    setPipelineLoading(true);
    try {
      await fetch(`${API_URL}/api/v1/admin/trigger-full-pipeline`, { method: "POST" });
      setTimeout(() => {
        fetchActivity();
        fetchStats();
        setPipelineLoading(false);
      }, 2000);
    } catch (e) {
      console.error("Failed to trigger pipeline:", e);
      setPipelineLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchStats();
    fetchActivity();
    fetchFreshness();
    const statusInterval = setInterval(fetchStatus, 10000);
    const statsInterval = setInterval(fetchStats, 30000);
    const activityInterval = setInterval(fetchActivity, 15000);
    const freshnessInterval = setInterval(fetchFreshness, 60000);
    return () => {
      clearInterval(statusInterval);
      clearInterval(statsInterval);
      clearInterval(activityInterval);
      clearInterval(freshnessInterval);
    };
  }, []);

  const toggleSystem = async (turnOn: boolean) => {
    setLoading(true);
    await fetch(`${API_URL}/api/v1/internal/system/${turnOn ? "on" : "off"}`, {
      method: "POST",
    });
    setTimeout(() => {
      fetchStatus();
      fetchStats();
      setLoading(false);
    }, 800);
  };

  const StatCard = ({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) => (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 text-center">
      <Icon className={`w-6 h-6 mx-auto mb-2 ${color}`} />
      <p className="text-3xl font-bold text-white">{value.toLocaleString()}</p>
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-5xl font-bold text-white mb-8 text-center">
          BullsBears v5 — Master Control
        </h1>

        {/* Top Row: Status + Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Status Card */}
          <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-xl text-white mb-4 flex items-center gap-3">
              <AlertTriangle className="w-5 h-5" />
              System Status
            </h2>
            <div className="text-5xl font-bold text-center mt-4">
              {systemOn === null ? (
                <span className="text-gray-500">Loading...</span>
              ) : systemOn ? (
                <span className="text-emerald-400">ON</span>
              ) : (
                <span className="text-red-400">OFF</span>
              )}
            </div>
            <p className="text-center text-gray-400 mt-3 text-sm">
              Daily pipeline at 8:00 AM ET
            </p>
          </div>

          {/* Control Card */}
          <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-xl text-white mb-4 flex items-center gap-3">
              <Power className="w-5 h-5" />
              Master Switch
            </h2>
            <div className="flex gap-4 justify-center mt-4">
              <button
                onClick={() => toggleSystem(true)}
                disabled={loading || systemOn === true}
                className={`px-8 py-4 rounded-xl font-bold text-lg transition-all transform hover:scale-105 ${
                  systemOn
                    ? "bg-emerald-600/30 text-emerald-400 cursor-not-allowed"
                    : "bg-emerald-600 text-white hover:bg-emerald-500 shadow-lg shadow-emerald-500/50"
                }`}
              >
                TURN ON
              </button>
              <button
                onClick={() => toggleSystem(false)}
                disabled={loading || systemOn === false}
                className={`px-8 py-4 rounded-xl font-bold text-lg transition-all transform hover:scale-105 ${
                  !systemOn
                    ? "bg-red-600/30 text-red-400 cursor-not-allowed"
                    : "bg-red-600 text-white hover:bg-red-500 shadow-lg shadow-red-500/50"
                }`}
              >
                TURN OFF
              </button>
            </div>
            {loading && (
              <p className="text-center text-yellow-400 mt-4 animate-pulse text-sm">
                Updating system state...
              </p>
            )}
          </div>
        </div>

        {/* Data Freshness + Tier Counts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Data Freshness */}
          <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-xl text-white mb-4 flex items-center gap-3">
              <Clock className="w-5 h-5" />
              Data Freshness
            </h2>
            {freshness ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">OHLC Latest:</span>
                  <span className={`font-mono ${freshness.ohlc.latest_date === new Date().toISOString().split('T')[0] ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {freshness.ohlc.latest_date}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Shortlist Today:</span>
                  <span className="text-white font-mono">{freshness.shortlist.today_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Picks Today:</span>
                  <span className="text-white font-mono">{freshness.picks.today_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Total OHLC Rows:</span>
                  <span className="text-slate-300 font-mono">{freshness.ohlc.total_rows.toLocaleString()}</span>
                </div>
              </div>
            ) : (
              <p className="text-slate-500">Loading...</p>
            )}
          </div>

          {/* Stock Tier Funnel */}
          <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-xl text-white mb-4 flex items-center gap-3">
              <BarChart3 className="w-5 h-5" />
              Stock Tier Funnel
            </h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-24 text-slate-400">ALL</div>
                <div className="flex-1 bg-slate-700/50 rounded-full h-6 overflow-hidden">
                  <div className="bg-cyan-500/70 h-full rounded-full" style={{ width: '100%' }}></div>
                </div>
                <div className="w-16 text-right font-mono text-cyan-400">{tierCounts.all.toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-24 text-slate-400">ACTIVE</div>
                <div className="flex-1 bg-slate-700/50 rounded-full h-6 overflow-hidden">
                  <div className="bg-blue-500/70 h-full rounded-full" style={{ width: tierCounts.all > 0 ? `${(tierCounts.active / tierCounts.all) * 100}%` : '0%' }}></div>
                </div>
                <div className="w-16 text-right font-mono text-blue-400">{tierCounts.active.toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-24 text-slate-400">SHORT_LIST</div>
                <div className="flex-1 bg-slate-700/50 rounded-full h-6 overflow-hidden">
                  <div className="bg-amber-500/70 h-full rounded-full" style={{ width: tierCounts.active > 0 ? `${Math.min((tierCounts.shortlist / tierCounts.active) * 100, 100)}%` : '0%' }}></div>
                </div>
                <div className="w-16 text-right font-mono text-amber-400">{tierCounts.shortlist}</div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-24 text-slate-400">PICKS</div>
                <div className="flex-1 bg-slate-700/50 rounded-full h-6 overflow-hidden">
                  <div className="bg-emerald-500/70 h-full rounded-full" style={{ width: tierCounts.shortlist > 0 ? `${Math.min((tierCounts.picks / tierCounts.shortlist) * 100, 100)}%` : '0%' }}></div>
                </div>
                <div className="w-16 text-right font-mono text-emerald-400">{tierCounts.picks}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Pipeline Actions */}
        <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl mb-6">
          <h2 className="text-xl text-white mb-4 flex items-center gap-3">
            <Zap className="w-5 h-5" />
            Pipeline Actions
          </h2>
          <div className="flex gap-4 flex-wrap">
            <button
              onClick={triggerPipeline}
              disabled={pipelineLoading || !systemOn}
              className={`px-6 py-3 rounded-xl font-bold transition-all ${
                pipelineLoading || !systemOn
                  ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                  : "bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-500 hover:to-pink-500 shadow-lg"
              }`}
            >
              {pipelineLoading ? "Running..." : "▶ Run Full Pipeline"}
            </button>
            <button
              onClick={() => { fetchActivity(); fetchFreshness(); fetchStats(); }}
              className="px-6 py-3 rounded-xl font-bold bg-slate-700 text-white hover:bg-slate-600 transition-all flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh All
            </button>
          </div>
          {lastRefresh && <p className="text-slate-500 text-sm mt-3">Last refresh: {lastRefresh}</p>}
        </div>

        {/* Recent Activity */}
        <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
          <h2 className="text-xl text-white mb-4 flex items-center gap-3">
            <Activity className="w-5 h-5" />
            Recent Pipeline Activity
          </h2>
          {activity.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {activity.map((entry, i) => (
                <div key={i} className={`p-3 rounded-lg border ${entry.success ? 'bg-slate-800/40 border-slate-700/50' : 'bg-red-900/20 border-red-500/30'}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                        entry.step === 'arbitrator' ? 'bg-emerald-500/20 text-emerald-400' :
                        entry.step === 'prescreen' ? 'bg-amber-500/20 text-amber-400' :
                        entry.step === 'fmp_update' ? 'bg-cyan-500/20 text-cyan-400' :
                        entry.step === 'vision' ? 'bg-purple-500/20 text-purple-400' :
                        entry.step === 'social' ? 'bg-pink-500/20 text-pink-400' :
                        'bg-slate-500/20 text-slate-400'
                      }`}>{entry.step}</span>
                      <span className={`font-medium ${entry.success ? 'text-white' : 'text-red-400'}`}>{entry.action}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      {entry.duration_seconds && <span>{entry.duration_seconds.toFixed(1)}s</span>}
                      <span>{new Date(entry.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                  {entry.details && (
                    <div className="mt-2 text-sm text-slate-400">
                      {entry.details.picks && Array.isArray(entry.details.picks) ? (
                        <div className="flex flex-wrap gap-2 mt-1">
                          {(entry.details.picks as Array<{symbol: string; direction: string; confidence?: number}>).map((p, j) => (
                            <span key={j} className={`px-2 py-1 rounded text-xs font-mono ${p.direction === 'bullish' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                              {p.symbol} {p.confidence ? `(${(p.confidence * 100).toFixed(0)}%)` : ''}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="font-mono text-xs">{JSON.stringify(entry.details)}</span>
                      )}
                    </div>
                  )}
                  {entry.error_message && (
                    <div className="mt-2 text-sm text-red-400 font-mono">{entry.error_message}</div>
                  )}
                  {entry.tier_counts && (
                    <div className="mt-2 flex gap-4 text-xs">
                      <span className="text-cyan-400">ALL: {entry.tier_counts.all}</span>
                      <span className="text-blue-400">ACTIVE: {entry.tier_counts.active}</span>
                      <span className="text-amber-400">SHORT: {entry.tier_counts.shortlist}</span>
                      <span className="text-emerald-400">PICKS: {entry.tier_counts.picks}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-center py-8">No recent activity logs</p>
          )}
        </div>

        <p className="text-center text-gray-500 mt-8 text-sm">
          Protected URL • Only you know this exists • Powered by Render + Fireworks + Groq + Grok
        </p>
      </div>
    </div>
  );
}