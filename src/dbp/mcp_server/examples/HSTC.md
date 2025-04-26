# Hierarchical Semantic Tree Context: examples

## Directory Purpose
The examples directory provides reference implementations and sample code for using the Model Context Protocol (MCP) server capabilities. It contains working demonstrations that showcase the MCP functionality, particularly focused on streaming features and client-server interactions. These examples serve as educational resources for developers implementing their own MCP tools and clients, and can be used for testing and validation of the MCP protocol implementation. The code here emphasizes best practices in MCP development while providing concrete patterns that developers can adapt for their own applications.

## Local Files

### `sample_streaming_tool.py`
```yaml
source_file_intent: |
  Provides a sample implementation of a streaming-capable MCP tool.
  This serves as an example and reference for creating custom streaming tools.
  
source_file_design_principles: |
  - Demonstrates proper MCPStreamingTool implementation pattern
  - Shows how to yield data chunks incrementally
  - Includes examples for different streaming scenarios
  - Handles cancellation and progress reporting
  
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
    dependency: src/dbp/mcp_server/mcp/streaming_tool.py
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/streaming.py
  
change_history:
  - timestamp: "2025-04-26T00:39:06Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of sample_streaming_tool.py in HSTC.md"
```

### `streaming_client_example.py`
```yaml
source_file_intent: |
  Demonstrates how to implement a client that interacts with streaming MCP tools.
  Provides a complete working example of consuming streaming data from MCP servers.
  
source_file_design_principles: |
  - Shows proper client connection setup
  - Demonstrates streaming data consumption patterns
  - Handles streaming errors and interruptions
  - Implements progress tracking and cancellation
  
source_file_constraints: |
  - For demonstration purposes only, not for production use
  - Contains simplified error handling for clarity
  
dependencies:
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: aiohttp
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp/streaming.py
  - kind: codebase
    dependency: src/dbp_cli/mcp/streaming.py
  
change_history:
  - timestamp: "2025-04-26T00:39:06Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of streaming_client_example.py in HSTC.md"
