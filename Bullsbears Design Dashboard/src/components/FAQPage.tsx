import { HelpCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/accordion";

export function FAQPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <HelpCircle className="w-8 h-8 text-purple-400" />
          <h2 className="text-3xl text-slate-100">Frequently Asked Questions</h2>
        </div>
        <p className="text-slate-400">Find answers to common questions about BullsBears.xyz</p>
      </div>

      <Card className="shadow-xl bg-slate-900/60 border-slate-700">
        <CardContent className="pt-6">
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="item-1" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                How does the AI pick stocks?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Our AI uses advanced machine learning algorithms to analyze thousands of data points including 
                technical indicators, volume patterns, social sentiment, news sentiment, and historical price movements. 
                The system monitors 888 stocks in real-time and generates picks based on high-probability patterns 
                that have historically led to profitable trades.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-2" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                What do the confidence levels mean?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Confidence levels indicate how certain our AI is about a particular pick. High confidence (80%+) 
                means the AI has identified strong signals across multiple indicators. Medium confidence (65-79%) 
                indicates good signals but with more variables. We only show picks above 65% confidence to ensure 
                quality recommendations.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-3" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                How accurate is the AI historically?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Over the past 90 days, our AI has maintained a 92% accuracy rate in identifying profitable trading 
                opportunities. This means that when our AI generates a pick, 92% of the time the stock moves in 
                the predicted direction and reaches the target price within the expected timeframe. You can view 
                detailed historical performance in the Analytics tab.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-4" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                What's the difference between bullish and bearish picks?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Bullish picks are stocks our AI believes will increase in price, making them good candidates for 
                buying or holding. Bearish picks indicate stocks that may decrease in value, which could be 
                opportunities for short selling or avoiding. Each pick includes detailed reasoning and suggested 
                entry/exit points regardless of direction.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-5" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                How should I use the target price and stop loss?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                The target price is the price level our AI predicts the stock will reach, representing your 
                potential profit goal. The stop loss is a suggested price point to exit the trade if it moves 
                against you, helping limit potential losses. These are recommendations based on the AI's analysis, 
                but you should always adjust them based on your own risk tolerance and strategy.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-6" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                How often are picks updated?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                New AI picks are generated multiple times per day as our system continuously monitors market 
                conditions. You'll receive notifications when new high-confidence picks become available. 
                The "Recent Picks" section shows selections from the past 7 days so you can review historical 
                performance and track how picks have developed.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-7" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                Can I track my own portfolio performance?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Yes! Add any picks to your Watchlist to track their performance over time. The Watchlist shows 
                price changes since you added each stock, displays performance graphs, and provides AI alerts 
                when significant events occur. You can also add notes to track your trading decisions and strategies.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-8" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                Is this financial advice?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                No. BullsBears.xyz provides AI-generated insights and analysis for informational and educational 
                purposes only. We are not financial advisors and nothing on this platform should be construed as 
                financial advice. Always conduct your own research, understand the risks involved, and consider 
                consulting with a licensed financial advisor before making investment decisions.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-9" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                What makes your AI different from others?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Our AI combines multiple specialized models rather than relying on a single approach. We analyze 
                technical indicators, sentiment from thousands of sources, institutional trading patterns, and 
                proprietary pattern recognition algorithms. The system is continuously learning and improving 
                based on market conditions and historical performance, adapting to changing market dynamics.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-10" className="border-slate-700">
              <AccordionTrigger className="text-slate-200 hover:text-slate-100">
                How do I get started?
              </AccordionTrigger>
              <AccordionContent className="text-slate-400">
                Simply browse the AI Picks tab to see today's recommendations. Click on any pick to view detailed 
                analysis including reasoning, target prices, and stop losses. Add picks you're interested in to 
                your Watchlist to track them. Review the Analytics tab to understand the AI's historical performance 
                and confidence distribution. Start with high-confidence picks and always use proper risk management.
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>
    </div>
  );
}
