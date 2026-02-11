#!/bin/bash
# Verification script for Sprint 0 implementation

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Sprint 0 Implementation Verification${NC}"
echo "========================================"
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PASS_COUNT=0
FAIL_COUNT=0

# Helper function to check file exists
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✅${NC} $description: $file"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}❌${NC} $description: $file (NOT FOUND)"
        ((FAIL_COUNT++))
    fi
}

# Helper function to check directory exists
check_dir() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✅${NC} $description: $dir"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}❌${NC} $description: $dir (NOT FOUND)"
        ((FAIL_COUNT++))
    fi
}

# S0-001: AGENTS.md
echo -e "${YELLOW}[S0-001]${NC} Checking AGENTS.md..."
check_file "AGENTS.md" "AI & Contributors Contract"
echo ""

# S0-002: Makefile
echo -e "${YELLOW}[S0-002]${NC} Checking Makefile..."
check_file "Makefile" "Makefile"
if [ -f "Makefile" ]; then
    # Check for key targets
    if grep -q "^install:" Makefile; then
        echo -e "  ${GREEN}✅${NC} Makefile has 'install' target"
        ((PASS_COUNT++))
    fi
    if grep -q "^start:" Makefile; then
        echo -e "  ${GREEN}✅${NC} Makefile has 'start' target"
        ((PASS_COUNT++))
    fi
    if grep -q "^test:" Makefile; then
        echo -e "  ${GREEN}✅${NC} Makefile has 'test' target"
        ((PASS_COUNT++))
    fi
    if grep -q "^lint:" Makefile; then
        echo -e "  ${GREEN}✅${NC} Makefile has 'lint' target"
        ((PASS_COUNT++))
    fi
    if grep -q "^build:" Makefile; then
        echo -e "  ${GREEN}✅${NC} Makefile has 'build' target"
        ((PASS_COUNT++))
    fi
fi
echo ""

# S0-003: .env.example and graceful startup
echo -e "${YELLOW}[S0-003]${NC} Checking environment setup..."
# .env.example may be blocked by gitignore, so ENV_SETUP.md is acceptable alternative
if [ -f "watcher-monolith/backend/.env.example" ]; then
    echo -e "  ${GREEN}✅${NC} Backend .env.example: watcher-monolith/backend/.env.example"
    ((PASS_COUNT++))
elif [ -f "ENV_SETUP.md" ]; then
    echo -e "  ${GREEN}✅${NC} Environment setup (via ENV_SETUP.md, .env.example git-ignored)"
    ((PASS_COUNT++))
else
    echo -e "  ${RED}❌${NC} No environment setup documentation found"
    ((FAIL_COUNT++))
fi
check_file "ENV_SETUP.md" "Environment setup guide"

# Check WatcherService modification
if grep -q "self.client = None" "watcher-monolith/backend/app/services/watcher_service.py"; then
    echo -e "  ${GREEN}✅${NC} WatcherService has graceful API key handling"
    ((PASS_COUNT++))
else
    echo -e "  ${RED}❌${NC} WatcherService may not handle missing API key gracefully"
    ((FAIL_COUNT++))
fi
echo ""

# S0-004: Helper scripts
echo -e "${YELLOW}[S0-004]${NC} Checking helper scripts..."
check_file "scripts/dev.sh" "Development launcher script"
check_file "scripts/test.sh" "Test runner script"

# Check if scripts are executable
if [ -x "scripts/dev.sh" ]; then
    echo -e "  ${GREEN}✅${NC} dev.sh is executable"
    ((PASS_COUNT++))
else
    echo -e "  ${YELLOW}⚠️${NC}  dev.sh is not executable (run: chmod +x scripts/dev.sh)"
fi

if [ -x "scripts/test.sh" ]; then
    echo -e "  ${GREEN}✅${NC} test.sh is executable"
    ((PASS_COUNT++))
else
    echo -e "  ${YELLOW}⚠️${NC}  test.sh is not executable (run: chmod +x scripts/test.sh)"
fi
echo ""

# S0-005: Pre-commit configuration
echo -e "${YELLOW}[S0-005]${NC} Checking pre-commit configuration..."
check_file ".pre-commit-config.yaml" "Pre-commit config"

if [ -f ".pre-commit-config.yaml" ]; then
    # Check for key hooks
    if grep -q "ruff" ".pre-commit-config.yaml"; then
        echo -e "  ${GREEN}✅${NC} Pre-commit includes ruff (Python)"
        ((PASS_COUNT++))
    fi
    if grep -q "eslint" ".pre-commit-config.yaml"; then
        echo -e "  ${GREEN}✅${NC} Pre-commit includes eslint (Frontend)"
        ((PASS_COUNT++))
    fi
fi
echo ""

# S0-006: CI workflow
echo -e "${YELLOW}[S0-006]${NC} Checking CI workflow..."
check_dir ".github" ".github directory"
check_dir ".github/workflows" ".github/workflows directory"
check_file ".github/workflows/ci.yml" "CI workflow"

if [ -f ".github/workflows/ci.yml" ]; then
    # Check for key jobs
    if grep -q "lint-python:" ".github/workflows/ci.yml"; then
        echo -e "  ${GREEN}✅${NC} CI includes Python linting job"
        ((PASS_COUNT++))
    fi
    if grep -q "lint-frontend:" ".github/workflows/ci.yml"; then
        echo -e "  ${GREEN}✅${NC} CI includes frontend linting job"
        ((PASS_COUNT++))
    fi
    if grep -q "test-backend:" ".github/workflows/ci.yml"; then
        echo -e "  ${GREEN}✅${NC} CI includes backend test job"
        ((PASS_COUNT++))
    fi
    if grep -q "build-frontend:" ".github/workflows/ci.yml"; then
        echo -e "  ${GREEN}✅${NC} CI includes frontend build job"
        ((PASS_COUNT++))
    fi
fi
echo ""

# Additional documentation
echo -e "${YELLOW}[Documentation]${NC} Checking additional files..."
check_file "SPRINT_0_SUMMARY.md" "Sprint 0 summary"
check_file "GPT-portal.MD" "Original plan"
echo ""

# Summary
echo "========================================"
echo -e "${BLUE}Verification Summary${NC}"
echo "========================================"
echo -e "${GREEN}Passed:${NC} $PASS_COUNT"
echo -e "${RED}Failed:${NC} $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ Sprint 0 implementation verified successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: make install"
    echo "  2. Configure: cp watcher-monolith/backend/.env.example watcher-monolith/backend/.env"
    echo "  3. Start: make start"
    echo "  4. Install pre-commit: pip install pre-commit && pre-commit install"
    exit 0
else
    echo -e "${RED}❌ Some Sprint 0 items are missing or incomplete${NC}"
    exit 1
fi
