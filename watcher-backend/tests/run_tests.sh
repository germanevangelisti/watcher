#!/bin/bash
# Test runner script for Watcher Agent
# Ejecuta los tests válidos, ignorando los obsoletos del monolito

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Running Watcher Agent Test Suite${NC}"
echo ""

# Array de tests obsoletos a ignorar
IGNORE_TESTS=(
    "watcher-backend/tests/tests/test_extraction_integration.py"
    "watcher-backend/tests/tests/test_extraction_schemas.py"
    "watcher-backend/tests/tests/test_extractors.py"
    "watcher-backend/tests/tests/e2e/test_full_pipeline.py"
    "watcher-backend/tests/tests/integration/test_dia_kaa_flow.py"
    "watcher-backend/tests/tests/unit/test_kaa_agents.py"
)

# Construir argumentos de ignore
IGNORE_ARGS=""
for test in "${IGNORE_TESTS[@]}"; do
    IGNORE_ARGS="$IGNORE_ARGS --ignore=$test"
done

# Ejecutar pytest
python -m pytest watcher-backend/tests/ $IGNORE_ARGS "$@"

echo ""
echo -e "${GREEN}✅ Test run completed${NC}"
