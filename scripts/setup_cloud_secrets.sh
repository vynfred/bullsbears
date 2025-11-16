#!/bin/bash
# Setup Google Cloud Secrets for BullsBears Backend
# This creates all required secrets from backend/.env

set -e

echo "🔐 Setting up Google Cloud Secrets"
echo "==================================="
echo ""

PROJECT_ID="bullsbears"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Reading secrets from backend/.env...${NC}"
echo ""

# Source the .env file
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env not found"
    exit 1
fi

# Export variables from .env
export $(grep -v '^#' backend/.env | xargs)

# Create or update secrets
echo -e "${YELLOW}Creating/updating secrets in Google Cloud Secret Manager...${NC}"
echo ""

# Database password
echo "📝 DB_PASSWORD"
echo -n "$DB_PASSWORD" | gcloud secrets create DB_PASSWORD --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$DB_PASSWORD" | gcloud secrets versions add DB_PASSWORD --data-file=- --project=$PROJECT_ID

# FMP API Key
echo "📝 FMP_API_KEY"
echo -n "$FMP_API_KEY" | gcloud secrets create FMP_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$FMP_API_KEY" | gcloud secrets versions add FMP_API_KEY --data-file=- --project=$PROJECT_ID

# RunPod API Key
echo "📝 RUNPOD_API_KEY"
echo -n "$RUNPOD_API_KEY" | gcloud secrets create RUNPOD_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$RUNPOD_API_KEY" | gcloud secrets versions add RUNPOD_API_KEY --data-file=- --project=$PROJECT_ID

# Groq API Key
echo "📝 GROQ_API_KEY"
echo -n "$GROQ_API_KEY" | gcloud secrets create GROQ_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$GROQ_API_KEY" | gcloud secrets versions add GROQ_API_KEY --data-file=- --project=$PROJECT_ID

# Grok API Key
echo "📝 GROK_API_KEY"
echo -n "$GROK_API_KEY" | gcloud secrets create GROK_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$GROK_API_KEY" | gcloud secrets versions add GROK_API_KEY --data-file=- --project=$PROJECT_ID

# DeepSeek API Key
echo "📝 DEEPSEEK_API_KEY"
echo -n "$DEEPSEEK_API_KEY" | gcloud secrets create DEEPSEEK_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$DEEPSEEK_API_KEY" | gcloud secrets versions add DEEPSEEK_API_KEY --data-file=- --project=$PROJECT_ID

# Gemini API Key
echo "📝 GEMINI_PRO_API_KEY"
echo -n "$GEMINI_PRO_API_KEY" | gcloud secrets create GEMINI_PRO_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$GEMINI_PRO_API_KEY" | gcloud secrets versions add GEMINI_PRO_API_KEY --data-file=- --project=$PROJECT_ID

# Claude API Key
echo "📝 CLAUDE_ANTHROPIC_API_KEY"
echo -n "$CLAUDE_ANTHROPIC_API_KEY" | gcloud secrets create CLAUDE_ANTHROPIC_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$CLAUDE_ANTHROPIC_API_KEY" | gcloud secrets versions add CLAUDE_ANTHROPIC_API_KEY --data-file=- --project=$PROJECT_ID

# OpenAI API Key
echo "📝 OPENAI_API_KEY"
echo -n "$OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$OPENAI_API_KEY" | gcloud secrets versions add OPENAI_API_KEY --data-file=- --project=$PROJECT_ID

# Firebase API Key
echo "📝 FIREBASE_API_KEY"
echo -n "$FIREBASE_API_KEY" | gcloud secrets create FIREBASE_API_KEY --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$FIREBASE_API_KEY" | gcloud secrets versions add FIREBASE_API_KEY --data-file=- --project=$PROJECT_ID

echo ""
echo -e "${GREEN}✅ All secrets created/updated!${NC}"
echo ""
echo "📋 Secrets in Google Cloud Secret Manager:"
gcloud secrets list --project=$PROJECT_ID

echo ""
echo -e "${GREEN}🎉 Ready to deploy to Cloud Run!${NC}"
echo ""
echo "Next step: ./scripts/deploy_backend_to_cloud_run.sh"

