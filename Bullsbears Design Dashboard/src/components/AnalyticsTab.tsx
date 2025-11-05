import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import { motion } from "motion/react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "./ui/chart";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "./ui/carousel";

interface AnalyticsTabProps {
  onNavigateToPicks: () => void;
}

const accuracyOverTimeData = [
  { date: "8/7", accuracy: 68.2 },
  { date: "8/21", accuracy: 69.1 },
  { date: "9/4", accuracy: 68.8 },
  { date: "9/18", accuracy: 70.4 },
  { date: "10/2", accuracy: 71.2 },
  { date: "10/16", accuracy: 71.8 },
  { date: "11/5", accuracy: 72.4 }
];

const chartConfig = {
  accuracy: {
    label: "Accuracy",
    color: "hsl(217, 91%, 60%)"
  }
};

const recentWinsLosses = [
  { symbol: "NVDA", change: 31.2, time: "36h", confidence: 92, type: "win" },
  { symbol: "COIN", change: -28.4, time: "48h", confidence: 68, type: "loss" },
  { symbol: "TSLA", change: 18.7, time: "24h", confidence: 75, type: "win" },
  { symbol: "AMD", change: 22.3, time: "60h", confidence: 85, type: "win" },
  { symbol: "HOOD", change: -15.2, time: "72h", confidence: 71, type: "loss" },
  { symbol: "MSFT", change: 12.8, time: "18h", confidence: 90, type: "win" }
];

type TimePeriod = "7d" | "30d" | "90d";

