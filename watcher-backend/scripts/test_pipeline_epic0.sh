#!/bin/bash
#
# Script de prueba completo para Epic 0 - Pipeline de procesamiento
# Prueba un solo día para validar toda la cadena
#

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
API_BASE="http://localhost:8000/api/v1"
TEST_YEAR="2025"
TEST_MONTH="01"
TEST_DAY="03"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   EPIC 0 - Pipeline Test - Día ${TEST_DAY}/${TEST_MONTH}/${TEST_YEAR}${NC}"
echo -e "${BLUE}================================================${NC}\n"

# 1. Health Check
echo -e "${YELLOW}[1/6] Verificando salud del servidor...${NC}"
HEALTH=$(curl -s -w "\n%{http_code}" "${API_BASE}/dashboard/stats" | tail -1)
if [ "$HEALTH" == "200" ]; then
    echo -e "${GREEN}✓ Servidor OK${NC}\n"
else
    echo -e "${RED}✗ Servidor no responde (HTTP $HEALTH)${NC}"
    exit 1
fi

# 2. Contar documentos del día
echo -e "${YELLOW}[2/6] Contando documentos del día ${TEST_DAY}/${TEST_MONTH}/${TEST_YEAR}...${NC}"
COUNT_RESPONSE=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}")
TOTAL=$(echo $COUNT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
echo -e "Total documentos encontrados: ${BLUE}${TOTAL}${NC}"

if [ "$TOTAL" == "0" ]; then
    echo -e "${RED}✗ No hay documentos para procesar${NC}"
    exit 1
fi

COUNT_PENDING=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&status=pending" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
COUNT_COMPLETED=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&status=completed" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")

echo -e "  - Pendientes: ${YELLOW}${COUNT_PENDING}${NC}"
echo -e "  - Completados: ${GREEN}${COUNT_COMPLETED}${NC}\n"

# 3. Iniciar procesamiento
echo -e "${YELLOW}[3/6] Iniciando procesamiento (background)...${NC}"
PROCESS_RESPONSE=$(curl -s -X POST "${API_BASE}/boletines/process-batch?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&limit=100")
SESSION_ID=$(echo $PROCESS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'N/A'))" 2>/dev/null || echo "ERROR")

if [ "$SESSION_ID" == "ERROR" ] || [ "$SESSION_ID" == "N/A" ]; then
    echo -e "${RED}✗ Error al iniciar procesamiento${NC}"
    echo "Respuesta: $PROCESS_RESPONSE"
    exit 1
fi

echo -e "Session ID: ${BLUE}${SESSION_ID}${NC}"
echo -e "${GREEN}✓ Procesamiento iniciado en background${NC}\n"

# 4. Monitorear logs (polling cada 2 segundos durante 30 segundos)
echo -e "${YELLOW}[4/6] Monitoreando logs del procesamiento...${NC}"
echo -e "${BLUE}Esperando hasta 60 segundos para completar...${NC}\n"

for i in {1..30}; do
    sleep 2
    
    # Obtener logs
    LOGS=$(curl -s "${API_BASE}/processing/logs/${SESSION_ID}" 2>/dev/null || echo "[]")
    
    # Mostrar últimas 3 líneas
    echo "$LOGS" | python3 -c "
import sys, json
try:
    logs = json.load(sys.stdin)
    if logs:
        for log in logs[-3:]:
            level = log.get('level', 'info')
            msg = log.get('message', '')
            emoji = '📄' if level == 'info' else '✅' if level == 'success' else '⚠️' if level == 'warning' else '❌'
            print(f'{emoji} {msg}')
except:
    pass
" 2>/dev/null
    
    # Verificar si terminó
    COUNT_CURRENT=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&status=completed" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
    
    if [ "$COUNT_CURRENT" == "$TOTAL" ]; then
        echo -e "\n${GREEN}✓ Procesamiento completado!${NC}\n"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "\n${YELLOW}⚠ Timeout alcanzado, pero el procesamiento puede continuar en background${NC}\n"
    fi
done

# 5. Verificar estado final
echo -e "${YELLOW}[5/6] Verificando estado final...${NC}"
FINAL_PENDING=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&status=pending" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
FINAL_COMPLETED=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&status=completed" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
FINAL_FAILED=$(curl -s "${API_BASE}/boletines/count?year=${TEST_YEAR}&month=${TEST_MONTH}&day=${TEST_DAY}&status=failed" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")

echo -e "Estado final:"
echo -e "  - Completados: ${GREEN}${FINAL_COMPLETED}${NC} / ${TOTAL}"
echo -e "  - Pendientes: ${YELLOW}${FINAL_PENDING}${NC}"
echo -e "  - Fallidos: ${RED}${FINAL_FAILED}${NC}\n"

# 6. Resumen
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   RESUMEN DEL TEST${NC}"
echo -e "${BLUE}================================================${NC}"

if [ "$FINAL_COMPLETED" == "$TOTAL" ] && [ "$FINAL_FAILED" == "0" ]; then
    echo -e "${GREEN}✓ ÉXITO TOTAL${NC}"
    echo -e "${GREEN}  Todos los documentos fueron procesados correctamente${NC}"
    EXIT_CODE=0
elif [ "$FINAL_FAILED" -gt 0 ]; then
    echo -e "${RED}✗ PROCESAMIENTO CON ERRORES${NC}"
    echo -e "${RED}  ${FINAL_FAILED} documentos fallaron${NC}"
    EXIT_CODE=1
elif [ "$FINAL_PENDING" -gt 0 ]; then
    echo -e "${YELLOW}⚠ PROCESAMIENTO INCOMPLETO${NC}"
    echo -e "${YELLOW}  ${FINAL_PENDING} documentos aún pendientes${NC}"
    echo -e "${YELLOW}  Pueden estar procesándose en background${NC}"
    EXIT_CODE=2
else
    echo -e "${YELLOW}⚠ ESTADO DESCONOCIDO${NC}"
    EXIT_CODE=3
fi

echo -e "${BLUE}================================================${NC}\n"

# Mostrar logs finales del servidor
echo -e "${YELLOW}Últimos logs del servidor para sesión ${SESSION_ID}:${NC}"
curl -s "${API_BASE}/processing/logs/${SESSION_ID}" | python3 -c "
import sys, json
try:
    logs = json.load(sys.stdin)
    for log in logs[-10:]:
        print(f\"[{log.get('timestamp', '')}] {log.get('level', 'info').upper()}: {log.get('message', '')}\")
except:
    print('No se pudieron obtener los logs')
" 2>/dev/null || echo "Logs no disponibles"

echo ""
exit $EXIT_CODE
