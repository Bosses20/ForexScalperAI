#!/bin/bash
# Comprehensive testing script for CI/CD pipeline
# This script runs all unit tests, integration tests, and code quality checks

set -e  # Exit immediately if any command fails

echo "===== Starting Forex Trading Bot CI Tests ====="
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "Test run started at: $timestamp"

# Set up virtual environment
echo "Setting up virtual environment..."
python -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet -r requirements-dev.txt

# Run code quality checks
echo -e "\n===== Running Code Quality Checks ====="

echo "Running Black code formatter check..."
black --check src tests

echo "Running isort import order check..."
isort --check-only --profile black src tests

echo "Running flake8 linting..."
flake8 src tests

echo "Running mypy type checking..."
mypy --ignore-missing-imports src

# Run unit tests
echo -e "\n===== Running Unit Tests ====="

echo "Running strategy tests..."
pytest tests/unit/strategies -v

echo "Running market condition detector tests..."
pytest tests/unit/market_condition -v

echo "Running multi-asset tests..."
pytest tests/unit/multi_asset -v

echo "Running risk management tests..."
pytest tests/unit/risk_management -v

echo "Running execution engine tests..."
pytest tests/unit/execution -v

# Run integration tests
echo -e "\n===== Running Integration Tests ====="

echo "Running API integration tests..."
pytest tests/integration/api -v

echo "Running database integration tests..."
pytest tests/integration/database -v

echo "Running MT5 connector integration tests (mock mode)..."
pytest tests/integration/mt5_connector -v

# Run coverage report
echo -e "\n===== Generating Test Coverage Report ====="
pytest --cov=src --cov-report=xml --cov-report=term-missing tests/

# Validate configuration files
echo -e "\n===== Validating Configuration Files ====="

echo "Validating YAML configurations..."
python -c "
import yaml
import os
import sys

config_dir = 'config'
errors = False

for filename in os.listdir(config_dir):
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        filepath = os.path.join(config_dir, filename)
        try:
            with open(filepath, 'r') as f:
                yaml.safe_load(f)
            print(f'✓ {filepath} - Valid YAML')
        except yaml.YAMLError as e:
            print(f'✗ {filepath} - Invalid YAML: {str(e)}')
            errors = True

if errors:
    sys.exit(1)
"

# Run security checks
echo -e "\n===== Running Security Checks ====="

echo "Running Bandit security checks..."
bandit -r src/

echo "Checking for sensitive information in code..."
grep -r --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" \
    -E "(password|secret|key|token|credential)[\"']?\s*[:=]\s*[\"'][^\"']+[\"']" \
    --exclude-dir=venv .

# Run performance benchmark tests
echo -e "\n===== Running Performance Benchmarks ====="

echo "Running strategy execution benchmarks..."
python benchmarks/strategy_execution_benchmark.py

echo "Running database query benchmarks..."
python benchmarks/database_benchmark.py

# Create test summary
echo -e "\n===== Test Summary ====="
echo "All tests completed successfully!"
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "Test run completed at: $timestamp"

# Deactivate virtual environment
deactivate

exit 0
