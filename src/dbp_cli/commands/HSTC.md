# Hierarchical Semantic Tree Context: commands

## Directory Purpose
This directory contains command handler implementations for the Document Based Programming (DBP) CLI. Each command handler follows the Command pattern and extends a common BaseCommandHandler abstract class that enforces a consistent interface. The handlers provide specific CLI command implementations with argument parsing, execution logic, and formatted output. Together these command handlers form the core functionality of the CLI, exposing various features of the MCP server through a consistent command-line interface.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Command handlers for the DBP CLI.
  
source_file_design_principles: |
  - Simple module structure
  - Exports command handler classes
  
source_file_constraints: |
  - Should not contain implementation logic
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-16T10:00:00Z"
    summary: "Initial commit"
    details: "Added module docstring"
```

### `base.py`
```yaml
source_file_intent: |
  Defines the base command handler abstract class that all CLI command handlers
  must inherit from. Provides common functionality and a standard interface for
  command execution.
  
source_file_design_principles: |
  - Uses abstract base class to enforce interface.
  - Provides common helper methods for all command handlers.
  - Simplifies command implementation by standardizing parameters and dependencies.
  - Takes dependencies via constructor for better testability.
  - Design Decision: Abstract Base Class (2025-04-15)
    * Rationale: Enforces consistent interface across all command handlers.
    * Alternatives considered: Function-based commands (less enforced structure), 
      class-based without ABC (less explicit contract).
  
source_file_constraints: |
  - Requires Python 3.8+ for TypedDict usage.
  - Command execution must return an integer exit code.
  - Must have explicit error handling within execute().
  
dependencies:
  - kind: system
    dependency: argparse
  - kind: system
    dependency: logging
  - kind: system
    dependency: abc
  - kind: codebase
    dependency: src/dbp_cli/api.py
  - kind: codebase
    dependency: src/dbp_cli/output.py
  - kind: codebase
    dependency: src/dbp_cli/progress.py
  - kind: codebase
    dependency: src/dbp_cli/exceptions.py
  
change_history:
  - timestamp: "2025-04-15T13:04:40Z"
    summary: "Initial creation of BaseCommandHandler"
    details: "Implemented abstract base class with execute method and helper methods."
```

### `commit.py`
```yaml
source_file_intent: |
  Implements the CommitCommandHandler for the 'commit' CLI command, which exposes
  the commit message generation functionality of the MCP server's dbp_commit_message tool.
  
source_file_design_principles: |
  - Extends the BaseCommandHandler to implement the 'commit' command.
  - Provides options to control commit message generation.
  - Displays formatted results including supporting metadata.
  - Offers ability to save generated messages to file.
  
source_file_constraints: |
  - Depends on the MCP server supporting the 'dbp_commit_message' tool.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: other
    dependency: src/dbp_cli/commands/base.py
  
change_history:
  - timestamp: "2025-04-16T10:12:00Z"
    summary: "Initial creation of CommitCommandHandler"
    details: "Implemented command handler for commit message generation"
```

### `query.py`
```yaml
source_file_intent: |
  Implements the QueryCommandHandler for the 'query' CLI command, which exposes
  the natural language query functionality of the MCP server's dbp_general_query tool.
  
source_file_design_principles: |
  - Extends the BaseCommandHandler to implement the 'query' command.
  - Provides direct natural language access to the dbp_general_query MCP tool.
  - Simplifies interaction by focusing only on natural language.
  - Formats and displays results consistently.
  
source_file_constraints: |
  - Depends on the MCP server supporting the 'dbp_general_query' tool.
  - Query handling ultimately depends on the server's ability to interpret queries.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: other
    dependency: src/dbp_cli/commands/base.py
  
change_history:
  - timestamp: "2025-04-16T10:08:00Z"
    summary: "Initial creation of QueryCommandHandler"
    details: "Implemented command handler for natural language queries"
```

### `config.py`
```yaml
source_file_intent: |
  Implements the ConfigCommandHandler for the 'config' CLI command, which allows
  users to view and modify configuration settings for the DBP CLI and MCP server.
  
source_file_design_principles: |
  - Extends the BaseCommandHandler to implement the 'config' command.
  - Provides get, set, and list subcommands for configuration management.
  - Supports configuration scopes (user, project, default).
  - Clean interface for configuration operations.
  
source_file_constraints: |
  - Must handle different configuration storage locations.
  - Must validate configuration values based on schema.
  
dependencies:
  - kind: codebase
    dependency: src/dbp_cli/config.py
  - kind: other
    dependency: src/dbp_cli/commands/base.py
  
change_history:
  - timestamp: "2025-04-16T10:15:00Z"
    summary: "Initial creation of ConfigCommandHandler"
    details: "Implemented command handler for configuration management"
```

### `server.py`
```yaml
source_file_intent: |
  Implements the ServerCommandHandler for the 'server' CLI command, which provides
  functionality to start, stop, and manage the MCP server instance.
  
source_file_design_principles: |
  - Extends the BaseCommandHandler to implement the 'server' command.
  - Provides start, stop, status, and restart subcommands.
  - Handles server process management and status reporting.
  - Supports configuration options for server startup.
  
source_file_constraints: |
  - Must manage server process lifecycle correctly.
  - Must handle edge cases like already running servers.
  - Requires proper error handling for process management.
  
dependencies:
  - kind: system
    dependency: subprocess
  - kind: system
    dependency: os
  - kind: system
    dependency: signal
  - kind: codebase
    dependency: src/dbp_cli/config.py
  - kind: other
    dependency: src/dbp_cli/commands/base.py
  
change_history:
  - timestamp: "2025-04-16T10:20:00Z"
    summary: "Initial creation of ServerCommandHandler"
    details: "Implemented command handler for server management"
```

### `status.py`
```yaml
source_file_intent: |
  Implements the StatusCommandHandler for the 'status' CLI command, which provides
  information about the current state of the DBP system, including the server status,
  active components, and recent activity.
  
source_file_design_principles: |
  - Extends the BaseCommandHandler to implement the 'status' command.
  - Collects and organizes system status information.
  - Provides formatted output with visual indicators.
  - Supports various output formats (text, JSON, detailed).
  
source_file_constraints: |
  - Must handle cases where the server is not running.
  - Should provide useful information even with limited connectivity.
  
dependencies:
  - kind: codebase
    dependency: src/dbp_cli/api.py
  - kind: other
    dependency: src/dbp_cli/commands/base.py
  
change_history:
  - timestamp: "2025-04-16T10:25:00Z"
    summary: "Initial creation of StatusCommandHandler"
    details: "Implemented command handler for system status reporting"
```

End of HSTC.md file
