#!/bin/bash

# Script para ejecutar el test completo del workflow
# Uso: ./tests/run_test.sh [YYYYMMDD]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         WATCHER AGENT - TEST DE WORKFLOW COMPLETO                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Fecha de test (default: 1 de enero de 2025)
TEST_DATE=${1:-20250101}

echo -e "${YELLOW}📅 Fecha de test: ${TEST_DATE}${NC}"
echo -e "${YELLOW}🔍 Verificando dependencias...${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "watcher-monolith/backend/app/main.py" ]; then
    echo -e "${RED}❌ Error: Debes ejecutar este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Activar el entorno virtual del backend
if [ -d "watcher-monolith/backend/venv" ]; then
    echo -e "${GREEN}✓ Activando entorno virtual...${NC}"
    source watcher-monolith/backend/venv/bin/activate
else
    echo -e "${RED}❌ Error: No se encontró el entorno virtual${NC}"
    echo -e "${YELLOW}   Ejecuta: cd watcher-monolith/backend && python -m venv venv && pip install -r requirements.txt${NC}"
    exit 1
fi

# Verificar que la base de datos existe
if [ ! -f "watcher-monolith/backend/sqlite.db" ]; then
    echo -e "${RED}❌ Error: No se encontró la base de datos${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencias verificadas${NC}"
echo ""

# Ejecutar el test
echo -e "${BLUE}🚀 Ejecutando test...${NC}"
echo ""

python tests/test_complete_workflow.py

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  ✅ TEST PASADO EXITOSAMENTE                      ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ❌ TEST FALLIDO                                ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════╝${NC}"
fi

echo ""
echo -e "${YELLOW}📊 Revisa los resultados en: tests/test_results/${NC}"
echo ""

exit $EXIT_CODE
