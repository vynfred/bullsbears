# 🚀 BullsBears Deployment Guide

## Prerequisites

1. **Firebase Project**: `bullsbears-xyz` (Project ID: 603494406675)
2. **Google Cloud SQL**: PostgreSQL database
3. **FMP API Key**: Premium plan (300 calls/min)
4. **Firebase Service Account Key**: `serviceAccountKey.json` in project root

## 📋 Pre-Deployment Checklist

### 1. Environment Variables

**Frontend (.env.local)**:
```bash
NEXT_PUBLIC_API_URL=https://your-backend-url.run.app
NEXT_PUBLIC_FMP_API_KEY=your_fmp_api_key

# Firebase Configuration
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=bullsbears-xyz.firebaseapp.com
NEXT_PUBLIC_FIREBASE_DATABASE_URL=https://bullsbears-xyz-default-rtdb.firebaseio.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=bullsbears-xyz
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=bullsbears-xyz.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=603494406675
NEXT_PUBLIC_FIREBASE_APP_ID=your_firebase_app_id
```

**Backend (.env)**:
```bash
DATABASE_URL=postgresql://user:pass@/cloudsql/project:region:instance/bullsbears
FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccountKey.json
FMP_API_KEY=your_fmp_api_key
```

### 2. Database Migration

Run the watchlist migration to add user_id column:

```bash
cd backend
python scripts/migrate_watchlist_to_user_specific.py
```

Choose one of:
- Delete test data: `python scripts/migrate_watchlist_to_user_specific.py delete`
- Assign to user: `python scripts/migrate_watchlist_to_user_specific.py assign <firebase_uid>`

### 3. Firebase Setup

Install Firebase CLI:
```bash
npm install -g firebase-tools
firebase login
```

Deploy Firebase rules:
```bash
firebase deploy --only database    # Realtime Database rules
firebase deploy --only firestore   # Firestore rules
```

### 4. Set Admin User

After deploying, set yourself as admin:

```bash
# Install firebase-admin if not already installed
npm install firebase-admin

# Set admin user
node scripts/set_admin_user.js hellovynfred@gmail.com
```

This will:
- Look up your Firebase Auth user
- Set `role: 'admin'` in Firestore
- Grant access to `/admin` page

## 🌐 Deploy Frontend to Firebase Hosting

### Step 1: Build Next.js App

```bash
cd frontend
npm install
npm run build
```

This will create a static export in `frontend/out/` directory.

### Step 2: Deploy to Firebase

```bash
# From project root
firebase deploy --only hosting
```

Your site will be live at: `https://bullsbears-xyz.web.app`

### Step 3: Access Admin Dashboard

1. Go to `https://bullsbears-xyz.web.app/admin`
2. Sign in with your admin account (hellovynfred@gmail.com)
3. You should see the admin dashboard

## 🔧 Deploy Backend to Google Cloud Run

### Step 1: Build Docker Image

```bash
cd backend
gcloud builds submit --tag gcr.io/bullsbears-xyz/backend
```

### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy bullsbears-backend \
  --image gcr.io/bullsbears-xyz/backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances bullsbears-xyz:us-central1:bullsbears-db \
  --set-env-vars DATABASE_URL="postgresql://..." \
  --set-env-vars FIREBASE_CREDENTIALS_PATH="/app/serviceAccountKey.json" \
  --set-env-vars FMP_API_KEY="your_fmp_api_key"
```

### Step 3: Update Frontend API URL

Update `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://bullsbears-backend-xxxxx-uc.a.run.app
```

Rebuild and redeploy frontend:
```bash
cd frontend
npm run build
cd ..
firebase deploy --only hosting
```

## 🎯 Post-Deployment Steps

### 1. Test System Connections

Go to admin dashboard and verify all connections are green:
- ✅ Google Cloud SQL
- ✅ Firebase Realtime Database
- ✅ FMP API
- ✅ RunPod Endpoint

### 2. Prime Historical Data

In admin dashboard:
1. Click "Prime Data" button
2. Wait for 90 days of OHLC data to load (~30 minutes)
3. Monitor progress in admin dashboard

### 3. Turn System ON

Once data is primed:
1. Click "Turn System ON" in admin dashboard
2. System will start automated tasks:
   - Daily stock filtering (NASDAQ → ACTIVE)
   - AI agent analysis (ACTIVE → QUALIFIED → PICKS)
   - Real-time price updates during market hours
   - Push notifications for target hits

## 🔐 Security Notes

1. **Admin Access**: Only users with `role: 'admin'` in Firestore can access `/admin`
2. **Watchlist API**: Requires Firebase Auth token in `Authorization: Bearer <token>` header
3. **Firebase Rules**: Deployed rules protect user-specific data
4. **Service Account Key**: Never commit `serviceAccountKey.json` to git (already in .gitignore)

## 📊 Monitoring

### Admin Dashboard Features

- **System Status**: Real-time connection monitoring
- **Data Status**: Historical records count, latest data date
- **Stock Tiers**: ALL/ACTIVE/QUALIFIED/PICKS distribution
- **API Usage**: FMP, RunPod, Groq usage and costs
- **User Stats**: Total users, active users (24h), new users today
- **System Controls**: ON/OFF toggle, Prime Data, Run Once (test)

### Logs

- **Frontend**: Firebase Hosting logs in Firebase Console
- **Backend**: Cloud Run logs in Google Cloud Console
- **Database**: Cloud SQL logs in Google Cloud Console

## 🚨 Troubleshooting

### Admin page shows "Access Denied"

```bash
# Re-run admin script
node scripts/set_admin_user.js hellovynfred@gmail.com
```

### Backend can't connect to database

Check Cloud SQL connection:
```bash
gcloud sql instances describe bullsbears-db
```

Verify IP whitelist includes Cloud Run IP.

### Firebase rules blocking requests

Check Firebase Console → Realtime Database → Rules
Ensure rules match `database.rules.json`

## 🎉 You're Live!

Once deployed:
- **Public Site**: https://bullsbears-xyz.web.app
- **Admin Dashboard**: https://bullsbears-xyz.web.app/admin
- **Backend API**: https://bullsbears-backend-xxxxx-uc.a.run.app

Monitor the admin dashboard to ensure all systems are operational! 🚀

