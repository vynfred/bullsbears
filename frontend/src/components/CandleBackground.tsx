import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";

interface Candle {
  id: string;
  x: number;
  y: number;
  direction: "up" | "down";
  size: number;
  speed: number;
  delay: number;
}

interface CandleBackgroundProps {
  flashColor?: "green" | "red" | null;
}

export function CandleBackground({ flashColor = null }: CandleBackgroundProps) {
  const [candles, setCandles] = useState<Candle[]>([]);

  // Generate ambient floating candles continuously
  useEffect(() => {
    const generateCandle = () => {
      const direction = Math.random() > 0.5 ? "up" : "down";
      const newCandle: Candle = {
        id: `candle-${Date.now()}-${Math.random()}`,
        x: Math.random() * 100,
        y: direction === "up" ? 110 : -10,
        direction,
        size: Math.random() * 0.5 + 0.4,
        speed: Math.random() * 20 + 15, // 15-35 seconds
        delay: 0,
      };
      setCandles((prev) => [...prev.slice(-30), newCandle]);
    };

    // Generate initial candles
    for (let i = 0; i < 20; i++) {
      setTimeout(() => generateCandle(), i * 500);
    }

    // Continuously generate new candles
    const interval = setInterval(generateCandle, 1500);
    return () => clearInterval(interval);
  }, []);

  const renderCandle = (candle: Candle) => {
    const bodyHeight = 35 * candle.size;
    const wickTop = 20 * candle.size;
    const wickBottom = 20 * candle.size;
    const bodyWidth = 10 * candle.size;

    // Default colors - more visible for continuous background animation
    let candleColor = "rgba(100, 116, 139, 0.25)";
    let borderColor = "rgba(100, 116, 139, 0.4)";

    // Flash colors
    if (flashColor === "green") {
      candleColor = "rgba(34, 197, 94, 0.3)";
      borderColor = "rgba(34, 197, 94, 0.5)";
    } else if (flashColor === "red") {
      candleColor = "rgba(239, 68, 68, 0.3)";
      borderColor = "rgba(239, 68, 68, 0.5)";
    }

    return (
      <motion.div
        key={candle.id}
        className="absolute"
        initial={{
          left: `${candle.x}%`,
          top: `${candle.y}%`,
          opacity: 0,
        }}
        animate={{
          top: candle.direction === "up" ? "-15%" : "115%",
          opacity: [0, 0.8, 0.8, 0],
        }}
        transition={{
          duration: candle.speed,
          delay: candle.delay,
          ease: "linear",
        }}
        style={{
          width: `${bodyWidth}px`,
        }}
      >
        {/* Candlestick silhouette */}
        <div className="relative flex flex-col items-center">
          {/* Upper wick */}
          <motion.div
            style={{
              width: "2px",
              height: `${wickTop}px`,
            }}
            animate={{
              backgroundColor: borderColor,
            }}
            transition={{
              duration: 0.3,
              ease: "easeInOut",
            }}
          />
          {/* Body */}
          <motion.div
            style={{
              width: `${bodyWidth}px`,
              height: `${bodyHeight}px`,
              borderRadius: "2px",
            }}
            animate={{
              backgroundColor: candleColor,
              borderColor: borderColor,
            }}
            transition={{
              duration: 0.3,
              ease: "easeInOut",
            }}
            className="border-2"
          />
          {/* Lower wick */}
          <motion.div
            style={{
              width: "2px",
              height: `${wickBottom}px`,
            }}
            animate={{
              backgroundColor: borderColor,
            }}
            transition={{
              duration: 0.3,
              ease: "easeInOut",
            }}
          />
        </div>
      </motion.div>
    );
  };

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      <AnimatePresence>
        {candles.map((candle) => renderCandle(candle))}
      </AnimatePresence>
    </div>
  );
}
