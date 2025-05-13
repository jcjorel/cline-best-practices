# Phase 4: Switchover

## Overview

This phase focuses on completing the migration by updating entry points, ensuring backward compatibility, and performing final verifications to ensure a smooth transition from argparse to Click.

## Implementation Steps

### Step 1: Update Entry Points in setup.py

Update the package entry points to use the new Click-based CLI while temporarily maintaining the legacy CLI:

File: `setup.py` (updated)

```python
setup(
    name="dbp-cli",
    version="0.1.0",
    # Other setup parameters...
    
    # Update entry points
    entry_points={
        'console_scripts': [
            'dbp=dbp_cli.cli_click:main',  # New Click-based CLI (primary)
            'dbp-legacy=dbp_cli.cli:main',  # Keep legacy CLI for compatibility
        ],
    },
    
    # Additional configuration...
)
```

### Step 2: Add Deprecation Warning in Legacy CLI

Update the legacy CLI to display a deprecation warning:

File: `src/dbp_cli/cli.py` (updated)

```python
def main() -> int:
    """
    [Function intent]
    Serve as the main entry point for the legacy CLI application.
    
    [Implementation details]
    Displays a deprecation warning and then runs the legacy CLI.
    
    [Design principles]
    Maintains backward compatibility while encouraging users to migrate.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    import warnings
    import sys
    
    # Display deprecation warning to stderr
    warnings.filterwarnings("always", category=DeprecationWarning)
    warnings.warn(
        "You are using the legacy CLI interface which is deprecated and will be removed "
        "in a future release. Please use the new Click-based interface instead.",
        DeprecationWarning, 
        stacklevel=2
    )
    
    # Print colorized warning directly to stderr
    if sys.stderr.isatty():
        print("\033[33mWARNING: Legacy CLI interface is deprecated and will be removed in a future release.\033[0m", file=sys.stderr)
        print("\033[33mPlease use the new Click-based interface instead.\033[0m", file=sys.stderr)
    else:
        print("WARNING: Legacy CLI interface is deprecated and will be removed in a future release.", file=sys.stderr)
        print("Please use the new Click-based interface instead.", file=sys.stderr)
    
    # Run legacy CLI
    cli = DocumentationProgrammingCLI()
    return cli.run()
```

### Step 3: Create Migration Guide

File: `doc/CLI_MIGRATION_GUIDE.md`

```markdown
# CLI Migration Guide

## Introduction

The `dbp-cli` package has migrated from argparse to Click for its command-line interface. This guide will help you understand the changes and how to update your usage if needed.

## What's Changed?

The new CLI provides the same functionality as before but with several improvements:

- Better help text and documentation
- More consistent error handling
- Improved subcommand organization
- Better support for command completion

## Migration Steps

For most users, the migration should be seamless as the command signatures remain the same. However, if you're using any scripts that interact with the CLI, here are some things to be aware of:

### Command Changes

| Command | Status | Notes |
|---------|--------|-------|
| `dbp query` | Unchanged | Same arguments and options |
| `dbp config` | Unchanged | Same arguments and options |
| `dbp status` | Unchanged | Same arguments and options |
| `dbp commit` | Unchanged | Same arguments and options |
| `dbp hstc_agno` | Unchanged | Direct integration of Click command |

### Global Option Changes

All global options remain the same:

- `--version`: Show version and exit
- `--config FILE`: Path to configuration file
- `--server URL`: MCP server URL
- `--api-key KEY`: API key for authentication
- `--verbose, -v`: Increase verbosity level
- `--quiet, -q`: Suppress all non-error output
- `--output, -o`: Output format (text, json, markdown, html)
- `--no-color`: Disable colored output
- `--no-progress`: Disable progress indicators
- `--debug`: Enable debug mode with stack traces on errors

### Legacy CLI Availability

The legacy CLI is still available during the transition period via the `dbp-legacy` command. However, it will be removed in a future release, so we recommend migrating to the new CLI as soon as possible.

## Common Issues and Solutions

### Exit Codes

The new CLI maintains the same exit codes as the legacy CLI:

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Authentication error
- `4`: Connection error
- `5`: API error
- `130`: Operation cancelled (Ctrl+C)

### Error Messages

Error messages have been standardized and may appear slightly different but will contain the same information.

### Command Completion

To enable command completion for the new CLI, run:

```bash
# For bash
dbp --install-completion bash

# For zsh
dbp --install-completion zsh

# For fish
dbp --install-completion fish
```

## Feedback

If you encounter any issues with the new CLI, please report them on our issue tracker at [github.com/example/dbp-cli/issues](https://github.com/example/dbp-cli/issues).
```

### Step 4: Update Documentation and Help Text

#### Update README.md

Update the main README.md file with information about the new CLI:

