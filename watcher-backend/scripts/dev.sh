#!/bin/bash
# Development script - Start backend and frontend in parallel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Watcher Agent - Development Environment${NC}"
echo "=========================================="
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if backend dependencies are installed
if [ ! -d "$PROJECT_ROOT/watcher-backend/venv" ]; then
    echo -e "${YELLOW}⚠️  Backend virtual environment not found${NC}"
    echo -e "   Run: ${GREEN}make install-backend${NC}"
    echo ""
fi

# Check if frontend dependencies are installed
if [ ! -d "$PROJECT_ROOT/watcher-frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Frontend dependencies not found${NC}"
    echo -e "   Run: ${GREEN}make install-frontend${NC}"
    echo ""
fi

# Check for .env file
if [ ! -f "$PROJECT_ROOT/watcher-backend/.env" ]; then
    echo -e "${YELLOW}⚠️  Backend .env file not found${NC}"
    echo -e "   See ENV_SETUP.md for configuration instructions"
    echo -e "   The backend will run with fallback mode (no OpenAI features)"
    echo ""
fi

# Create log directory if it doesn't exist
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd "$PROJECT_ROOT/watcher-backend"

# Try to use virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "   Backend PID: ${BACKEND_PID}"
echo -e "   Logs: ${LOG_DIR}/backend.log"
echo -e "   URL: ${BLUE}http://localhost:8001${NC}"
echo ""

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend dev server...${NC}"
cd "$PROJECT_ROOT/watcher-frontend"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "   Frontend PID: ${FRONTEND_PID}"
echo -e "   Logs: ${LOG_DIR}/frontend.log"
echo -e "   URL: ${BLUE}http://localhost:5173${NC}"
echo ""

# Save PIDs to file for cleanup
echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"

echo -e "${GREEN}✅ Development servers started${NC}"
echo ""
echo "To stop servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  or run: pkill -f 'uvicorn app.main:app' && pkill -f 'vite'"
echo ""
echo "Watching logs..."
echo "  Backend:  tail -f $LOG_DIR/backend.log"
echo "  Frontend: tail -f $LOG_DIR/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop monitoring (servers will continue running)${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping development servers...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    rm -f "$LOG_DIR/backend.pid" "$LOG_DIR/frontend.pid"
    echo -e "${GREEN}✅ Servers stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Monitor both processes
while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; do
    sleep 1
done

echo -e "${RED}❌ One or both servers stopped unexpectedly${NC}"
echo "Check logs for details:"
echo "  Backend:  $LOG_DIR/backend.log"
echo "  Frontend: $LOG_DIR/frontend.log"
cleanup
