# 📚 SQL Cheat Sheet for BullsBears

## Basic Connection

```bash
# Connect to database
PGPASSWORD='<$?Fh*QNNmfJ0vTD' psql -h 104.198.40.56 -U postgres -d postgres
```

---

## Useful Commands

### List all tables
```sql
\dt
```

### Describe a table structure
```sql
\d picks
\d shortlist_candidates
\d pick_outcomes_detailed
```

### Count records in a table
```sql
SELECT COUNT(*) FROM picks;
SELECT COUNT(*) FROM shortlist_candidates;
SELECT COUNT(*) FROM pick_outcomes_detailed;
```

### See recent records
```sql
-- Last 5 picks
SELECT symbol, direction, confidence, created_at 
FROM picks 
ORDER BY created_at DESC 
LIMIT 5;

-- Today's shortlist candidates
SELECT symbol, rank, prescreen_score, was_picked
FROM shortlist_candidates
WHERE date = CURRENT_DATE
ORDER BY rank
LIMIT 10;
```

---

## Learning System Queries

### Check if pick_context is populated
```sql
SELECT 
    symbol, 
    direction,
    pick_context IS NOT NULL as has_context,
    created_at
FROM picks
ORDER BY created_at DESC
LIMIT 5;
```

### View a pick's complete context
```sql
SELECT 
    symbol,
    direction,
    confidence,
    pick_context
FROM picks
WHERE symbol = 'AAPL'
ORDER BY created_at DESC
LIMIT 1;
```

### See which candidates were picked today
```sql
SELECT 
    symbol,
    rank,
    prescreen_score,
    social_score,
    was_picked,
    picked_direction
FROM shortlist_candidates
WHERE date = CURRENT_DATE
ORDER BY rank;
```

### Find missed opportunities (high gainers we didn't pick)
```sql
SELECT 
    symbol,
    rank,
    prescreen_score,
    max_gain_30d,
    was_picked
FROM shortlist_candidates
WHERE was_picked = FALSE
  AND max_gain_30d > 20.0
ORDER BY max_gain_30d DESC
LIMIT 10;
```

### Check outcome tracking
```sql
SELECT 
    symbol,
    direction,
    outcome,
    max_gain_percent,
    hours_to_max_gain
FROM pick_outcomes_detailed
WHERE outcome != 'pending'
ORDER BY created_at DESC
LIMIT 10;
```

### Win rate by direction
```sql
SELECT 
    direction,
    COUNT(*) as total_picks,
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM pick_outcomes_detailed
WHERE outcome != 'pending'
GROUP BY direction;
```

---

## Maintenance Queries

### Delete old test data
```sql
-- Delete picks older than 30 days
DELETE FROM picks WHERE created_at < NOW() - INTERVAL '30 days';

-- Delete old shortlist candidates
DELETE FROM shortlist_candidates WHERE date < CURRENT_DATE - INTERVAL '30 days';
```

### Check database size
```sql
SELECT 
    pg_size_pretty(pg_database_size('postgres')) as database_size;
```

### Check table sizes
```sql
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(table_name::text)) as size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(table_name::text) DESC;
```

---

## Troubleshooting

### Check if migration ran
```sql
-- Should return 2 rows
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('shortlist_candidates', 'pick_outcomes_detailed');

-- Should return 1 row
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'picks' AND column_name = 'pick_context';
```

### Check for errors in data
```sql
-- Picks without context (should be 0 after system is running)
SELECT COUNT(*) 
FROM picks 
WHERE pick_context IS NULL 
  AND created_at > CURRENT_DATE;

-- Candidates without vision flags
SELECT COUNT(*) 
FROM shortlist_candidates 
WHERE vision_flags IS NULL 
  AND date = CURRENT_DATE;
```

---

## Exit psql
```
\q
```

or press `Ctrl+D`

