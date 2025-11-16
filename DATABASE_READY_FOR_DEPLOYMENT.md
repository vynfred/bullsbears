# ✅ DATABASE SCHEMA - READY FOR DEPLOYMENT

## 🎯 **Status: COMPLETE & PRODUCTION-READY**

All database tables, indexes, and initial data are configured and ready to deploy to Google Cloud SQL.

---

## 📊 **Database Schema Summary**

### **Total Tables: 22**

#### **Core Pipeline Tables (6)**
1. ✅ `picks` - Final 6 daily picks with targets, outcomes, agent metadata
2. ✅ `shortlist_candidates` - All 75 SHORT_LIST candidates daily (for learning)
3. ✅ `stock_classifications` - Tier tracking: ALL → ACTIVE → SHORT_LIST → PICKS
4. ✅ `prime_ohlc_90d` - 90-day OHLC data for all 6,960 NASDAQ stocks
5. ✅ `stock_charts` - Base64 PNG charts (256x256) for Vision Agent
6. ✅ `watchlist` - User watchlist entries with Firebase Auth user_id

#### **AI Agent Tables (8)**
7. ✅ `agent_performance` - Agent accuracy tracking
8. ✅ `agent_weights` - Arbitrator trust weights (updated by Learner)
9. ✅ `feature_weights` - ML feature weights (updated by Learner)
10. ✅ `prompt_examples` - Few-shot learning examples with outcomes
11. ✅ `arbitrator_decisions` - Arbitrator pick selection reasoning
12. ✅ `confidence_factors` - Confidence calculation breakdown
13. ✅ `learning_feedback` - Structured feedback for Learner
14. ✅ `learning_cycles` - Weekly learner run metadata

#### **Market Data Tables (5)**
15. ✅ `market_conditions` - VIX, SPY, kill switch status
16. ✅ `social_sentiment` - Social/news sentiment scores
17. ✅ `trending_stocks` - Trending stock detection
18. ✅ `kill_switch_log` - Kill switch activation history
19. ✅ `pick_outcomes_detailed` - Detailed outcome tracking for learning

#### **System Tables (4)**
20. ✅ `scan_errors` - Error logging for debugging
21. ✅ `prompt_updates` - Prompt update history
22. ✅ `model_weights` - Legacy weights (backward compatibility)

---

## 🔧 **Key Features**

### **1. Complete Indexes (30+)**
- Symbol lookups (picks, shortlist, classifications, charts)
- Date range queries (OHLC, picks, candidates)
- Tier filtering (stock_classifications)
- Agent performance tracking
- Outcome analysis

### **2. Initial Seed Data**
- ✅ Feature weights (8 weights)
- ✅ Agent weights (9 agents)
- ✅ Agent performance (7 agents)
- ✅ Market conditions (default values)

### **3. Data Integrity**
- Foreign key constraints (pick_id references)
- Unique constraints (symbol+date, user+symbol)
- Check constraints (confidence 0-100, direction bullish/bearish)
- Default values for all critical fields

### **4. Production Optimizations**
- JSONB columns for flexible data storage
- Composite indexes for complex queries
- ON CONFLICT clauses for upserts
- Timestamp tracking (created_at, updated_at)

---

## 🚀 **Deployment Instructions**

### **Option 1: Deploy from Home (Whitelisted IP)**

```bash
# 1. Connect to Google Cloud SQL
gcloud sql connect bullsbears-db --user=postgres --project=bullsbears

# 2. Run the schema
\i /Users/vynfred/Documents/bullsbears/scripts/setup_database.sql

# 3. Verify tables
\dt

# 4. Check table counts
SELECT 
  'picks' as table_name, COUNT(*) as count FROM picks
UNION ALL
SELECT 'stock_classifications', COUNT(*) FROM stock_classifications
UNION ALL
SELECT 'prime_ohlc_90d', COUNT(*) FROM prime_ohlc_90d
UNION ALL
SELECT 'feature_weights', COUNT(*) FROM feature_weights
UNION ALL
SELECT 'agent_weights', COUNT(*) FROM agent_weights;
```

### **Option 2: Deploy via Cloud SQL Import**

```bash
# 1. Upload schema to Cloud Storage
gsutil cp scripts/setup_database.sql gs://bullsbears-db-backups/

# 2. Import to Cloud SQL
gcloud sql import sql bullsbears-db \
  gs://bullsbears-db-backups/setup_database.sql \
  --database=bullsbears \
  --project=bullsbears

# 3. Verify via Cloud Console
# Go to: https://console.cloud.google.com/sql/instances/bullsbears-db/databases
```

---

## 📋 **Post-Deployment Checklist**

- [ ] All 22 tables created successfully
- [ ] All 30+ indexes created
- [ ] Initial seed data inserted (feature_weights, agent_weights, agent_performance)
- [ ] Foreign key constraints working
- [ ] Unique constraints enforced
- [ ] Backend can connect from Cloud Run
- [ ] Admin dashboard shows correct table counts

---

## 🔍 **Verification Queries**

```sql
-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;

-- Check seed data
SELECT * FROM feature_weights ORDER BY name;
SELECT * FROM agent_weights ORDER BY agent_name;
SELECT * FROM agent_performance ORDER BY agent_name;
```

---

## ✅ **READY TO DEPLOY!**

The database schema is complete, tested, and ready for production deployment. All tables required by the backend services, AI agents, and admin dashboard are included.

