# FastMCP Integration Implementation Plan

## Overview

This document outlines the plan for replacing the homemade MCP server implementation with the fastmcp library. The goal is to achieve the best integration possible with fastmcp while preserving the existing FastAPI usage and health route.

## Implementation Strategy

The implementation follows these principles:

1. **Complete Replacement**: Remove all homemade MCP implementation code.
2. **Preserve FastAPI Integration**: Maintain the existing health route and FastAPI setup.
3. **Maintain Component Architecture**: Keep the MCPServerComponent for lifecycle management.
4. **No Backward Compatibility**: As specified, we do not maintain backward compatibility with the old implementation.

## Implementation Steps

### 1. Create MCPServer Class

Create a new `MCPServer` class in `src/dbp/mcp_server/server.py` that:

- Encapsulates the FastMCP instance
- Provides methods for server lifecycle management
- Handles server startup and shutdown
- Maintains proper error handling and logging
- Adds a health endpoint to the FastAPI app

Design decisions:
- Future developments should still use MCPTool for Pydantic validation to benefit from mandatory input/output schema validation.

### 2. Update MCPServerComponent

Update the `MCPServerComponent` class in `src/dbp/mcp_server/component.py` to:

- Use the new `MCPServer` class
- Remove `register_mcp_tool` and `register_mcp_resource` methods (use fastmcp decorators directly)
- Call `MCPServer.start()` during initialization
- Remove `start_server()` method
- Add `wait_for_server_exit()` method for `__main__.py` to wait indefinitely for HTTP server exit
- Simplify the component implementation

### 3. Update __main__.py

Update `src/dbp/mcp_server/__main__.py` to:

- Use the new `wait_for_server_exit()` method instead of `start_server()`

### 4. Delete Former MCP Protocol Implementation Files

Delete the following files that are part of the homemade MCP implementation:

#### Server-side files:
- `src/dbp/mcp_server/mcp/progress.py`
- `src/dbp/mcp_server/mcp/cancellation.py`
- `src/dbp/mcp_server/mcp/negotiation.py`
- `src/dbp/mcp_server/mcp/session.py`
- `src/dbp/mcp_server/mcp/streaming.py`
- `src/dbp/mcp_server/mcp/streaming_tool.py`
- `src/dbp/mcp_server/mcp/__init__.py`
- `src/dbp/mcp_server/mcp/error.py`
- `src/dbp/mcp_server/mcp/tool.py`
- `src/dbp/mcp_server/mcp/resource.py`
- `src/dbp/mcp_server/mcp_protocols.py`

#### Client-side files:
- `src/dbp_cli/mcp/__init__.py`
- `src/dbp_cli/mcp/error.py`
- `src/dbp_cli/mcp/client.py`
- `src/dbp_cli/mcp/tool_client.py`
- `src/dbp_cli/mcp/resource_client.py`
- `src/dbp_cli/mcp/negotiation.py`
- `src/dbp_cli/mcp/session.py`
- `src/dbp_cli/mcp/streaming.py`

### 5. Update Example Files

Update the example files to use the new FastMCP implementation:

- `src/dbp/mcp_server/examples/sample_streaming_tool.py`
- `src/dbp/mcp_server/examples/streaming_client_example.py`

### 6. Update Dependencies

Update the project dependencies to include fastmcp:

- Add `fastmcp>=2.0.0` to `requirements.txt`

## Testing Plan

1. **Unit Tests**:
   - Test MCPServer class
   - Test MCPServerComponent class

2. **Integration Tests**:
   - Test server startup and shutdown
   - Test health endpoint
   - Test tool registration and execution
   - Test resource registration and access

3. **End-to-End Tests**:
   - Test client-server communication
   - Test streaming functionality
   - Test error handling

## Migration Guide

Create a migration guide for developers to help them transition from the homemade MCP implementation to FastMCP:

1. **For Tool Developers**:
   - How to use FastMCP decorators for tool registration
   - How to handle tool execution

2. **For Resource Developers**:
   - How to use FastMCP decorators for resource registration
   - How to handle resource access

3. **For Client Developers**:
   - How to use the FastMCP client
   - How to handle client-server communication

## Timeline

1. **Phase 1 (Week 1)**:
   - Create MCPServer class
   - Update MCPServerComponent class
   - Update __main__.py

2. **Phase 2 (Week 2)**:
   - Delete former MCP protocol implementation files
   - Update example files
   - Update dependencies

3. **Phase 3 (Week 3)**:
   - Testing
   - Documentation
   - Migration guide

## Risks and Mitigations

1. **Risk**: Breaking existing tools and resources
   **Mitigation**: Thorough testing and providing a clear migration guide

2. **Risk**: Performance issues with FastMCP
   **Mitigation**: Performance testing and optimization

3. **Risk**: Compatibility issues with FastAPI
   **Mitigation**: Thorough testing of FastAPI integration
