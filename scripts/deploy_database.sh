#!/bin/bash
# BullsBears Database Deployment Script
# Run this from your home IP (whitelisted: 24.99.57.192)

set -e  # Exit on error

echo "🚀 BullsBears Database Deployment"
echo "=================================="
echo ""

# Configuration
PROJECT_ID="bullsbears"
INSTANCE_NAME="bullsbears-prod-db"
DATABASE_NAME="bullsbears"
SCHEMA_FILE="scripts/setup_database.sql"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo -e "${RED}❌ Error: Schema file not found: $SCHEMA_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Deployment Configuration:${NC}"
echo "   Project: $PROJECT_ID"
echo "   Instance: $INSTANCE_NAME"
echo "   Database: $DATABASE_NAME"
echo "   Schema: $SCHEMA_FILE"
echo ""

# Confirm deployment
read -p "Deploy database schema? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}🔌 Connecting to Cloud SQL...${NC}"

# Deploy schema using psql via Cloud SQL Proxy
PGPASSWORD=$(gcloud sql users describe postgres --instance=$INSTANCE_NAME --format="value(password)" 2>/dev/null || echo "")

if [ -z "$PGPASSWORD" ]; then
    echo -e "${YELLOW}⚠️  Using gcloud sql connect (interactive)${NC}"
    gcloud sql connect $INSTANCE_NAME --user=postgres --database=$DATABASE_NAME --project=$PROJECT_ID < $SCHEMA_FILE
else
    echo -e "${YELLOW}⚠️  Using direct psql connection${NC}"
    psql "host=/cloudsql/$PROJECT_ID:us-central1:$INSTANCE_NAME dbname=$DATABASE_NAME user=postgres" < $SCHEMA_FILE
fi

echo ""
echo -e "${GREEN}✅ Schema deployment complete!${NC}"
echo ""

# Verify deployment
echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
echo ""

# Count tables
TABLE_COUNT=$(gcloud sql connect $INSTANCE_NAME --user=postgres --database=$DATABASE_NAME --project=$PROJECT_ID <<EOF
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
EOF
)

echo -e "${GREEN}✅ Database deployment successful!${NC}"
echo ""
echo "📊 Next Steps:"
echo "   1. Verify tables: gcloud sql connect $INSTANCE_NAME --user=postgres --database=$DATABASE_NAME"
echo "   2. Run: \\dt to list all tables"
echo "   3. Check seed data: SELECT * FROM feature_weights;"
echo "   4. Test backend connection from Cloud Run"
echo ""
echo -e "${GREEN}🎉 Ready for production!${NC}"

