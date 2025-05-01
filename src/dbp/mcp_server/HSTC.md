# Hierarchical Semantic Tree Context: mcp_server

## Directory Purpose
This directory implements the Model Context Protocol (MCP) server component for the DBP system, providing a standardized interface for large language model (LLM) interactions through tools and resources. The MCP server enables LLMs to access external capabilities like data retrieval, file operations, specialized processing, and API integrations. It uses the FastMCP library to ensure protocol compliance while maintaining a clean Component-based architecture. The implementation includes authentication, request validation, error handling, and extensibility through a tool/resource registration system that allows other components to provide domain-specific functionality to LLMs.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports MCP server classes and functions for use throughout the DBP system.
  
source_file_design_principles: |
  - Provides clean imports for MCP server classes
  - Maintains hierarchical package structure
  - Prevents circular imports
  
source_file_constraints: |
  - Should only export necessary classes and functions
  - Must not contain implementation logic
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-15T09:00:00Z"
    summary: "Initial creation of mcp_server package"
    details: "Created __init__.py with exports for key MCP server classes"
```

### `__main__.py`
```yaml
source_file_intent: |
  Provides an entry point for running the MCP server as a standalone application.
  It initializes the server component and waits for server shutdown.
  
source_file_design_principles: |
  - Simple entry point for standalone server execution
  - Proper initialization and shutdown handling
  - Command-line argument processing
  - Clear error messaging
  
source_file_constraints: |
  - Must handle initialization errors gracefully
  - Must support proper process termination
  - Should allow configurable server parameters via CLI args
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/component.py
  
change_history:
  - timestamp: "2025-04-27T00:17:00Z"
    summary: "Updated main entry point for FastMCP integration"
    details: "Changed server start method to wait_for_server_exit() to match new FastMCP-based implementation"
```

### `adapter.py`
```yaml
source_file_intent: |
  Implements adapter classes that bridge between the FastMCP library and DBP system components,
  ensuring seamless integration while maintaining separation of concerns.
  
source_file_design_principles: |
  - Adapter pattern for integrating external libraries
  - Clean separation between FastMCP and DBP
  - Consistent error handling and logging
  - Simple interface for FastMCP interaction
  
source_file_constraints: |
  - Must handle FastMCP versioning correctly
  - Must maintain backward compatibility
  - Should minimize coupling with FastMCP internals
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: codebase
    dependency: src/dbp/mcp_server/data_models.py
  
change_history:
  - timestamp: "2025-04-27T00:16:00Z"
    summary: "Created adapter for FastMCP integration"
    details: "Implemented adapter classes for FastMCP integration with the DBP system"
```

### `auth.py`
```yaml
source_file_intent: |
  Implements authentication and authorization mechanisms for the MCP server,
  including API key management, permission checking, and secure header handling.
  
source_file_design_principles: |
  - Simple yet secure authentication
  - Configuration-driven API key management
  - Permission-based authorization model
  - Clean separation of authentication and authorization concerns
  
source_file_constraints: |
  - Must securely handle API keys
  - Must integrate with FastMCP authentication system
  - Must provide clear authorization failures
  - Should support flexible permission models
  
dependencies:
  - kind: system
    dependency: fastmcp.auth
  
change_history:
  - timestamp: "2025-04-27T00:18:00Z"
    summary: "Updated authentication for FastMCP"
    details: "Modified authentication mechanisms to work with FastMCP's authentication system"
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
    summary: "Updated ComponentNotInitializedError import"
    details: "Removed local ComponentNotInitializedError class definition, added import for ComponentNotInitializedError from core.exceptions, improved code organization by using centralized exception definitions"
  - timestamp: "2025-04-27T00:16:00Z"
    summary: "Replaced homemade MCP implementation with FastMCP"
    details: "Completely replaced the homemade MCP implementation with FastMCP, removed register_mcp_tool and register_mcp_resource methods, modified component to use MCPServer class from server.py, added wait_for_server_exit() method for __main__.py, removed start_server() method, simplified component implementation"
  - timestamp: "2025-04-26T02:05:00Z"
    summary: "Removed _register_resources method"
    details: "Removed _register_resources method as resources are registered by external components, updated initialization to no longer call _register_resources, made code more compliant with the distributed MCP resource registration concept"
  - timestamp: "2025-04-26T02:00:00Z"
    summary: "Removed _register_tools method"
    details: "Removed _register_tools method as it's not needed - tools are registered by external components, updated initialization to no longer call _register_tools, made code more compliant with the distributed MCP tool registration concept"
