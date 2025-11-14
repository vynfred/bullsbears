#!/bin/bash

# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
sleep 10

# Download models
echo "📥 Downloading AI models..."
ollama pull llama3.2:3b
ollama pull deepseek-r1:8b
ollama pull qwen2.5:32b
ollama pull llama3.2-vision:11b

echo "✅ All models ready!"

# Start RunPod handler
python /workspace/runpod_handler.py
