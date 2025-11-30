// src/app/page.tsx - Public Landing Page
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { TrendingUp, Shield, Zap, BarChart3 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { AnimatedLogo } from "@/components/shared/AnimatedLogo";
import { CandleBackground } from "@/components/shared/CandleBackground";

export default function LandingPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  // Redirect logged-in users to dashboard
  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  return (
    <div className="dark min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <CandleBackground flashColor={null} />

      {/* Header */}
      <header className="border-b border-slate-800 sticky top-0 bg-slate-950/95 backdrop-blur-sm z-20">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <AnimatedLogo className="text-2xl font-black" />
            <div className="flex gap-3">
              <Link href="/login" className="px-4 py-2 text-slate-300 hover:text-white transition-colors">
                Sign In
              </Link>
              <Link href="/signup" className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 py-16 max-w-6xl relative z-10">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-black text-white mb-6">
            AI-Powered <span className="text-emerald-400">Bullish</span> & <span className="text-rose-400">Bearish</span> Stock Picks
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-8">
            Get daily AI-generated stock picks with confidence scores, target prices, and real-time tracking.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/signup" className="px-8 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold text-lg transition-all hover:scale-105">
              Start Free →
            </Link>
            <Link href="/login" className="px-8 py-4 border border-slate-700 hover:border-slate-500 text-white rounded-xl font-bold text-lg transition-colors">
              Sign In
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center mb-4">
              <TrendingUp className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Daily Picks</h3>
            <p className="text-slate-400 text-sm">6 AI-selected stocks every trading day at 8:30 AM ET</p>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Risk Managed</h3>
            <p className="text-slate-400 text-sm">Stop losses and target prices for every pick</p>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-blue-400" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Real-Time</h3>
            <p className="text-slate-400 text-sm">Live price tracking and target hit notifications</p>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-rose-500/20 rounded-lg flex items-center justify-center mb-4">
              <BarChart3 className="w-6 h-6 text-rose-400" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Performance</h3>
            <p className="text-slate-400 text-sm">Track win rates and accuracy over time</p>
          </div>
        </div>

        {/* Stats */}
        <div className="text-center py-12 border-t border-slate-800">
          <p className="text-slate-500 text-sm uppercase tracking-wider mb-8">Powered by</p>
          <div className="flex justify-center gap-12 flex-wrap text-slate-400">
            <span>16 AI Agents</span>
            <span>•</span>
            <span>6,960 NASDAQ Stocks</span>
            <span>•</span>
            <span>Self-Learning ML</span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8">
        <div className="container mx-auto px-4 text-center text-slate-500 text-sm">
          © 2024 BullsBears.xyz • Not financial advice
        </div>
      </footer>
    </div>
  );
}