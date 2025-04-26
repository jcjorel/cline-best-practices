# FastMCP Integration Plan

## Overview

This document outlines the implementation plan for replacing the current homemade MCP server implementation with the fastmcp library. The goal is to achieve the best integration possible with fastmcp while preserving the existing FastAPI usage and health route.

## Current Architecture

The current MCP implementation consists of:

1. **MCPServer class** (`src/dbp/mcp_server/server.py`): Handles HTTP server setup, route registration, and MCP protocol implementation.
2. **MCPServerComponent class** (`src/dbp/mcp_server/component.py`): Manages the server lifecycle within the component system.
3. **MCP Protocol Implementation** (`src/dbp/mcp_server/mcp/`): Contains the core MCP protocol classes and utilities.
4. **Client Implementation** (`src/dbp_cli/mcp/`): Provides client-side functionality for interacting with MCP servers.

## FastMCP Architecture

FastMCP provides:

1. **FastMCP class**: A high-level, decorator-based API for creating MCP servers.
2. **Tool and Resource Registration**: Simple decorators for registering tools and resources.
3. **Transport Options**: Support for various transport protocols (SSE, WebSockets, etc.).
4. **FastAPI Integration**: Built on FastAPI for HTTP server functionality.

## Integration Strategy

The integration will follow these principles:

1. **Complete Replacement**: Remove all homemade MCP implementation code.
2. **Preserve FastAPI Integration**: Maintain the existing health route and FastAPI setup.
3. **Maintain Component Architecture**: Keep the MCPServerComponent for lifecycle management.
4. **No Backward Compatibility**: As specified, we will not maintain backward compatibility with the old implementation.

## Implementation Plan

### Phase 1: Core Server Implementation

#### 1.1. Update Dependencies

Add fastmcp to the project dependencies:

```python
# setup.py or requirements.txt
"fastmcp>=2.0.0"
```

#### 1.2. Replace MCPServer Class

Create a new implementation of the MCPServer class that uses FastMCP internally:

