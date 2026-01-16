#!/bin/bash

# Test Runner for Ralphs Loop
# usage: ./test_runner.sh [backend|frontend|e2e|all]

TYPE=${1:-all}

echo "Running tests: $TYPE"

export PYTHONPATH=$PYTHONPATH:.

if [ "$TYPE" == "e2e" ] || [ "$TYPE" == "all" ]; then
    echo "----------------------------------------"
    echo "Running E2E Flow Tests (Mocked CDP)"
    echo "----------------------------------------"
    python3 -m pytest tests/test_e2e_flow.py -v
fi

if [ "$TYPE" == "backend" ] || [ "$TYPE" == "all" ]; then
    echo "----------------------------------------"
    echo "Running Backend Unit Tests"
    echo "----------------------------------------"
    python3 -m pytest tests/ -v --ignore=tests/test_e2e_flow.py
fi

# Frontend tests placeholder
if [ "$TYPE" == "frontend" ] || [ "$TYPE" == "all" ]; then
    if [ -f "package.json" ]; then
        echo "----------------------------------------"
        echo "Running Frontend Tests"
        echo "----------------------------------------"
        npm test
    else
        echo "No package.json found, skipping frontend tests."
    fi
fi

# Generate coverage/report if needed
echo "----------------------------------------"
echo "Done."
