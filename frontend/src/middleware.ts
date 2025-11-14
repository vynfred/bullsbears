// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// TEMPORARILY DISABLED - Auth will be added later
// For now, all routes are accessible without authentication

export function middleware(request: NextRequest) {
  // Allow all requests through
  return NextResponse.next();
}

export const config = {
  matcher: ['/', '/watchlist', '/analytics', '/profile', '/settings', '/landing', '/faq', '/terms', '/login', '/signup']
};