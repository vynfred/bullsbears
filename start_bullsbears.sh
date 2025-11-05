#!/bin/bash

# BullsBears System Startup Script
# This script starts all components needed to run the BullsBears AI/ML stock analysis system

echo "🚀 Starting BullsBears AI/ML Stock Analysis System"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service_name to be ready"
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e " ${GREEN}✅${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}❌ Timeout${NC}"
    return 1
}

echo -e "${BLUE}Step 1: Checking Prerequisites${NC}"

# Check if Redis is installed
if ! command_exists redis-server; then
    echo -e "${RED}❌ Redis not found. Installing...${NC}"
    brew install redis
fi

# Check if Python 3 is installed
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command_exists node; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check complete${NC}"

echo -e "${BLUE}Step 2: Starting Redis${NC}"

# Start Redis if not running
if ! port_in_use 6379; then
    echo "Starting Redis server..."
    brew services start redis
    sleep 2
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Redis${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Redis already running${NC}"
fi

echo -e "${BLUE}Step 3: Starting Backend API${NC}"

# Kill any existing backend process
if port_in_use 8000; then
    echo "Stopping existing backend process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start backend in background
echo "Starting FastAPI backend server..."
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
if wait_for_service "http://127.0.0.1:8000/health" "Backend API"; then
    echo -e "${GREEN}✅ Backend API started successfully (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Failed to start Backend API${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${BLUE}Step 4: Starting Frontend${NC}"

# Kill any existing frontend process
if port_in_use 3000; then
    echo "Stopping existing frontend process..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start frontend in background
echo "Starting Next.js frontend server..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
if wait_for_service "http://localhost:3000" "Frontend"; then
    echo -e "${GREEN}✅ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}❌ Failed to start Frontend${NC}"
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${BLUE}Step 5: System Status Check${NC}"

# Test API endpoints
echo "Testing API endpoints..."
if curl -s "http://127.0.0.1:8000/api/v1/bullish_alerts/" >/dev/null; then
    echo -e "${GREEN}✅ Bullish alerts API working${NC}"
else
    echo -e "${YELLOW}⚠️ Bullish alerts API not responding${NC}"
fi

if curl -s "http://127.0.0.1:8000/api/v1/bearish_alerts/" >/dev/null; then
    echo -e "${GREEN}✅ Bearish alerts API working${NC}"
else
    echo -e "${YELLOW}⚠️ Bearish alerts API not responding${NC}"
fi

echo ""
echo -e "${GREEN}🎉 BullsBears System Started Successfully!${NC}"
echo "=================================================="
echo -e "${BLUE}📱 Frontend:${NC} http://localhost:3000"
echo -e "${BLUE}🔧 Backend API:${NC} http://127.0.0.1:8000"
echo -e "${BLUE}📚 API Docs:${NC} http://127.0.0.1:8000/docs"
echo -e "${BLUE}💾 Redis:${NC} localhost:6379"
echo ""
echo -e "${YELLOW}📋 Process IDs:${NC}"
echo -e "   Backend: $BACKEND_PID"
echo -e "   Frontend: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}📄 Logs:${NC}"
echo -e "   Backend: backend.log"
echo -e "   Frontend: frontend.log"
echo ""
echo -e "${BLUE}🛑 To stop the system:${NC}"
echo "   ./stop_bullsbears.sh"
echo "   or manually: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo -e "${GREEN}Ready for testing! 🚀${NC}"

# Save PIDs for stop script
echo "$BACKEND_PID" > .backend_pid
echo "$FRONTEND_PID" > .frontend_pid
