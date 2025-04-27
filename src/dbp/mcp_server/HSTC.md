# Hierarchical Semantic Tree Context: mcp_server

## Directory Purpose
This directory implements an MCP (Model Context Protocol) server using the FastMCP library. It provides a component-based integration with the DBP system for managing the MCP server lifecycle, along with base classes for implementing MCP tools and resources. The implementation follows a clean architecture with clear separation between the component interface, server implementation, and tool/resource definitions. The server supports streaming capabilities, progress reporting, and cancellation handling.

## Child Directories

### internal_tools
This directory contains internal MCP tools that provide implementation for functionality exposed through public tools. These internal tools are not intended to be used directly by MCP clients but are accessed through the public tools defined in the MCP server. The directory implements a clear separation between public and internal tools with consistent interfaces, proper naming conventions, and common error handling patterns.

### examples
This directory contains example implementations of MCP tools and resources for demonstration and reference purposes. It serves as a practical guide for developers creating custom MCP tools and resources using the unified API. The examples demonstrate proper implementation patterns, including streaming capabilities, progress reporting, cancellation handling, and parameter validation using Pydantic models.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Initializes the mcp_server package and exports key classes and functions.
  
source_file_design_principles: |
  - Clean package exports
  - Simplified imports for consumers
  - Clear documentation of public API
  
source_file_constraints: |
  - Only export public API elements
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-27T22:15:00Z"
    summary: "Updated package exports for FastMCP integration"
    details: "Modified exports to include FastMCP-compatible classes and functions"
```

### `__main__.py`
```yaml
source_file_intent: |
  Provides the entry point for running the MCP server as a standalone application.
  
source_file_design_principles: |
  - Simple command-line interface
  - Component-based initialization
  - Clean error handling and logging
  
source_file_constraints: |
  - Must initialize the MCPServerComponent
  - Must handle command-line arguments
  - Must provide proper error handling
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/component.py
  - kind: codebase
    dependency: src/dbp/core/system.py
  
change_history:
  - timestamp: "2025-04-27T22:18:00Z"
    summary: "Updated main entry point for FastMCP integration"
    details: "Modified to use wait_for_server_exit() instead of start_server()"
```

### `adapter.py`
```yaml
source_file_intent: |
  Provides adapter functions to convert between FastMCP and DBP system components.
  
source_file_design_principles: |
  - Clean adaptation between FastMCP and DBP
  - Support for both synchronous and asynchronous execution
  - Proper error handling and conversion
  
source_file_constraints: |
  - Must maintain compatibility with existing interfaces
  - Must properly convert between error types
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: codebase
    dependency: src/dbp/core/component.py
  
change_history:
  - timestamp: "2025-04-25T08:14:00Z"
    summary: "Created adapter functions for FastMCP integration"
    details: "Implemented functions to convert between FastMCP and DBP components"
```

### `auth.py`
```yaml
source_file_intent: |
  Implements authentication and authorization for the MCP server.
  
source_file_design_principles: |
  - Secure authentication mechanisms
  - Role-based authorization
  - Integration with FastMCP auth system
  
source_file_constraints: |
  - Must maintain security best practices
  - Must integrate with FastMCP auth system
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: codebase
    dependency: src/dbp/core/auth.py
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Implemented authentication and authorization"
    details: "Created authentication and authorization mechanisms for MCP server"
```

### `component.py`
```yaml
source_file_intent: |
  Implements the MCPServerComponent class using FastMCP library.
  This component maintains the same interface as the original but replaces the
  homemade MCP implementation with FastMCP for better compliance with the MCP specification.
  
source_file_design_principles: |
  - Maintains the Component protocol interface (`src/dbp/core/component.py`).
  - Preserves integration with config_manager.
  - Uses FastMCP for MCP protocol implementation.
  - Maintains the same lifecycle management API.
  - Provides clear logging for operation.
  - Simplifies component implementation by delegating to MCPServer class.
  
source_file_constraints: |
  - Must maintain the same interface as the original component.
  - Should maintain integration with config_manager.
  - Must provide clear log messages during operation.
  - Must use FastMCP for MCP protocol implementation.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: src/dbp/core/component.py
  - kind: codebase
    dependency: src/dbp/core/fs_utils.py
  - kind: codebase
    dependency: src/dbp/config/config_manager.py
  - kind: codebase
    dependency: src/dbp/mcp_server/server.py
  - kind: system
    dependency: fastmcp
  
change_history:
  - timestamp: "2025-04-27T17:26:00Z"
    summary: "Updated ComponentNotInitializedError import by CodeAssistant"
    details: "Removed local ComponentNotInitializedError class definition"
```

### `data_models.py`
```yaml
source_file_intent: |
  Defines data models for MCP server operations.
  
