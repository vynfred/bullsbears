import { Brain, TrendingUp, Eye, LineChart, Zap, Shield, Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

export function HowItWorksPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-3xl text-slate-100">How BullsBears.xyz Works</h2>
        <p className="text-slate-400">AI-powered stock picks to help you make smarter trades</p>
      </div>

      {/* Overview */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-blue-950/30 border-2 border-purple-700/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-center justify-center text-slate-100">
            <Brain className="w-6 h-6 text-purple-400" />
            AI-Powered Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <p className="text-slate-300 leading-relaxed">
            Our advanced machine learning algorithms analyze thousands of data points including market sentiment, 
            technical indicators, volume patterns, news sentiment, and historical trends to identify high-probability 
            trading opportunities.
          </p>
          <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/50">
            92% Historical Accuracy
          </Badge>
        </CardContent>
      </Card>

      {/* The Process */}
      <div className="space-y-4">
        <h3 className="text-xl text-slate-100 text-center">The Process</h3>
        
        {/* Step 1 */}
        <Card className="shadow-lg bg-gradient-to-br from-emerald-950/60 via-slate-900/40 to-teal-950/30 border-2 border-emerald-700/40">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 text-white shrink-0">
                1
              </div>
              <div className="flex-1">
                <h4 className="text-lg text-slate-100 mb-2 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-emerald-400" />
                  Data Collection
                </h4>
                <p className="text-slate-300 text-sm leading-relaxed">
                  Our AI monitors 888 stocks in real-time, analyzing price movements, volume, social sentiment, 
                  news articles, earnings reports, and institutional trading patterns.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 2 */}
        <Card className="shadow-lg bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 text-white shrink-0">
                2
              </div>
              <div className="flex-1">
                <h4 className="text-lg text-slate-100 mb-2 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  AI Analysis
                </h4>
                <p className="text-slate-300 text-sm leading-relaxed">
                  Multiple machine learning models work together to identify patterns, anomalies, and opportunities. 
                  Each signal is scored based on confidence level and potential risk/reward ratio.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 3 */}
        <Card className="shadow-lg bg-gradient-to-br from-blue-950/60 via-slate-900/40 to-cyan-950/30 border-2 border-blue-700/40">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 text-white shrink-0">
                3
              </div>
              <div className="flex-1">
                <h4 className="text-lg text-slate-100 mb-2 flex items-center gap-2">
                  <Target className="w-5 h-5 text-blue-400" />
                  Pick Generation
                </h4>
                <p className="text-slate-300 text-sm leading-relaxed">
                  High-scoring opportunities are packaged with entry prices, target prices, stop losses, 
                  and detailed reasoning. Only picks meeting strict criteria are presented to you.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Features */}
      <Card className="shadow-xl bg-slate-900/60 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 text-center">Key Features</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3">
            <TrendingUp className="w-5 h-5 text-emerald-400 mt-1" />
            <div>
              <h5 className="text-slate-200 mb-1">AI Picks</h5>
              <p className="text-sm text-slate-400">
                Get daily AI-generated stock picks with confidence scores, entry points, and price targets
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <Eye className="w-5 h-5 text-purple-400 mt-1" />
            <div>
              <h5 className="text-slate-200 mb-1">Watchlist</h5>
              <p className="text-sm text-slate-400">
                Track your favorite picks, monitor performance, and receive alerts when conditions change
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <LineChart className="w-5 h-5 text-blue-400 mt-1" />
            <div>
              <h5 className="text-slate-200 mb-1">Analytics</h5>
              <p className="text-sm text-slate-400">
                View historical accuracy, confidence distribution, and track the AI model's performance over time
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-rose-400 mt-1" />
            <div>
              <h5 className="text-slate-200 mb-1">Risk Management</h5>
              <p className="text-sm text-slate-400">
                Every pick includes suggested stop losses and risk/reward ratios to help you manage your portfolio
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Disclaimer */}
      <Card className="shadow-lg bg-gradient-to-br from-amber-950/60 via-slate-900/40 to-orange-950/30 border-2 border-amber-700/40">
        <CardContent className="pt-6 text-center">
          <p className="text-sm text-slate-400 leading-relaxed">
            <strong className="text-amber-400">Disclaimer:</strong> BullsBears.xyz provides AI-generated insights for 
            informational purposes only. Past performance does not guarantee future results. Always conduct your own 
            research and consider your risk tolerance before making investment decisions.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
