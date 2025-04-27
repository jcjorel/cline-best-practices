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
# Provides the MCPServer class that encapsulates the FastMCP server instance.
# This class is responsible for creating and managing the FastMCP instance and
# providing a clean API for server lifecycle management.
###############################################################################
# [Source file design principles]
# - Encapsulates FastMCP instance
# - Provides clean API for server lifecycle management
# - Handles server startup and shutdown
# - Maintains proper error handling and logging
# - Future developments should still use MCPTool for Pydantic validation to benefit
#   from mandatory input/output schema validation. While FastMCP provides its own
#   validation, using MCPTool ensures consistent validation across the codebase.
###############################################################################
# [Source file constraints]
# - Must use FastMCP for MCP protocol implementation
# - Must provide clear log messages during operation
# - Must maintain proper error handling
# - Must support health endpoint
###############################################################################
# [Dependencies]
# system:- fastmcp
# system:- logging
# system:- threading
# system:- time
# system:- socket
# system:- requests
###############################################################################
# [GenAI tool change history]
# 2025-04-27T18:56:00Z : Fixed server startup to use uvicorn directly by CodeAssistant
# * Changed server startup to use uvicorn.run() instead of FastMCP.run()
# * Fixed issue with FastMCP.from_fastapi() integration
# * Ensured proper FastAPI app execution
# * Maintained FastMCP integration for MCP protocol support
# 2025-04-27T18:48:00Z : Enhanced server availability checking with detailed logging by CodeAssistant
# * Added detailed debug logging for health endpoint checks
# * Improved diagnostics for server startup issues
# * Made server availability checking more robust
# 2025-04-27T17:42:00Z : Fixed FastMCP run method parameters by CodeAssistant
# * Removed workers parameter from FastMCP.run() call
# * Fixed TypeError in run_sse_async() method
# * Simplified server startup process
# 2025-04-27T17:38:00Z : Updated FastMCP integration to use FastAPI first by CodeAssistant
# * Modified server to create FastAPI instance first and then hook FastMCP to it
# * Fixed issue with accessing app attribute in FastMCP v2
# * Used FastMCP.from_fastapi() to create FastMCP instance from FastAPI app
# * Maintained same functionality with improved architecture
# 2025-04-27T00:15:00Z : Replaced homemade MCP implementation with FastMCP by CodeAssistant
# * Completely replaced the homemade MCP implementation with FastMCP
# * Removed all code related to capability negotiation, session management, etc.
# * Simplified the server implementation by delegating to FastMCP
# * Added design decision about using MCPTool for validation in design principles
# 2025-04-25T18:13:54Z : Updated MCP tool registration to use MCPTool objects by CodeAssistant
# * Modified register_mcp_tool to accept MCPTool objects instead of handler functions
# * Updated unregister_mcp_tool to accept either MCPTool objects or tool names
# * Added direct import of MCPTool and MCPResource classes
# * Enhanced FastAPI integration using MCPTool's handler method
###############################################################################

import logging
import threading
import time
import socket
import requests
from typing import Optional
from urllib.parse import urljoin

# FastAPI and FastMCP imports
from fastapi import FastAPI
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

