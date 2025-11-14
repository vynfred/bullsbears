import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { HistoryEntry } from '../../lib/types';

interface PicksCarouselProps {
  entries: HistoryEntry[];
  onCardClick: (entry: HistoryEntry) => void;
}

const PicksCarousel: React.FC<PicksCarouselProps> = ({ entries, onCardClick }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isScrolling, setIsScrolling] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);

  const getClassificationColor = (classification: string) => {
    switch (classification) {
      case 'MOON': return 'text-green-600 bg-green-100';
      case 'PARTIAL_MOON': return 'text-green-500 bg-green-50';
      case 'WIN': return 'text-blue-600 bg-blue-100';
      case 'MISS': return 'text-gray-600 bg-gray-100';
      case 'RUG': return 'text-red-600 bg-red-100';
      case 'NUCLEAR_RUG': return 'text-red-700 bg-red-200';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const formatPrice = (price: number) => `$${price.toFixed(0)}`;
  const formatPercent = (pct: number) => `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`;

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.targetTouches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.targetTouches[0].clientX;
  };

  const handleTouchEnd = () => {
    if (!touchStartX.current || !touchEndX.current) return;
    
    const distance = touchStartX.current - touchEndX.current;
    const isLeftSwipe = distance > 50;
    const isRightSwipe = distance < -50;

    if (isLeftSwipe && currentIndex < entries.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
    if (isRightSwipe && currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const scrollToIndex = (index: number) => {
    if (scrollContainerRef.current) {
      const cardWidth = 280; // Card width + gap
      scrollContainerRef.current.scrollTo({
        left: index * cardWidth,
        behavior: 'smooth'
      });
    }
  };

  useEffect(() => {
    scrollToIndex(currentIndex);
  }, [currentIndex]);

  if (entries.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 text-center">
        <div className="text-gray-400 text-lg mb-2">Your Pulse is quiet</div>
        <div className="text-gray-500 text-sm">Do a gut check to see your edge.</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Your Picks</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
            disabled={currentIndex === 0}
            className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-gray-400">
            {currentIndex + 1} of {entries.length}
          </span>
          <button
            onClick={() => setCurrentIndex(Math.min(entries.length - 1, currentIndex + 1))}
            disabled={currentIndex === entries.length - 1}
            className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Carousel */}
      <div
        ref={scrollContainerRef}
        className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 -mx-4 px-4"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {entries.map((entry, index) => (
          <div
            key={entry.id}
            className={`flex-shrink-0 w-64 bg-gray-700 rounded-lg p-4 cursor-pointer transition-all duration-200 ${
              index === currentIndex ? 'ring-2 ring-blue-400 shadow-lg' : 'hover:bg-gray-600'
            }`}
            onClick={() => onCardClick(entry)}
          >
            {/* Header Row */}
            <div className="flex items-center justify-between mb-3">
              <div className="text-lg font-bold text-white">
                {entry.ticker}
              </div>
              <div className="flex items-center gap-2">
                <div className={`text-lg font-bold ${
                  entry.actual_percent >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {formatPercent(entry.actual_percent)}
                </div>
                <div className={`px-2 py-1 rounded text-xs font-bold ${getClassificationColor(entry.classification)}`}>
                  {entry.classification.replace('_', ' ')}
                </div>
              </div>
            </div>

            {/* Price Row */}
            <div className="flex items-center justify-between mb-3 text-sm">
              <div>
                <span className="text-gray-400">Entry </span>
                <span className="text-white font-medium">{formatPrice(entry.entry_price)}</span>
              </div>
              <div>
                <span className="text-gray-400">Now </span>
                <span className="text-white font-medium">{formatPrice(entry.current_price)}</span>
              </div>
            </div>

            {/* Details Row */}
            <div className="flex items-center justify-between text-sm">
              <div>
                <span className="text-gray-400">Days: </span>
                <span className="text-white font-medium">{entry.days_to_hit}</span>
              </div>
              <div>
                <span className="text-gray-400">AI: </span>
                <span className="font-medium text-cyan-400">
                  {entry.ai_confidence}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Dots Indicator */}
      <div className="flex items-center justify-center gap-2 mt-4">
        {entries.map((_, index) => (
          <button
            key={index}
            onClick={() => setCurrentIndex(index)}
            className={`w-2 h-2 rounded-full transition-colors ${
              index === currentIndex ? 'bg-blue-400' : 'bg-gray-600 hover:bg-gray-500'
            }`}
          />
        ))}
      </div>
    </div>
  );
};

export default PicksCarousel;