source_file_design_principles: |
  - Clear data model definitions
  - Pydantic models for validation
  - Consistent naming conventions
  
source_file_constraints: |
  - Must use Pydantic for validation
  - Must maintain consistent naming conventions
  
dependencies:
  - kind: system
    dependency: pydantic
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created data models for MCP server"
    details: "Defined Pydantic models for MCP server operations"
```

### `error_handler.py`
```yaml
source_file_intent: |
  Implements error handling for the MCP server.
  
source_file_design_principles: |
  - Consistent error handling
  - Clear error messages
  - Proper logging of errors
  
source_file_constraints: |
  - Must maintain consistent error handling
  - Must provide clear error messages
  
dependencies:
  - kind: system
    dependency: fastapi
  - kind: system
    dependency: fastmcp
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Implemented error handling for MCP server"
    details: "Created error handling mechanisms for MCP server"
```

### `exceptions.py`
```yaml
source_file_intent: |
  Defines exceptions for the MCP server.
  
source_file_design_principles: |
  - Clear exception hierarchy
  - Descriptive error messages
  - Consistent exception naming
  
source_file_constraints: |
  - Must maintain consistent exception naming
  - Must provide descriptive error messages
  
dependencies:
  - kind: codebase
    dependency: src/dbp/core/exceptions.py
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created exceptions for MCP server"
    details: "Defined exception classes for MCP server"
```

### `mcp_resource.py`
```yaml
source_file_intent: |
  Defines the MCPResource base class for implementing MCP resources.
  
source_file_design_principles: |
  - Clean base class for resource implementation
  - Support for parameter validation
  - Integration with FastMCP
  
source_file_constraints: |
  - Must use Pydantic for validation
  - Must integrate with FastMCP
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: system
    dependency: pydantic
  
change_history:
  - timestamp: "2025-04-27T01:51:00Z"
    summary: "Updated MCPResource for FastMCP integration"
    details: "Modified MCPResource to work with FastMCP"
```

### `mcp_tool.py`
```yaml
source_file_intent: |
  Defines the MCPTool base class for implementing MCP tools.
  
source_file_design_principles: |
  - Clean base class for tool implementation
  - Support for input/output validation
  - Support for streaming and progress reporting
  - Integration with FastMCP
  
source_file_constraints: |
  - Must use Pydantic for validation
  - Must support streaming and progress reporting
  - Must integrate with FastMCP
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: system
    dependency: pydantic
  - kind: system
    dependency: asyncio
  
change_history:
  - timestamp: "2025-04-27T02:03:00Z"
    summary: "Updated MCPTool for FastMCP integration"
    details: "Modified MCPTool to work with FastMCP"
```

### `registry.py`
```yaml
source_file_intent: |
  Implements the registry for MCP tools and resources.
  
source_file_design_principles: |
  - Clean registry implementation
  - Support for tool and resource registration
  - Thread-safe operations
  
source_file_constraints: |
  - Must be thread-safe
  - Must support dynamic registration and unregistration
  
dependencies:
  - kind: system
    dependency: fastmcp
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created registry for MCP tools and resources"
    details: "Implemented registry for MCP tools and resources"
```

### `resources.py`
```yaml
source_file_intent: |
  Implements built-in MCP resources.
  
source_file_design_principles: |
  - Clean resource implementations
  - Consistent interface
  - Clear documentation
  
source_file_constraints: |
  - Must follow MCPResource pattern
  - Must provide clear documentation
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_resource.py
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created built-in MCP resources"
    details: "Implemented built-in MCP resources"
```

### `server.py`
```yaml
source_file_intent: |
  Provides the MCPServer class that encapsulates the FastMCP server instance.
  This class is responsible for creating and managing the FastMCP instance and
  providing a clean API for server lifecycle management.
  
source_file_design_principles: |
  - Encapsulates FastMCP instance
  - Provides clean API for server lifecycle management
  - Handles server startup and shutdown
  - Maintains proper error handling and logging
  - Future developments should still use MCPTool for Pydantic validation to benefit
    from mandatory input/output schema validation. While FastMCP provides its own
    validation, using MCPTool ensures consistent validation across the codebase.
  
source_file_constraints: |
  - Must use FastMCP for MCP protocol implementation
  - Must provide clear log messages during operation
  - Must maintain proper error handling
  - Must support health endpoint
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: system
    dependency: logging
  - kind: system
    dependency: threading
  - kind: system
    dependency: time
  - kind: system
    dependency: socket
  - kind: system
    dependency: requests
  
change_history:
  - timestamp: "2025-04-27T18:56:00Z"
    summary: "Fixed server startup to use uvicorn directly by CodeAssistant"
    details: "Changed server startup to use uvicorn.run() instead of FastMCP.run()"
```

<!-- End of HSTC.md file -->
