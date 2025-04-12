#!/bin/bash

# Exit on error
set -e

echo "====== Installing Firecrawl MCP Server ======"

# Create directory for MCP servers
mkdir -p /home/jcjorel/Cline/MCP/firecrawl-mcp-server
cd /home/jcjorel/Cline/MCP/firecrawl-mcp-server

echo "====== Creating MCP server configuration ======"

# Copy the existing cline_mcp_settings.json
cp /home/jcjorel/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json ./cline_mcp_settings.json.bak

# Create a new configuration file with the Firecrawl MCP server
cat > ./firecrawl_mcp_settings.json << EOL
{
  "mcpServers": {
    "github.com/mendableai/firecrawl-mcp-server": {
      "command": "npx",
      "args": [
        "-y", 
        "firecrawl-mcp"
      ],
      "env": {
        "FIRECRAWL_API_KEY": "fc-7d1cf1d12700475fbe99e932c17462e2",
        "FIRECRAWL_RETRY_MAX_ATTEMPTS": "3",
        "FIRECRAWL_RETRY_INITIAL_DELAY": "1000",
        "FIRECRAWL_RETRY_MAX_DELAY": "10000",
        "FIRECRAWL_RETRY_BACKOFF_FACTOR": "2",
        "FIRECRAWL_CREDIT_WARNING_THRESHOLD": "1000",
        "FIRECRAWL_CREDIT_CRITICAL_THRESHOLD": "100"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
EOL

echo "====== Adding Firecrawl MCP server to cline_mcp_settings.json ======"
# Merge the configuration with the existing one
python3 -c '
import json
import sys
import os

# Read the existing configuration
with open("/home/jcjorel/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json", "r") as f:
    existing = json.load(f)

# Read the new configuration
with open("./firecrawl_mcp_settings.json", "r") as f:
    new = json.load(f)

# Merge the configurations
if "mcpServers" in existing:
    existing["mcpServers"].update(new["mcpServers"])
else:
    existing["mcpServers"] = new["mcpServers"]

# Write the merged configuration
with open("/home/jcjorel/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json", "w") as f:
    json.dump(existing, f, indent=2)

print("Successfully merged MCP server configurations")
'

echo "====== Installation complete ======"
