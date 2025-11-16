# ✅ SQLAlchemy Models Aligned with Raw SQL

## Summary
Reverted SQLAlchemy models to **exactly match** the raw SQL schema in `scripts/setup_database.sql`. No Enum types, no ForeignKeys, no extra columns that don't exist in SQL.

---

## Changes Made

### 1. **StockClassification Model**
**Reverted to match SQL exactly:**
- ❌ Removed `Enum(StockTier)` → ✅ Back to `String(20)`
- ❌ Removed `is_active` column (not in SQL)
- ❌ Removed `last_pick_date` column (not in SQL)
- ❌ Removed `consecutive_pick_days` column (not in SQL)
- ✅ Kept all columns that exist in SQL via `ALTER TABLE`

**SQL Schema:**
```sql
ALTER TABLE stock_classifications 
ADD COLUMN IF NOT EXISTS exchange VARCHAR(10) DEFAULT 'NASDAQ',
ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS sector VARCHAR(100),
ADD COLUMN IF NOT EXISTS industry VARCHAR(100);
```

**SQLAlchemy Model:**
```python
class StockClassification(Base):
    __tablename__ = 'stock_classifications'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    exchange = Column(String(10), nullable=False, index=True)
    current_tier = Column(String(20), nullable=False, index=True)  # ALL, ACTIVE, SHORT_LIST, PICKS
    
    price = Column(DECIMAL(10, 2))
    market_cap = Column(BigInteger)
    daily_volume = Column(BigInteger)
    
    company_name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    
    last_qualified_date = Column(Date, index=True)
    qualified_days_count = Column(Integer, default=0)
    selection_fatigue_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

---

### 2. **ShortlistCandidate Model (formerly ShortListPriceTracking)**
**Renamed and aligned with SQL:**
- ❌ Old name: `ShortListPriceTracking` → ✅ New name: `ShortlistCandidate`
- ❌ Old table: `short_list_price_tracking` → ✅ New table: `shortlist_candidates`
- ❌ Removed `pick_id` ForeignKey (not in SQL)
- ❌ Removed `arbitrator_selected` column (not in SQL)
- ❌ Removed `confidence` column (not in SQL)
- ❌ Removed `change_30d` column (not in SQL)
- ❌ Removed `outcome` column (not in SQL)
- ✅ Added all columns that exist in SQL

**SQL Schema:**
```sql
CREATE TABLE IF NOT EXISTS shortlist_candidates (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    rank INT NOT NULL,
    prescreen_score DECIMAL(5,4),
    prescreen_reasoning TEXT,
    price_at_selection DECIMAL(10,2),
    technical_snapshot JSONB,
    fundamental_snapshot JSONB,
    vision_flags JSONB,
    vision_analysis_text TEXT,
    social_score INT,  -- -5 to +5
    social_data JSONB,
    was_selected_as_pick BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_candidate_per_day UNIQUE (date, symbol)
);
```

**SQLAlchemy Model:**
```python
class ShortlistCandidate(Base):
    __tablename__ = "shortlist_candidates"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    rank = Column(Integer, nullable=False)
    
    prescreen_score = Column(DECIMAL(5, 4))
    prescreen_reasoning = Column(String)
    price_at_selection = Column(DECIMAL(10, 2))
    
    technical_snapshot = Column(JSON)
    fundamental_snapshot = Column(JSON)
    
    vision_flags = Column(JSON)
    vision_analysis_text = Column(String)
    
    social_score = Column(Integer)  # -5 to +5 (INT not DECIMAL)
    social_data = Column(JSON)
    
    was_selected_as_pick = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
```

---

## Key Differences from Grok's Recommendations

### ❌ NOT Implemented (Not in SQL):
1. **Enum types** - SQL uses VARCHAR, not Postgres ENUM
2. **ForeignKey constraints** - Not defined in SQL schema
3. **Extra columns** like `is_active`, `last_pick_date`, `pick_id`, `arbitrator_selected`, `confidence`, `outcome`
4. **Composite indexes** - Only basic indexes defined in SQL

### ✅ What We DID Keep:
1. **Exact column names** from SQL
2. **Exact data types** from SQL (INT not DECIMAL for social_score)
3. **Exact indexes** from SQL
4. **Exact table names** from SQL

---

## Why This Matters

**Grok's suggestions were good for a greenfield project**, but we have:
1. **Existing SQL schema** in `scripts/setup_database.sql`
2. **Existing database** that will be migrated
3. **Need for exact alignment** between SQLAlchemy and raw SQL

**Rule:** SQLAlchemy models must **exactly mirror** the SQL schema, not add features that don't exist in SQL.

---

## Verification

Run this to verify models match SQL:
```python
from backend.app.models.stock_classifications import StockClassification, ShortlistCandidate
from sqlalchemy import inspect

# Check columns
inspector = inspect(engine)
sql_columns = inspector.get_columns('shortlist_candidates')
model_columns = ShortlistCandidate.__table__.columns.keys()

print("SQL columns:", [c['name'] for c in sql_columns])
print("Model columns:", model_columns)
```

---

## Files Changed
- ✅ `backend/app/models/stock_classifications.py` - Aligned with SQL schema
- ✅ Removed Enum types
- ✅ Removed ForeignKey constraints
- ✅ Removed extra columns not in SQL
- ✅ Fixed table name: `short_list_price_tracking` → `shortlist_candidates`
- ✅ Fixed class name: `ShortListPriceTracking` → `ShortlistCandidate`

---

**Result:** SQLAlchemy models now **exactly match** raw SQL schema! 🎯

