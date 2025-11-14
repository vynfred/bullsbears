// src/components/shared/CleanStockCard.tsx
'use client';

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StockPick } from '@/lib/types';

interface CleanStockCardProps {
  pick: StockPick;
  onClick?: () => void;
}

export default function CleanStockCard({ pick, onClick }: CleanStockCardProps) {
  const isBullish = pick.sentiment === 'bullish';
  const change = pick.change?.toFixed(2) ?? '0.00';

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
            {pick.symbol}
          </CardTitle>
          <Badge variant={isBullish ? 'default' : 'destructive'}>
            {isBullish ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
            {isBullish ? 'BULLISH' : 'BEARISH'}
          </Badge>
        </div>
        <p className="text-sm text-gray-400">{pick.company_name}</p>
      </CardHeader>

      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Current</p>
            <p className="text-xl font-semibold text-white">
              ${pick.current_price?.toFixed(2) ?? '—'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Change</p>
            <p className={Number(change) >= 0 ? 'text-emerald-400' : 'text-red-400'}>
              {Number(change) >= 0 ? '+' : ''}{change}%
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}