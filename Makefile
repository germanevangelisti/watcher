.PHONY: help install install-backend install-frontend install-frontend-legacy install-lab install-test start start-backend stop-backend start-frontend start-frontend-legacy test test-backend test-frontend test-unit test-integration test-e2e test-coverage test-fast test-pds test-dia test-kaa test-oex lint lint-backend lint-frontend build build-frontend clean

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
	@echo "  make stop-backend      - Stop backend server"
	@echo "  make start-frontend    - Start frontend dev server"
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
	@echo "📦 Installing backend dependencies (core)..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Using uv (fast mode)..."; \
		cd watcher-backend && uv pip install --system "."; \
	else \
		echo "Using pip..."; \
		cd watcher-backend && pip install --timeout 100 --retries 10 "."; \
	fi
	@echo "✅ Backend core dependencies installed"

install-backend-ai:
	@echo "📦 Installing backend AI dependencies..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv pip install --system ".[ai]"; \
	else \
		cd watcher-backend && pip install --timeout 100 ".[ai]"; \
	fi
	@echo "✅ Backend AI dependencies installed"

install-backend-dev:
	@echo "📦 Installing backend dev dependencies..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv pip install --system ".[dev]"; \
	else \
		cd watcher-backend && pip install ".[dev]"; \
	fi
	@echo "✅ Backend dev dependencies installed"

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd watcher-frontend && npm install
	@echo "✅ Frontend dependencies installed"

install-frontend-legacy:
	@echo "📦 Installing legacy frontend dependencies..."
	cd watcher-frontend-legacy && npm install
	@echo "✅ Legacy frontend dependencies installed"

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

start-frontend-legacy:
	@echo "🚀 Starting legacy frontend dev server..."
	cd watcher-frontend-legacy && npm run dev

# Testing
test: test-backend test-frontend
	@echo "✅ All tests completed"

test-backend:
	@echo "🧪 Running backend tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest tests/ -v --tb=short || echo "⚠️  Some tests failed"; \
	else \
		./watcher-backend/tests/run_tests.sh -v || echo "⚠️  Some tests failed"; \
	fi

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd watcher-frontend && npm run test -- --run || echo "⚠️  Some frontend tests failed"

# New architecture test commands (uv run when available)
_PYTEST = $(shell command -v uv >/dev/null 2>&1 && echo "cd watcher-backend && uv run pytest" || echo "pytest watcher-backend")

test-unit:
	@echo "🧪 Running unit tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest tests/tests/unit/ -v; \
	else \
		pytest watcher-backend/tests/tests/unit/ -v; \
	fi

test-integration:
	@echo "🧪 Running integration tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest tests/tests/integration/ -v -m integration; \
	else \
		pytest watcher-backend/tests/tests/integration/ -v -m integration; \
	fi

test-e2e:
	@echo "🧪 Running end-to-end tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest tests/tests/e2e/ -v -m e2e; \
	else \
		pytest watcher-backend/tests/tests/e2e/ -v -m e2e; \
	fi

test-coverage:
	@echo "🧪 Running tests with coverage..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest tests/ --cov=app --cov=agents --cov-report=html --cov-report=term-missing -v; \
	else \
		pytest watcher-backend/tests/ --cov=watcher-backend/app --cov=watcher-backend/agents --cov-report=html --cov-report=term-missing -v; \
	fi
	@echo "📊 Coverage report generated in htmlcov/"

test-fast:
	@echo "🧪 Running fast tests only..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest -m "not slow" tests/ -v; \
	else \
		pytest -m "not slow" watcher-backend/tests/ -v; \
	fi

test-pds:
	@echo "🧪 Running PDS layer tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest -m pds tests/ -v; \
	else \
		pytest -m pds watcher-backend/tests/ -v; \
	fi

test-dia:
	@echo "🧪 Running DIA layer tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest -m dia tests/ -v; \
	else \
		pytest -m dia watcher-backend/tests/ -v; \
	fi

test-kaa:
	@echo "🧪 Running KAA layer tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest -m kaa tests/ -v; \
	else \
		pytest -m kaa watcher-backend/tests/ -v; \
	fi

test-oex:
	@echo "🧪 Running OEx layer tests..."
	@if command -v uv >/dev/null 2>&1; then \
		cd watcher-backend && uv run pytest -m oex tests/ -v; \
	else \
		pytest -m oex watcher-backend/tests/ -v; \
	fi

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
	rm -rf watcher-frontend/dist watcher-frontend-legacy/dist
	rm -rf htmlcov .coverage coverage.xml .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Install test dependencies
install-test:
	@echo "📦 Installing test dependencies..."
	pip install -r requirements-test.txt
	@echo "✅ Test dependencies installed"
