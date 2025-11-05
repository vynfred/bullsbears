'use client';

import React, { useEffect } from 'react';

export default function Home() {
  useEffect(() => {
    // Redirect to dashboard page for MVP
    window.location.href = '/dashboard';
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary)' }}>
      <div className="text-center">
        <div className="text-4xl mb-4">🚀🌙</div>
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>BullsBears</h1>
        <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>Your Trading Co-Pilot</p>
        <div className="animate-spin w-6 h-6 border-2 rounded-full mx-auto" style={{
          borderColor: 'var(--color-primary)',
          borderTopColor: 'transparent'
        }}></div>
        <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>Redirecting to Dashboard...</p>
      </div>
    </div>
  );
}

