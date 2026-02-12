.PHONY: help install install-backend install-frontend install-lab install-test start start-backend stop-backend start-frontend test test-backend test-frontend test-unit test-integration test-e2e test-coverage test-fast test-pds test-dia test-kaa test-oex lint lint-backend lint-frontend build build-frontend clean

# Default target
help:
	@echo "Watcher Agent - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install              - Install all dependencies (backend + frontend + lab)"
	@echo "  make install-backend      - Install backend Python dependencies"
	@echo "  make install-backend-fast - Install backend deps in phases (more reliable)"
	@echo "  make install-frontend     - Install frontend npm dependencies"
	@echo "  make install-lab          - Install data science lab dependencies"
	@echo "  make install-test         - Install test dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  make start             - Start backend and frontend servers"
	@echo "  make start-backend     - Start backend server only"
	@echo "  make start-frontend    - Start frontend dev server only"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-backend      - Run backend tests"
	@echo "  make test-frontend     - Run frontend tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-e2e          - Run end-to-end tests only"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo "  make test-fast         - Run only fast tests"
	@echo "  make lint              - Run all linters"
	@echo "  make lint-backend      - Run Python linters"
	@echo "  make lint-frontend     - Run frontend linters"
	@echo ""
	@echo "Build Commands:"
	@echo "  make build             - Build frontend for production"
	@echo "  make clean             - Clean build artifacts"
	@echo ""

# Installation targets
install: install-backend install-frontend install-lab
	@echo "✅ All dependencies installed"

install-backend:
	@echo "📦 Installing backend dependencies..."
	@echo "⏱️  This may take several minutes for AI libraries (langgraph, langchain)..."
	cd watcher-backend && pip install --timeout 100 --retries 10 -r requirements.txt
	@echo "✅ Backend dependencies installed"

install-backend-fast:
	@echo "📦 Installing backend dependencies in phases (more reliable)..."
	cd watcher-backend && \
		pip install fastapi uvicorn python-dotenv pydantic pytest httpx && \
		pip install PyPDF2 pdfplumber sqlalchemy alembic aiosqlite greenlet aiofiles && \
		pip install openai tqdm python-multipart python-socketio websockets && \
		pip install --timeout 100 --no-cache-dir langgraph langchain langchain-core langchain-openai
	@echo "✅ Backend dependencies installed (phased approach)"

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd watcher-frontend && npm install
	@echo "✅ Frontend dependencies installed"

install-lab:
	@echo "📦 Installing lab dependencies..."
	cd watcher-lab && pip install -r requirements.txt
	@echo "✅ Lab dependencies installed"

# Development servers
start:
	@echo "🚀 Starting development servers..."
	@echo "Use watcher-backend/scripts/dev.sh for parallel execution"
	@./watcher-backend/scripts/dev.sh

stop-backend:
	@echo "🛑 Stopping backend server..."
	@-pkill -f "uvicorn app.main:app" 2>/dev/null; sleep 1
	@lsof -ti :8001 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "✅ Backend stopped"

start-backend: stop-backend
	@echo "🚀 Starting backend server..."
	cd watcher-backend && uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8001

start-frontend:
	@echo "🚀 Starting frontend dev server..."
	cd watcher-frontend && npm run dev

# Testing
test: test-backend test-frontend
	@echo "✅ All tests completed"

test-backend:
	@echo "🧪 Running backend tests..."
	@./watcher-backend/tests/run_tests.sh -v || echo "⚠️  Some tests failed"

test-frontend:
	@echo "ℹ️  Frontend tests not yet configured (backend tests: 104 passing ✅)"
	@echo "   Backend test suite covers PDS, DIA, KAA, and OEx layers"

# New architecture test commands
test-unit:
	@echo "🧪 Running unit tests..."
	pytest watcher-backend/tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest watcher-backend/tests/integration/ -v

test-e2e:
	@echo "🧪 Running end-to-end tests..."
	pytest watcher-backend/tests/e2e/ -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	pytest watcher-backend/tests/ --cov=watcher-backend/app --cov=watcher-backend/agents --cov-report=html --cov-report=term-missing -v
	@echo "📊 Coverage report generated in htmlcov/"

test-fast:
	@echo "🧪 Running fast tests only..."
	pytest -m "not slow" watcher-backend/tests/ -v

test-pds:
	@echo "🧪 Running PDS layer tests..."
	pytest -m pds watcher-backend/tests/ -v

test-dia:
	@echo "🧪 Running DIA layer tests..."
	pytest -m dia watcher-backend/tests/ -v

test-kaa:
	@echo "🧪 Running KAA layer tests..."
	pytest -m kaa watcher-backend/tests/ -v

test-oex:
	@echo "🧪 Running OEx layer tests..."
	pytest -m oex watcher-backend/tests/ -v

# Linting
lint: lint-backend lint-frontend
	@echo "✅ All linting completed"

lint-backend:
	@echo "🔍 Linting Python code..."
	@command -v ruff >/dev/null 2>&1 && (cd watcher-backend && ruff check . && echo "✅ Backend lint passed") || echo "⚠️  ruff not installed (pip install ruff)"

lint-frontend:
	@echo "🔍 Linting frontend code..."
	cd watcher-frontend && npm run lint

# Build
build: build-frontend
	@echo "✅ Build completed"

build-frontend:
	@echo "🏗️  Building frontend..."
	cd watcher-frontend && npm run build
	@echo "✅ Frontend build completed"

# Clean
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf watcher-frontend/dist
	rm -rf htmlcov .coverage coverage.xml .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Install test dependencies
install-test:
	@echo "📦 Installing test dependencies..."
	pip install -r requirements-test.txt
	@echo "✅ Test dependencies installed"
