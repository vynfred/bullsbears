# Admin Panel Usage Guide

## Overview

The BullsBears admin panel provides complete control over the system with persistent state management. All system state is stored in Firebase Realtime Database, ensuring it persists across sessions, server restarts, and laptop closures.

## Accessing the Admin Panel

The admin panel is accessible via a secret URL (not linked from public pages):
```
https://bullsbears-xyz.web.app/admin
```

## System State Management

### How It Works

1. **Persistent Storage**: System ON/OFF state is stored in Firebase at `/system/state`
2. **Session Independence**: State persists when you:
   - Close your laptop
   - Log off
   - Restart the server
   - Refresh the page
3. **Task Control**: All Celery tasks check `SystemState.is_system_on()` before executing
4. **Visual Feedback**: Buttons show clear visual states (active button is highlighted with glow effect)

### System Controls

#### Turn System ON
- Click the **"Turn ON"** button (left button)
- System state changes to "ONLINE" (green badge)
- Button shows "✓ System ON" with emerald glow
- All scheduled tasks will execute at their scheduled times
- State is immediately saved to Firebase

#### Turn System OFF
- Click the **"Turn OFF"** button (right button)
- System state changes to "OFFLINE" (gray badge)
- Button shows "✓ System OFF" with red glow
- All scheduled tasks will skip execution (logged as "System is OFF")
- State is immediately saved to Firebase

### Button States

**When System is ON:**
- ✓ System ON button: Emerald background with bright border and glow
- Turn OFF button: Dimmed red background

**When System is OFF:**
- Turn ON button: Dimmed emerald background
- ✓ System OFF button: Red background with bright border and glow

## Data Management

### Prime Database
Before turning the system ON for the first time, you must prime the database with historical data:

1. Click **"Prime Data"** button
2. System loads 90 days of OHLC data for all ~6,960 NASDAQ stocks
3. Process takes several minutes (progress shown in Firebase)
4. "Data Primed ✓" badge appears when complete
5. Only needs to be done once (unless you reset the database)

## Status Monitoring

### System Status Card
Shows:
- Current state: ONLINE or OFFLINE
- Last updated timestamp
- Data primed status (if applicable)

### Database Connections
- Google Cloud SQL: PostgreSQL database
- Firebase Realtime DB: System state and picks storage

### API Keys & Services
- FMP API: Financial data provider
- Groq API: Vision analysis agent
- Grok API: Social context agent
- DeepSeek API: Arbitrator agent

### RunPod Infrastructure
- RunPod Serverless Endpoint: GPU-based AI agents (Prescreen, Learner)

## How Celery Scheduler Works

### Scheduler (Celery Beat)
- Runs continuously in the background
- Triggers tasks at scheduled times (see schedule below)
- Does NOT execute tasks directly

### Worker (Celery Worker)
- Receives tasks from Redis queue
- Checks `SystemState.is_system_on()` before executing
- If OFF: Logs "System is OFF - skipping [task_name]" and returns
- If ON: Executes the task

### RunPod Integration
- RunPod workers are NOT always running
- Celery worker triggers RunPod endpoint when needed
- RunPod spins up GPU instance, executes task, shuts down
- Cost: Only pay for actual GPU time used

## Daily Schedule (EST/EDT)

When system is ON, tasks execute at these times:

```
8:00 AM - FMP Delta Update (update stock data)
8:05 AM - Build ACTIVE Symbols (filter ~3,000 active stocks)
8:10 AM - Prescreen (ACTIVE → SHORT_LIST 75 stocks) 🔥 RunPod GPU
8:15 AM - Generate Charts (75 charts for vision analysis)
8:16 AM - Groq Vision Analysis (chart pattern detection)
8:17 AM - Grok Social Analysis (social sentiment + news)
8:20 AM - Final Arbitrator (select 3-6 final picks)
8:25 AM - Publish to Firebase (make picks available to users)

Every 5 min - Statistics Cache Update
Every 2 min (market hours) - Badge Data Update
Every hour - Statistics Validation
Daily 12 PM - Statistics Report

Saturday 4:00 AM - Weekly Learner (review outcomes, update weights) 🔥 RunPod GPU
```

## Workflow

### Initial Setup (One-Time)
1. Access admin panel
2. Verify all connections are green
3. Click "Prime Data" and wait for completion
4. Verify "Data Primed ✓" badge appears

### Daily Operation
1. Turn system ON (morning before 8:00 AM)
2. System automatically runs all scheduled tasks
3. Monitor status throughout the day
4. Turn system OFF (evening after market close) - OPTIONAL

### Maintenance
- System can stay ON indefinitely
- Only turn OFF if you need to:
  - Perform database maintenance
  - Update code/configuration
  - Prevent tasks from running during holidays

## Troubleshooting

### System won't turn ON
1. Check Firebase connection (should be green)
2. Check browser console for errors
3. Verify Firebase credentials are valid

### Tasks not executing
1. Verify system state is "ONLINE"
2. Check Celery worker is running
3. Check Celery beat scheduler is running
4. Check Redis connection

### Data not priming
1. Check FMP API key is valid
2. Check Google Cloud SQL connection
3. Monitor backend logs for errors

## Cost Control

### When System is OFF
- No tasks execute
- No RunPod GPU costs
- No API calls made
- Redis and databases still running (minimal cost)

### When System is ON
- RunPod GPU: Only during prescreen (8:10 AM) and learner (Saturday 4 AM)
- API calls: Only during scheduled tasks
- Estimated daily cost: $2-5 (mostly API calls)

## Security

- Admin panel has no public links
- Access via secret URL only
- Consider adding authentication in production
- Firebase rules restrict write access to system state

## Next Steps

After setting up the admin panel:
1. Deploy Celery Worker and Beat (see `docs/CELERY_DEPLOYMENT.md`)
2. Test system ON/OFF functionality
3. Monitor first daily run
4. Verify picks are published to Firebase

