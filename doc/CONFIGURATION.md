# Documentation-Based Programming Configuration

This document describes the configuration parameters available for the Documentation-Based Programming system components, including the MCP CLI client.

## Configuration Overview

The Documentation-Based Programming system follows a policy of reasonable default values while providing configuration options through several mechanisms:

1. **File-based configuration**: Configuration files in standard formats (JSON, YAML)
2. **Cline software settings**: Integration with Cline's configuration system
3. **Environment variables**: For containerized or headless environments
4. **Command-line parameters**: For one-time overrides

All configuration parameters have carefully selected defaults that work in most environments without requiring manual setup, while still allowing customization for specific needs.

**Design Rationale**: Default values are carefully selected to work in most environments, configuration documentation clearly indicates defaults and valid ranges, and the system remains operational with minimal setup while allowing customization when needed.

## Default Configuration Management

The system implements a centralized approach to default configuration values:

1. **Single Source of Truth**: All default values are maintained in `src/dbp/config/default_config.py`
2. **Organized Structure**: Values are organized in dictionaries corresponding to configuration sections
3. **Descriptive Documentation**: Each value includes inline documentation explaining its purpose
4. **Schema Separation**: Clear separation between schema definition and default values
5. **Configuration Consistency**: Values referenced in schema models are imported from the centralized module

This approach provides several benefits:
- Simplified maintenance of default values
- Comprehensive view of all defaults in one place
- Easier consistency between code and documentation
- Reduced risk of default value drift between components

## MCP Python CLI Client Configuration

### CLI Connection Settings

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `cli_server_connection.default` | Default MCP server to connect to | `"local"` | Any configured server name |
| `cli_server_connection.bind_address` | Network address to bind server to | `"127.0.0.1"` | Valid IP address or hostname |
| `cli_server_connection.port` | Port to use when connecting to MCP servers | `6231` | `1024-65535` |
| `cli_server_connection.timeout` | Connection timeout in seconds | `30` | `1-60` |
| `cli_server_connection.retry_attempts` | Number of connection retry attempts | `3` | `0-10` |
| `cli_server_connection.retry_interval` | Seconds between retry attempts | `2` | `1-30` |

### CLI Output Formatting

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `cli_output.format` | Default output format for responses | `"formatted"` | `"json", "yaml", "formatted"` |
| `cli_output.color` | Use colored output in terminal | `true` | `true, false` |
| `cli_output.verbosity` | Level of detail in output | `"normal"` | `"minimal", "normal", "detailed"` |
| `cli_output.max_width` | Maximum width for formatted output | Terminal width | `80-1000` |

### CLI Command History

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `cli_history.enabled` | Enable command history | `true` | `true, false` |
| `cli_history.size` | Maximum number of commands to store | `100` | `10-1000` |
| `cli_history.file` | File location for persistent history | `"${general.base_dir}/cli_history"` | Valid file path |
| `cli_history.save_failed` | Include failed commands in history | `true` | `true, false` |

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
| `database.type` | Database backend to use | `"sqlite"` | `"sqlite", "postgresql"` |
| `database.path` | Path to SQLite database file (when using SQLite) | `"coding_assistant/dbp/database.db"` | Valid file path |
| `database.connection_string` | PostgreSQL connection string (when using PostgreSQL) | `null` | Valid PostgreSQL connection string |
| `database.max_size_mb` | Maximum database size in megabytes (SQLite only) | `500` | `10-10000` |
| `database.vacuum_threshold` | Threshold for automatic vacuum (% free space) (SQLite only) | `20` | `5-50` |
| `database.connection_timeout` | Database connection timeout in seconds | `5` | `1-30` |
| `database.max_connections` | Maximum number of concurrent database connections | `4` | `1-16` |
| `database.use_wal_mode` | Use Write-Ahead Logging mode for SQLite | `true` | `true, false` |
| `database.echo_sql` | Log SQL statements executed by SQLAlchemy | `false` | `true, false` |
| `database.alembic_ini_path` | Path to the Alembic configuration file | `"alembic.ini"` | Valid file path |
| `database.verbose_migrations` | Enable detailed logging during database migrations | `true` | `true, false` |

### Recommendation Lifecycle Settings

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `recommendations.auto_purge_enabled` | Enable automatic purging of old recommendations | `true` | `true, false` |
| `recommendations.purge_age_days` | Age in days after which recommendations are purged | `7` | `1-365` |
| `recommendations.purge_decisions_with_recommendations` | Also purge related developer decisions | `true` | `true, false` |
| `recommendations.auto_invalidate` | Automatically invalidate recommendation on codebase change | `true` | `true, false` |

