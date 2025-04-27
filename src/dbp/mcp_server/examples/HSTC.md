# Hierarchical Semantic Tree Context: examples

## Directory Purpose
This directory contains example implementations of MCP tools and resources for demonstration and reference purposes. It serves as a practical guide for developers creating custom MCP tools and resources using the unified API. The examples demonstrate proper implementation patterns, including streaming capabilities, progress reporting, cancellation handling, and parameter validation using Pydantic models.

## Child Directories
<!-- No child directories with HSTC.md -->

## Local Files

### `example_tool.py`
```yaml
source_file_intent: |
  Provides an example implementation of an MCP tool using the MCPTool base class.
  This serves as a reference for creating custom MCP tools with the unified API.
  
source_file_design_principles: |
  - Demonstrates proper MCPTool implementation pattern
  - Shows how to implement both execute and stream methods
  - Includes examples for progress reporting and cancellation handling
  - Demonstrates how to register the tool with FastMCP
  
source_file_constraints: |
  - For demonstration purposes only, not for production use
  - Does not perform any actual meaningful operations
  
dependencies:
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  - kind: system
    dependency: pydantic
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_tool.py
  
change_history:
  - timestamp: "2025-04-27T00:41:00Z"
    summary: "Created example tool implementation by CodeAssistant"
    details: "Implemented ExampleTool class using MCPTool base class"
```

### `example_resource.py`
```yaml
source_file_intent: |
  Provides an example implementation of an MCP resource using the MCPResource base class.
  This serves as a reference for creating custom MCP resources with the unified API.
  
source_file_design_principles: |
  - Demonstrates proper MCPResource implementation pattern
  - Shows how to implement the get_content method
  - Includes examples for context handling
  - Demonstrates how to register the resource with FastMCP
  
source_file_constraints: |
  - For demonstration purposes only, not for production use
  - Does not perform any actual meaningful operations
  
dependencies:
  - kind: system
    dependency: typing
  - kind: system
    dependency: pydantic
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_resource.py
  
change_history:
  - timestamp: "2025-04-27T01:27:00Z"
    summary: "Created example resource implementation by CodeAssistant"
    details: "Implemented ExampleResource class using MCPResource base class"
```

### `sample_streaming_tool.py`
```yaml
source_file_intent: |
  Provides a sample implementation of a streaming MCP tool that demonstrates
  advanced streaming capabilities and progress reporting.
  
source_file_design_principles: |
  - Focuses on streaming implementation best practices
  - Shows how to handle streaming with progress updates
  - Demonstrates cancellation handling in streaming context
  
source_file_constraints: |
  - For demonstration purposes only, not for production use
  - Does not perform any actual meaningful operations
  
dependencies:
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  - kind: system
    dependency: pydantic
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_tool.py
  
change_history:
  - timestamp: "2025-04-27T00:22:00Z"
    summary: "Created sample streaming tool implementation by CodeAssistant"
    details: "Implemented streaming functionality with progress reporting"
```

### `streaming_client_example.py`
```yaml
source_file_intent: |
  Demonstrates how to use the MCP client to interact with streaming tools,
  including handling progress updates and cancellation.
  
source_file_design_principles: |
  - Shows client-side streaming consumption patterns
  - Demonstrates progress handling and cancellation from client side
  - Provides complete working examples for client integration
  
source_file_constraints: |
  - For demonstration purposes only, not for production use
  - Requires a running MCP server with the sample tools registered
  
dependencies:
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  - kind: codebase
    dependency: src/dbp_cli/mcp/client.py
  
change_history:
  - timestamp: "2025-04-25T23:40:00Z"
    summary: "Created streaming client example by CodeAssistant"
    details: "Implemented client-side streaming consumption examples"
```

<!-- End of HSTC.md file -->
