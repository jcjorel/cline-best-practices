# Legacy CLI File Removal List

This document provides a detailed inventory of all files to be removed as part of the legacy CLI removal process, along with their purpose and replacement in the new Click-based implementation.

## Core CLI Files

| File Path | Purpose | Replacement | Notes |
|-----------|---------|-------------|-------|
| `src/dbp_cli/cli.py` | Main CLI implementation using argparse | `src/dbp_cli/cli_click/main.py` | Entry point for the old CLI system |
| `src/dbp_cli/__main__.py` | CLI entry point | `src/dbp_cli/cli_click/__main__.py` | May need verification if it has been updated already |

## Command Structure Files

| File Path | Purpose | Replacement | Notes |
|-----------|---------|-------------|-------|
| `src/dbp_cli/commands/base.py` | Abstract base class for command handlers | N/A - Click uses decorators | Core of the old command system |
| `src/dbp_cli/commands/click_adapter.py` | Adapter for transitioning to Click | N/A - Transitional code | Used during the migration process |
| `src/dbp_cli/commands/__init__.py` | Command module initialization | N/A | Verify if it contains any imports used elsewhere |

## Command Implementation Files

| File Path | Purpose | Replacement | Notes |
|-----------|---------|-------------|-------|
| `src/dbp_cli/commands/commit.py` | Commit command implementation | `src/dbp_cli/cli_click/commands/commit.py` | Handles commit operations |
| `src/dbp_cli/commands/config.py` | Configuration command | `src/dbp_cli/cli_click/commands/config.py` | Manages configuration settings |
| `src/dbp_cli/commands/query.py` | Query command | `src/dbp_cli/cli_click/commands/query.py` | Executes queries |
| `src/dbp_cli/commands/server.py` | Server management | `src/dbp_cli/cli_click/commands/server.py` | Controls server operations |
| `src/dbp_cli/commands/status.py` | Status reporting | N/A or to be identified | Verify if migrated to Click |
| `src/dbp_cli/commands/hstc.py` | HSTC command | `src/dbp_cli/cli_click/commands/hstc_agno.py` | HSTC functionality |
| `src/dbp_cli/commands/modeldiscovery.py` | Model discovery functionality | Likely in `test_bedrock.py` or `test_llm.py` | Verify the replacement |

## Documentation Files

| File Path | Purpose | Replacement | Notes |
|-----------|---------|-------------|-------|
| `src/dbp_cli/commands/HSTC.md` | HSTC documentation | May need to be moved | Verify if this should be preserved or relocated |

## Test Files

| File Path | Purpose | Replacement | Notes |
|-----------|---------|-------------|-------|
| `src/dbp_cli/commands/test/` | Tests for old commands | `src/dbp_cli/cli_click/tests/` | Directory containing tests for the old implementation |

## Verification Checklist

For each file to be removed, verify:

- [ ] The file's functionality has been properly migrated to the new Click-based implementation
- [ ] No other files in the codebase import or reference this file
- [ ] The file is not used by any external scripts or processes
- [ ] Documentation referencing this file has been updated
- [ ] Tests depending on this file have been updated or removed

## Implementation Priority

1. **Test files** - Remove first as they only depend on the implementation files
2. **Command implementation files** - Remove after verifying each command's functionality in the new implementation
3. **Command structure files** - Remove after all command implementations are removed
4. **Core CLI files** - Remove last after all other components are cleaned up