```python
# src/dbp/mcp_server/server.py
from fastmcp import FastMCP
import logging
from typing import Dict, Any, Optional, List

class MCPServer:
    """
    [Class intent]
    Implements the MCP server using the fastmcp library, providing a FastAPI-based
    HTTP server with MCP protocol support.
    
    [Design principles]
    - Uses fastmcp for MCP protocol implementation
    - Maintains FastAPI integration for HTTP server
    - Provides clean API for server lifecycle management
    - Supports health endpoint for monitoring
    
    [Implementation details]
    - Wraps FastMCP instance for MCP protocol handling
    - Configures FastAPI/Uvicorn for HTTP server
    - Exposes API for server lifecycle management
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        description: str,
        version: str,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        [Function intent]
        Initializes the MCPServer with fastmcp integration.
        
        [Design principles]
        Minimal dependencies for fast initialization.
        Clean separation of server configuration from runtime behaviors.
        
        [Implementation details]
        Creates a FastMCP instance with the provided configuration.
        Sets up FastAPI with the health endpoint.
        
        Args:
            host: Host address to bind to
            port: Port number to listen on
            name: Server name
            description: Server description
            version: Server version
            logger_override: Optional logger instance
        """
        self.host = host
        self.port = port
        self.name = name
        self.description = description
        self.version = version
        self.logger = logger_override or logging.getLogger(__name__)
        
        # Create FastMCP instance
        self._mcp = FastMCP(
            name=name,
            description=description,
            version=version
        )
        
        # Add health endpoint
        @self._mcp.app.get("/health")
        async def health_check():
            """Health check endpoint for the MCP server."""
            # Get initialization status
            init_status = getattr(self, '_init_status', {})
            startup_time = getattr(self, '_startup_time', None)
            
            # Calculate uptime if server has finished initialization
            uptime = None
            if startup_time:
                import time
                uptime = time.time() - startup_time

            # Determine overall status based on initialization state
            status = init_status.get('state', 'initializing')
            
            return {
                "status": status,
                "server": self.name,
                "version": self.version,
                "uptime": uptime,
                "initialization": {
                    "state": init_status.get('state', 'initializing'),
                    "current_step": init_status.get('current_step'),
                    "total_steps": init_status.get('total_steps'),
                    "message": init_status.get('message'),
                    "completed_steps": init_status.get('completed_steps', []),
                    "error": init_status.get('error')
                }
            }
        
        self._is_running = False
        self.logger.debug(f"MCPServer '{self.name}' v{self.version} initialized.")

    def start(self):
        """
        [Function intent]
        Starts the MCP server in a background thread.
        
        [Design principles]
        Non-blocking server startup.
        Clear logging of server state.
        
        [Implementation details]
        Uses fastmcp's run method with the appropriate transport.
        Sets server state flags.
        """
        if self._is_running:
            self.logger.warning(f"MCP Server '{self.name}' is already running.")
            return

        self.logger.info(f"Starting MCP server '{self.name}' on {self.host}:{self.port}...")
        
        # Configure server
        config = getattr(self, 'config', {})
        
        # Start the server in a background thread
        import threading
        self._server_thread = threading.Thread(
            target=lambda: self._mcp.run(
                host=self.host,
                port=self.port,
                workers=config.get("workers", 1),
                transport="sse",  # Use SSE transport by default
                log_level="info"
            ),
            daemon=True
        )
        self._server_thread.start()
        self._is_running = True
        
        # Record startup time for uptime calculation
        import time
        self._startup_time = time.time()
        
        self.logger.info(f"MCP Server '{self.name}' started.")

    def stop(self):
        """
        [Function intent]
        Stops the MCP server.
        
        [Design principles]
        Clean server shutdown.
        Clear logging of server state.
        
        [Implementation details]
        Signals the server to stop and waits for thread completion.
        Resets server state flags.
        """
        if not self._is_running:
            self.logger.warning(f"MCP Server '{self.name}' is not running.")
            return

        self.logger.info(f"Stopping MCP server '{self.name}'...")
        
        # Signal the server to stop
        # Note: FastMCP doesn't provide a direct stop method, so we'll need to
        # implement a custom shutdown mechanism
        
        # For now, we'll just set the flag and let the thread exit naturally
        self._is_running = False
        
        # Wait for server thread to exit
        if self._server_thread and self._server_thread.is_alive():
            self.logger.debug("Waiting for server thread to exit...")
            self._server_thread.join(timeout=10.0)  # Wait for thread
            if self._server_thread.is_alive():
                self.logger.warning("Server thread did not exit cleanly.")

        self._server_thread = None
        self.logger.info(f"MCP Server '{self.name}' stopped.")

    @property
    def is_running(self) -> bool:
        """Checks if the server is currently running."""
        return self._is_running

    def _update_init_status(self, step: str, message: str, error: str = None):
        """
        [Function intent]
        Updates the initialization status of the server for health endpoint reporting.
        
        [Design principles]
        Detailed status tracking for monitoring and troubleshooting.
        Progressive step tracking to show initialization progress.
        
        [Implementation details]
        Updates the internal status dictionary with current state.
        Tracks completed steps and current progress.
        Maintains error information when problems occur.
        
        Args:
            step: Current initialization step identifier
            message: Human-readable message about the current step
            error: Optional error message if the step failed
        """
        if not hasattr(self, '_init_status'):
            self._init_status = {}
            
        # If we're given a step name, track it as the current step
        if step:
            # If we're moving to a new step, add the previous step to completed_steps
            if 'current_step' in self._init_status and self._init_status['current_step'] != step:
                if not 'completed_steps' in self._init_status:
                    self._init_status['completed_steps'] = []
                if self._init_status['current_step'] not in ['failed', 'ready']:  # Don't add terminal states
                    self._init_status['completed_steps'].append(self._init_status['current_step'])
            
            self._init_status['current_step'] = step
                
        # Update the state based on the step
        if step == 'ready':
            self._init_status['state'] = 'healthy'
            self.logger.info(f"=== MCP SERVER READY ===")
            self.logger.info(f"MCP server is now ready to serve HTTP requests on {self.host}:{self.port}")
            self.logger.info(f"======================")
        elif step == 'failed':
            self._init_status['state'] = 'failed'
        else:
            self._init_status['state'] = 'initializing'
            
        # Always update the message if provided
        if message:
            self._init_status['message'] = message
            
        # Add error information if provided
        if error:
            self._init_status['error'] = error
            
        # Log the status update
        if error:
            self.logger.error(f"Server initialization status: {step} - {message} - ERROR: {error}")
        else:
            self.logger.info(f"Server initialization status: {step} - {message}")

    def register_router(self, router):
        """
        [Function intent]
        Registers a FastAPI router with the server.
        
        [Design principles]
        Maintains compatibility with existing FastAPI usage.
        
        [Implementation details]
        Delegates to FastMCP's app.include_router method.
        
        Args:
            router: FastAPI router to register
            prefix: Optional prefix for the router
        """
        self._mcp.app.include_router(router)
        self.logger.debug(f"Router registered")

    def register_get_route(self, path, handler, **kwargs):
        """
        [Function intent]
        Registers a GET route handler with the server.
        
        [Design principles]
        Maintains compatibility with existing FastAPI usage.
        
        [Implementation details]
        Delegates to FastMCP's app.get method.
        
        Args:
            path: URL path for the endpoint
            handler: Function to handle requests to this endpoint
            **kwargs: Additional parameters to pass to FastAPI's route decorator
        """
        self._mcp.app.get(path, **kwargs)(handler)
        self.logger.debug(f"GET route registered: {path}")

    def register_post_route(self, path, handler, **kwargs):
        """
        [Function intent]
        Registers a POST route handler with the server.
        
        [Design principles]
        Maintains compatibility with existing FastAPI usage.
        
        [Implementation details]
        Delegates to FastMCP's app.post method.
        
        Args:
            path: URL path for the endpoint
            handler: Function to handle requests to this endpoint
            **kwargs: Additional parameters to pass to FastAPI's route decorator
        """
        self._mcp.app.post(path, **kwargs)(handler)
        self.logger.debug(f"POST route registered: {path}")

    def register_mcp_tool(self, tool):
        """
        [Function intent]
        Registers an MCP tool with the server.
        
        [Design principles]
        Adapts existing tool interface to fastmcp.
        
        [Implementation details]
        Converts the MCPTool to a fastmcp tool function.
        
        Args:
            tool: MCPTool instance to register
        """
        # FastMCP uses decorators for tool registration, but we need to adapt
        # our existing MCPTool objects to work with it
        
        # Create a wrapper function that calls the tool's execute method
        @self._mcp.tool(name=tool.name, description=tool.description)
        async def tool_wrapper(**kwargs):
            """Tool wrapper for fastmcp integration."""
            # Convert kwargs to a Pydantic model
            input_model = tool.input_schema(**kwargs)
            
            # Execute the tool
            result = await tool.execute(input_model)
            
            # Convert result to dict if it's a Pydantic model
            if hasattr(result, "dict"):
                return result.dict()
            return result
        
        self.logger.debug(f"MCP tool registered: {tool.name}")

    def register_mcp_resource(self, resource_name, handler):
        """
        [Function intent]
        Registers an MCP resource with the server.
        
        [Design principles]
        Adapts existing resource interface to fastmcp.
        
        [Implementation details]
        Converts the resource handler to a fastmcp resource function.
        
        Args:
            resource_name: Name of the MCP resource
            handler: Function to handle resource requests
        """
        # FastMCP uses decorators for resource registration, but we need to adapt
        # our existing resource handlers to work with it
        
        # Create a wrapper function that calls the resource handler
        @self._mcp.resource(resource_name)
        async def resource_wrapper(**kwargs):
            """Resource wrapper for fastmcp integration."""
            # Extract resource_id from kwargs if present
            resource_id = kwargs.pop("resource_id", None)
            
            # Call the handler
            result = handler(resource_id, kwargs, {})
            
            return result
        
        self.logger.debug(f"MCP resource registered: {resource_name}")
```

