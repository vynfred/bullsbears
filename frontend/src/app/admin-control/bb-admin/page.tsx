// src/app/admin-control/bb-admin/page.tsx
"use client";

import { useState, useEffect } from "react";
import { Power, AlertTriangle, Database, Users, TrendingUp, ListChecks, Clock, RefreshCw } from "lucide-react";

interface Stats {
  stocks: number;
  shortlist: number;
  picks: number;
  users: number;
}

interface LogEntry {
  timestamp: string;
  action: string;
  details: string;
}

export default function AdminControlPanel() {
  const [systemOn, setSystemOn] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats>({ stocks: 0, shortlist: 0, picks: 0, users: 0 });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastRefresh, setLastRefresh] = useState<string>("");
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
          shortlist: data.shortlist?.total || 0,
          picks: data.picks?.total || 0,
          users: data.users?.total || 0,
        });
        setLogs(data.recent_logs || []);
      }
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    }
    setLastRefresh(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    fetchStatus();
    fetchStats();
    const statusInterval = setInterval(fetchStatus, 10000);
    const statsInterval = setInterval(fetchStats, 30000);
    return () => {
      clearInterval(statusInterval);
      clearInterval(statsInterval);
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

        {/* Stats Row */}
        <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl text-white flex items-center gap-3">
              <Database className="w-5 h-5" />
              Database Stats
            </h2>
            <button
              onClick={fetchStats}
              className="text-slate-400 hover:text-white flex items-center gap-2 text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              {lastRefresh && <span>Last: {lastRefresh}</span>}
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Database} label="Stocks" value={stats.stocks} color="text-cyan-400" />
            <StatCard icon={ListChecks} label="Shortlist" value={stats.shortlist} color="text-amber-400" />
            <StatCard icon={TrendingUp} label="Picks" value={stats.picks} color="text-emerald-400" />
            <StatCard icon={Users} label="Users" value={stats.users} color="text-purple-400" />
          </div>
        </div>

        {/* Recent Logs */}
        <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
          <h2 className="text-xl text-white mb-4 flex items-center gap-3">
            <Clock className="w-5 h-5" />
            Recent Activity
          </h2>
          {logs.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {logs.map((log, i) => (
                <div key={i} className="flex items-start gap-3 text-sm p-2 bg-slate-800/40 rounded-lg">
                  <span className="text-slate-500 whitespace-nowrap">{log.timestamp}</span>
                  <span className="text-emerald-400 font-medium">{log.action}</span>
                  <span className="text-slate-300">{log.details}</span>
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