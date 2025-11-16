#!/bin/bash
# Create Google Cloud SQL Instance for BullsBears
# Run this once to create the PostgreSQL instance

set -e  # Exit on error

echo "🚀 Creating Google Cloud SQL Instance"
echo "======================================"
echo ""

# Configuration
PROJECT_ID="bullsbears"
INSTANCE_NAME="bullsbears-db"
DATABASE_NAME="bullsbears"
REGION="us-central1"
TIER="db-f1-micro"  # Smallest tier for testing, upgrade to db-n1-standard-1 for production
POSTGRES_VERSION="POSTGRES_15"
STORAGE_SIZE="10GB"
WHITELISTED_IP="24.99.57.192"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Instance Configuration:${NC}"
echo "   Project: $PROJECT_ID"
echo "   Instance: $INSTANCE_NAME"
echo "   Region: $REGION"
echo "   Tier: $TIER (upgrade to db-n1-standard-1 for production)"
echo "   PostgreSQL: $POSTGRES_VERSION"
echo "   Storage: $STORAGE_SIZE"
echo "   Whitelisted IP: $WHITELISTED_IP"
echo ""

# Confirm creation
read -p "Create Cloud SQL instance? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Instance creation cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}🔨 Creating Cloud SQL instance...${NC}"
echo "This will take 5-10 minutes..."
echo ""

# Create the instance
gcloud sql instances create $INSTANCE_NAME \
    --database-version=$POSTGRES_VERSION \
    --tier=$TIER \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=$STORAGE_SIZE \
    --storage-auto-increase \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=4 \
    --project=$PROJECT_ID

echo ""
echo -e "${GREEN}✅ Instance created successfully!${NC}"
echo ""

# Set root password
echo -e "${YELLOW}🔐 Setting postgres user password...${NC}"
POSTGRES_PASSWORD=$(openssl rand -base64 32)
gcloud sql users set-password postgres \
    --instance=$INSTANCE_NAME \
    --password="$POSTGRES_PASSWORD" \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Password set!${NC}"
echo ""
echo -e "${RED}⚠️  IMPORTANT: Save this password!${NC}"
echo "   Password: $POSTGRES_PASSWORD"
echo ""

# Create database
echo -e "${YELLOW}🗄️  Creating database: $DATABASE_NAME${NC}"
gcloud sql databases create $DATABASE_NAME \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Database created!${NC}"
echo ""

# Whitelist home IP
echo -e "${YELLOW}🔓 Whitelisting your home IP: $WHITELISTED_IP${NC}"
gcloud sql instances patch $INSTANCE_NAME \
    --authorized-networks=$WHITELISTED_IP \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ IP whitelisted!${NC}"
echo ""

# Get connection info
echo -e "${YELLOW}📊 Instance Information:${NC}"
gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="table(name,databaseVersion,region,settings.tier,ipAddresses[0].ipAddress)"

echo ""
echo -e "${GREEN}🎉 Cloud SQL instance ready!${NC}"
echo ""
echo "📋 Next Steps:"
echo "   1. Save the postgres password above"
echo "   2. Run: ./scripts/deploy_database.sh"
echo "   3. Verify connection: gcloud sql connect $INSTANCE_NAME --user=postgres --database=$DATABASE_NAME"
echo ""
echo -e "${YELLOW}💰 Cost Estimate:${NC}"
echo "   db-f1-micro: ~\$7-10/month (testing)"
echo "   db-n1-standard-1: ~\$50-70/month (production)"
echo ""

