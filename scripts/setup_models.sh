#!/bin/bash

# BullsBears AI Models Setup Script

# Model list with sizes (approximate) – Updated November 10, 2025
declare -A MODELS=(
    # LOCAL – RunPod only (what actually runs on your hardware)
    ["finma-7b"]="4.2GB"        # Prescreen Agent – ACTIVE → exactly 75 SHORT_LIST (one call daily)

    # CLOUD – API only (zero local VRAM, zero infra)
    ["groq-llama3.2-11b-vision"]="0GB"   # Vision Agent – 75 charts → 6 boolean flags
    ["grok-api"]="0GB"                   # Social + News + Events + Polymarket context
    ["deepseek-v3"]="0GB"                # Arbitrator (Mon & Sat)
    ["gemini-2.5-pro"]="0GB"             # Arbitrator (Tue & Sun)
    ["grok-4"]="0GB"                     # Arbitrator (Wed)
    ["claude-sonnet-4"]="0GB"            # Arbitrator (Thu)
    ["gpt-5"]="0GB"                      # Arbitrator (Fri – o3 mode)
)

echo ""
echo "📦 Pulling required models..."
echo "Total estimated size: ~265GB"
echo ""


echo "🎯 Model setup complete!"
echo ""
echo "📊 Available models:"
ollama list

echo ""
echo "🚀 BullsBears AI inference server is ready!"
echo "   API endpoint: http://localhost:11434"
echo "   Health check: http://localhost:11434/api/tags"
