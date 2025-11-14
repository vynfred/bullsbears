# Firebase Setup Guide for BullsBears

## 🔥 Firebase Realtime Database Setup

Your Firebase project ID: `603494406675`

### Step 1: Configure Security Rules

Go to your Firebase Console:
https://console.firebase.google.com/project/603494406675/database/603494406675-default-rtdb/rules

**Replace the default rules with:**

```json
{
  "rules": {
    "pulse": {
      ".read": true,
      ".write": true
    },
    "watchlist": {
      ".read": true,
      ".write": true
    },
    "analytics": {
      ".read": true,
      ".write": true
    }
  }
}
```

**Important**: These are open rules for development. We'll secure them later when adding authentication.

### Step 2: Test Database Structure

After setting the rules, your database should accept these paths:
- `/pulse/latest` - Latest AI picks
- `/watchlist/{symbol}` - Individual stock watchlist data  
- `/analytics/latest` - Performance analytics

### Step 3: Verify Setup

Once rules are updated, run this test:

```bash
cd backend
python3 -m app.services.firebase_service
```

You should see:
```
✅ Firebase initialization: SUCCESS
✅ Sample picks push: SUCCESS
✅ Retrieve picks: SUCCESS
```

## 🎯 Database Schema

### `/pulse/latest`
```json
{
  "timestamp": "2024-11-09T10:30:00Z",
  "picks": [
    {
      "symbol": "TSLA",
      "direction": "bullish",
      "confidence": 0.75,
      "target_low": 250.0,
      "target_medium": 275.0,
      "target_high": 300.0,
      "current_price": 240.0,
      "reasoning": "Strong technical breakout with high volume",
      "risk_level": "medium",
      "estimated_days": 7,
      "created_at": "2024-11-09T10:30:00Z"
    }
  ],
  "metadata": {
    "total_picks": 1,
    "analysis_time": "2024-11-09T10:30:00Z",
    "system_version": "18-agent-v1.0"
  }
}
```

### `/watchlist/{symbol}`
```json
{
  "symbol": "TSLA",
  "current_price": 240.0,
  "change_percent": 2.5,
  "sentiment_score": 0.65,
  "last_updated": "2024-11-09T10:30:00Z",
  "news_sentiment": {
    "score": 0.7,
    "articles_count": 5
  },
  "social_sentiment": {
    "score": 0.6,
    "mentions_count": 150
  }
}
```

### `/analytics/latest`
```json
{
  "accuracy_metrics": {
    "win_rate": 0.68,
    "total_picks": 156,
    "successful_picks": 106
  },
  "performance_history": [
    {
      "date": "2024-11-09",
      "accuracy": 0.75,
      "picks_count": 6
    }
  ],
  "win_rate": 0.68,
  "total_picks": 156,
  "last_updated": "2024-11-09T10:30:00Z"
}
```

## 🚀 Next Steps After Firebase Setup

1. **Test Firebase Connection** ✅
2. **Run First Production Analysis** - Generate real picks with 18-agent system
3. **Update Frontend** - Connect to Firebase for real-time data
4. **Test End-to-End** - Verify picks show up in frontend

## 🔧 Troubleshooting

### Common Issues:

**404 Error**: Security rules not set or database doesn't exist
- Solution: Set the security rules above in Firebase Console

**403 Error**: Permission denied
- Solution: Check security rules allow read/write access

**Network Error**: Connection issues
- Solution: Verify Firebase project ID and database URL

### Test Commands:

```bash
# Test Firebase connection
cd backend && python3 -m app.services.firebase_service

# Test with curl (after rules are set)
curl -X GET "https://603494406675-default-rtdb.firebaseio.com/pulse/latest.json"
```

## 🎯 Ready for Production

Once Firebase is working:
1. ✅ Real-time data pipeline established
2. 🔄 Run first 18-agent analysis 
3. 🔄 Connect frontend to Firebase
4. 🔄 Test complete system end-to-end
