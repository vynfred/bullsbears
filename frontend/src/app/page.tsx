'use client';

import React, { useEffect } from 'react';

export default function Home() {
  useEffect(() => {
    // Redirect to dashboard page for MVP
    window.location.href = '/dashboard';
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4">🚀🌙</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">BullsBears</h1>
        <p className="text-gray-600 mb-4">Your Trading Co-Pilot</p>
        <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
        <p className="text-sm text-gray-500 mt-2">Redirecting to Dashboard...</p>
      </div>
    </div>
  );
}

