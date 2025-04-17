# Configuration Key Reorganization for Clarity

## Decision Date: 2025-04-17

## Decision Makers

CodeAssistant in collaboration with system stakeholders

## Context

The DBP system's configuration in `src/dbp/config/default_config.py` had several naming inconsistencies and organizational issues:
- Similar naming between `SERVER_DEFAULTS` and `MCP_SERVER_DEFAULTS` caused confusion about their distinct purposes
- CLI-specific configuration keys like `OUTPUT_DEFAULTS` and `HISTORY_DEFAULTS` lacked clear association with the CLI
- `COORDINATOR_LLM_DEFAULTS` referenced an incorrect model (Amazon Titan) when Nova Lite is actually used
- CLI-related defaults were scattered throughout the file rather than grouped together

## Decision

1. Rename `SERVER_DEFAULTS` to `CLI_SERVER_CONNECTION_DEFAULTS` to clarify it's for CLI connections to the server
2. Rename `OUTPUT_DEFAULTS` to `CLI_OUTPUT_DEFAULTS` to clearly associate with CLI
3. Rename `HISTORY_DEFAULTS` to `CLI_HISTORY_DEFAULTS` to clearly associate with CLI
4. Update `COORDINATOR_LLM_DEFAULTS` to reference the Nova Lite model actually used
5. Group all CLI-related defaults at the end of the file for better organization

## Rationale

- **Clarity**: The new naming scheme makes it immediately clear which component each configuration block belongs to
- **Consistency**: All CLI-related configuration now follows the same prefix pattern
- **Accuracy**: Configuration now correctly references the actual models and components used
- **Organization**: Related configuration settings are now grouped together

## Alternatives Considered

1. **Keeping the existing naming**: Rejected as it was causing confusion and potential misuse of configuration values.
2. **Using a nested structure with a top-level CLI key**: Rejected as it would require substantial changes to the configuration schema and all code that accesses these values.

## Implementation Details

The implementation includes:

1. Renaming the configuration constants in `default_config.py`
2. Updating references in documentation (`CONFIGURATION.md`)
3. Grouping all CLI-related settings at the end of the file
4. Updating the model reference in `COORDINATOR_LLM_DEFAULTS` to align with actual usage

## Implications

- Code that directly references the old configuration key names will need to be updated
- Documentation now correctly reflects the actual configuration structure
- Future development should follow the established naming pattern for clarity

## Related Decisions

- Centralized Default Configuration Values (2025-04-16)

# Git Root-relative Path Resolution for Configuration

## Decision Date: 2025-04-17

## Decision Makers

CodeAssistant in collaboration with system stakeholders

## Context

The DBP system requires access to various files and directories for its operation, including:
- SQLite database files: `.dbp/database.sqlite`
- Server logs directory: `.dbp/logs/`
- CLI configuration files: `.dbp/cli_config.json`
- Server PID files: `.dbp/mcp_server.pid`

When specifying these paths in configuration, we need a consistent way to resolve them regardless of where in the project directory structure the application is executed from.

## Decision

1. All relative paths in the configuration will be resolved relative to the Git project root (where `.git/` directory is located)
2. A centralized path resolution system will be implemented in `src/dbp/core/fs_utils.py` to handle this consistently
3. If the Git root cannot be found, the system will raise an error rather than falling back to the current working directory
4. All components that work with file paths will use this centralized resolution system

## Rationale

- **Consistency**: No matter which directory the user starts the application from, paths will always be resolved correctly
- **Project Organization**: Keeps all DBP system files in a single `.dbp/` directory at the project root
- **Explicit Failure**: Fails clearly when running outside a Git repository rather than creating files in unexpected locations
- **Centralized Logic**: Single implementation ensures consistent behavior across all components

## Alternatives Considered

1. **Current Working Directory Resolution**: Using the current working directory for resolving relative paths.
   * Rejected because it would lead to files spread across different directories depending on where the application is started from.

