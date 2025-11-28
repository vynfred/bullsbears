// src/app/admin-control/bb-admin/page.tsx
"use client";

import { useState, useEffect } from "react";
import { Power, AlertTriangle } from "lucide-react";

export default function AdminControlPanel() {
  const [systemOn, setSystemOn] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchStatus = async () => {
    const res = await fetch(`${API_URL}/api/v1/internal/system/status`);
    const data = await res.json();
    setSystemOn(data.system_on);
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const toggleSystem = async (turnOn: boolean) => {
    setLoading(true);
    await fetch(`${API_URL}/api/v1/internal/system/${turnOn ? "on" : "off"}`, {
      method: "POST",
    });
    setTimeout(() => {
      fetchStatus();
      setLoading(false);
    }, 800);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-bold text-white mb-8 text-center">
          BullsBears v5 — Master Control
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Status Card */}
          <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-8 shadow-2xl">
            <h2 className="text-2xl text-white mb-4 flex items-center gap-3">
              <AlertTriangle className="w-4 h-8" />
              System Status
            </h2>
            <div className="text-6xl font-bold text-center mt-8">
              {systemOn === null ? (
                <span className="text-gray-500">Loading...</span>
              ) : systemOn ? (
                <span className="text-emerald-400">ON</span>
              ) : (
                <span className="text-red-400">OFF</span>
              )}
            </div>
            <p className="text-center text-gray-400 mt-4">
              Daily pipeline at 8:00 AM ET
            </p>
          </div>

          {/* Control Card */}
          <div className="bg-slate-900/80 backdrop-blur border border-purple-500/30 rounded-2xl p-8 shadow-2xl">
            <h2 className="text-2xl text-white mb-6 flex items-center gap-3">
              <Power className="w-8 h-8" />
              Master Switch
            </h2>

            <div className="flex gap-6 justify-center mt-12">
              <button
                onClick={() => toggleSystem(true)}
                disabled={loading || systemOn === true}
                className={`px-12 py-6 rounded-xl font-bold text-2xl transition-all transform hover:scale-105 ${
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
                className={`px-12 py-6 rounded-xl font-bold text-2xl transition-all transform hover:scale-105 ${
                  !systemOn
                    ? "bg-red-600/30 text-red-400 cursor-not-allowed"
                    : "bg-red-600 text-white hover:bg-red-500 shadow-lg shadow-red-500/50"
                }`}
              >
                TURN OFF
              </button>
            </div>

            {loading && (
              <p className="text-center text-yellow-400 mt-6 animate-pulse">
                Updating system state...
              </p>
            )}
          </div>
        </div>

        <p className="text-center text-gray-500 mt-16 text-sm">
          Protected URL • Only you know this exists • Powered by Render + Fireworks + Groq + Grok
        </p>
      </div>
    </div>
  );
}