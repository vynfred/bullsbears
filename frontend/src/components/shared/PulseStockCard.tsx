// src/components/shared/PulseStockCard.tsx
'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StockPick } from '@/lib/types';

interface PulseStockCardProps {
  alert: StockPick;
  onClick?: () => void;
}

export default function PulseStockCard({ alert, onClick }: PulseStockCardProps) {
  const alertTime = React.useMemo(() => {
    try {
      const d = new Date(alert.timestamp);
      return d.toLocaleString('en-US', {
        month: 'numeric',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        hour12: true,
      });
    } catch {
      return '—';
    }
  }, [alert.timestamp]);

  const isBullish = alert.sentiment === 'bullish';
  const change = alert.change?.toFixed(2) ?? '0.00';
  const changeSign = Number(change) >= 0 ? '+' : '';

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-lg ${
        isBullish ? 'border-emerald-500' : 'border-red-500'
      }`}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-bold text-white">
            {alert.symbol}
          </CardTitle>
          <Badge variant={isBullish ? 'default' : 'destructive'} className="text-xs">
            {isBullish ? (
              <TrendingUp className="w-3 h-3 mr-1" />
            ) : (
              <TrendingDown className="w-3 h-3 mr-1" />
            )}
            {isBullish ? 'BULLISH' : 'BEARISH'}
          </Badge>
        </div>
        <p className="text-sm text-gray-400">
          {alert.company_name}
        </p>
      </CardHeader>

      <CardContent className="space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Current</p>
            <p className="text-xl font-semibold text-white">
              ${alert.current_price?.toFixed(2) ?? '—'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Change</p>
            <p
              className={`text-lg font-medium ${
                Number(change) >= 0 ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              {changeSign}{change}%
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500">AI Confidence</p>
          <p className="text-sm font-medium text-white">
            {alert.confidence?.toFixed(0) ?? '—'}%
          </p>
        </div>

        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="w-3 h-3" />
          <span>{alertTime}</span>
        </div>
      </CardContent>
    </Card>
  );
}