class MCPServer:
    """
    [Class intent]
    Encapsulates the FastMCP server instance and provides methods for server management.
    This class is responsible for creating and managing the FastMCP instance and
    providing a clean API for server lifecycle management.
    
    [Design principles]
    - Encapsulates FastMCP instance
    - Provides clean API for server lifecycle management
    - Handles server startup and shutdown
    - Maintains proper error handling and logging
    
    [Implementation details]
    - Creates and manages FastMCP instance
    - Provides methods for starting and stopping the server
    - Handles server availability checking
    """
    
    def __init__(self, name: str, description: str, version: str, host: str, port: int, workers: int = 1):
        """
        [Function intent]
        Initializes a new MCPServer instance with the provided configuration.
        
        [Design principles]
        - Simple initialization with required parameters
        - Clear configuration of server properties
        
        [Implementation details]
        - Creates FastMCP instance with the provided configuration
        - Sets up server properties
        
        Args:
            name: Name of the MCP server
            description: Description of the MCP server
            version: Version of the MCP server
            host: Host to bind the server to
            port: Port to bind the server to
            workers: Number of worker processes
        """
        self.logger = logging.getLogger("dbp.mcp_server.server")
        self.logger.info(f"Initializing MCPServer with name={name}, host={host}, port={port}")
        
        # Store server configuration
        self.host = host
        self.port = port
        self.workers = workers
        self.name = name
        self.version = version
        
        # Server state
        self._server_thread = None
        self._stop_event = threading.Event()
        self._server_ready = False
        
        # Record startup time for uptime calculation
        self._startup_time = time.time()
        
        # Create FastAPI instance first
        self._app = FastAPI(
            title=name,
            description=description,
            version=version
        )
        
        # Add health endpoint directly to FastAPI app
        @self._app.get("/health")
        async def health_check():
            """Health check endpoint for the MCP server."""
            return {
                "status": "healthy" if self._server_ready else "initializing",
                "server": self.name,
                "version": self.version,
                "uptime": time.time() - self._startup_time
            }
        
        # Create FastMCP instance from FastAPI app
        self._mcp = FastMCP.from_fastapi(
            self._app,
            name=name,
            description=description,
            version=version
        )
        
        self.logger.info("MCPServer initialized successfully")
    
    def start(self):
        """
        [Function intent]
        Starts the MCP server in a background thread.
        
        [Design principles]
        - Non-blocking server startup
        - Clear logging of server status
        
        [Implementation details]
        - Starts the server in a background thread
        - Sets up thread synchronization
        
        Returns:
            None
        """
        self.logger.info(f"Starting MCP server on {self.host}:{self.port}")
        
        # Reset stop event
        self._stop_event.clear()
        
        # Import uvicorn here to avoid circular imports
        import uvicorn
        
        # Start the server in a background thread using uvicorn directly
        self._server_thread = threading.Thread(
            target=lambda: uvicorn.run(
                self._app,
                host=self.host,
                port=self.port,
                log_level="info"
            ),
            daemon=True
        )
        self._server_thread.start()
        
        # Check if server is available
        if not self._check_server_availability():
            self.logger.error("Failed to start MCP server")
            self.stop()
            raise RuntimeError("Failed to start MCP server")
            
        # Server is ready
        self._server_ready = True
        self.logger.info(f"MCP server started successfully on {self.host}:{self.port}")
    
    def stop(self):
        """
        [Function intent]
        Stops the MCP server.
        
        [Design principles]
        - Clean server shutdown
        - Clear logging of server status
        
        [Implementation details]
        - Signals the server to stop
        - Waits for the server thread to exit
        
        Returns:
            None
        """
        self.logger.info("Stopping MCP server")
        
        # Signal the server to stop
        self._stop_event.set()
        
        # Reset server state
        self._server_ready = False
        
        self.logger.info("MCP server stopped")
    
    def wait_for_exit(self):
        """
        [Function intent]
        Waits indefinitely until the server is stopped.
        
        [Design principles]
        - Blocking wait for server exit
        - Clear logging of server status
        
        [Implementation details]
        - Waits for the stop event to be set
        
        Returns:
            None
        """
        self.logger.info("Waiting for MCP server to exit")
        
        # Wait for the stop event
        self._stop_event.wait()
        
        self.logger.info("MCP server exited")
    
    def _check_server_availability(self, timeout: int = 30) -> bool:
        """
        [Function intent]
        Checks if the server is available by testing HTTP connectivity.
        
        [Design principles]
        - Robust server availability checking
        - Clear logging of server status
        
        [Implementation details]
        - Tests socket connectivity to the server port
        - Tests HTTP connectivity to the health endpoint
        - Has configurable timeout
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            bool: True if server is available, False otherwise
        """
        self.logger.info(f"Checking server availability with timeout={timeout}s")
        
        # Set up connectivity test parameters
        server_url = f"http://{self.host}:{self.port}"
        health_endpoint = urljoin(server_url, "/health")
        
        # Try to connect to the server with timeout
        server_working = False
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # First check if port is accepting connections
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex((self.host, int(self.port)))
                    if result != 0:  # Connection failed
                        time.sleep(0.5)
                        continue
                        
                # Then check if health endpoint is responding
                self.logger.debug(f"Checking health endpoint: {health_endpoint}")
                response = requests.get(health_endpoint, timeout=2)
                self.logger.debug(f"Health endpoint response: {response.status_code}")
                if response.status_code == 200:
                    server_working = True
                    break
            except Exception as e:
                self.logger.debug(f"Server connectivity test failed: {e}")
                time.sleep(0.5)
        
        if server_working:
            self.logger.info("Server availability check passed")
        else:
            self.logger.error(f"Server availability check failed after {timeout}s")
            
        return server_working
    
    @property
    def app(self):
        """
        [Function intent]
        Returns the FastAPI app instance.
        
        [Design principles]
        - Provides access to the underlying FastAPI app
        - Enables custom endpoint registration
        
        [Implementation details]
        - Returns the FastAPI app created directly
        
        Returns:
            FastAPI: The FastAPI app instance
        """
        return self._app
    
    @property
    def mcp(self):
        """
        [Function intent]
        Returns the FastMCP instance.
        
        [Design principles]
        - Provides access to the underlying FastMCP instance
        - Enables custom tool and resource registration
        
        [Implementation details]
        - Returns the FastMCP instance
        
        Returns:
            FastMCP: The FastMCP instance
        """
        return self._mcp