```

### `data_models.py`
```yaml
source_file_intent: |
  Defines data models for MCP protocol requests, responses, and errors,
  ensuring type safety and consistent structure throughout the MCP server.
  
source_file_design_principles: |
  - Pydantic models for type safety and validation
  - Clear separation of request, response, and error models
  - Consistent structure aligned with MCP protocol standards
  - Serialization and deserialization support
  
source_file_constraints: |
  - Must conform to MCP protocol specification
  - Must support JSON serialization/deserialization
  - Must provide clear validation errors
  - Should be compatible with FastAPI/Pydantic
  
dependencies:
  - kind: system
    dependency: pydantic
  - kind: system
    dependency: fastmcp.models
  
change_history:
  - timestamp: "2025-04-27T00:19:00Z"
    summary: "Updated data models for FastMCP compatibility"
    details: "Modified data models to ensure compatibility with FastMCP's model structure and validation requirements"
```

### `error_handler.py`
```yaml
source_file_intent: |
  Implements error handling mechanisms for the MCP server, converting exceptions
  into standardized error responses according to the MCP protocol specification.
  
source_file_design_principles: |
  - Consistent error response format
  - Detailed error information for debugging
  - Clean error category mapping
  - Centralized error handling logic
  
source_file_constraints: |
  - Must map application exceptions to MCP error codes
  - Must sanitize sensitive information in errors
  - Must provide useful error messages
  - Should support structured logging of errors
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/data_models.py
  - kind: codebase
    dependency: src/dbp/mcp_server/exceptions.py
  
change_history:
  - timestamp: "2025-04-27T00:20:00Z"
    summary: "Updated error handling for FastMCP"
    details: "Modified error handler to integrate with FastMCP's error handling mechanisms"
```

### `exceptions.py`
```yaml
source_file_intent: |
  Defines custom exceptions specific to the MCP server operations,
  providing clear error categorization and context for better error handling.
  
source_file_design_principles: |
  - Hierarchical exception structure
  - Specific exception types for different error scenarios
  - Error code and message standardization
  - Integration with MCP protocol error model
  
source_file_constraints: |
  - Must provide meaningful error messages
  - Must map cleanly to MCP protocol error codes
  - Should include context information where relevant
  
dependencies:
  - kind: system
    dependency: fastmcp.exceptions
  
change_history:
  - timestamp: "2025-04-27T00:21:00Z"
    summary: "Updated exceptions for FastMCP integration"
    details: "Modified exceptions to align with FastMCP's exception hierarchy and error handling mechanisms"
```

### `mcp_resource.py`
```yaml
source_file_intent: |
  Defines the MCPResource base class that all MCP resources must implement,
  providing a standardized interface and lifecycle management for resources.
  
source_file_design_principles: |
  - Abstract base class for consistent resource interface
  - Clear resource identification and metadata
  - Standardized resource initialization and access
  - Integration with FastMCP resource system
  
source_file_constraints: |
  - Must be compatible with FastMCP resource model
  - Must support URI-based resource identification
  - Must handle resource initialization errors gracefully
  
dependencies:
  - kind: system
    dependency: fastmcp.resource
  - kind: codebase
    dependency: src/dbp/mcp_server/exceptions.py
  
change_history:
  - timestamp: "2025-04-27T00:22:00Z"
    summary: "Updated MCPResource for FastMCP"
    details: "Modified MCPResource to extend FastMCP's resource base class while maintaining the original interface"
