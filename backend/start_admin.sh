#!/bin/bash

# BullsBears Admin Dashboard Startup Script

echo "🚀 BullsBears Admin Dashboard"
echo "============================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update requirements
echo "📥 Installing requirements..."
pip install -r requirements_admin.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "📝 Please create .env file with required API keys:"
    echo "   RUNPOD_API_KEY=your_key_here"
    echo "   FMP_API_KEY=your_key_here"
    echo "   DATABASE_URL=your_db_url_here"
    echo ""
    echo "❓ Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Exiting..."
        exit 1
    fi
fi

# Start the admin server
echo "🌐 Starting admin dashboard..."
echo "📊 Dashboard will be available at: http://localhost:8001"
echo "🔧 API documentation at: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================="

python3 run_admin_server.py
