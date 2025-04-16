###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the main MCPServer class, responsible for running the actual server
# process using FastAPI/Uvicorn. It receives MCP requests, routes them
# to registered tools or resources, handles authentication/authorization via
# providers, formats responses, and manages the server lifecycle (start/stop).
###############################################################################
# [Source file design principles]
# - Acts as the entry point for MCP communication.
# - Integrates with FastAPI and Uvicorn to handle HTTP requests.
# - Parses incoming requests into MCPRequest objects.
# - Uses ToolRegistry and ResourceProvider to find handlers for requests.
# - Uses AuthenticationProvider and ErrorHandler for request processing middleware.
# - Formats results or errors into MCPResponse objects.
# - Manages the server's running state.
# - Design Decision: Placeholder Web Framework (2025-04-15)
#   * Rationale: Focuses on the MCP logic rather than specific web framework details. A concrete implementation would replace placeholders with FastAPI/Flask/etc. routes and handlers.
#   * Alternatives considered: Implementing full FastAPI/Flask server (adds significant complexity and dependencies).
###############################################################################
# [Source file constraints]
# - Requires concrete implementations of MCPTool, MCPResource, AuthenticationProvider, ErrorHandler, ToolRegistry, ResourceProvider.
# - Placeholder server logic needs replacement with a real web framework implementation (e.g., FastAPI, Uvicorn).
# - Threading model for handling requests depends on the chosen web framework.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/mcp_server/data_models.py
# - src/dbp/mcp_server/mcp_protocols.py
# - src/dbp/mcp_server/registry.py
# - src/dbp/mcp_server/auth.py
# - src/dbp/mcp_server/error_handler.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:37:00Z : Implemented FastAPI/Uvicorn integration by CodeAssistant
# * Replaced placeholder web server implementation with concrete FastAPI routes
# * Added proper route handlers for tools and resources with Pydantic models
# * Implemented proper Uvicorn server configuration and graceful shutdown
# 2025-04-15T16:35:58Z : Updated server to use centralized exceptions by CodeAssistant
# * Modified imports to use exceptions from centralized exceptions module
# * Simplified error handling by using ToolNotFoundError and ResourceNotFoundError
###############################################################################

import logging
import threading
import time
import json
import uuid
from typing import Dict, Optional, Any, List, Callable, Union, Type

# MCP server imports
try:
    from .data_models import (
        MCPRequest, MCPResponse, MCPError, 
        MCPToolRequest, MCPResourceRequest, MCPResponseModel, MCPErrorModel,
        create_mcp_request_from_tool, create_mcp_request_from_resource,
        mcp_response_to_model, get_http_status_for_mcp_error
    )
    from .mcp_protocols import MCPTool, MCPResource
    from .registry import ToolRegistry, ResourceProvider
    from .exceptions import (
        ToolNotFoundError, ResourceNotFoundError,
        AuthenticationError, AuthorizationError
    )
    from .auth import AuthenticationProvider
    from .error_handler import ErrorHandler
