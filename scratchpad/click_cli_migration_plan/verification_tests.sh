#!/bin/bash
# Verification tests for CLI migration
# This script tests both the legacy CLI (dbp) and the new Click-based CLI (dbp-click)
# to verify that they produce the same outputs for the same inputs.

# Set error handling
set -e
set -o pipefail

# Colors for output formatting
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== CLI Migration Verification Tests ===${NC}"
echo -e "This script will verify that the new Click-based CLI produces"
echo -e "the same results as the legacy CLI for common operations.\n"

# Function to run a test
run_test() {
    local test_name="$1"
    local legacy_command="$2"
    local click_command="$3"
    local expected_exit_code="$4"

    echo -e "\n${YELLOW}Running test: ${test_name}${NC}"
    
    # Run legacy command
    echo "Legacy command: $legacy_command"
    eval "$legacy_command > legacy_output.txt 2>&1" || true
    legacy_exit=$?
    
    # Run Click command
    echo "Click command:  $click_command"
    eval "$click_command > click_output.txt 2>&1" || true
    click_exit=$?
    
    # Check exit codes
    if [ "$legacy_exit" != "$expected_exit_code" ]; then
        echo -e "${RED}FAIL: Legacy command exit code $legacy_exit, expected $expected_exit_code${NC}"
        failed_tests=$((failed_tests + 1))
        return
    fi
    
    if [ "$click_exit" != "$expected_exit_code" ]; then
        echo -e "${RED}FAIL: Click command exit code $click_exit, expected $expected_exit_code${NC}"
        failed_tests=$((failed_tests + 1))
        return
    fi
    
    # Check output equivalence (ignoring exact formatting)
    # This is a simplified check - in a real scenario you might need more sophisticated comparison
    legacy_relevant=$(grep -v "DEPRECATION WARNING" legacy_output.txt | grep -v "^$" | sort)
    click_relevant=$(grep -v "^$" click_output.txt | sort)
    
    if diff <(echo "$legacy_relevant") <(echo "$click_relevant") >/dev/null; then
        echo -e "${GREEN}PASS: Both commands produced equivalent output with exit code $expected_exit_code${NC}"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}FAIL: Command outputs differ${NC}"
        echo "Legacy output:"
        cat legacy_output.txt
        echo "Click output:"
        cat click_output.txt
        failed_tests=$((failed_tests + 1))
    fi
}

# Counter for passed and failed tests
passed_tests=0
failed_tests=0

# Basic command tests
run_test "Version Command" "dbp --version" "dbp-click --version" 0

# Config commands
run_test "Config Get" "dbp config get cli.output_format" "dbp-click config get cli.output_format" 0
run_test "Config List" "dbp config list" "dbp-click config list" 0

# Status commands
run_test "Status Basic" "dbp status" "dbp-click status" 0

# Help commands
run_test "Main Help" "dbp --help" "dbp-click --help" 0
run_test "Query Help" "dbp query --help" "dbp-click query --help" 0

# Error handling
run_test "Invalid Command" "dbp invalid_command" "dbp-click invalid_command" 1
run_test "Missing Argument" "dbp query" "dbp-click query" 2

# Advanced command tests (comment out if the command requires interactive input)
# run_test "Query Command" "dbp query \"What is AWS S3?\" --format json" "dbp-click query \"What is AWS S3?\" --format json" 0

# Print test summary
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
echo -e "${GREEN}Passed: $passed_tests${NC}"
echo -e "${RED}Failed: $failed_tests${NC}"

# Clean up temporary files
rm -f legacy_output.txt click_output.txt

# Return exit code based on test results
if [ "$failed_tests" -gt 0 ]; then
    exit 1
else
    exit 0
fi
