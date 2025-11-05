#!/bin/bash

# BullsBears System Stop Script
# This script stops all BullsBears system components

echo "🛑 Stopping BullsBears AI/ML Stock Analysis System"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
port_in_use() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Function to kill process by PID
kill_process() {
    local pid=$1
    local name=$2
    
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "Stopping $name (PID: $pid)..."
        kill -TERM "$pid" 2>/dev/null
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing $name..."
            kill -KILL "$pid" 2>/dev/null
        fi
        echo -e "${GREEN}✅ $name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️ $name not running${NC}"
    fi
}

echo -e "${BLUE}Step 1: Stopping Frontend${NC}"

# Stop frontend using saved PID
if [ -f ".frontend_pid" ]; then
    FRONTEND_PID=$(cat .frontend_pid)
    kill_process "$FRONTEND_PID" "Frontend"
    rm -f .frontend_pid
fi

# Kill any process on port 3000
if port_in_use 3000; then
    echo "Killing any remaining processes on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

echo -e "${BLUE}Step 2: Stopping Backend${NC}"

# Stop backend using saved PID
if [ -f ".backend_pid" ]; then
    BACKEND_PID=$(cat .backend_pid)
    kill_process "$BACKEND_PID" "Backend"
    rm -f .backend_pid
fi

# Kill any process on port 8000
if port_in_use 8000; then
    echo "Killing any remaining processes on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

echo -e "${BLUE}Step 3: Redis Status${NC}"

# Note: We don't stop Redis as it might be used by other applications
if port_in_use 6379; then
    echo -e "${YELLOW}ℹ️ Redis still running (not stopped - may be used by other apps)${NC}"
    echo -e "${BLUE}   To stop Redis manually: brew services stop redis${NC}"
else
    echo -e "${GREEN}✅ Redis not running${NC}"
fi

echo -e "${BLUE}Step 4: Cleanup${NC}"

# Clean up log files (optional)
if [ -f "backend.log" ]; then
    echo "Archiving backend.log..."
    mv backend.log "backend_$(date +%Y%m%d_%H%M%S).log"
fi

if [ -f "frontend.log" ]; then
    echo "Archiving frontend.log..."
    mv frontend.log "frontend_$(date +%Y%m%d_%H%M%S).log"
fi

# Remove PID files
rm -f .backend_pid .frontend_pid

echo ""
echo -e "${GREEN}🎉 BullsBears System Stopped Successfully!${NC}"
echo "=============================================="
echo -e "${BLUE}📄 Logs archived with timestamp${NC}"
echo -e "${BLUE}🔄 To restart: ./start_bullsbears.sh${NC}"
echo ""
