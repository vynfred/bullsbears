#!/bin/bash
# Direct psql deployment to Cloud SQL
# Use this if gcloud sql connect has IPv6 issues

set -e

echo "🚀 BullsBears Database Deployment (Direct psql)"
echo "================================================"
echo ""

# Configuration
INSTANCE_IP="104.198.40.56"
DATABASE_NAME="bullsbears"
SCHEMA_FILE="scripts/setup_database.sql"

echo "📋 Configuration:"
echo "   Instance IP: $INSTANCE_IP"
echo "   Database: $DATABASE_NAME"
echo "   Schema: $SCHEMA_FILE"
echo ""

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Error: Schema file not found: $SCHEMA_FILE"
    exit 1
fi

echo "🔐 You'll be prompted for the postgres password"
echo ""

# Deploy schema
echo "🔌 Connecting to Cloud SQL and deploying schema..."
echo ""

PGPASSWORD="" psql -h $INSTANCE_IP -U postgres -d $DATABASE_NAME -f $SCHEMA_FILE

echo ""
echo "✅ Schema deployment complete!"
echo ""
echo "🔍 Verifying deployment..."
echo ""

# Verify tables
PGPASSWORD="" psql -h $INSTANCE_IP -U postgres -d $DATABASE_NAME -c "\dt" -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"

echo ""
echo "✅ Database deployment successful!"
echo ""
echo "📊 Next Steps:"
echo "   1. Get Cloud Run backend URL"
echo "   2. Update frontend/.env.local with backend URL"
echo "   3. Deploy frontend to Firebase"
echo ""

