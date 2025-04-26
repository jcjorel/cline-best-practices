# FastMCP Integration

This directory contains a sample implementation for replacing the homemade MCP server implementation with the fastmcp library. The goal is to achieve the best integration possible with fastmcp while preserving the existing FastAPI usage and health route.

## Overview

The implementation consists of the following components:

1. **Component Implementation** (`component.py`): A replacement for the MCPServerComponent class that uses FastMCP internally.
2. **Adapters** (`adapters.py`): Functions to convert existing MCPTool objects and resource handlers to fastmcp-compatible functions.
3. **Client Implementation** (`client.py`): A replacement for the MCPClient class that uses fastmcp's Client class internally.

## Integration Strategy

The integration follows these principles:

1. **Complete Replacement**: Remove all homemade MCP implementation code.
2. **Preserve FastAPI Integration**: Maintain the existing health route and FastAPI setup.
3. **Maintain Component Architecture**: Keep the MCPServerComponent for lifecycle management.
4. **No Backward Compatibility**: As specified, we do not maintain backward compatibility with the old implementation.

## Implementation Details

### Component Implementation

The `MCPServerComponent` class in `component.py` maintains the same interface as the original component but uses FastMCP internally. It:

- Creates a FastMCP instance during initialization
- Adds a health endpoint to the FastAPI app
- Provides methods for starting and stopping the server
- Adapts existing tools and resources to work with fastmcp

### Adapters

The `adapters.py` file provides functions to convert existing MCPTool objects and resource handlers to fastmcp-compatible functions:

- `adapt_mcp_tool`: Converts an MCPTool object to a fastmcp tool function
- `adapt_mcp_resource`: Converts a resource handler to a fastmcp resource function

These adapters handle both synchronous and asynchronous execution, and maintain proper error handling.

### Client Implementation

The `client.py` file provides a replacement for the MCPClient class that uses fastmcp's Client class internally. It:

- Maintains the same interface as the original MCPClient
- Uses fastmcp's Client for MCP protocol implementation
- Handles both synchronous and asynchronous execution
- Maintains proper error handling

## Usage

### Server Side

To use the new implementation, replace the existing MCPServerComponent with the one provided in this directory:

```python
# Import the new component
from src.dbp.mcp_server.component import MCPServerComponent

# Create and initialize the component
component = MCPServerComponent()
component.initialize(context)

# Start the server
component.start_server()
```

### Client Side

To use the new client implementation, replace the existing MCPClient with the one provided in this directory:

```python
# Import the new client
from src.dbp_cli.mcp.client import MCPClient

# Create a client
client = MCPClient("http://localhost:8000")

# Call a tool
result = await client.call_tool("my_tool", {"param1": "value1"})

# Read a resource
resource = await client.read_resource("my://resource/123")
```

## Migration Guide

### For Tool Developers

1. **Existing MCPTool Classes**: These will be adapted automatically to work with fastmcp.
2. **New Tools**: Use the fastmcp decorator syntax directly:

```python
@mcp.tool()
def my_tool(param1: str, param2: int) -> dict:
    """Tool description"""
    # Implementation
    return {"result": "success"}
```

### For Resource Developers

1. **Existing Resource Handlers**: These will be adapted automatically to work with fastmcp.
2. **New Resources**: Use the fastmcp decorator syntax directly:

```python
@mcp.resource("my://resource/{id}")
def my_resource(id: str, param1: str = None) -> dict:
    """Resource description"""
    # Implementation
    return {"id": id, "data": "value"}
```

### For Client Developers

1. **Existing Client Code**: Update imports to use the new client implementation.
2. **New Client Code**: Use the fastmcp client directly:

```python
from fastmcp import Client

async with Client("http://localhost:8000") as client:
    result = await client.call_tool("my_tool", {"param1": "value", "param2": 42})
    resource = await client.read_resource("my://resource/123")
```

## Dependencies

- fastmcp >= 2.0.0
- pydantic
- fastapi
- uvicorn
- asyncio

## Implementation Plan

For a detailed implementation plan, see the `fastmcp_integration_plan.md` file in the parent directory.
