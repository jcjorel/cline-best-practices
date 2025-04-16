#!/bin/bash

# Script to start the server with debug logging enabled

# Set environment variable for debug logging
export DBP_LOG_LEVEL=DEBUG

# Restart the server with debug logging
echo "Starting server with DEBUG log level..."
dbp server restart

# View the logs (additional command that users can uncomment if needed)
# echo "Showing last 100 lines of logs:"
# tail -n 100 $HOME/.dbp/logs/mcp_server_stderr.log
