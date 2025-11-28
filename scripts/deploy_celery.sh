#!/bin/bash
# Deploy Celery Worker and Beat to Google Cloud Run
# Usage: ./scripts/deploy_celery.sh [worker|beat|all]

set -e

# Configuration
PROJECT_ID="bullsbears-xyz"
REGION="us-central1"
WORKER_SERVICE="bullsbears-celery-worker"
BEAT_SERVICE="bullsbears-celery-beat"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}Error: backend/.env file not found${NC}"
    echo "Please create backend/.env with required environment variables"
    exit 1
fi

# Load environment variables
source backend/.env

# Check required environment variables
REQUIRED_VARS=(
    "DATABASE_URL"
    "CELERY_BROKER_URL"
    "CELERY_RESULT_BACKEND"
    "FMP_API_KEY"
    "GROQ_API_KEY"
    "GROK_API_KEY"
    "DEEPSEEK_API_KEY"
    "RUNPOD_API_KEY"
    "FIREBASE_CREDENTIALS_JSON"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: $var is not set in .env${NC}"
        exit 1
    fi
done

# Function to deploy worker
deploy_worker() {
    echo -e "${GREEN}Deploying Celery Worker...${NC}"
    
    gcloud run deploy $WORKER_SERVICE \
        --source backend \
        --dockerfile backend/Dockerfile.worker \
        --region $REGION \
        --platform managed \
        --project $PROJECT_ID \
        --no-allow-unauthenticated \
        --set-env-vars="DATABASE_URL=$DATABASE_URL" \
        --set-env-vars="CELERY_BROKER_URL=$CELERY_BROKER_URL" \
        --set-env-vars="CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND" \
        --set-env-vars="FMP_API_KEY=$FMP_API_KEY" \
        --set-env-vars="GROQ_API_KEY=$GROQ_API_KEY" \
        --set-env-vars="GROK_API_KEY=$GROK_API_KEY" \
        --set-env-vars="DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY" \
        --set-env-vars="RUNPOD_API_KEY=$RUNPOD_API_KEY" \
        --set-env-vars="FIREBASE_CREDENTIALS_JSON=$FIREBASE_CREDENTIALS_JSON" \
        --min-instances=1 \
        --max-instances=1 \
        --memory=2Gi \
        --cpu=2 \
        --timeout=3600 \
        --no-cpu-throttling
    
    echo -e "${GREEN}✅ Celery Worker deployed successfully${NC}"
}

# Function to deploy beat
deploy_beat() {
    echo -e "${GREEN}Deploying Celery Beat...${NC}"
    
    gcloud run deploy $BEAT_SERVICE \
        --source backend \
        --dockerfile backend/Dockerfile.beat \
        --region $REGION \
        --platform managed \
        --project $PROJECT_ID \
        --no-allow-unauthenticated \
        --set-env-vars="DATABASE_URL=$DATABASE_URL" \
        --set-env-vars="CELERY_BROKER_URL=$CELERY_BROKER_URL" \
        --set-env-vars="CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND" \
        --set-env-vars="FMP_API_KEY=$FMP_API_KEY" \
        --set-env-vars="GROQ_API_KEY=$GROQ_API_KEY" \
        --set-env-vars="GROK_API_KEY=$GROK_API_KEY" \
        --set-env-vars="DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY" \
        --set-env-vars="RUNPOD_API_KEY=$RUNPOD_API_KEY" \
        --set-env-vars="FIREBASE_CREDENTIALS_JSON=$FIREBASE_CREDENTIALS_JSON" \
        --min-instances=1 \
        --max-instances=1 \
        --memory=512Mi \
        --cpu=1 \
        --timeout=3600 \
        --no-cpu-throttling
    
    echo -e "${GREEN}✅ Celery Beat deployed successfully${NC}"
}

# Main deployment logic
case "${1:-all}" in
    worker)
        deploy_worker
        ;;
    beat)
        deploy_beat
        ;;
    all)
        deploy_worker
        deploy_beat
        ;;
    *)
        echo -e "${RED}Usage: $0 [worker|beat|all]${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "To check status:"
echo "  gcloud run services describe $WORKER_SERVICE --region $REGION"
echo "  gcloud run services describe $BEAT_SERVICE --region $REGION"
echo ""
echo "To view logs:"
echo "  gcloud run services logs read $WORKER_SERVICE --region $REGION"
echo "  gcloud run services logs read $BEAT_SERVICE --region $REGION"

