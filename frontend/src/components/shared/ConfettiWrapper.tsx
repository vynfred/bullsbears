'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import react-confetti to avoid SSR issues
const Confetti = dynamic(() => import('react-confetti'), {
  ssr: false,
  loading: () => null
});

interface ConfettiWrapperProps {
  children: React.ReactNode;
}

export function ConfettiWrapper({ children }: ConfettiWrapperProps) {
  const [showConfetti, setShowConfetti] = useState(false);
  const [windowDimensions, setWindowDimensions] = useState({
    width: 0,
    height: 0
  });

  // Handle window resize
  useEffect(() => {
    const updateDimensions = () => {
      setWindowDimensions({
        width: window.innerWidth,
        height: window.innerHeight
      });
    };

    // Set initial dimensions
    updateDimensions();

    // Add resize listener
    window.addEventListener('resize', updateDimensions);
    
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Listen for confetti trigger events
  useEffect(() => {
    const handleConfettiTrigger = (event: CustomEvent) => {
      console.log('🎊 Confetti event received:', event.detail);
      setShowConfetti(true);
      
      // Auto-hide confetti after duration
      const duration = event.detail?.duration || 3000;
      setTimeout(() => {
        setShowConfetti(false);
      }, duration);
    };

    // Add event listener for confetti triggers
    window.addEventListener('triggerConfetti', handleConfettiTrigger as EventListener);
    
    return () => {
      window.removeEventListener('triggerConfetti', handleConfettiTrigger as EventListener);
    };
  }, []);

  return (
    <>
      {children}
      {showConfetti && (
        <Confetti
          width={windowDimensions.width}
          height={windowDimensions.height}
          recycle={false}
          numberOfPieces={200}
          gravity={0.2}
          colors={['#84CC16', '#10B981', '#06B6D4', '#3B82F6', '#8B5CF6', '#F59E0B']}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            zIndex: 9999,
            pointerEvents: 'none'
          }}
        />
      )}
    </>
  );
}
