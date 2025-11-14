// src/components/private/AnalyticsTab.tsx
'use client';

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "../ui/carousel";
import { useModelAccuracy, useRecentOutcomes, useAccuracyTrend } from "../../hooks/useRealData";
import { useStatistics } from "../../hooks/useStatistics";

interface AnalyticsTabProps {
  onNavigateToPicks: () => void;
}

type TimePeriod = "7d" | "30d" | "90d";

const chartConfig = {
  accuracy: {
    label: "Accuracy",
    color: "hsl(217, 91%, 60%)"
  }
};

export default function AnalyticsTab({ onNavigateToPicks }: AnalyticsTabProps) {
  const [countdown, setCountdown] = useState({
    hours: 6,
    minutes: 12,
    seconds: 3
  });
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("30d");

  const { accuracyData, isLoading: accuracyLoading, error: accuracyError } = useModelAccuracy();
  const { outcomes, isLoading: outcomesLoading } = useRecentOutcomes();
  const { trendData, isLoading: trendLoading } = useAccuracyTrend(timePeriod);
  const { badgeData } = useStatistics();

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        let { hours, minutes, seconds } = prev;
        
        if (seconds > 0) {
          seconds--;
        } else if (minutes > 0) {
          minutes--;
          seconds = 59;
        } else if (hours > 0) {
          hours--;
          minutes = 59;
          seconds = 59;
        }
        
        return { hours, minutes, seconds };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-6">
      {/* 1. Model Accuracy Badge - Circular */}
      <div className="flex justify-center">
        <div className="relative">
          <motion.div
            animate={{
              scale: [1, 1.05, 1],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="w-48 h-48 rounded-full bg-gradient-to-br from-emerald-500 via-blue-500 to-purple-500 p-1 shadow-2xl"
          >
            <div className="w-full h-full rounded-full flex flex-col items-center justify-center relative" style={{ backgroundColor: 'var(--bg-primary)' }}>
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-emerald-500/5 via-blue-500/5 to-purple-500/5"></div>
              <div className="relative z-10 flex flex-col items-center justify-center h-full">
                {accuracyLoading ? (
                  <div className="text-2xl text-blue-400">Loading...</div>
                ) : accuracyError ? (
                  <div className="text-2xl text-red-400">Error</div>
                ) : (
                  <>
                    <div className="text-4xl text-blue-400">
                      {accuracyData?.overall_accuracy ? `${accuracyData.overall_accuracy.toFixed(1)}%` : '0.0%'}
                    </div>
                    <div className="text-xs text-blue-400">MODEL ACCURACY</div>
                    <div className="flex items-center gap-1 text-emerald-400 text-sm mt-1">
                      <TrendingUp className="w-3 h-3" />
                      ↑{badgeData?.analytics_tab?.precision ? (badgeData.analytics_tab.precision - 60).toFixed(1) : '0.0'}%
                    </div>
                    <div className="text-xs text-blue-400 mt-2">
                      ({accuracyData?.total_predictions || 0} total picks)
                    </div>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Header */}
      <div className="text-center">
        <p className="text-slate-400">
          Real-time insights into our AI / ML model
        </p>
      </div>

      <div className="text-center space-y-1">
        <p className="text-slate-400 text-sm">Last retrain: Nov 6, 2025 at 8:30 AM</p>
        <p className="flex items-center justify-center gap-2 text-sm">
          <span className="text-slate-400">Next retrain in</span>
          <span className="font-mono text-blue-400">
            {countdown.hours}h {countdown.minutes.toString().padStart(2, '0')}m {countdown.seconds.toString().padStart(2, '0')}s
          </span>
        </p>
      </div>

      {/* 2. Accuracy Over Time */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-center text-slate-100">Accuracy Over Time</CardTitle>
          <CardDescription className="text-center text-slate-400">Rolling accuracy trend</CardDescription>
        </CardHeader>
        <CardContent className="px-0 pb-4">
          <ChartContainer className="h-[300px] w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData.map(point => ({
                date: new Date(point.date).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' }),
                accuracy: point.accuracy,
                picks: point.total_picks,
                bullishAccuracy: point.bullish_accuracy,
                bearishAccuracy: point.bearish_accuracy
              }))} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
                <XAxis 
                  dataKey="date" 
                  stroke="rgba(148, 163, 184, 0.6)"
                  tick={{ fontSize: 11, fill: 'rgba(148, 163, 184, 0.8)' }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis 
                  domain={[65, 75]} 
                  stroke="rgba(148, 163, 184, 0.6)"
                  tick={{ fontSize: 11, fill: 'rgba(148, 163, 184, 0.8)' }}
                  width={45}
                />
                <ChartTooltip
  content={
    <ChartTooltipContent
      formatter={(value: any, name: any) => {
        if (name === 'accuracy') {
          return [`${value.toFixed(1)}%`, 'Model Accuracy'];
        }
        return [value, name];
      }}
      labelFormatter={(label) => {
        const dataPoint = trendData.find(d =>
          new Date(d.date).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' }) === label
        );
        const picks = dataPoint?.total_picks || 0;
        const bullish = dataPoint?.bullish_accuracy || 0;
        const bearish = dataPoint?.bearish_accuracy || 0;
        return `${label}: ${picks} picks (${bullish.toFixed(1)}% bullish, ${bearish.toFixed(1)}% bearish)`;
      }}
    />
  }
/>
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#60a5fa"
                  strokeWidth={3}
                  dot={(props: any) => {
                    const { cx, cy, payload, index } = props;
                    const chartData = trendData.map(point => ({
                      date: new Date(point.date).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' }),
                      accuracy: point.accuracy,
                      picks: point.total_picks,
                      bullishAccuracy: point.bullish_accuracy,
                      bearishAccuracy: point.bearish_accuracy
                    }));
                    const isLastPoint = index === chartData.length - 1;

                    if (!isLastPoint) return <></>;

                    return (
                      <motion.circle
                        key={`accuracy-glow-dot-${index}-${payload?.date || 'unknown'}`}
                        cx={cx}
                        cy={cy}
                        r={6}
                        fill="#60a5fa"
                        stroke="#1e293b"
                        strokeWidth={2}
                        animate={{
                          opacity: [1, 0.4, 1],
                          scale: [1, 1.3, 1],
                        }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                          ease: "easeInOut",
                        }}
                      />
                    );
                  }}
                  activeDot={{
                    r: 8,
                    fill: '#60a5fa',
                    strokeWidth: 2,
                    stroke: '#1e293b'
                  }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>

        {/* Time Period Selector Below Chart */}
        <div className="px-4 pb-4">
          <div className="flex gap-2 justify-center">
            <Button
              size="sm"
              variant={timePeriod === "7d" ? "default" : "outline"}
              onClick={() => setTimePeriod("7d")}
              className="shadow-md"
            >
              7D
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "30d" ? "default" : "outline"}
              onClick={() => setTimePeriod("30d")}
              className="shadow-md"
            >
              30D
            </Button>
            <Button
              size="sm"
              variant={timePeriod === "90d" ? "default" : "outline"}
              onClick={() => setTimePeriod("90d")}
              className="shadow-md"
            >
              90D
            </Button>
          </div>
        </div>
      </Card>

      {/* 3. Confidence Tiers - REMOVED MOCK DATA */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">Confidence Tiers</CardTitle>
          <CardDescription className="text-center text-slate-400">Performance by confidence level (relative scale)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-2">
              <p className="text-slate-400">No confidence tier data available</p>
              <p className="text-slate-500 text-sm">Data will appear once the backend is running</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 4. What We Track */}
      <Card className="shadow-xl bg-gradient-to-br from-cyan-950/60 via-slate-900/40 to-blue-950/30 border-2 border-cyan-700/40">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">What We Track</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center">
            <div className="text-cyan-400 mb-1">TECHNICAL</div>
            <p className="text-slate-400 text-sm">42 indicators • volume surge • RSI • MACD • Bollinger bands</p>
          </div>
          <div className="text-center">
            <div className="text-purple-400 mb-1">SOCIAL</div>
            <p className="text-slate-400 text-sm">1.2M X posts • Grok+DeepSeek sentiment • CEO activity spikes</p>
          </div>
          <div className="text-center">
            <div className="text-pink-400 mb-1">ECONOMIC</div>
            <p className="text-slate-400 text-sm">Fed policy • CPI data • yield curve • VIX volatility pops</p>
          </div>
        </CardContent>
      </Card>

      {/* 5. Screening Scale - REMOVED MOCK DATA */}
      <Card className="shadow-xl bg-gradient-to-br from-slate-900/60 via-slate-800/40 to-slate-900/30 border-2 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">Screening Scale</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-center">
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <p className="text-slate-400">No screening data available</p>
              <p className="text-slate-500 text-sm">Data will appear once the backend is running</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 6. All Time Best Wins */}
      <Card className="shadow-xl bg-gradient-to-br from-emerald-950/60 via-slate-900/40 to-teal-950/30 border-2 border-emerald-700/40">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">All Time Best Wins</CardTitle>
          <CardDescription className="text-center text-slate-400">Top performing predictions</CardDescription>
        </CardHeader>
        <CardContent>
          {outcomesLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-slate-400">Loading recent outcomes...</div>
            </div>
          ) : outcomes.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-slate-400">No recent outcomes available</div>
            </div>
          ) : (
            <Carousel className="w-full">
              <CarouselContent>
                {outcomes.map((outcome) => (
                  <CarouselItem key={outcome.id} className="md:basis-1/2 lg:basis-1/3">
                    <Card className={`shadow-lg border-2 ${outcome.outcome === 'win' ? 'border-emerald-500/50 bg-gradient-to-br from-emerald-950/50 to-emerald-900/30' : 'border-rose-500/50 bg-gradient-to-br from-rose-950/50 to-rose-900/30'}`}>
                      <CardContent className="p-6 text-center">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-2xl text-slate-100">{outcome.symbol}</span>
                            <Badge variant={outcome.outcome === 'win' ? 'default' : 'destructive'} className={outcome.outcome === 'win' ? 'bg-emerald-600' : 'bg-rose-600'}>
                              {outcome.confidence.toFixed(0)}%
                            </Badge>
                          </div>
                          <div className={`flex items-center justify-center gap-2 ${outcome.outcome === 'win' ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {outcome.outcome === 'win' ? (
                              <TrendingUp className="w-5 h-5" />
                            ) : (
                              <TrendingDown className="w-5 h-5" />
                            )}
                            <span className="text-2xl">
                              {outcome.change_percent >= 0 ? '+' : ''}{outcome.change_percent.toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-slate-400">in {outcome.days_to_outcome}d</p>
                          {outcome.outcome === 'win' && outcome.change_percent > 20 && <p className="text-emerald-400">MOON</p>}
                          {outcome.outcome === 'loss' && outcome.change_percent < -20 && <p className="text-rose-400">RUG</p>}
                        </div>
                      </CardContent>
                    </Card>
                  </CarouselItem>
                ))}
              </CarouselContent>
              <CarouselPrevious className="bg-slate-800 border-slate-600 hover:bg-slate-700" />
              <CarouselNext className="bg-slate-800 border-slate-600 hover:bg-slate-700" />
            </Carousel>
          )}
        </CardContent>
      </Card>

      {/* 7. One-Tap Footer */}
      <div className="flex justify-center py-4">
        <motion.div
          animate={{
            scale: [1, 1.08, 1],
            boxShadow: [
              "0 0 20px rgba(16, 185, 129, 0.3)",
              "0 0 40px rgba(16, 185, 129, 0.6)",
              "0 0 20px rgba(16, 185, 129, 0.3)"
            ]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <Button 
            size="lg" 
            className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white shadow-2xl px-8 py-6"
            onClick={onNavigateToPicks}
          >
            SEE RECENT PICKS
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </motion.div>
      </div>
    </div>
  );
}