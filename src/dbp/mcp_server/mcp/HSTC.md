# Hierarchical Semantic Tree Context: mcp

## Directory Purpose
The mcp directory contains the core implementation of the Model Context Protocol (MCP) specification for the server-side of the Documentation-Based Programming system. It provides the foundational protocol abstractions, interfaces, and utility classes required to implement a compliant MCP server. This module separates protocol concerns from server implementation details, enabling clean architecture with proper separation of interfaces from concrete implementations. The directory includes protocol definitions for tools, resources, error handling, session management, and streaming capabilities, serving as the backbone for MCP-based communication.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Package initialization for the MCP (Model Context Protocol) implementation.
  Exports all the key classes and entities for the MCP protocol to provide 
  a clean, unified interface to the rest of the codebase.
  
source_file_design_principles: |
  - Acts as a facade for all MCP protocol components
  - Provides clean imports for consumers of the MCP protocol
  - Maintains clear separation of concerns via modular imports
  - Follows standard Python package initialization patterns
  
source_file_constraints: |
  - Must re-export all necessary classes for external consumption
  - No implementation logic should be placed here
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/progress.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/cancellation.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/tool.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/resource.py
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of MCP protocol implementation directory in HSTC.md"
```

### `cancellation.py`
```yaml
source_file_intent: |
  Implements the MCPCancellationToken class for controlling cancellation of long-running MCP operations.
  Provides a mechanism for clients to signal cancellation requests and for server operations to check and respect these requests.
  
source_file_design_principles: |
  - Thread-safe cancellation state management
  - Non-blocking check mechanism
  - Clean callback registration pattern
  - Atomic operation guarantees
  
source_file_constraints: |
  - Must be thread-safe for concurrent access
  - Must handle callback errors gracefully
  - Should be lightweight with minimal overhead
  
dependencies:
  - kind: system
    dependency: threading
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of cancellation.py in HSTC.md"
```

### `error.py`
```yaml
source_file_intent: |
  Defines the error handling framework for MCP operations including error codes, error classes, and formatting utilities.
  Establishes a standardized approach to error reporting across the MCP implementation.
  
source_file_design_principles: |
  - Comprehensive error code enumeration
  - Hierarchical exception structure
  - Consistent error message formatting
  - Protocol-compliant error responses
  
source_file_constraints: |
  - Must align with MCP protocol error specifications
  - Must provide informative but secure error information
  - Should be extensible for specialized error types
  
dependencies:
  - kind: system
    dependency: enum
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of error.py in HSTC.md"
```

### `negotiation.py`
```yaml
source_file_intent: |
  Implements the capability negotiation protocol for MCP, allowing clients and servers to discover
  and agree on supported features, protocol versions, and extensions.
  
source_file_design_principles: |
  - Data-driven capability discovery
  - Version compatibility checks
  - Feature matching algorithms
  - Graceful degradation support
  
source_file_constraints: |
  - Must handle protocol versioning correctly
  - Must support both mandatory and optional capabilities
  - Should prioritize backward compatibility
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of negotiation.py in HSTC.md"
```

### `progress.py`
```yaml
source_file_intent: |
  Implements the MCPProgressReporter class for reporting progress updates during long-running MCP operations.
  Allows tools to provide real-time feedback on operation completion percentage and status.
  
source_file_design_principles: |
  - Thread-safe progress reporting
  - Standardized progress format
  - Optional message context
  - Throttled update mechanism
  
source_file_constraints: |
  - Must be thread-safe for concurrent updates
  - Should avoid excessive progress updates
  - Must handle callback errors gracefully
  
dependencies:
  - kind: system
    dependency: time
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of progress.py in HSTC.md"
```

### `resource.py`
```yaml
source_file_intent: |
  Defines the MCPResource protocol and base implementations for serving static and dynamic resources through the MCP protocol.
  Establishes the contract for resource providers and consumers.
  
source_file_design_principles: |
  - Clean protocol interface definition
  - Content type handling
  - URI-based resource identification
  - Standardized response format
  
source_file_constraints: |
  - Must align with MCP protocol resource specifications
  - Must handle large resources efficiently
  - Should support content negotiation
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: system
    dependency: typing
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of resource.py in HSTC.md"
```

### `session.py`
```yaml
source_file_intent: |
  Implements the MCP session management system that maintains conversational context
  across multiple requests between clients and the MCP server.
  
source_file_design_principles: |
  - Stateful session tracking
  - Secure session identification
  - Session expiration and cleanup
  - Context preservation across requests
  
source_file_constraints: |
  - Must maintain session security
  - Must handle concurrent session access
  - Should manage resource cleanup on expiration
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: system
    dependency: uuid
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of session.py in HSTC.md"
```

### `streaming.py`
```yaml
source_file_intent: |
  Implements the streaming response abstractions for MCP, allowing for real-time data transmission
  from server to client for progressive results and ongoing operations.
  
source_file_design_principles: |
  - Asynchronous stream handling
  - Event-based notification pattern
  - Backpressure management
  - Connection lifecycle awareness
  
source_file_constraints: |
  - Must handle network interruptions gracefully
  - Should implement proper flow control
  - Must support asynchronous operation
  
dependencies:
  - kind: system
    dependency: asyncio
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of streaming.py in HSTC.md"
```

### `streaming_tool.py`
```yaml
source_file_intent: |
  Extends the MCP tool framework with streaming capabilities, allowing tools to provide 
  incremental results to clients and enabling real-time feedback during long operations.
  
source_file_design_principles: |
  - Builds on core tool abstractions
  - Async streaming response handling
  - Incremental result delivery
  - Stream lifecycle management
  
source_file_constraints: |
  - Must maintain protocol compatibility
  - Must handle stream interruptions
  - Should provide clean error handling for streams
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/tool.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/streaming.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: system
    dependency: asyncio
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of streaming_tool.py in HSTC.md"
```

### `tool.py`
```yaml
source_file_intent: |
  Defines the MCPTool protocol interface and base implementations for creating executable
  tools that can be invoked by clients through the MCP protocol.
  
source_file_design_principles: |
  - Clean protocol interface definition
  - Schema-based input validation
  - Standardized response format
  - Error handling patterns
  
source_file_constraints: |
  - Must align with MCP protocol tool specifications
  - Must enforce schema validation
  - Should support cancellation for long-running operations
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/error.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/cancellation.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/progress.py
  - kind: system
    dependency: typing
  - kind: system
    dependency: json
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-26T00:36:51Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of tool.py in HSTC.md"
