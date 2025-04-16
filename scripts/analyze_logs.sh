#!/bin/bash

# Script to analyze MCP server logs for component issues

LOG_FILE="$HOME/.dbp/logs/mcp_server_stderr.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found at $LOG_FILE"
    exit 1
fi

echo "=== Component Registration Analysis ==="
echo "Components that were successfully registered:"
grep -E "Registering component: '.*'" "$LOG_FILE" | sort | uniq

echo -e "\n=== Dependency Validation ==="
grep -E "Validating dependencies. Registered components:" "$LOG_FILE" | tail -1

echo -e "\n=== Dependency Errors ==="
grep -E "Component '.*' depends on '.*' which is not registered" "$LOG_FILE" | sort | uniq

echo -e "\n=== Component Initialization Order ==="
grep -E "Component initialization order:" "$LOG_FILE" | tail -1

echo -e "\n=== Components Successfully Initialized ==="
grep -E "Component '.*' initialized successfully" "$LOG_FILE" | sort | uniq

echo -e "\n=== Component Initialization Failures ==="
grep -E "Failed to initialize component '.*'" "$LOG_FILE" | sort | uniq

echo -e "\n=== Exceptions During Initialization ==="
grep -E "Exception type:" "$LOG_FILE" | sort | uniq

echo -e "\n=== Full Server Initialization Errors ==="
grep -E "Error: Failed to restart server" -A 20 "$LOG_FILE" | tail -20