#### 1.3. Update MCPServerComponent

Update the MCPServerComponent class to work with the new MCPServer implementation:

```python
# src/dbp/mcp_server/component.py
# Keep most of the existing implementation, but update the initialization
# to use the new MCPServer class
```

### Phase 2: Tool and Resource Adaptation

#### 2.1. Create Adapter for Existing Tools

Create an adapter to convert existing MCPTool objects to fastmcp tool functions:

```python
# src/dbp/mcp_server/adapters.py
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel
from fastmcp import FastMCP

def adapt_mcp_tool(mcp: FastMCP, tool):
    """
    Adapts an existing MCPTool object to work with fastmcp.
    
    Args:
        mcp: FastMCP instance
        tool: MCPTool instance to adapt
        
    Returns:
        The registered tool function
    """
    @mcp.tool(name=tool.name, description=tool.description)
    async def tool_wrapper(**kwargs):
        """Tool wrapper for fastmcp integration."""
        # Convert kwargs to a Pydantic model
        input_model = tool.input_schema(**kwargs)
        
        # Execute the tool
        result = await tool.execute(input_model)
        
        # Convert result to dict if it's a Pydantic model
        if hasattr(result, "dict"):
            return result.dict()
        return result
    
    return tool_wrapper

def adapt_mcp_resource(mcp: FastMCP, resource_name: str, handler: Callable):
    """
    Adapts an existing MCP resource handler to work with fastmcp.
    
    Args:
        mcp: FastMCP instance
        resource_name: Name of the resource
        handler: Resource handler function
        
    Returns:
        The registered resource function
    """
    @mcp.resource(resource_name)
    async def resource_wrapper(**kwargs):
        """Resource wrapper for fastmcp integration."""
        # Extract resource_id from kwargs if present
        resource_id = kwargs.pop("resource_id", None)
        
        # Call the handler
        result = handler(resource_id, kwargs, {})
        
        return result
    
    return resource_wrapper
```

### Phase 3: Client Implementation

