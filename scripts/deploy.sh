#!/bin/bash
# BullsBears Deployment Script
# This script builds and deploys the frontend to Firebase Hosting

set -e  # Exit on error

echo "🚀 BullsBears Deployment Script"
echo "================================"
echo ""

# Check if we're in the project root
if [ ! -f "firebase.json" ]; then
  echo "❌ Error: firebase.json not found. Please run this script from the project root."
  exit 1
fi

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
  echo "❌ Error: Firebase CLI not found. Install with: npm install -g firebase-tools"
  exit 1
fi

# Check if logged in to Firebase
if ! firebase projects:list &> /dev/null; then
  echo "❌ Error: Not logged in to Firebase. Run: firebase login"
  exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Build frontend
echo "📦 Building Next.js frontend..."
cd frontend
npm install
npm run build

if [ ! -d "out" ]; then
  echo "❌ Error: Build failed - 'out' directory not found"
  exit 1
fi

echo "✅ Frontend build complete"
echo ""

# Go back to project root
cd ..

# Deploy to Firebase
echo "🚀 Deploying to Firebase..."
echo ""
echo "This will deploy:"
echo "  - Frontend (Firebase Hosting)"
echo "  - Realtime Database rules"
echo "  - Firestore rules"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
  firebase deploy
  
  echo ""
  echo "✅ Deployment complete!"
  echo ""
  echo "🌐 Your site is live at:"
  echo "   https://bullsbears-xyz.web.app"
  echo ""
  echo "🔐 Admin dashboard:"
  echo "   https://bullsbears-xyz.web.app/admin"
  echo ""
  echo "📝 Next steps:"
  echo "   1. Set admin user: node scripts/set_admin_user.js <your_email>"
  echo "   2. Sign in to the admin dashboard"
  echo "   3. Prime historical data"
  echo "   4. Turn system ON"
  echo ""
else
  echo "❌ Deployment cancelled"
  exit 1
fi