```markdown
## CLI Usage

The Documentation-Based Programming CLI (`dbp`) provides a command-line interface for interacting with the MCP server and managing documentation.

### Installation

```bash
pip install dbp-cli
```

### Basic Commands

```bash
# Get help
dbp --help

# Query the documentation
dbp query how does the configuration system work

# Manage configuration
dbp config list
dbp config set api.url https://example.com/api

# Check status
dbp status --verbose

# Generate commit messages
dbp commit --all --execute
```

### Command Completion

The CLI supports command completion for bash, zsh, and fish:

```bash
# For bash
dbp --install-completion bash

# For zsh
dbp --install-completion zsh

# For fish
dbp --install-completion fish
```
```

### Step 5: Final Verification Tests

Create a comprehensive verification test script to ensure the new CLI works as expected:

File: `scripts/verify_cli_migration.sh`

```bash
#!/bin/bash

# Verify CLI Migration
# This script performs a series of tests to verify that the new Click-based CLI
# works correctly and maintains backward compatibility.

set -e  # Exit on error

echo "===== CLI Migration Verification ====="

# Install the package
pip install -e .

# Check version
echo -e "\n==== Testing version command ===="
dbp --version
dbp-legacy --version

# Check help text
echo -e "\n==== Testing help command ===="
dbp --help
dbp-legacy --help

# Test basic commands
echo -e "\n==== Testing basic commands ===="

# Status command
echo "Testing status command..."
dbp status
dbp-legacy status

# Config command
echo "Testing config command..."
dbp config list
dbp-legacy config list

# Compare outputs
echo -e "\n==== Testing command outputs ===="
echo "Testing query command output..."

# Create temporary files for output comparison
mkdir -p tmp
dbp query "test query" --output json > tmp/new_query_output.json
dbp-legacy query "test query" --output json > tmp/legacy_query_output.json

# Compare outputs (ignoring order)
diff -w <(jq -S . tmp/new_query_output.json) <(jq -S . tmp/legacy_query_output.json)

# Clean up
rm -rf tmp

echo -e "\n==== All tests passed! ===="
```

### Step 6: Update Installation Instructions

Update any installation instructions in documentation to reflect the new CLI:

1. Update documentation in the `doc/` directory
2. Update any README files
3. Update any online documentation or wikis

### Step 7: Release Notes

Create release notes for the new version that includes the CLI migration:

File: `RELEASE_NOTES.md`

```markdown
# Release Notes - v0.2.0

## Major Changes

### CLI Migration from argparse to Click

The CLI has been migrated from argparse to Click to provide a more robust and feature-rich command-line interface. Key benefits include:

- Better help text and documentation
- More consistent error handling
- Improved subcommand organization
- Better support for command completion

The legacy CLI is still available via the `dbp-legacy` command during the transition period but will be removed in a future release.

See the [CLI Migration Guide](doc/CLI_MIGRATION_GUIDE.md) for more details.

### Command Completion

The CLI now supports command completion for bash, zsh, and fish:

```bash
# For bash
dbp --install-completion bash

# For zsh
dbp --install-completion zsh

# For fish
dbp --install-completion fish
```

## Other Changes

- Bug fixes and performance improvements
- [Additional changes...]
```

### Step 8: Create a CLI Transition Timeline

File: `doc/CLI_TRANSITION_TIMELINE.md`

```markdown
# CLI Transition Timeline

## Phase 1: Dual CLI Period (Current)

- Both CLIs available: `dbp` (Click-based) and `dbp-legacy` (argparse-based)
- Legacy CLI displays deprecation warnings
- Documentation updated to focus on new CLI
- Users are encouraged to migrate to the new CLI

## Phase 2: Deprecation Period (Next Release)

- Legacy CLI still available but with more prominent warnings
- Scripts using legacy CLI should be updated
- No new features added to legacy CLI

## Phase 3: Removal (Future Release)

- Legacy CLI removed entirely
- Only Click-based CLI available
- All documentation and examples updated to reflect only the new CLI
```

## Expected Outcome

At the end of Phase 4, we will have:

1. Updated the entry points to use the new Click-based CLI
2. Added deprecation warnings to the legacy CLI
3. Created comprehensive documentation for the migration
4. Verified that the new CLI works correctly
5. Created a transition plan for users

This completes the migration from argparse to Click, while providing a smooth transition path for users.

## Dependencies

- Completed Phase 1, Phase 2, and Phase 3
- Python 3.8+
- Click package
- jq (for verification script)

## Testing

Run the verification script to ensure the new CLI works as expected:

```bash
# From the project root
bash scripts/verify_cli_migration.sh
```

Manually test key commands and verify behavior:

```bash
# Test basic functionality
dbp --version
dbp --help
dbp status

# Test command registration
dbp config --help
dbp query --help
dbp commit --help
dbp hstc_agno --help

# Test global options
dbp --no-color status
dbp --verbose query "test query"
