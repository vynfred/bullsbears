#!/bin/bash
# Run the complete database setup
# This creates ALL tables for the BullsBears learning system

echo "🔧 Running BullsBears database setup..."
echo ""

PGPASSWORD='<$?Fh*QNNmfJ0vTD' psql \
  -h 104.198.40.56 \
  -U postgres \
  -d postgres \
  -f scripts/setup_database.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database setup complete!"
    echo ""
    echo "Verifying tables..."
    PGPASSWORD='<$?Fh*QNNmfJ0vTD' psql \
      -h 104.198.40.56 \
      -U postgres \
      -d postgres \
      -c "\dt" \
      -c "\d+ shortlist_candidates" \
      -c "\d+ pick_outcomes_detailed" \
      -c "\d picks"
else
    echo ""
    echo "❌ Database setup failed!"
    exit 1
fi

