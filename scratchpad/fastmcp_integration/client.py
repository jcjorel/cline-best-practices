###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Provides a client implementation for interacting with MCP servers using fastmcp.
# This client maintains the same interface as the original MCPClient but uses
# fastmcp's Client class internally for better compliance with the MCP specification.
###############################################################################
# [Source file design principles]
# - Uses fastmcp's Client for MCP protocol implementation
# - Maintains compatibility with existing code where possible
# - Provides clean API for MCP operations
# - Handles both synchronous and asynchronous execution
# - Maintains proper error handling and logging
###############################################################################
# [Source file constraints]
# - Must maintain the same interface as the original MCPClient
# - Must handle both synchronous and asynchronous execution
# - Must preserve error handling semantics
# - Must support health check and other custom endpoints
###############################################################################
# [Dependencies]
# codebase:- src/dbp_cli/mcp/client.py
# codebase:- src/dbp_cli/mcp/error.py
# system:- fastmcp
# system:- asyncio
# system:- logging
###############################################################################
# [GenAI tool change history]
# 2025-04-26T23:20:00Z : Created client implementation using fastmcp by CodeAssistant
# * Implemented MCPClient class using fastmcp's Client
# * Maintained same interface as original MCPClient
# * Added support for both synchronous and asynchronous execution
# * Added proper error handling and logging
###############################################################################

import logging
import asyncio
from typing import Dict, Any, Optional, Union, List

# Import fastmcp
from fastmcp import Client as FastMCPClient

# Import error handling
from src.dbp_cli.mcp.error import MCPError, MCPErrorCode

logger = logging.getLogger(__name__)

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
    - Handles both synchronous and asynchronous execution
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
        self.logger = logger_override or logger
        
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
        
        Returns:
            None
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
            
        Raises:
            MCPError: For all types of errors during tool execution
        """
        try:
            result = await self._client.call_tool(tool_name, params)
            return result
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {str(e)}")
            # Convert to MCPError for consistent error handling
            raise MCPError(
                MCPErrorCode.TOOL_EXECUTION_ERROR,
                f"Error calling tool {tool_name}: {str(e)}"
            )
    
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
            
        Raises:
            MCPError: For all types of errors during resource access
        """
        try:
            result = await self._client.read_resource(resource_uri, params)
            return result
        except Exception as e:
            self.logger.error(f"Error reading resource {resource_uri}: {str(e)}")
            # Convert to MCPError for consistent error handling
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"Error reading resource {resource_uri}: {str(e)}"
            )
    
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
            
        Raises:
            MCPError: If server is not available or health check fails
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
            # Convert to MCPError for consistent error handling
            raise MCPError(
                MCPErrorCode.SERVER_UNAVAILABLE,
                f"Server health check failed: {str(e)}"
            )
    
    async def list_tools(self) -> List[str]:
        """
        [Function intent]
        Lists available tools on the MCP server.
        
        [Design principles]
        - Simple interface for tool discovery
        - Consistent error handling
        
        [Implementation details]
        - Delegates to fastmcp Client's list_tools method
        - Handles errors and returns results
        
        Returns:
            List of available tool names
            
        Raises:
            MCPError: For all types of errors during tool discovery
        """
        try:
            tools = await self._client.list_tools()
            return tools
        except Exception as e:
            self.logger.error(f"Error listing tools: {str(e)}")
            # Convert to MCPError for consistent error handling
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Error listing tools: {str(e)}"
            )
    
    async def list_resources(self) -> List[str]:
        """
        [Function intent]
        Lists available resources on the MCP server.
        
        [Design principles]
        - Simple interface for resource discovery
        - Consistent error handling
        
        [Implementation details]
        - Delegates to fastmcp Client's list_resources method
        - Handles errors and returns results
        
        Returns:
            List of available resource URIs
            
        Raises:
            MCPError: For all types of errors during resource discovery
        """
        try:
            resources = await self._client.list_resources()
            return resources
        except Exception as e:
            self.logger.error(f"Error listing resources: {str(e)}")
            # Convert to MCPError for consistent error handling
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Error listing resources: {str(e)}"
            )
    
    def __enter__(self):
        """
        [Function intent]
        Enables context manager pattern for the client.
        
        [Design principles]
        - Support for 'with' statement
        - Ensures proper resource management
        
        [Implementation details]
        - Returns self for use within context
        
        Returns:
            Self for use in with statement
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        [Function intent]
        Cleans up resources when exiting context manager.
        
        [Design principles]
        - Proper resource cleanup
        - Completes context manager protocol
        
        [Implementation details]
        - Calls close() to free resources
        - Does not suppress exceptions
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
            
        Returns:
            None
        """
        # Create an event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Close the client
        if hasattr(self, '_client'):
            loop.run_until_complete(self.close())
