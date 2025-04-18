#!/bin/bash

###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# A utility script to start the DBP MCP server with debug logging enabled.
# This script makes it easy to run the server in debug mode for development and
# troubleshooting without manually configuring logging settings.
###############################################################################
# [Source file design principles]
# - Simplifies the server debugging process with a single command
# - Uses appropriate environment variables for configuration
# - Shows helpful information about log file locations
# - Provides commented examples for common debugging tasks
###############################################################################
# [Source file constraints]
# - Requires the dbp CLI to be installed and in the PATH
# - Expects the standard .dbp directory structure to be in place
###############################################################################
# [Reference documentation]
# - doc/CONFIGURATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-18T07:58:00Z : Removed invalid environment variable configuration by CodeAssistant
# * Removed DBP_LOG__LEVEL environment variable that caused config path error
# * Fixed the error: "'AppConfig' object has no attribute 'log'"
# * Using CLI --log-level parameter only for setting debug level
# 2025-04-18T07:51:00Z : Fixed incorrect environment variable and added log location by CodeAssistant
# * Fixed environment variable name to correctly set debug logging
# * Added proper header comments according to project standards
# * Added explicit log file path determination
# * Improved user feedback for log file locations
###############################################################################

# Script to start the server with debug logging enabled

# Get the base directory path from configuration or use default
DBP_BASE_DIR="${DBP_BASE_DIR:-.dbp}"
LOGS_DIR="$DBP_BASE_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

echo "=== DBP Server Debug Mode ==="
echo "Base directory: $DBP_BASE_DIR"
echo "Logs directory: $LOGS_DIR"

# Note: We're not using environment variables for log level configuration
# as we're passing it directly to the CLI with --log-level

echo "Starting server with DEBUG log level..."
dbp server restart --log-level debug

# Check if the server started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "Server started in DEBUG mode."
    echo "Log files are available at:"
    echo "  - Stdout: $LOGS_DIR/mcp_server_stdout.log"
    echo "  - Stderr: $LOGS_DIR/mcp_server_stderr.log"
    echo ""
    echo "To view logs in real-time, run:"
    echo "  tail -f $LOGS_DIR/mcp_server_stderr.log"
    echo ""
    echo "To stop the server, run:"
    echo "  dbp server stop"
else
    echo ""
    echo "Server failed to start. View the logs for more details:"
    echo "  cat $LOGS_DIR/mcp_server_stderr.log"
fi

# Commented out commands that might be useful (uncomment as needed)
# echo "Showing last 20 lines of logs:"
# tail -n 20 "$LOGS_DIR/mcp_server_stderr.log"

# echo "Monitoring logs in real-time (Ctrl+C to exit):"
# tail -f "$LOGS_DIR/mcp_server_stderr.log"
