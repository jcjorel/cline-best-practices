# Documentation-Based Programming Configuration

This document describes the configuration parameters available for the Documentation-Based Programming system components, including the MCP CLI client.

## Configuration Overview

The Documentation-Based Programming system supports configuration options through several mechanisms:

1. **File-based configuration**: Configuration files in standard formats (JSON, YAML)
2. **Cline software settings**: Integration with Cline's configuration system
3. **Environment variables**: For containerized or headless environments
4. **Command-line parameters**: For one-time overrides

## MCP Python CLI Client Configuration

### Connection Settings

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `server.default` | Default MCP server to connect to | `"local"` | Any configured server name |
| `server.port` | Port to use when connecting to MCP servers | `6231` | `1024-65535` |
| `server.timeout` | Connection timeout in seconds | `5` | `1-60` |
| `server.retry_attempts` | Number of connection retry attempts | `3` | `0-10` |
| `server.retry_interval` | Seconds between retry attempts | `2` | `1-30` |

### Output Formatting

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `output.format` | Default output format for responses | `"formatted"` | `"json", "yaml", "formatted"` |
| `output.color` | Use colored output in terminal | `true` | `true, false` |
| `output.verbosity` | Level of detail in output | `"normal"` | `"minimal", "normal", "detailed"` |
| `output.max_width` | Maximum width for formatted output | Terminal width | `80-1000` |

### Command History

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `history.enabled` | Enable command history | `true` | `true, false` |
| `history.size` | Maximum number of commands to store | `100` | `10-1000` |
| `history.file` | File location for persistent history | `"~/.mcp_cli_history"` | Valid file path |
| `history.save_failed` | Include failed commands in history | `true` | `true, false` |

### Scripting Support

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `script.directories` | Directories to search for custom scripts | `["~/.mcp_scripts"]` | Array of valid paths |
| `script.autoload` | Automatically load scripts at startup | `true` | `true, false` |
| `script.allow_remote` | Allow loading scripts from remote URLs | `false` | `true, false` |

## Documentation Monitoring Configuration

### Background Task Scheduler

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `scheduler.enabled` | Enable the background scheduler | `true` | `true, false` |
| `scheduler.delay_seconds` | Debounce delay before processing changes | `10` | `1-60` |
| `scheduler.max_delay_seconds` | Maximum delay for any file | `120` | `30-600` |
| `scheduler.worker_threads` | Number of worker threads | `2` | `1-8` |
| `scheduler.max_queue_size` | Maximum size of change queue | `1000` | `100-10000` |
| `scheduler.batch_size` | Files processed in one batch | `20` | `1-100` |

### File System Monitoring

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `monitor.enabled` | Enable file system monitoring | `true` | `true, false` |
| `monitor.ignore_patterns` | Additional patterns to ignore beyond .gitignore | `["*.tmp", "*.log"]` | Array of glob patterns |
| `monitor.recursive` | Monitor subdirectories recursively | `true` | `true, false` |

### Database Settings

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `database.path` | Path to SQLite database file | `"~/.dbp/metadata.db"` | Valid file path |
| `database.max_size_mb` | Maximum database size in megabytes | `500` | `10-10000` |
| `database.vacuum_threshold` | Threshold for automatic vacuum (% free space) | `20` | `5-50` |
| `database.connection_timeout` | Database connection timeout in seconds | `5` | `1-30` |
| `database.max_connections` | Maximum number of concurrent database connections | `4` | `1-16` |

## Configuration File Format

Configuration can be specified in JSON format:

```json
{
  "server": {
    "default": "local",
    "port": 6231,
    "timeout": 5,
    "retry_attempts": 3,
    "retry_interval": 2
  },
  "output": {
    "format": "formatted",
    "color": true,
    "verbosity": "normal"
  },
  "history": {
    "enabled": true,
    "size": 100,
    "file": "~/.mcp_cli_history",
    "save_failed": true
  },
  "script": {
    "directories": ["~/.mcp_scripts"],
    "autoload": true,
    "allow_remote": false
  },
  "monitor": {
    "enabled": true,
    "delay": 10,
    "batch_size": 20
  },
  "database": {
    "path": "~/.dbp/metadata.db",
    "max_size_mb": 500,
    "vacuum_threshold": 20
  }
}
```

## Environment Variables

All configuration parameters can be overridden using environment variables with the `DBP_` prefix and uppercase parameter names:

| Environment Variable | Corresponding Parameter |
|---------------------|-------------------------|
| `DBP_SERVER_DEFAULT` | `server.default` |
| `DBP_SERVER_PORT` | `server.port` |
| `DBP_OUTPUT_FORMAT` | `output.format` |
| `DBP_MONITOR_DELAY` | `monitor.delay` |

## Cline Integration

When used within the Cline environment, the following integration points are available:

1. Shared configuration settings between Cline and DBP components
2. Automatic detection of project-specific settings
3. Configuration override through Cline's command interface

## Command-line Parameters

For the CLI client, configuration can be overridden using command-line parameters:

```
mcp-cli --server.port=7000 --output.format=json connect local
```

## Configuration Precedence

Configuration values are applied in the following order of precedence (highest to lowest):

1. Command-line parameters
2. Environment variables
3. Project-specific configuration file
4. User configuration file
5. System-wide configuration file
6. Default values
