#!/bin/bash

# BullsBears System Test Script
# This script runs comprehensive tests on the running BullsBears system

echo "🧪 BullsBears System Test Suite"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_status="$3"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        if [ "$expected_status" = "success" ]; then
            echo -e "${GREEN}✅ PASS${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}❌ FAIL (expected failure but got success)${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        if [ "$expected_status" = "fail" ]; then
            echo -e "${GREEN}✅ PASS (expected failure)${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}❌ FAIL${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
}

# Function to test API endpoint with response validation
test_api_endpoint() {
    local endpoint="$1"
    local test_name="$2"
    
    echo -n "Testing $test_name... "
    
    response=$(curl -s -w "%{http_code}" "$endpoint")
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        # Check if response is valid JSON
        if echo "$response_body" | python3 -m json.tool >/dev/null 2>&1; then
            echo -e "${GREEN}✅ PASS (HTTP $http_code, valid JSON)${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${YELLOW}⚠️ PARTIAL (HTTP $http_code, invalid JSON)${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        echo -e "${RED}❌ FAIL (HTTP $http_code)${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo -e "${BLUE}Infrastructure Tests${NC}"
echo "-------------------"

# Test Redis connection
run_test "Redis Connection" "redis-cli ping | grep -q PONG" "success"

# Test database file exists
run_test "Database File" "test -f backend/test.db" "success"

echo ""
echo -e "${BLUE}Backend API Tests${NC}"
echo "-----------------"

# Test health endpoint
test_api_endpoint "http://127.0.0.1:8000/health" "Health Endpoint"

# Test bullish alerts endpoint
test_api_endpoint "http://127.0.0.1:8000/api/v1/bullish_alerts/" "Bullish Alerts API"

# Test bearish alerts endpoint
test_api_endpoint "http://127.0.0.1:8000/api/v1/bearish_alerts/" "Bearish Alerts API"

# Test API documentation
run_test "API Documentation" "curl -s http://127.0.0.1:8000/docs | grep -q 'FastAPI'" "success"

echo ""
echo -e "${BLUE}Frontend Tests${NC}"
echo "--------------"

# Test frontend homepage
run_test "Frontend Homepage" "curl -s http://localhost:3000 | grep -q 'BullsBears'" "success"

# Test frontend dashboard
run_test "Frontend Dashboard" "curl -s http://localhost:3000/dashboard | grep -q 'html'" "success"

echo ""
echo -e "${BLUE}Database Tests${NC}"
echo "--------------"

# Test database has data
echo -n "Testing Database Data... "
db_count=$(python3 -c "
import sqlite3
conn = sqlite3.connect('backend/test.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM analysis_results')
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null)

if [ "$db_count" -gt 0 ]; then
    echo -e "${GREEN}✅ PASS ($db_count records)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ FAIL (no data)${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""
echo -e "${BLUE}Performance Tests${NC}"
echo "-----------------"

# Test API response time
echo -n "Testing API Response Time... "
response_time=$(curl -o /dev/null -s -w "%{time_total}" http://127.0.0.1:8000/health)
response_time_ms=$(echo "$response_time * 1000" | bc)

if (( $(echo "$response_time < 1.0" | bc -l) )); then
    echo -e "${GREEN}✅ PASS (${response_time_ms}ms)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️ SLOW (${response_time_ms}ms)${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""
echo "==============================="
echo -e "${BLUE}Test Results Summary${NC}"
echo "==============================="
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $TESTS_PASSED * 100 / $TOTAL_TESTS" | bc)
    echo -e "${BLUE}📊 Success Rate: ${SUCCESS_RATE}%${NC}"
fi

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All tests passed! System is ready for use.${NC}"
    exit 0
else
    echo ""
    echo -e "${YELLOW}⚠️ Some tests failed. Check the system status.${NC}"
    exit 1
fi
