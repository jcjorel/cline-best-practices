# Documentation-Based Programming CLI

A command-line interface for the Documentation-Based Programming system that helps maintain consistency between documentation and code.

## Overview

The DBP CLI provides tools for:

- Analyzing consistency between code and documentation files
- Generating recommendations to fix inconsistencies
- Applying recommendations to update code or documentation
- Analyzing relationships between documentation files
- Generating visual diagrams of document relationships
- Managing configuration settings

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/example/dbp-cli
cd dbp-cli

# Install the package
pip install -e .
```

### Using pip (once released)

```bash
pip install dbp-cli
```

## Basic Usage

```bash
# Check server status and connectivity
dbp status

# Analyze consistency between a code file and a documentation file
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md

# Generate recommendations for an inconsistency
dbp recommend --inconsistency-id abc123

# Apply a recommendation
dbp apply def456 --dry-run

# Analyze document relationships and generate a diagram
dbp relationships doc/DESIGN.md --diagram --save-diagram design_relationships.md

# Configure CLI settings
dbp config set mcp_server.url http://localhost:3000 --save
```

## Configuration

The CLI can be configured using:

1. Configuration files:
   - System-wide: `/etc/dbp/config.json`
   - User-specific: `~/.dbp/config.json`
   - Project-specific: `./.dbp.json`

2. Environment variables:
   - `DBP_API_KEY`: API key for authentication
   - `DBP_CLI_*`: Any configuration value using uppercase and underscores

3. Command-line arguments:
   - `--config FILE`: Path to a configuration file
   - `--server URL`: MCP server URL
   - `--api-key KEY`: API key for authentication
   - `--output FORMAT`: Output format (text, json, markdown, html)
   - `--no-color`: Disable colored output
   - `--no-progress`: Disable progress indicators

### Configuration Management

```bash
# View current configuration
dbp config list

# Set a configuration value
dbp config set mcp_server.url http://localhost:3000

# Save configuration to user config file
dbp config set mcp_server.url http://localhost:3000 --save

# Reset configuration to defaults
dbp config reset
```

## Commands

### analyze

Analyze consistency between code and documentation files.

```bash
# Analyze specific files
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md

# Analyze files in directories
dbp analyze --code-dir src/auth --doc-dir doc/auth

# Filter by severity
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md --severity high

# Show only summary
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md --summary-only
```

### recommend

Generate recommendations for fixing inconsistencies.

```bash
# Get recommendations for a specific inconsistency
dbp recommend --inconsistency-id abc123

# Get recommendations for a specific file
dbp recommend --file src/auth/user.py

# Get recommendations with code snippets
dbp recommend --inconsistency-id abc123 --show-code

# Limit number of recommendations
dbp recommend --file src/auth/user.py --limit 5
```

### apply

Apply a recommendation to fix an inconsistency.

```bash
# Apply a recommendation
dbp apply abc123

# Perform a dry run to see changes without applying them
dbp apply abc123 --dry-run

# Create backup files before applying changes
dbp apply abc123 --backup
```

### relationships

Analyze relationships between documentation files.

```bash
# Analyze relationships for a document
dbp relationships doc/DESIGN.md

# Generate a Mermaid diagram
dbp relationships doc/DESIGN.md --diagram

# Save diagram to a file
dbp relationships doc/DESIGN.md --diagram --save-diagram design_relationships.md

# Analyze all documents in a directory
dbp relationships --directory doc/

# Control relationship depth
dbp relationships doc/DESIGN.md --depth 2
```

### config

Manage CLI configuration settings.

```bash
# List all configuration settings
dbp config list

# Get a specific configuration value
dbp config get mcp_server.url

# Set a configuration value
dbp config set mcp_server.url http://localhost:3000

# Save configuration to user config file
dbp config set mcp_server.url http://localhost:3000 --save

# Reset configuration to defaults
dbp config reset
```

### status

Check the status of the Documentation-Based Programming system.

```bash
# Check status of server and authentication
dbp status

# Check only server connectivity
dbp status --check-server

# Check only authentication
dbp status --check-auth

# Show current settings
dbp status --show-settings

# Show detailed information
dbp status --verbose
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=dbp_cli
```

### Code Style

```bash
# Format code
black src/

# Sort imports
isort src/

# Check types
mypy src/

# Lint code
flake8 src/
