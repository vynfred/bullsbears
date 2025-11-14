// src/components/shared/WhyModal.tsx
'use client';

import React from 'react';
import { X, Lightbulb, TrendingUp } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { StockPick } from '@/lib/types';

interface WhyModalProps {
  pick: StockPick | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function WhyModal({ pick, open, onOpenChange }: WhyModalProps) {
  if (!pick) return null;

  const reasons = (pick.reasons ?? []).filter(Boolean);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg bg-gray-900 text-white border-gray-700">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Lightbulb className="w-6 h-6 text-yellow-400" />
            Why {pick.symbol}?
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            AI reasoning behind this {pick.sentiment} pick
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {reasons.length > 0 ? (
            reasons.map((reason, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-800 border border-gray-700"
              >
                <TrendingUp className="w-5 h-5 text-emerald-400 mt-0.5" />
                <p className="text-sm">{reason}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-400 italic">
              No detailed reasoning available.
            </p>
          )}

          <div className="flex items-center justify-between pt-2 text-xs text-gray-500">
            <span>Confidence: {pick.confidence?.toFixed(0) ?? '—'}%</span>
            <span>
              Alerted:{' '}
              {new Date(pick.timestamp).toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: 'numeric',
                hour12: true,
              })}
            </span>
          </div>
        </div>

        <div className="flex justify-end mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            <X className="w-4 h-4 mr-1" />
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}