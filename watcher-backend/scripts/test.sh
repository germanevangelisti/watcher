#!/bin/bash
# Test script - Run all tests for backend and frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Watcher Agent - Test Suite${NC}"
echo "==============================="
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Track test results
BACKEND_TESTS_PASSED=0
FRONTEND_TESTS_PASSED=0

# Backend Tests
echo -e "${GREEN}Running Backend Tests...${NC}"
echo "----------------------------------------"
cd "$PROJECT_ROOT/watcher-backend"

# Check if pytest is available
if command -v pytest &> /dev/null; then
    # Check if tests directory exists
    if [ -d "tests" ] && [ "$(ls -A tests 2>/dev/null)" ]; then
        if python -m pytest tests/ -v --color=yes; then
            echo -e "${GREEN}✅ Backend tests passed${NC}"
            BACKEND_TESTS_PASSED=1
        else
            echo -e "${RED}❌ Backend tests failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No backend tests found in tests/ directory${NC}"
        BACKEND_TESTS_PASSED=1  # Don't fail if no tests exist
    fi
else
    echo -e "${YELLOW}⚠️  pytest not installed - skipping backend tests${NC}"
    echo -e "   Install with: ${GREEN}pip install pytest${NC}"
    BACKEND_TESTS_PASSED=1  # Don't fail if pytest not installed
fi

echo ""

# Frontend Tests
echo -e "${GREEN}Running Frontend Tests...${NC}"
echo "----------------------------------------"
cd "$PROJECT_ROOT/watcher-frontend"

# Check if test script exists in package.json
if grep -q '"test"' package.json; then
    if npm test; then
        echo -e "${GREEN}✅ Frontend tests passed${NC}"
        FRONTEND_TESTS_PASSED=1
    else
        echo -e "${RED}❌ Frontend tests failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No frontend tests configured${NC}"
    echo -e "   Add test script to package.json"
    FRONTEND_TESTS_PASSED=1  # Don't fail if no tests configured
fi

echo ""
echo "==============================="
echo -e "${BLUE}Test Summary${NC}"
echo "==============================="

if [ $BACKEND_TESTS_PASSED -eq 1 ] && [ $FRONTEND_TESTS_PASSED -eq 1 ]; then
    echo -e "${GREEN}✅ All tests passed${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    [ $BACKEND_TESTS_PASSED -eq 0 ] && echo -e "  - Backend tests: ${RED}FAILED${NC}"
    [ $FRONTEND_TESTS_PASSED -eq 0 ] && echo -e "  - Frontend tests: ${RED}FAILED${NC}"
    exit 1
fi