#### 3.1. Replace Client Implementation

Replace the existing client implementation with fastmcp's client:

```python
# src/dbp_cli/mcp/client.py
from fastmcp import Client as FastMCPClient
from typing import Dict, Any, Optional, Union, List

class MCPClient:
    """
    [Class intent]
    Client for interacting with MCP servers using fastmcp.
    
    [Design principles]
    - Uses fastmcp's Client for MCP protocol implementation
    - Maintains compatibility with existing code where possible
    - Provides clean API for MCP operations
    
    [Implementation details]
    - Wraps fastmcp's Client for MCP protocol handling
    - Adapts the interface to match the existing MCPClient
    """
    
    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        auth_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        [Function intent]
        Initializes a new MCP client with fastmcp integration.
        
        [Design principles]
        - Flexible configuration with sensible defaults
        - Support for multiple authentication methods
        - Configurable timeout and retry handling
        
        [Implementation details]
        - Creates fastmcp Client with the provided configuration
        - Sets up authentication headers
        - Initializes logging
        
        Args:
            base_url: The base URL of the MCP server (e.g., "http://localhost:8000")
            auth_token: Optional authentication token
            auth_headers: Optional dictionary of authentication headers
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            logger_override: Optional logger instance
        """
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.timeout = timeout
        self.logger = logger_override or logging.getLogger(__name__)
        
        # Set up authentication
        self.headers = {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        if auth_headers:
            self.headers.update(auth_headers)
        
        # Create fastmcp Client
        self._client = FastMCPClient(
            base_url,
            headers=self.headers,
            timeout=timeout
        )
        
        self.logger.debug(f"MCPClient initialized for server: {base_url}")
    
    async def close(self):
        """
        [Function intent]
        Closes the client's connection to free resources.
        
        [Design principles]
        - Proper resource management
        - Clean shutdown of connections
        
        [Implementation details]
        - Closes the fastmcp Client
        """
        await self._client.close()
        self.logger.debug("MCP client session closed")
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Calls an MCP tool with the provided parameters.
        
        [Design principles]
        - Simple interface for tool execution
        - Consistent error handling
        
        [Implementation details]
        - Delegates to fastmcp Client's call_tool method
        - Handles errors and returns results
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters to pass to the tool
            
        Returns:
            Tool execution result
        """
        try:
            result = await self._client.call_tool(tool_name, params)
            return result
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {str(e)}")
            raise
    
    async def read_resource(self, resource_uri: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Reads an MCP resource with the provided parameters.
        
        [Design principles]
        - Simple interface for resource access
        - Consistent error handling
        
        [Implementation details]
        - Delegates to fastmcp Client's read_resource method
        - Handles errors and returns results
        
        Args:
            resource_uri: URI of the resource to read
            params: Optional parameters to pass to the resource
            
        Returns:
            Resource data
        """
        try:
            result = await self._client.read_resource(resource_uri, params)
            return result
        except Exception as e:
            self.logger.error(f"Error reading resource {resource_uri}: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        [Function intent]
        Checks if the MCP server is available and functioning.
        
        [Design principles]
        - Simple health check to verify connectivity
        - Uses standard endpoint pattern
        
        [Implementation details]
        - Makes a GET request to the health endpoint
        - Has shorter timeout for quick checking
        
        Returns:
            Server health status
        """
        try:
            # Use the client's session to make a direct request
            async with self._client._session.get(
                f"{self.base_url}/health",
                timeout=5
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            raise
```

#### 3.2. Update Tool and Resource Clients

Update the tool and resource client implementations to use fastmcp's client:

```python
# src/dbp_cli/mcp/tool_client.py and resource_client.py
# Similar adaptations to use fastmcp's Client
```

### Phase 4: Configuration Updates

#### 4.1. Update Configuration Schema

Update the configuration schema to include fastmcp-specific settings:

```python
# src/dbp/config/config_schema.py
# Add fastmcp-specific settings to MCPServerConfig
```

#### 4.2. Update Default Configuration

Update the default configuration values:

```python
# src/dbp/config/default_config.py
# Add fastmcp-specific default values
```

### Phase 5: Testing and Validation

#### 5.1. Unit Tests

Update unit tests to work with the new implementation:

```python
# tests/unit/mcp_server/test_server.py
# Update tests to use fastmcp
```

#### 5.2. Integration Tests

Update integration tests to work with the new implementation:

```python
# tests/integration/mcp_server/test_server_integration.py
# Update tests to use fastmcp
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

## Conclusion

This implementation plan provides a comprehensive approach to replacing the homemade MCP implementation with fastmcp. By following this plan, we can achieve a clean integration that preserves the existing FastAPI usage and health route while taking full advantage of fastmcp's features.
