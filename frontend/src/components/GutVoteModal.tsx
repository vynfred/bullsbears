'use client';

import React, { useState, useEffect, useRef } from 'react';
import { MoonAlert } from '@/lib/demoData';
import { TrendingUp, TrendingDown, X } from 'lucide-react';

interface GutVoteModalProps {
  alert: MoonAlert;
  onVote: (vote: 'UP' | 'DOWN' | 'PASS') => void;
  onClose: () => void;
}

export default function GutVoteModal({ alert, onVote, onClose }: GutVoteModalProps) {
  const [timer, setTimer] = useState(5);
  const [hasVoted, setHasVoted] = useState(false);
  const [selectedVote, setSelectedVote] = useState<'UP' | 'DOWN' | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  // Strict 5-second countdown timer
  useEffect(() => {
    if (hasVoted) return;

    timerRef.current = setInterval(() => {
      setTimer((prev) => {
        if (prev <= 1) {
          // Auto-submit as PASS if no vote selected
          handleVote('PASS');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [hasVoted]);

  // Handle vote selection and submission
  const handleVote = (vote: 'UP' | 'DOWN' | 'PASS') => {
    if (hasVoted) return;

    setHasVoted(true);
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    // Brief delay for visual feedback
    setTimeout(() => {
      onVote(vote);
      onClose();
    }, 300);
  };

  // Handle button clicks
  const handleVoteClick = (vote: 'UP' | 'DOWN') => {
    setSelectedVote(vote);
    handleVote(vote);
  };

  // Close modal handler
  const handleClose = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-2xl p-8 text-center max-w-sm w-full border border-cyan-500/30">
        {/* Close Button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-6 h-6" />
        </button>
        {/* Anonymous Stock ID */}
        <div className="mb-6">
          <div className="text-3xl font-bold text-cyan-400 mb-2">
            #{alert.randomId}
          </div>
          <div className="text-sm text-yellow-400 font-medium">
            🔒 ANONYMOUS GUT CHECK
          </div>
        </div>

        {/* Timer */}
        <div className={`text-8xl font-black mb-6 transition-all duration-300 ${
          timer <= 2 ? 'text-red-400 animate-pulse' : 'text-cyan-400'
        }`}>
          {hasVoted ? '✓' : timer}
        </div>

        {/* Instructions */}
        {!hasVoted && (
          <>
            <div className="text-gray-300 text-lg mb-8 font-medium">
              Will this moon? Trust your gut.
            </div>

            {/* Vote Buttons */}
            <div className="flex gap-6 justify-center mb-6">
              <button
                onClick={() => handleVoteClick('DOWN')}
                className={`bg-red-600 text-white px-8 py-6 rounded-2xl text-xl font-bold hover:bg-red-700 transition-all min-w-[120px] flex items-center justify-center gap-3 ${
                  selectedVote === 'DOWN' ? 'scale-110 ring-4 ring-red-400' : ''
                }`}
                disabled={hasVoted}
              >
                <TrendingDown className="w-6 h-6" />
                DOWN
              </button>
              <button
                onClick={() => handleVoteClick('UP')}
                className={`bg-green-600 text-white px-8 py-6 rounded-2xl text-xl font-bold hover:bg-green-700 transition-all min-w-[120px] flex items-center justify-center gap-3 ${
                  selectedVote === 'UP' ? 'scale-110 ring-4 ring-green-400' : ''
                }`}
                disabled={hasVoted}
              >
                <TrendingUp className="w-6 h-6" />
                UP
              </button>
            </div>

            {/* Timer Warning */}
            {timer <= 2 && (
              <div className="text-red-400 text-sm mt-4 animate-pulse font-bold">
                Auto-submit as PASS in {timer}s
              </div>
            )}
          </>
        )}

        {/* Vote Confirmation */}
        {hasVoted && (
          <div className="text-green-400 text-lg font-bold">
            {selectedVote === 'PASS' ? 'No vote recorded' : `Voted ${selectedVote}!`}
          </div>
        )}

        {/* Instructions */}
        <div className="text-xs text-gray-500 mt-6">
          Trust your first instinct • No overthinking
        </div>
      </div>
    </div>
  );
}
