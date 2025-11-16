# 🚀 BullsBears Production Readiness Checklist

## ✅ COMPLETED ITEMS

### Frontend Build & Deployment
- [x] **Next.js build successful** - Static export working
- [x] **TypeScript compilation** - All type errors resolved
- [x] **Firebase Auth integration** - Google OAuth + Email/Password
- [x] **Real-time price updates** - FMP API with 5-min caching
- [x] **User-specific watchlist** - WatchlistEntry type with live prices
- [x] **Push notifications** - usePushNotifications hook ready
- [x] **Admin page protection** - Role-based access control
- [x] **Firebase hosting config** - `.firebaserc` and `firebase.json` ready

### Backend Architecture
- [x] **Dockerfile** - Production-ready with TA-Lib, non-root user, health checks
- [x] **FastAPI app** - CORS, structured logging, startup/shutdown hooks
- [x] **Database integration** - PostgreSQL with connection pooling
- [x] **Redis caching** - Async client with retry logic
- [x] **Firebase client** - Real-time database integration
- [x] **RunPod client** - AI model inference ready
- [x] **Watchlist API** - User-specific endpoints with auth

### GitHub Workflow
- [x] **Deploy workflow exists** - `.github/workflows/deploy.yml`
- [x] **Secrets configured** - 11 secrets set
- [x] **Variables configured** - 3 variables set
- [x] **Cloud Run deployment** - Automated on push to main

---

## ⚠️ REQUIRED BEFORE GOING LIVE

### 1. GitHub Workflow Review
**Current Issues:**
```yaml
# Line 31: Missing environment variables
--set-env-vars DB_HOST=${{ vars.DB_HOST }},DB_USER=postgres,DB_NAME=postgres,DB_PORT=5432
```

**Missing from workflow:**
- ❌ `FIREBASE_PROJECT_ID` (should be `bullsbears-xyz` or `603494406675`)
- ❌ `FIREBASE_DATABASE_URL` (should be `https://bullsbears-xyz-default-rtdb.firebaseio.com`)
- ❌ `FIREBASE_API_KEY` (secret)
- ❌ `RUNPOD_API_KEY` (secret)
- ❌ `RUNPOD_ENDPOINT_ID` (should be `0bv1yn1beqszt7` or `3fjac9v4neycka`)
- ❌ `REDIS_URL` (if using external Redis)
- ❌ `SECRET_KEY` (for JWT/session signing)
- ❌ `ENVIRONMENT=production`

**Region mismatch:**
- Line 29: `--region us-central1`
- Line 41: `--region ${{ vars.GCP_REGION }}`
- ⚠️ These should match!

### 2. Database Migration
```bash
# Run this ONCE before going live:
python backend/scripts/migrate_watchlist_to_user_specific.py
```

### 3. Firebase Admin Setup
```bash
# Set yourself as admin:
node scripts/set_admin_user.js hellovynfred@gmail.com
```

### 4. Frontend Environment Variables
Ensure `frontend/.env.local` has:
```bash
NEXT_PUBLIC_API_URL=https://bullsbears-backend-<hash>.run.app
NEXT_PUBLIC_FMP_API_KEY=<your_fmp_key>
NEXT_PUBLIC_FIREBASE_API_KEY=<your_key>
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=bullsbears-xyz.firebaseapp.com
NEXT_PUBLIC_FIREBASE_DATABASE_URL=https://bullsbears-xyz-default-rtdb.firebaseio.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=bullsbears-xyz
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=bullsbears-xyz.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=603494406675
NEXT_PUBLIC_FIREBASE_APP_ID=<your_app_id>
```

### 5. Backend Service Account
- ❌ Upload `serviceAccountKey.json` to Google Cloud Secret Manager
- ❌ Update workflow to mount secret as file or set `FIREBASE_CREDENTIALS_PATH`

### 6. Cloud SQL IP Whitelist
- ✅ Already whitelisted: `24.99.57.192`
- ⚠️ Add Cloud Run IP ranges if using public IP connection
- ✅ OR use Cloud SQL Proxy (recommended)

---

## 🔧 RECOMMENDED FIXES

### Fix 1: Update GitHub Workflow
```yaml
# Add to .github/workflows/deploy.yml line 31:
--set-env-vars DB_HOST=${{ vars.DB_HOST }},\
DB_USER=postgres,\
DB_NAME=postgres,\
DB_PORT=5432,\
ENVIRONMENT=production,\
FIREBASE_PROJECT_ID=bullsbears-xyz,\
FIREBASE_DATABASE_URL=https://bullsbears-xyz-default-rtdb.firebaseio.com,\
RUNPOD_ENDPOINT_ID=3fjac9v4neycka,\
ALPHA_VANTAGE_API_KEY=${{ secrets.ALPHA_VANTAGE_API_KEY }},\
FMP_API_KEY=${{ secrets.FMP_API_KEY }} \
--set-secrets DB_PASSWORD=bullsbears-db-password:latest,\
FIREBASE_API_KEY=firebase-api-key:latest,\
RUNPOD_API_KEY=runpod-api-key:latest,\
SECRET_KEY=app-secret-key:latest
```

### Fix 2: Use Cloud SQL Proxy (Recommended)
```yaml
# Add to deploy command:
--add-cloudsql-instances=<PROJECT_ID>:us-central1:<INSTANCE_NAME>
```

Then use Unix socket connection:
```bash
DATABASE_URL=postgresql://user:pass@/bullsbears?host=/cloudsql/<PROJECT_ID>:us-central1:<INSTANCE_NAME>
```

---

## 📋 DEPLOYMENT STEPS

### Step 1: Fix GitHub Workflow
```bash
# Edit .github/workflows/deploy.yml with missing env vars
```

### Step 2: Push to Main
```bash
git add .
git commit -m "Production deployment ready"
git push origin main
```

### Step 3: Monitor Deployment
```bash
# Watch GitHub Actions:
# https://github.com/vynfred/bullsbears/actions

# Or use CLI:
gh run watch
```

### Step 4: Get Cloud Run URL
```bash
gcloud run services describe bullsbears-backend \
  --region us-central1 \
  --format="value(status.url)"
```

### Step 5: Update Frontend API URL
```bash
# Update frontend/.env.local:
NEXT_PUBLIC_API_URL=<cloud_run_url>

# Rebuild and deploy frontend:
cd frontend && npm run build
firebase deploy
```

### Step 6: Test Admin Dashboard
```
https://bullsbears-xyz.web.app/admin
```

---

## ✅ READY TO GO LIVE?

**YES, if you:**
1. ✅ Fix GitHub workflow environment variables
2. ✅ Run database migration
3. ✅ Set admin user in Firebase
4. ✅ Update frontend API URL after backend deploys

**Current Status: 85% Ready** 🟡

Missing: Environment variables in GitHub workflow, database migration, admin user setup