except ImportError as e:
    logging.getLogger(__name__).error(f"MCPServer ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders for critical errors only to allow module loading
    MCPRequest, MCPResponse, MCPError = object, object, object
    MCPTool, MCPResource = object, object
    ToolRegistry, ResourceProvider = object, object
    AuthenticationProvider = object
    AuthenticationError, AuthorizationError = Exception, Exception
    ToolNotFoundError, ResourceNotFoundError = ValueError, ValueError
    ErrorHandler = object

# FastAPI and Uvicorn imports
try:
    from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query, Path
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError as e:
    logging.getLogger(__name__).error(f"FastAPI/Uvicorn not available: {e}. Web server will not function properly.", exc_info=True)
    # Create placeholder classes to allow module loading
    class FastAPI:
        def __init__(self, *args, **kwargs): pass
        def add_middleware(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda func: func
        def post(self, *args, **kwargs): return lambda func: func
    class CORSMiddleware: pass
    class JSONResponse: 
        def __init__(self, *args, **kwargs): pass
    class Request:
        def __init__(self): self.headers = {}
    class Path: pass
    class Query: pass
    class HTTPException(Exception): pass
    class Depends: pass
    
    class uvicorn:
        class Config:
            def __init__(self, *args, **kwargs): pass
        class Server:
            def __init__(self, *args, **kwargs): 
                self.should_exit = False
            def run(self): pass

logger = logging.getLogger(__name__)

class MCPServer:
    """
    Represents the MCP server instance, handling incoming requests and routing
    them to appropriate tools or resources.
    (Web server part is currently a placeholder).
    """

    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        description: str,
        version: str,
        tool_registry: ToolRegistry,
        resource_provider: ResourceProvider,
        auth_provider: Optional[AuthenticationProvider] = None,
        error_handler: Optional[ErrorHandler] = None,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initializes the MCPServer.

        Args:
            host: Host address to bind to.
            port: Port number to listen on.
            name: Server name.
            description: Server description.
            version: Server version.
            tool_registry: Registry containing MCP tools.
            resource_provider: Provider containing MCP resources.
            auth_provider: Optional authentication/authorization provider.
            error_handler: Optional handler for processing exceptions.
            logger_override: Optional logger instance.
        """
        self.host = host
        self.port = port
        self.name = name
        self.description = description
        self.version = version
        self.logger = logger_override or logger
        self._tool_registry = tool_registry
        self._resource_provider = resource_provider
        self._auth_provider = auth_provider
        self._error_handler = error_handler or ErrorHandler(self.logger) # Default error handler
        self._server_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

        # Placeholder for the actual web server app (e.g., FastAPI instance)
        self._app = self._create_web_app()

        self.logger.debug(f"MCPServer '{self.name}' v{self.version} initialized.")

    def _create_web_app(self):
        """Creates and configures the FastAPI application."""
        self.logger.info("Creating FastAPI application...")
        app = FastAPI(
            title=self.name,
            description=self.description,
            version=self.version,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Setup CORS middleware if enabled in config
        config = getattr(self, 'config', {})
        if config.get("enable_cors", False):
            self.logger.info("Setting up CORS middleware...")
            app.add_middleware(
                CORSMiddleware,
                allow_origins=config.get("cors_origins", ["*"]),
                allow_credentials=config.get("cors_allow_credentials", False),
                allow_methods=config.get("cors_methods", ["*"]),
                allow_headers=config.get("cors_headers", ["*"]),
            )
        
        self._setup_routes(app)
        return app

    def _setup_routes(self, app: FastAPI):
        """Sets up FastAPI routes for MCP requests."""
        self.logger.debug("Setting up MCP routes...")
        
        @app.post("/mcp/tool/{tool_name}")
        async def handle_tool_request(
            tool_name: str = Path(..., description="Name of the MCP tool to execute"),
            tool_request: MCPToolRequest = None,
            request: Request = None
        ):
            """
            Execute an MCP tool with the provided parameters.
            
            Args:
                tool_name: The name of the tool to execute
                tool_request: The tool request parameters
                request: FastAPI request object
            """
            try:
                # Ensure we have a tool_request even if body was empty
                if tool_request is None:
                    tool_request = MCPToolRequest()
                
                # Extract headers from FastAPI request
                headers = dict(request.headers) if request else {}
                
                # Convert Pydantic model to internal MCPRequest
                mcp_request = create_mcp_request_from_tool(tool_request, tool_name, headers)
                
                # Process the request through the core MCP handler
                mcp_response = self.handle_request(mcp_request)
                
                # Convert to Pydantic model for API response
                response_model = mcp_response_to_model(mcp_response)
                
                # Map MCP status to HTTP status code
                status_code = 200
                if mcp_response.status == "error" and mcp_response.error:
                    status_code = get_http_status_for_mcp_error(mcp_response.error.code)
                
                # Return as JSON response
                return JSONResponse(
                    content=response_model.dict(exclude_none=True),
                    status_code=status_code
                )
            except Exception as e:
                self.logger.error(f"Error handling tool request: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error: {str(e)}"
                )
        
        @app.get("/mcp/resource/{resource_path:path}")
        async def handle_resource_request(
            resource_path: str = Path(..., description="Path to the MCP resource"),
            request: Request = None,
            resource_request: MCPResourceRequest = Depends()
        ):
            """
            Access an MCP resource with the provided parameters.
            
            Args:
                resource_path: The path to the resource
                request: FastAPI request object
                resource_request: The resource request parameters
            """
            try:
                # Extract query parameters and headers from FastAPI request
                query_params = dict(request.query_params) if request else {}
                headers = dict(request.headers) if request else {}
                
                # Convert Pydantic model to internal MCPRequest
                mcp_request = create_mcp_request_from_resource(
                    resource_request, resource_path, query_params, headers
                )
                
                # Process the request through the core MCP handler
                mcp_response = self.handle_request(mcp_request)
                
                # Convert to Pydantic model for API response
                response_model = mcp_response_to_model(mcp_response)
                
                # Map MCP status to HTTP status code
                status_code = 200
                if mcp_response.status == "error" and mcp_response.error:
                    status_code = get_http_status_for_mcp_error(mcp_response.error.code)
                
                # Return as JSON response
                return JSONResponse(
                    content=response_model.dict(exclude_none=True),
                    status_code=status_code
                )
            except Exception as e:
                self.logger.error(f"Error handling resource request: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error: {str(e)}"
                )
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint for the MCP server."""
            return {
                "status": "healthy",
                "server": self.name,
                "version": self.version,
                "uptime": "unknown"  # Could be enhanced with actual uptime tracking
            }

    def start(self):
        """Starts the MCP server in a background thread."""
        if self._is_running:
            self.logger.warning(f"MCP Server '{self.name}' is already running.")
            return

        self.logger.info(f"Starting MCP server '{self.name}' on {self.host}:{self.port}...")
        self._stop_event.clear()
        self._is_running = True

        # Start the web server in a separate thread
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        self.logger.info(f"MCP Server '{self.name}' started.")

    def _run_server(self):
        """Runs the FastAPI server using Uvicorn."""
        self.logger.debug("Server thread started.")
        
        # Get configuration values from MCPServerConfig
        config = getattr(self, 'config', {})
        workers = config.get("workers", 1)
        graceful_shutdown_timeout = config.get("graceful_shutdown_timeout", 10)
        keep_alive = config.get("keep_alive", 5)
        
        # Configure Uvicorn
        uvicorn_config = uvicorn.Config(
            app=self._app,
            host=self.host,
            port=self.port,
            log_level="warning",  # Use a lower log level to avoid too much output
            loop="asyncio",
            workers=workers,  # Number of worker processes
            timeout_keep_alive=keep_alive,
            timeout_graceful_shutdown=graceful_shutdown_timeout
        )
        
        # Create and store Uvicorn server instance
        self._server = uvicorn.Server(uvicorn_config)
        
        try:
            # Start server, blocks until self._server.should_exit is set
            self._server.run()
        except Exception as e:
            self.logger.critical(f"Web server failed to run: {e}", exc_info=True)
        finally:
            self._is_running = False
            self.logger.info("Web server process stopped.")

    def stop(self):
        """Stops the MCP server."""
        if not self._is_running:
            self.logger.warning(f"MCP Server '{self.name}' is not running.")
            return

        self.logger.info(f"Stopping MCP server '{self.name}'...")
        self._stop_event.set()
        
        # Gracefully shut down Uvicorn server
        if hasattr(self, '_server') and self._server:
            self.logger.debug("Sending shutdown signal to Uvicorn...")
            self._server.should_exit = True
            
            # Additional clean shutdown for worker processes if needed
            if hasattr(self._server, 'force_exit'):
                self.logger.debug("Forcing exit for workers after grace period...")
                self._server.force_exit = True

        # Wait for server thread to exit
        if self._server_thread and self._server_thread.is_alive():
            self.logger.debug("Waiting for server thread to exit...")
            self._server_thread.join(timeout=10.0)  # Wait for thread
            if self._server_thread.is_alive():
                self.logger.warning("Server thread did not exit cleanly.")

        self._is_running = False
        self._server_thread = None
        self.logger.info(f"MCP Server '{self.name}' stopped.")

    @property
    def is_running(self) -> bool:
        """Checks if the server is currently running."""
        return self._is_running

    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handles an incoming MCPRequest, performing auth, routing, execution, and error handling.
        This method would typically be called by the web framework's route handlers.
        """
        auth_context: Optional[Dict[str, Any]] = None
        try:
            self.logger.info(f"Handling MCP request ID: {request.id}, Type: {request.type}, Target: {request.target}")
            self.logger.debug(f"Request Data: {request.data}")

            # 1. Authentication
            if self._auth_provider:
                auth_context = self._auth_provider.authenticate(request)
                if auth_context is None:
                    # Authentication failed, error handler will format MCPError
                    raise AuthenticationError("Authentication failed: Invalid or missing API key.")

            # 2. Route based on type
            if request.type == "tool":
                response = self._handle_tool_request(request, auth_context)
            elif request.type == "resource":
                response = self._handle_resource_request(request, auth_context)
            else:
                raise ValueError(f"Invalid MCP request type: '{request.type}'")

            self.logger.info(f"Request ID {request.id} completed with status: {response.status}")
            return response

        except Exception as e:
            # 3. Centralized Error Handling
            # Let the error handler convert the exception to an MCPError
            mcp_error = self._error_handler.handle_error(e, request)
            return MCPResponse(
                id=request.id,
                status="error",
                error=mcp_error,
                result=None
            )

    def _handle_tool_request(self, request: MCPRequest, auth_context: Optional[Dict[str, Any]]) -> MCPResponse:
        """Handles a validated 'tool' type request."""
        tool_name = request.target
        tool = self._tool_registry.get_tool(tool_name)

        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found.") # Let error handler convert this

        # Authorization
        if self._auth_provider:
            if not self._auth_provider.authorize(auth_context, "tool", tool_name, "execute"):
                raise AuthorizationError(f"Not authorized to execute tool '{tool_name}'.", required_permission=f"tool:{tool_name}:execute")

        # TODO: Validate request.data against tool.input_schema before execution

        # Execute the tool
        result_data = tool.execute(request.data, auth_context)

        # TODO: Validate result_data against tool.output_schema before returning

        return MCPResponse(
            id=request.id,
            status="success",
            error=None,
            result=result_data
        )

    def _handle_resource_request(self, request: MCPRequest, auth_context: Optional[Dict[str, Any]]) -> MCPResponse:
        """Handles a validated 'resource' type request."""
        resource_uri = request.target
        # Basic URI parsing (e.g., "documentation/DESIGN.md")
        parts = resource_uri.split('/', 1)
        resource_name = parts[0]
        resource_id = parts[1] if len(parts) > 1 else None

        resource_handler = self._resource_provider.get_resource(resource_name)

        if not resource_handler:
            raise ResourceNotFoundError(f"Resource type '{resource_name}' not found.") # Let error handler convert

        # Authorization (assuming 'get' action for now)
        action = "get" # Or determine from request method if using HTTP verbs directly
        if self._auth_provider:
            # Authorize access to the resource type, potentially checking resource_id too
            if not self._auth_provider.authorize(auth_context, "resource", resource_name, action):
                 raise AuthorizationError(f"Not authorized to {action} resource '{resource_name}'.", required_permission=f"resource:{resource_name}:{action}")

        # Access the resource
        result_data = resource_handler.get(resource_id, request.data, auth_context)

        return MCPResponse(
            id=request.id,
            status="success",
            error=None,
            result=result_data
        )