### Component Enablement Settings

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `component_enabled.config_manager` | Enable configuration manager component | `true` | `true, false` |
| `component_enabled.file_access` | Enable file access component | `true` | `true, false` |
| `component_enabled.database` | Enable database component | `true` | `true, false` |
| `component_enabled.fs_monitor` | Enable file system monitor component | `false` | `true, false` |
| `component_enabled.filter` | Enable file filter component | `false` | `true, false` |
| `component_enabled.change_queue` | Enable change queue component | `false` | `true, false` |
| `component_enabled.memory_cache` | Enable memory cache component | `false` | `true, false` |
| `component_enabled.consistency_analysis` | Enable consistency analysis component | `false` | `true, false` |
| `component_enabled.doc_relationships` | Enable document relationships component | `false` | `true, false` |
| `component_enabled.recommendation_generator` | Enable recommendation generator component | `false` | `true, false` |
| `component_enabled.scheduler` | Enable scheduler component | `false` | `true, false` |
| `component_enabled.metadata_extraction` | Enable metadata extraction component | `false` | `true, false` |
| `component_enabled.llm_coordinator` | Enable LLM coordinator component | `true` | `true, false` |
| `component_enabled.mcp_server` | Enable MCP server component | `true` | `true, false` |

## Configuration File Format

Configuration can be specified in JSON format:

```json
{
  "cli_server_connection": {
    "default": "local",
    "bind_address": "127.0.0.1",
    "port": 6231,
    "timeout": 30,
    "retry_attempts": 3,
    "retry_interval": 2
  },
  "cli_output": {
    "format": "formatted",
    "color": true,
    "verbosity": "normal"
  },
  "cli_history": {
    "enabled": true,
    "size": 100,
    "file": "${general.base_dir}/cli_history",
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
    "type": "sqlite",
    "path": "coding_assistant/dbp/database.db",
    "max_size_mb": 500,
    "vacuum_threshold": 20,
    "use_wal_mode": true
  },
  "recommendations": {
    "auto_purge_enabled": true,
    "purge_age_days": 7,
    "purge_decisions_with_recommendations": true,
    "max_active_recommendations": 100
  }
}
```

## Path Resolution

The Documentation-Based Programming system uses a consistent approach to resolve all relative paths specified in configuration:

1. **Git Root-Relative Resolution**: All relative paths are resolved relative to the Git project root (where the `.git/` directory is located)
2. **Explicit Failure**: If the Git root cannot be found, the system will raise an error rather than falling back to the current working directory
3. **Absolute Paths**: Absolute paths are used unchanged
4. **Home Directory Expansion**: Paths starting with `~` are expanded to the user's home directory

This Git root-relative approach ensures:

- Consistent path resolution regardless of where in the project directory the application is executed from
- Centralized storage of all DBP system files in predictable locations
- Clear error reporting when running outside a Git repository context
- Reliable access to resources across different components

For example, when specifying `database.path` as `"coding_assistant/dbp/database.db"`, this path will always resolve to `<git_project_root>/coding_assistant/dbp/database.db`, ensuring that components find the database file regardless of their current working directory.

## Environment Variables

All configuration parameters can be overridden using environment variables with the `DBP_` prefix and uppercase parameter names:

| Environment Variable | Corresponding Parameter |
|---------------------|-------------------------|
| `DBP_CLI_SERVER_CONNECTION_DEFAULT` | `cli_server_connection.default` |
| `DBP_CLI_SERVER_CONNECTION_PORT` | `cli_server_connection.port` |
| `DBP_CLI_OUTPUT_FORMAT` | `cli_output.format` |
| `DBP_MONITOR_DELAY` | `monitor.delay` |
| `DBP_DATABASE_TYPE` | `database.type` |
| `DBP_RECOMMENDATIONS_PURGE_AGE_DAYS` | `recommendations.purge_age_days` |

## Cline Integration

When used within the Cline environment, the following integration points are available:

1. Shared configuration settings between Cline and DBP components
2. Automatic detection of project-specific settings
3. Configuration override through Cline's command interface
4. **Interface Consistency**: There must not be a single difference between starting MCP server from command line or from Cline editor MCP client
   - **Rationale**: Ensures consistent behavior across all client access methods
   - **Implementation**: Shared initialization code path, unified configuration handling
   - **Benefits**: Simplifies testing, eliminates potential inconsistencies between environments

## Command-line Parameters

For the CLI client, configuration can be overridden using command-line parameters:

```
mcp-cli --cli_server_connection.port=7000 --cli_output.format=json connect local
```

## Configuration Precedence

Configuration values are applied in the following order of precedence (highest to lowest):

1. Command-line parameters
2. Environment variables
3. Project-specific configuration file
4. User configuration file
5. System-wide configuration file
6. Default values
