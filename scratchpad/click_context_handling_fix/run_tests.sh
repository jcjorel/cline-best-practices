#!/bin/bash

set -e  # Exit on any error

echo "=== Click Context Handling Fix Tests ==="
echo

echo "Running Python unit tests for context handling..."
pytest -v src/dbp_cli/cli_click/tests/test_context_handling.py

echo
echo "Running integration tests for migrated commands..."

echo
echo "1. Testing query command..."
python -m src.dbp_cli.cli_click.main query "test query" --help
# Add more query command tests as needed

echo
echo "2. Testing commit command..."
python -m src.dbp_cli.cli_click.main commit --help
# Add more commit command tests as needed

echo
echo "=== All tests completed successfully ==="
