'use client';

import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';

interface StickyHeaderProps {
  title?: string;
  showLogo?: boolean;
  className?: string;
  onLogoClick?: () => void;
}

export function StickyHeader({ title, showLogo = true, className = '', onLogoClick }: StickyHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className={`sticky top-0 bg-gray-900 z-50 border-b border-gray-800 ${className}`} style={{ position: 'sticky', top: 0 }}>
      <div className="flex items-center justify-between px-4 py-3">
        {/* Left: Hamburger Menu */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>

        {/* Center: Logo Only */}
        <button
          onClick={onLogoClick}
          className={`flex items-center gap-2 ${onLogoClick ? 'hover:opacity-80 transition-opacity' : ''}`}
          title={onLogoClick ? 'Exit to Home' : undefined}
        >
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">BB</span>
          </div>
          <span className="text-white font-bold text-lg">BullsBears</span>
        </button>

        {/* Right: Spacer for balance */}
        <div className="w-10"></div>
      </div>

      {/* Dropdown Menu */}
      {menuOpen && (
        <div className="absolute top-full left-0 right-0 bg-gray-800 border-b border-gray-700 shadow-lg">
          <div className="px-4 py-3 space-y-2">
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors">
              Settings
            </button>
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors">
              Notifications
            </button>
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors">
              Watchlist
            </button>
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors">
              Help & Support
            </button>
            <div className="border-t border-gray-600 pt-2 mt-2">
              <button className="w-full text-left px-3 py-2 text-red-400 hover:text-red-300 hover:bg-gray-700 rounded-lg transition-colors">
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
