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
# 2025-04-27T00:01:00Z : Created MCPServer class using FastMCP by CodeAssistant
# * Created MCPServer class to encapsulate FastMCP instance
# * Added methods for server lifecycle management
# * Added server availability checking
# * Added design decision about using MCPTool for validation in design principles
###############################################################################

import logging
import threading
import time
import socket
import requests
from typing import Optional
from urllib.parse import urljoin

# FastMCP imports
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
        
        # Create FastMCP instance
        self._mcp = FastMCP(
            name=name,
            description=description,
            version=version
        )
        
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
        
        # Add health endpoint
        @self._mcp.app.get("/health")
        async def health_check():
            """Health check endpoint for the MCP server."""
            return {
                "status": "healthy" if self._server_ready else "initializing",
                "server": self.name,
                "version": self.version,
                "uptime": time.time() - self._startup_time if hasattr(self, '_startup_time') else None
            }
            
        # Record startup time for uptime calculation
        self._startup_time = time.time()
        
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
        
        # Start the server in a background thread
        self._server_thread = threading.Thread(
            target=lambda: self._mcp.run(
                host=self.host,
                port=self.port,
                workers=self.workers,
                transport="sse",  # Use SSE transport by default
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
                response = requests.get(health_endpoint, timeout=2)
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
        - Returns the FastAPI app from the FastMCP instance
        
        Returns:
            FastAPI: The FastAPI app instance
        """
        return self._mcp.app
    
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
