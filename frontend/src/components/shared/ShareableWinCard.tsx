// src/components/shared/ShareableWinCard.tsx
'use client';

import React from 'react';
import { TrendingUp, Share2, Download } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StockPick } from '@/lib/types';
import html2canvas from 'html2canvas';

interface ShareableWinCardProps {
  pick: StockPick;
}

export default function ShareableWinCard({ pick }: ShareableWinCardProps) {
  const cardRef = React.useRef<HTMLDivElement>(null);

  const downloadImage = async () => {
    if (!cardRef.current) return;
    const canvas = await html2canvas(cardRef.current);
    const link = document.createElement('a');
    link.download = `${pick.symbol}-win.png`;
    link.href = canvas.toDataURL();
    link.click();
  };

  const share = async () => {
    if (navigator.share && cardRef.current) {
      const canvas = await html2canvas(cardRef.current);
      canvas.toBlob(async (blob) => {
        if (!blob) return;
        const file = new File([blob], `${pick.symbol}-win.png`, { type: 'image/png' });
        await navigator.share({ files: [file], title: `BullsBears Win – ${pick.symbol}` });
      });
    } else {
      downloadImage();
    }
  };

  const change = pick.change?.toFixed(2) ?? '0.00';
  const isPositive = Number(change) >= 0;

  return (
    <div ref={cardRef} className="bg-gradient-to-br from-emerald-900 to-emerald-700 p-6 rounded-xl text-white max-w-sm mx-auto">
      <Card className="bg-transparent border-none shadow-none">
        <CardHeader className="pb-3 text-center">
          <div className="flex justify-center mb-2">
            <TrendingUp className="w-10 h-10 text-emerald-300" />
          </div>
          <CardTitle className="text-2xl font-bold">WIN!</CardTitle>
          <p className="text-lg">{pick.symbol}</p>
          <p className="text-sm opacity-80">{pick.company_name}</p>
        </CardHeader>

        <CardContent className="space-y-3 text-center">
          <div>
            <p className="text-4xl font-bold">{isPositive ? '+' : ''}{change}%</p>
            <p className="text-sm opacity-80">Return since alert</p>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="opacity-80">Entry</p>
              <p className="font-medium">${pick.entry_price?.toFixed(2) ?? '—'}</p>
            </div>
            <div>
              <p className="opacity-80">Current</p>
              <p className="font-medium">${pick.current_price?.toFixed(2) ?? '—'}</p>
            </div>
          </div>

          <div className="pt-2">
            <p className="text-xs opacity-70">
              AI Confidence: {pick.confidence?.toFixed(0) ?? '—'}%
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-center gap-3 mt-4">
        <Button size="sm" variant="secondary" onClick={share}>
          <Share2 className="w-4 h-4 mr-1" />
          Share
        </Button>
        <Button size="sm" variant="secondary" onClick={downloadImage}>
          <Download className="w-4 h-4 mr-1" />
          Save
        </Button>
      </div>
    </div>
  );
}