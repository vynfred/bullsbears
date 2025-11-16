#!/bin/bash
# Deploy BullsBears Backend to Google Cloud Run
# This builds the Docker image and deploys to Cloud Run

set -e  # Exit on error

echo "🚀 BullsBears Backend Deployment to Cloud Run"
echo "=============================================="
echo ""

# Configuration
PROJECT_ID="bullsbears"
SERVICE_NAME="bullsbears-backend"
REGION="us-central1"
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}"
DB_INSTANCE="bullsbears-prod-db"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Deployment Configuration:${NC}"
echo "   Project: $PROJECT_ID"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Image: $IMAGE_NAME"
echo "   Database: $DB_INSTANCE"
echo ""

# Confirm deployment
read -p "Deploy backend to Cloud Run? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
echo "This will take 5-10 minutes (TA-Lib compilation)..."
echo ""

# Build and push using Cloud Build
cd backend
gcloud builds submit \
    --tag $IMAGE_NAME \
    --project=$PROJECT_ID \
    --timeout=20m

echo ""
echo -e "${GREEN}✅ Image built and pushed!${NC}"
echo ""

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
echo ""

gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --cpu-boost \
    --set-env-vars "ENVIRONMENT=production,DATABASE_NAME=bullsbears,DATABASE_HOST=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE},DATABASE_PORT=5432,DATABASE_USER=postgres,FIREBASE_PROJECT_ID=bullsbears-xyz,FIREBASE_DATABASE_URL=https://bullsbears-xyz-default-rtdb.firebaseio.com/,ADMIN_EMAIL=hellovynfred@gmail.com" \
    --set-cloudsql-instances "${PROJECT_ID}:${REGION}:${DB_INSTANCE}" \
    --set-secrets "DATABASE_PASSWORD=DB_PASSWORD:latest,FMP_API_KEY=FMP_API_KEY:latest,GROQ_API_KEY=GROQ_API_KEY:latest,GROK_API_KEY=GROK_API_KEY:latest,RUNPOD_API_KEY=RUNPOD_API_KEY:latest,FIREBASE_API_KEY=FIREBASE_API_KEY:latest,DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest,GEMINI_PRO_API_KEY=GEMINI_PRO_API_KEY:latest,CLAUDE_ANTHROPIC_API_KEY=CLAUDE_ANTHROPIC_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,ADMIN_PASSWORD_HASH=ADMIN_PASSWORD_HASH:latest"

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --format='value(status.url)')

echo -e "${GREEN}🎉 Backend deployed successfully!${NC}"
echo ""
echo "📊 Service Information:"
echo "   URL: $SERVICE_URL"
echo "   Health Check: ${SERVICE_URL}/health"
echo "   Admin Dashboard: ${SERVICE_URL}/admin"
echo ""
echo "📋 Next Steps:"
echo "   1. Test health endpoint: curl ${SERVICE_URL}/health"
echo "   2. Update frontend/.env.local with: NEXT_PUBLIC_API_URL=${SERVICE_URL}"
echo "   3. Deploy frontend to Firebase"
echo ""
echo -e "${YELLOW}💰 Cost Estimate:${NC}"
echo "   Cloud Run: ~\$0.10-0.50/day (with min-instances=0)"
echo "   Cloud SQL: ~\$0.30/day (db-custom-2-8192)"
echo ""