2. **Fixed Absolute Paths**: Requiring absolute paths for all configuration.
   * Rejected because it reduces portability and makes configuration more verbose.

3. **Fallback to Current Working Directory**: When Git root cannot be found, fall back to resolving paths from the current directory.
   * Rejected as this would lead to silent creation of files in unexpected locations.

## Implementation Details

The implementation includes:

1. A `find_git_root()` function that:
   - First attempts to use the `git` command to find the repository root
   - Falls back to searching for a `.git` directory by traversing up from the current directory
   - Returns the Git root path or `None` if not found

2. A `resolve_path()` function that:
   - Handles path normalization and user home directory expansion
   - Returns absolute paths unchanged
   - For relative paths, resolves them relative to the Git root
   - Raises a `RuntimeError` if Git root cannot be found

3. Updated directory creation utilities that:
   - Use the path resolution functions to ensure paths are resolved correctly
   - Create any missing directories with proper error handling
   - Verify write permissions after directory creation

## Implications

- The application requires running within a Git repository
- Components must handle the possibility of a RuntimeError when resolving paths
- No fallback behaviors - if Git root can't be found, components should fail explicitly rather than proceeding with potentially incorrect paths
- The centralized approach ensures that if path resolution behavior needs to be modified in the future, changes need to be made in just one place

## Related Decisions

- Default locations for database files and other system files
- Component initialization sequence and error handling

# Standardized Log Format for System-Wide Consistency

## Decision Date: 2025-04-17

## Decision Makers

CodeAssistant in collaboration with system stakeholders

## Context

The DBP system previously had inconsistent log formats across different components. Some components were using the default Python logging format (e.g., "ERROR:root:message"), while others had custom formatters. This inconsistency made logs difficult to parse, analyze, and correlate.

## Decision

1. Standardize all application logs to follow this exact format:
   ```
   YYYY-MM-DD HH:MM:SS,mmm - logger.name - LOGLEVEL - message
   ```

   Example:
   ```
   2025-04-17 17:24:30,221 - dbp.core.lifecycle - INFO - Starting Documentation-Based Programming system...
   ```

2. Implement a centralized logging setup through `setup_application_logging()` in `log_utils.py`
   
3. Configure the root logger early in the application startup process to prevent default-formatted logs

4. Use the `MillisecondFormatter` class to ensure consistent millisecond timestamps

## Rationale

- **Consistency**: All log messages follow the same format for easier reading and parsing
- **Precision**: Timestamps include milliseconds for accurate timing analysis
- **Clarity**: Logger name clearly shows which component generated the message
- **Standards Compliance**: Format is similar to standard logging formats while maintaining our specific requirements

## Alternatives Considered

1. **JSON-formatted logs**: Considered for better machine parsing, but rejected for human readability.
2. **Including thread ID**: Considered for multi-threaded debugging, but excluded for simplicity and readability.
3. **Allowing component-specific formats**: Rejected to maintain system-wide consistency.
4. **Different datetime formats**: Considered ISO-8601 with 'T' separator, but kept space separator for readability.

## Implementation Details

1. Enhanced `setup_application_logging()` in `log_utils.py` to:
   - Reset any existing logging configuration to prevent format inconsistencies
   - Configure logging.basicConfig() early to catch logs that might appear before handlers are added
   - Use the custom MillisecondFormatter for precise timestamp formatting
   - Configure both the root logger and component-specific loggers consistently

2. Updated the MillisecondFormatter to:
   - Format timestamps with exactly 3 digits of millisecond precision
   - Remove duplicate log level prefixes from messages
   - Handle both uppercase and lowercase log level names in prefixes

3. Ensure all application components:
   - Use the centralized setup function at startup
   - Get loggers through the provided utility functions
   - Avoid direct calls to logging.basicConfig() or custom formatters

## Implications

- All components must use the centralized logging configuration
- Logs will have a consistent format throughout the system
- Better troubleshooting and log analysis capabilities
- Improved ability to correlate events across different components

## Related Decisions

- Component initialization sequence
- Error handling strategy
