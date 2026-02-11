#!/bin/bash
# Watcher Agent Test Runner Script
# Provides convenient commands for running different test suites

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print usage
print_usage() {
    cat << EOF
Usage: ./run_tests.sh [COMMAND]

Commands:
  all              Run all tests (default)
  unit             Run unit tests only
  integration      Run integration tests only
  e2e              Run end-to-end tests only
  pds              Run PDS layer tests
  dia              Run DIA layer tests
  kaa              Run KAA layer tests
  oex              Run OEx layer tests
  fast             Run only fast tests (exclude slow)
  coverage         Run tests with coverage report
  watch            Run tests in watch mode
  clean            Clean test artifacts and cache
  help             Show this help message

Examples:
  ./run_tests.sh all
  ./run_tests.sh unit
  ./run_tests.sh pds
  ./run_tests.sh coverage

EOF
}

# Function to check if pytest is installed
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        print_color "$RED" "Error: pytest not found. Please install test dependencies:"
        echo "  pip install -r requirements-test.txt"
        exit 1
    fi
}

# Function to clean test artifacts
clean_tests() {
    print_color "$YELLOW" "Cleaning test artifacts..."
    rm -rf .pytest_cache
    rm -rf htmlcov
    rm -rf .coverage
    rm -rf coverage.xml
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    print_color "$GREEN" "✓ Test artifacts cleaned"
}

# Main script logic
main() {
    check_pytest
    
    case "${1:-all}" in
        all)
            print_color "$BLUE" "Running all tests..."
            pytest tests/ -v
            ;;
        unit)
            print_color "$BLUE" "Running unit tests..."
            pytest tests/unit/ -v
            ;;
        integration)
            print_color "$BLUE" "Running integration tests..."
            pytest tests/integration/ -v
            ;;
        e2e)
            print_color "$BLUE" "Running end-to-end tests..."
            pytest tests/e2e/ -v
            ;;
        pds)
            print_color "$BLUE" "Running PDS layer tests..."
            pytest -m pds tests/ -v
            ;;
        dia)
            print_color "$BLUE" "Running DIA layer tests..."
            pytest -m dia tests/ -v
            ;;
        kaa)
            print_color "$BLUE" "Running KAA layer tests..."
            pytest -m kaa tests/ -v
            ;;
        oex)
            print_color "$BLUE" "Running OEx layer tests..."
            pytest -m oex tests/ -v
            ;;
        fast)
            print_color "$BLUE" "Running fast tests only..."
            pytest -m "not slow" tests/ -v
            ;;
        coverage)
            print_color "$BLUE" "Running tests with coverage..."
            pytest tests/ \
                --cov=watcher-monolith/backend/app \
                --cov=agents \
                --cov-report=html \
                --cov-report=term-missing \
                --cov-report=xml \
                -v
            print_color "$GREEN" "✓ Coverage report generated in htmlcov/"
            ;;
        watch)
            print_color "$BLUE" "Running tests in watch mode..."
            if command -v pytest-watch &> /dev/null; then
                ptw tests/
            else
                print_color "$YELLOW" "pytest-watch not installed. Installing..."
                pip install pytest-watch
                ptw tests/
            fi
            ;;
        clean)
            clean_tests
            ;;
        help)
            print_usage
            ;;
        *)
            print_color "$RED" "Unknown command: $1"
            print_usage
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