export function AnalyticsTab({ onNavigateToPicks }: AnalyticsTabProps) {
  const [countdown, setCountdown] = useState({
    hours: 6,
    minutes: 12,
    seconds: 3
  });
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("90d");

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
            <div className="w-full h-full rounded-full bg-slate-900 flex flex-col items-center justify-center">
              <div className="text-4xl text-blue-400">72.4%</div>
              <div className="text-xs text-slate-400">MODEL ACCURACY</div>
              <div className="flex items-center gap-1 text-emerald-400 text-sm mt-1">
                <TrendingUp className="w-3 h-3" />
                ↑0.8%
              </div>
              <div className="text-xs text-slate-500 mt-2">(145 total picks)</div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Header */}
      <div className="text-center">
        <p className="text-slate-400">
          Real-time insights into our AI model's performance
        </p>
      </div>

      <Card className="shadow-xl bg-gradient-to-br from-slate-900/60 via-slate-800/40 to-slate-900/30 border-2 border-slate-700/50">
        <CardContent className="pt-6 text-center">
          <div className="space-y-1">
            <p className="text-slate-400 text-sm">Last retrain 2h 14m ago</p>
            <p className="flex items-center justify-center gap-2 text-sm">
              <span className="text-slate-400">Next retrain in</span>
              <span className="font-mono text-blue-400">
                {countdown.hours}h {countdown.minutes.toString().padStart(2, '0')}m {countdown.seconds.toString().padStart(2, '0')}s
              </span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 2. Accuracy Over Time */}
      <Card className="shadow-xl bg-gradient-to-br from-blue-950/60 via-slate-900/40 to-indigo-950/30 border-2 border-blue-700/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-center text-slate-100">Accuracy Over Time</CardTitle>
          <CardDescription className="text-center text-slate-400">Rolling accuracy trend</CardDescription>
          
          {/* Time Period Selector */}
          <div className="flex gap-2 justify-center pt-3">
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
        </CardHeader>
        <CardContent className="px-0 pb-4">
          <ChartContainer config={chartConfig} className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={accuracyOverTimeData} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
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
                  content={<ChartTooltipContent />}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#60a5fa"
                  strokeWidth={3}
                  dot={{ r: 5, fill: '#60a5fa', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* 3. Confidence Tiers */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">Confidence Tiers</CardTitle>
          <CardDescription className="text-center text-slate-400">Performance by confidence level (relative scale)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-200">High 80–92%</span>
                <span className="text-emerald-400">88% hit (12/14)</span>
              </div>
              <div className="h-10 bg-slate-800/50 rounded-lg overflow-hidden relative shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: '88%' }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-lg shadow-lg"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-200">Med 65–79%</span>
                <span className="text-yellow-400">71% hit (17/24)</span>
              </div>
              <div className="h-10 bg-slate-800/50 rounded-lg overflow-hidden relative shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: '71%' }}
                  transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                  className="h-full bg-gradient-to-r from-yellow-500 to-amber-400 rounded-lg shadow-lg"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-200">Low 55–64%</span>
                <span className="text-orange-400">52% hit (11/21)</span>
              </div>
              <div className="h-10 bg-slate-800/50 rounded-lg overflow-hidden relative shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: '52%' }}
                  transition={{ duration: 1, ease: "easeOut", delay: 0.4 }}
                  className="h-full bg-gradient-to-r from-orange-500 to-orange-400 rounded-lg shadow-lg"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-700/50 space-y-1 text-center">
            <p className="text-slate-400 text-sm">Relative scale • Today's ceiling = 92% (NVDA)</p>
            <p className="text-slate-400 text-sm">Yesterday's max was 89%. Scale adjusts with market conditions.</p>
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

      {/* 5. Screening Scale */}
      <Card className="shadow-xl bg-gradient-to-br from-slate-900/60 via-slate-800/40 to-slate-900/30 border-2 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">Screening Scale</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-center">
          <div className="flex items-center justify-between px-4">
            <span className="text-slate-400">Stocks monitored</span>
            <span className="text-blue-400">888</span>
          </div>
          <div className="flex items-center justify-between px-4">
            <span className="text-slate-400">Bullish events detected</span>
            <span className="text-emerald-400">2,076</span>
          </div>
          <div className="flex items-center justify-between px-4">
            <span className="text-slate-400">Bearish events detected</span>
            <span className="text-rose-400">1,020</span>
          </div>
        </CardContent>
      </Card>

      {/* 6. 24H Wins & Misses */}
      <Card className="shadow-xl bg-gradient-to-br from-emerald-950/60 via-slate-900/40 to-teal-950/30 border-2 border-emerald-700/40">
        <CardHeader>
          <CardTitle className="text-center text-slate-100">24H Wins & Misses</CardTitle>
          <CardDescription className="text-center text-slate-400">Auto-rotating recent performance</CardDescription>
        </CardHeader>
        <CardContent>
          <Carousel className="w-full">
            <CarouselContent>
              {recentWinsLosses.map((item, index) => (
                <CarouselItem key={index} className="md:basis-1/2 lg:basis-1/3">
                  <Card className={`shadow-lg border-2 ${item.type === 'win' ? 'border-emerald-500/50 bg-gradient-to-br from-emerald-950/50 to-emerald-900/30' : 'border-rose-500/50 bg-gradient-to-br from-rose-950/50 to-rose-900/30'}`}>
                    <CardContent className="p-6 text-center">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-2xl text-slate-100">{item.symbol}</span>
                          <Badge variant={item.type === 'win' ? 'default' : 'destructive'} className={item.type === 'win' ? 'bg-emerald-600' : 'bg-rose-600'}>
                            {item.confidence}%
                          </Badge>
                        </div>
                        <div className={`flex items-center justify-center gap-2 ${item.type === 'win' ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {item.type === 'win' ? (
                            <TrendingUp className="w-5 h-5" />
                          ) : (
                            <TrendingDown className="w-5 h-5" />
                          )}
                          <span className="text-2xl">
                            {item.change >= 0 ? '+' : ''}{item.change}%
                          </span>
                        </div>
                        <p className="text-slate-400">in {item.time}</p>
                        {item.type === 'win' && <p className="text-emerald-400">MOON</p>}
                        {item.type === 'loss' && <p className="text-rose-400">RUG</p>}
                      </div>
                    </CardContent>
                  </Card>
                </CarouselItem>
              ))}
            </CarouselContent>
            <CarouselPrevious className="bg-slate-800 border-slate-600 hover:bg-slate-700" />
            <CarouselNext className="bg-slate-800 border-slate-600 hover:bg-slate-700" />
          </Carousel>
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
