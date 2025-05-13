# Migration Guide: Legacy CLI to Click-based CLI

This guide will help you transition from the legacy `dbp` command to the new Click-based `dbp-click` command.

## Overview

The CLI for Documentation-Based Programming has been reimplemented using the Click framework, providing these benefits:

- **Improved help text**: More consistent and readable help documentation
- **Better error messages**: Clearer error reporting with context
- **Enhanced tab completion**: Better shell completion support
- **Consistent option parsing**: Standardized option handling across all commands
- **Type validation**: Automatic type checking and validation of command arguments
- **Extensibility**: Easier to add new commands and features in the future

The new CLI maintains full compatibility with the existing command structure and options, making migration simple.

## Getting Started

To start using the new CLI, simply use `dbp-click` instead of `dbp` for your commands:

```bash
# Legacy CLI
dbp query "How do I optimize an S3 bucket?"

# New Click-based CLI
dbp-click query "How do I optimize an S3 bucket?"
```

## Command Mapping

All commands from the legacy CLI are available in the new CLI with the same names and behavior:

| Legacy Command | New Command | Description |
|---------------|-------------|-------------|
| `dbp query` | `dbp-click query` | Execute queries against Bedrock models |
| `dbp config` | `dbp-click config` | Manage configuration settings |
| `dbp status` | `dbp-click status` | Check system status |
| `dbp commit` | `dbp-click commit` | Generate commit messages |
| `dbp hstc_agno` | `dbp-click hstc_agno` | Manage HSTC documentation |
| `dbp server` | `dbp-click server` | Manage the MCP server |

## Global Options

All global options from the legacy CLI are available in the new CLI:

| Legacy Option | New Option | Description |
|--------------|------------|-------------|
| `--version` | `--version` | Show version information |
| `--config FILE` | `--config FILE` | Path to configuration file |
| `--server URL` | `--server URL` | MCP server URL |
| `--api-key KEY` | `--api-key KEY` | API key for authentication |
| `--verbose, -v` | `--verbose, -v` | Increase verbosity level |
| `--quiet, -q` | `--quiet, -q` | Suppress non-error output |
| `--output, -o` | `--output, -o` | Output format |
| `--no-color` | `--no-color` | Disable colored output |
| `--no-progress` | `--no-progress` | Disable progress indicators |
| `--debug` | `--debug` | Enable debug mode |

## Command Options

All command-specific options maintain the same names and behavior in the new CLI. Here are some examples:

### Query Command

```bash
# Legacy CLI
dbp query "How do I optimize code?" --budget 10 --timeout 30

# New Click-based CLI
dbp-click query "How do I optimize code?" --budget 10 --timeout 30
```

### Config Command

```bash
# Legacy CLI
dbp config set api.url https://example.com/api
dbp config get api.url

# New Click-based CLI
dbp-click config set api.url https://example.com/api
dbp-click config get api.url
```

### HSTC Agno Command

```bash
# Legacy CLI
dbp hstc_agno update src/my_file.py --verbose

# New Click-based CLI
dbp-click hstc_agno update src/my_file.py --verbose
```

## Key Differences

While the commands and options are the same, there are some subtle differences in behavior:

1. **Help text formatting**: The formatting of help text differs slightly due to Click's presentation style
2. **Error message wording**: While error conditions are handled the same way, the specific error message text may differ
3. **Command grouping**: The Click CLI may organize some commands differently in help output

## Tips for a Smooth Transition

1. **Update scripts**: If you have any scripts that use the `dbp` command, update them to use `dbp-click` instead
2. **Check aliases**: If you have any shell aliases defined for `dbp` commands, update them for the new CLI
3. **Review help**: Use `dbp-click --help` and `dbp-click [command] --help` to get familiar with the new help format
4. **Consider completion**: The new CLI supports better tab completion in compatible shells

## Timeline

The legacy `dbp` command is deprecated but will continue to work for a transition period. In a future release, the `dbp` command will be aliased to `dbp-click`, and eventually the legacy implementation will be removed.

When you use the legacy `dbp` command, you'll see a deprecation warning to remind you of this transition.

## Reporting Issues

If you encounter any issues while migrating to the new CLI, please report them by creating an issue in the project repository, including:

1. The command you were trying to run
2. The expected behavior
3. The actual behavior or error message
4. Any relevant context (OS, environment, etc.)

## Need Help?

If you need further assistance with the migration, please reach out to the Documentation-Based Programming team.