```

### `mcp_tool.py`
```yaml
source_file_intent: |
  Defines the MCPTool base class that all MCP tools must implement,
  providing a standardized interface and lifecycle management for tools.
  
source_file_design_principles: |
  - Abstract base class for consistent tool interface
  - Clear tool identification and metadata
  - Schema-based input/output validation
  - Integration with FastMCP tool system
  
source_file_constraints: |
  - Must be compatible with FastMCP tool model
  - Must support input schema validation
  - Must handle tool execution errors gracefully
  
dependencies:
  - kind: system
    dependency: fastmcp.tool
  - kind: codebase
    dependency: src/dbp/mcp_server/exceptions.py
  
change_history:
  - timestamp: "2025-04-27T00:23:00Z"
    summary: "Updated MCPTool for FastMCP"
    details: "Modified MCPTool to extend FastMCP's tool base class while maintaining the original interface"
```

### `registry.py`
```yaml
source_file_intent: |
  Implements the registry for MCP tools and resources, providing a central
  lookup system for managing and accessing registered capabilities.
  
source_file_design_principles: |
  - Singleton registry pattern
  - Thread-safe registration and lookup
  - Validation of tool/resource compliance
  - Clean API for registration and discovery
  
source_file_constraints: |
  - Must handle concurrent registration safely
  - Must validate tool/resource conformance
  - Must prevent duplicate registrations
  - Should provide efficient lookup mechanisms
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_tool.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_resource.py
  - kind: codebase
    dependency: src/dbp/mcp_server/exceptions.py
  
change_history:
  - timestamp: "2025-04-27T00:24:00Z"
    summary: "Updated registry for FastMCP"
    details: "Modified registry to work with FastMCP's registration mechanisms"
```

### `resources.py`
```yaml
source_file_intent: |
  Implements standard MCP resources provided by the server,
  including health, version, and capability information.
  
source_file_design_principles: |
  - Standard resource implementations
  - Consistent resource access patterns
  - Clean separation of resource logic
  - Integration with system components
  
source_file_constraints: |
  - Must follow MCPResource interface
  - Must provide accurate system information
  - Should be efficiently implemented
  - Resources should be stateless where possible
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_resource.py
  - kind: codebase
    dependency: src/dbp/mcp_server/registry.py
  
change_history:
  - timestamp: "2025-04-27T00:25:00Z"
    summary: "Updated standard resources for FastMCP"
    details: "Modified standard resources to use FastMCP's resource model and API"
```

### `server.py`
```yaml
source_file_intent: |
  Implements the main MCPServer class that creates and manages the FastMCP server instance,
  handling server lifecycle, configuration, and integration with the Component system.
  
source_file_design_principles: |
  - Clean server lifecycle management
  - FastMCP integration with DBP component system
  - Configuration-driven server setup
  - Robust error handling and recovery
  
source_file_constraints: |
  - Must handle server startup/shutdown gracefully
  - Must provide clear status information
  - Must integrate seamlessly with FastMCP
  - Should support runtime configuration updates
  
dependencies:
  - kind: system
    dependency: fastmcp
  - kind: system
    dependency: fastmcp.server
  - kind: codebase
    dependency: src/dbp/mcp_server/adapter.py
  
change_history:
  - timestamp: "2025-04-27T00:26:00Z"
    summary: "Created MCPServer using FastMCP"
    details: "Implemented MCPServer class that wraps FastMCP's server functionality and integrates with the DBP component system"
```

## Child Directories

### examples
This directory contains example MCP tool and resource implementations that demonstrate proper usage patterns and integration techniques. It serves as a reference for developers creating new tools and resources, providing working examples of different capability types, input/output patterns, and error handling approaches. These examples are not used in production but are valuable for understanding the MCP protocol implementation and extension points.

### internal_tools
This directory implements internal MCP tools used by the DBP system for various functions such as visualization, document analysis, and system monitoring. These tools are specifically designed for internal use by DBP components rather than being general-purpose extensions. They provide specialized functionality that supports core DBP features while following the MCP tool interface for consistency and modularity.

End of HSTC.md file
