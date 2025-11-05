-- Migration: Update terminology from Moon/Rug to Bullish/Bearish
-- Date: 2024-11-04
-- Description: Updates AlertType enum values and related data from MOON/RUG to BULLISH/BEARISH

-- Step 1: Add new enum values to AlertType
-- Note: PostgreSQL requires adding new values before dropping old ones
ALTER TYPE alerttype ADD VALUE IF NOT EXISTS 'BULLISH';
ALTER TYPE alerttype ADD VALUE IF NOT EXISTS 'BEARISH';

-- Step 2: Update existing data to use new terminology
UPDATE analysis_results 
SET alert_type = 'BULLISH' 
WHERE alert_type = 'MOON';

UPDATE analysis_results 
SET alert_type = 'BEARISH' 
WHERE alert_type = 'RUG';

-- Step 3: Update any string references in JSON fields or comments
UPDATE analysis_results 
SET features_json = jsonb_set(
    features_json::jsonb, 
    '{alert_type}', 
    '"BULLISH"'::jsonb
)
WHERE features_json::jsonb->>'alert_type' = 'MOON';

UPDATE analysis_results 
SET features_json = jsonb_set(
    features_json::jsonb, 
    '{alert_type}', 
    '"BEARISH"'::jsonb
)
WHERE features_json::jsonb->>'alert_type' = 'RUG';

-- Step 4: Update any analysis_type fields that might reference moon/rug
UPDATE analysis_results 
SET analysis_type = 'bullish_analysis' 
WHERE analysis_type = 'moon_analysis';

UPDATE analysis_results 
SET analysis_type = 'bearish_analysis' 
WHERE analysis_type = 'rug_analysis';

-- Step 5: Create backup of old enum values (for rollback if needed)
-- Note: We cannot drop enum values in PostgreSQL, they remain for backward compatibility
-- The old MOON and RUG values will remain in the enum but won't be used

-- Step 6: Update any indexes or constraints that reference the old terminology
-- (Most indexes are on the enum column itself, so they'll work with new values)

-- Verification queries (uncomment to run after migration):
-- SELECT alert_type, COUNT(*) FROM analysis_results GROUP BY alert_type;
-- SELECT DISTINCT analysis_type FROM analysis_results WHERE analysis_type LIKE '%moon%' OR analysis_type LIKE '%rug%';
-- SELECT COUNT(*) FROM analysis_results WHERE features_json::jsonb->>'alert_type' IN ('MOON', 'RUG');

COMMIT;
