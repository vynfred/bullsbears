#!/bin/bash

# BullsBears AI RunPod Minimal & Lethal Setup Script (November 10, 2025)
# Optimized for current production pipeline: 1 local model + cloud APIs

set -e

echo "BullsBears AI – Lean Production Setup"
echo "====================================================================="

# System update
echo "Updating system & installing essentials..."
apt-get update -y
apt-get install -y curl wget git python3 python3-pip build-essential postgresql-client redis-tools jq

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

# Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install \
    fastapi uvicorn[standard] \
    asyncio aiohttp \
    asyncpg \
    python-dotenv \
    pandas numpy \
    requests \
    celery[redis] \
    redis \
    matplotlib \
    python-dateutil \
    plotly

# Create workspace
echo "Creating workspace..."
mkdir -p /workspace/bullsbears/{backend,scripts,logs,prompts,learning_history}
cd /workspace/bullsbears

# Start Ollama
echo "Starting Ollama service..."
export OLLAMA_HOST=0.0.0.0:11434
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama
echo "Waiting for Ollama to be ready..."
for i in {1..20}; do
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "Ollama ready!"
        break
    fi
    echo "Still waiting... ($i/20)"
    sleep 3
done

# ONLY ONE LOCAL MODEL
echo "Downloading FinMA-7b (Prescreen Agent – ACTIVE to exactly 75 SHORT_LIST)..."
ollama pull finma-7b

echo "All local models ready (just 1 – perfect!)"
echo "FinMA-7b VRAM usage: ~4.2 GB"

# Create final folder structure
echo "Setting up final agent structure..."
mkdir -p backend/app/{api/v1,services/{agents,data_collectors},core}
mkdir -p backend/app/services/agents/prompts

# Copy your current prompt files (preserved across restarts)
cat > backend/app/services/agents/prompts/finma_prescreen_v3.txt << 'EOF'
You are FinMA-7b explosive-move hunter...
EOF

cat > backend/app/services/agents/prompts/vision_prompt.txt << 'EOF'
You are ChartVision. Detect ONLY these six patterns...
EOF

cat > backend/app/services/agents/prompts/social_context_prompt.txt << 'EOF'
Return ONLY a single integer from -5 to +5...
EOF

# Status
echo ""
echo "BullsBears AI – Production Ready!"
echo "============================================"
echo "Local (RunPod):"
echo "   • FinMA-7b (4.2 GB) – Prescreen only"
echo ""
echo "Cloud APIs (zero local VRAM):"
echo "   • Groq Llama-3.2-11B-Vision – 75 vision calls"
echo "   • Grok API – Social + News + Polymarket"
echo "   • Rotating Arbitrator (DeepSeek-V3 / Gemini 2.5 Pro / Grok 4 / etc.)"
echo ""
echo "Ollama API: http://0.0.0.0:11434"
echo "Workspace: /workspace/bullsbears"
echo "Logs: /workspace/bullsbears/logs"
echo ""
echo "RunPod is now MINIMAL & LETHAL."
echo "Ready for Celery pipeline start!"
echo ""

# Keep Ollama alive
wait $OLLAMA_PID