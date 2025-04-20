# Hierarchical Semantic Tree Context - Commands Module

This directory contains command handler implementations for the DBP CLI application. Each command handler extends the BaseCommandHandler abstract class and implements specific functionality like querying the system, committing changes, configuring settings, checking server status, etc.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'base.py':
**Source file intent**: Defines the base command handler abstract class that all CLI command handlers
must inherit from. Provides common functionality and a standard interface for
command execution.

**Source file design principles**: 
- Uses abstract base class to enforce interface.
- Provides common helper methods for all command handlers.
- Simplifies command implementation by standardizing parameters and dependencies.
- Takes dependencies via constructor for better testability.
- Design Decision: Abstract Base Class (2025-04-15)
  * Rationale: Enforces consistent interface across all command handlers.
  * Alternatives considered: Function-based commands (less enforced structure), 
    class-based without ABC (less explicit contract).

**Source file constraints**:
- Requires Python 3.8+ for TypedDict usage.
- Command execution must return an integer exit code.
- Must have explicit error handling within execute().

### Filename 'commit.py':
**Source file intent**: Implements the CommitCommandHandler for the 'commit' CLI command, which exposes
the commit message generation functionality of the MCP server's dbp_commit_message tool.

**Source file design principles**: 
- Extends the BaseCommandHandler to implement the 'commit' command.
- Provides options to control commit message generation.
- Displays formatted results including supporting metadata.
- Offers ability to save generated messages to file.

**Source file constraints**:
- Depends on the MCP server supporting the 'dbp_commit_message' tool.

### Filename 'config.py':
**Source file intent**: Implements the ConfigCommandHandler for the 'config' CLI command, which allows
users to manage CLI configuration settings. This includes viewing, setting, and
resetting configuration values for the DBP CLI application.

**Source file design principles**: 
- Extends the BaseCommandHandler to implement the 'config' command.
- Provides operations for getting, setting, listing, and resetting configuration.
- Supports dot notation for accessing nested configuration values.
- Persists configuration changes to disk when needed.
- Validates configuration keys and values.

**Source file constraints**:
- Depends on the ConfigurationManager from config.py.
- Configuration keys are case-sensitive.
- File writing depends on filesystem permissions.

### Filename 'query.py':
**Source file intent**: Implements the QueryCommandHandler for the 'query' CLI command, which exposes
the natural language query functionality of the MCP server's dbp_general_query tool.

**Source file design principles**: 
- Extends the BaseCommandHandler to implement the 'query' command.
- Provides direct natural language access to the dbp_general_query MCP tool.
- Simplifies interaction by focusing only on natural language.
- Formats and displays results consistently.

**Source file constraints**:
- Depends on the MCP server supporting the 'dbp_general_query' tool.
- Query handling ultimately depends on the server's ability to interpret queries.

### Filename 'server.py':
**Source file intent**: Implements the ServerCommandHandler for the 'server' CLI command, which allows
users to start, stop, and manage the MCP server instance directly from the
command line. This simplifies the workflow by avoiding the need to manually
start the server in a separate terminal.

**Source file design principles**: 
- Extends the BaseCommandHandler to implement the 'server' command.
- Uses subprocess to start the MCP server in a background process.
- Provides options to start, stop, restart, and check status of the server.
- Supports customization of host, port, and other server parameters.
- Maintains an easily discoverable interface for server management.

**Source file constraints**:
- Requires Python's subprocess module for process management.
- Server processes started in background mode need proper cleanup.
- PID tracking is used to manage server processes.

**Change History:**
- 2025-04-20T23:43:45Z : Added explicit server startup timeout logging
- 2025-04-17T16:16:00Z : Removed duplicate log path information
- 2025-04-17T15:52:00Z : Fixed import error in server startup
- 2025-04-17T15:49:00Z : Fixed startup configuration access

### Filename 'status.py':
**Source file intent**: Implements the StatusCommandHandler for the 'status' CLI command, which allows
users to check the status of the Documentation-Based Programming system,
including server connectivity, authentication status, and configuration.

**Source file design principles**: 
- Extends the BaseCommandHandler to implement the 'status' command.
- Provides options to check server connectivity and authentication.
- Displays current configuration settings.
- Returns appropriate exit codes for automation.

**Source file constraints**:
- Server status checks depend on network connectivity.
- Authentication checks may trigger authorization-only API calls.

### Filename '__init__.py':
**Source file intent**: Command handlers for the DBP CLI.
