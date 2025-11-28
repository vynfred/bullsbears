#!/bin/bash
set -e

# BullsBears Cloud Scheduler Setup
# Creates Cloud Scheduler jobs to trigger internal task endpoints

PROJECT_ID="bullsbears"
REGION="us-central1"
SERVICE_URL="https://bullsbears-backend-saonzofwoa-uc.a.run.app"
TIMEZONE="America/New_York"

echo "🚀 Setting up Cloud Scheduler jobs for BullsBears"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service URL: $SERVICE_URL"
echo ""

# Enable Cloud Scheduler API if not already enabled
echo "📦 Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Create service account for Cloud Scheduler if it doesn't exist
echo "🔐 Setting up service account..."
SA_EMAIL="cloud-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    gcloud iam service-accounts create cloud-scheduler \
        --display-name="Cloud Scheduler Service Account" \
        --project=$PROJECT_ID
    echo "✅ Service account created"
else
    echo "✅ Service account already exists"
fi

# Grant Cloud Run Invoker role to service account
echo "🔐 Granting Cloud Run Invoker role..."
gcloud run services add-iam-policy-binding bullsbears-backend \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" \
    --region=$REGION \
    --project=$PROJECT_ID

echo ""
echo "📅 Creating scheduler jobs..."
echo ""

# Helper function to create or update a job
create_or_update_job() {
    local JOB_NAME=$1
    local SCHEDULE=$2
    local ENDPOINT=$3
    local DESCRIPTION=$4
    
    echo "⏰ $JOB_NAME: $SCHEDULE"
    
    # Check if job exists
    if gcloud scheduler jobs describe $JOB_NAME --location=$REGION --project=$PROJECT_ID &>/dev/null; then
        echo "   Updating existing job..."
        gcloud scheduler jobs update http $JOB_NAME \
            --location=$REGION \
            --schedule="$SCHEDULE" \
            --uri="${SERVICE_URL}${ENDPOINT}" \
            --http-method=POST \
            --oidc-service-account-email=$SA_EMAIL \
            --oidc-token-audience="${SERVICE_URL}" \
            --time-zone="$TIMEZONE" \
            --project=$PROJECT_ID \
            --quiet
    else
        echo "   Creating new job..."
        gcloud scheduler jobs create http $JOB_NAME \
            --location=$REGION \
            --schedule="$SCHEDULE" \
            --uri="${SERVICE_URL}${ENDPOINT}" \
            --http-method=POST \
            --oidc-service-account-email=$SA_EMAIL \
            --oidc-token-audience="${SERVICE_URL}" \
            --time-zone="$TIMEZONE" \
            --description="$DESCRIPTION" \
            --project=$PROJECT_ID
    fi
    echo "   ✅ Done"
    echo ""
}

# Daily Pipeline (8:00 AM - 8:25 AM EST)
create_or_update_job "fmp-delta-update" "0 8 * * *" "/internal/fmp-delta" "8:00 AM - FMP Daily Delta Update"
create_or_update_job "build-active-tier" "5 8 * * *" "/internal/build-active" "8:05 AM - Build ACTIVE tier"
create_or_update_job "run-prescreen" "10 8 * * *" "/internal/prescreen" "8:10 AM - Prescreen Agent"
create_or_update_job "generate-charts" "15 8 * * *" "/internal/generate-charts" "8:15 AM - Generate Charts"
create_or_update_job "vision-analysis" "16 8 * * *" "/internal/vision-analysis" "8:16 AM - Vision Analysis"
create_or_update_job "social-analysis" "17 8 * * *" "/internal/social-analysis" "8:17 AM - Social Analysis"
create_or_update_job "run-arbitrator" "20 8 * * *" "/internal/arbitrator" "8:20 AM - Final Arbitrator"
create_or_update_job "publish-picks" "25 8 * * *" "/internal/publish-picks" "8:25 AM - Publish to Firebase"

# Weekly Learner (Saturday 4:00 AM EST)
create_or_update_job "weekly-learner" "0 4 * * 6" "/internal/weekly-learner" "Saturday 4:00 AM - Weekly Learner"

# Continuous Updates
create_or_update_job "update-statistics" "*/5 * * * *" "/internal/update-statistics" "Every 5 minutes - Update Statistics"
create_or_update_job "update-badges" "*/2 9-16 * * 1-5" "/internal/update-badges" "Every 2 min (market hours) - Update Badges"

echo ""
echo "✅ All Cloud Scheduler jobs created successfully!"
echo ""
echo "📋 View all jobs:"
echo "   gcloud scheduler jobs list --location=$REGION --project=$PROJECT_ID"
echo ""
echo "🧪 Test a job manually:"
echo "   gcloud scheduler jobs run fmp-delta-update --location=$REGION --project=$PROJECT_ID"
echo ""
echo "📊 View job logs:"
echo "   gcloud logging read 'resource.type=cloud_scheduler_job' --limit=50 --project=$PROJECT_ID"
echo ""
echo "🎉 Setup complete! Your daily pipeline will run automatically at 8:00 AM EST."

