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
# Implements the main MCPServer class, responsible for running the HTTP server
# process using FastAPI/Uvicorn. It starts quickly with minimal dependencies and 
# provides an API for other components to register routes and MCP handlers as they
# become ready. This ensures the server is available to serve HTTP requests
# as soon as possible, regardless of whether other system components are ready.
###############################################################################
# [Source file design principles]
# - Acts as a lightweight HTTP server with minimal dependencies.
# - Starts rapidly with only essential configuration and health check endpoint.
# - Provides a thread-safe API for dynamic route registration by other components.
# - Maintains independence from other system components beyond config_manager.
# - Uses callback mechanism for route handlers to avoid direct dependencies.
# - Offers an internal API for other components to register MCP tool/resource handlers.
# - Separates HTTP server lifecycle from MCP protocol handling.
###############################################################################
# [Source file constraints]
# - Must start with only config_manager dependency.
# - Must be able to start without any MCP tools or resources registered.
# - Must provide clean extension points for other components to register handlers.
# - Must maintain thread-safety for concurrent registration API calls.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# system:- fastapi
# system:- uvicorn
# system:- threading
# system:- typing
# system:- socket
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:13:54Z : Updated MCP tool registration to use MCPTool objects by CodeAssistant
# * Modified register_mcp_tool to accept MCPTool objects instead of handler functions
# * Updated unregister_mcp_tool to accept either MCPTool objects or tool names
# * Added direct import of MCPTool and MCPResource classes
# * Enhanced FastAPI integration using MCPTool's handler method
# 2025-04-25T16:19:43Z : Redesigned server for early startup and dynamic route registration by CodeAssistant
# * Completely refactored to start with minimal dependencies and just health endpoint
# * Added API for dynamic route registration by other components
# * Removed direct dependencies on other system components
# * Added thread-safe route and tool registration mechanisms
# * Maintained MCP protocol support through callback-based registration
# 2025-04-25T15:53:45Z : Added HTTP server readiness verification by CodeAssistant
# * Added socket-based connectivity test for HTTP server subsystem
# * Modified server startup to verify server is accepting connections
# * Added detailed logging for server readiness state
# * Enhanced reliability by verifying actual connection acceptance
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
import socket
from typing import Dict, Optional, Any, List, Callable, Union, Type, Set

# Import the new capability negotiation and session modules
from src.dbp.mcp_server.mcp.session import SessionManager, MCPSession, create_anonymous_session
from src.dbp.mcp_server.mcp.negotiation import (
    NegotiationRequest, NegotiationResponse, ServerCapabilityType,
    ClientCapabilityType, CapabilityDetail, get_capability_metadata
)

# FastAPI and Uvicorn imports
try:
    from fastapi import FastAPI, Request, Response, HTTPException, Depends, APIRouter, Body, Path, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
    from pydantic import BaseModel
except ImportError as e:
    logging.getLogger(__name__).error(f"FastAPI/Uvicorn not available: {e}. Web server will not function properly.", exc_info=True)
    # Create placeholder classes to allow module loading
    class FastAPI:
        def __init__(self, *args, **kwargs): pass
        def add_middleware(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda func: func
        def post(self, *args, **kwargs): return lambda func: func
        def include_router(self, *args, **kwargs): pass
    class APIRouter:
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda func: func
        def post(self, *args, **kwargs): return lambda func: func
    class CORSMiddleware: pass
    class JSONResponse: 
        def __init__(self, *args, **kwargs): pass
    class Request:
        def __init__(self): self.headers = {}
    class Body: pass
    class Path: pass
    class Query: pass
    class HTTPException(Exception): pass
    class Depends: pass
    class BaseModel: pass
    
    class uvicorn:
        class Config:
            def __init__(self, *args, **kwargs): pass
        class Server:
            def __init__(self, *args, **kwargs): 
                self.should_exit = False
            def run(self): pass

logger = logging.getLogger(__name__)

from src.dbp.mcp_server.mcp_protocols import MCPTool, MCPResource
from src.dbp.mcp_server.mcp.error import MCPError

# Type definitions for route registration callbacks
ResourceHandlerFunc = Callable[[Optional[str], Dict[str, Any], Dict[str, Any]], Dict[str, Any]] 
RouteHandlerFunc = Callable[..., Any]

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
        logger_override: Optional[logging.Logger] = None,
        require_negotiation: bool = False,
        session_timeout_seconds: int = 3600
    ):
        """
        [Function intent]
        Initializes the MCPServer with minimal dependencies, making it ready to start
        immediately without requiring other system components.
        
        [Design principles]
        Minimal dependencies for fast initialization.
        Clean separation of server configuration from runtime behaviors.
        
        [Implementation details]
        Stores basic configuration parameters.
        Creates a FastAPI application with only the health endpoint.
        Sets up thread synchronization for dynamic route registration.
        Initializes session management for capability negotiation.

        Args:
            host: Host address to bind to
            port: Port number to listen on
            name: Server name
            description: Server description
            version: Server version
            logger_override: Optional logger instance
            require_negotiation: Whether to require capability negotiation for all requests
            session_timeout_seconds: Timeout for inactive sessions in seconds
        """
        self.host = host
        self.port = port
        self.name = name
        self.description = description
        self.version = version
        self.logger = logger_override or logger
        self.require_negotiation = require_negotiation
        
        # Initialize collections for dynamic registration
        self._registered_tools: Dict[str, MCPTool] = {}
        self._registered_resources: Dict[str, ResourceHandlerFunc] = {}
        self._registered_routes: Dict[str, Dict[str, Any]] = {}
        
        # Initialize session management
        self._session_manager = SessionManager(session_timeout_seconds=session_timeout_seconds)
        self._server_capabilities = self._determine_server_capabilities()
        
        # Thread synchronization for dynamic route registration
        self._router_lock = threading.RLock()
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

    def _determine_server_capabilities(self) -> Set[str]:
        """
        [Function intent]
        Determines the server's capabilities based on its configuration and available features.
        
        [Design principles]
        Dynamic capability discovery based on server state.
        Centralized capability determination for consistency.
        
        [Implementation details]
        Examines server configuration and registered components to build capability set.
        
        Returns:
            Set[str]: Set of capability strings supported by this server.
        """
        # Start with base capabilities
        capabilities = {
            ServerCapabilityType.TOOLS.value,
            ServerCapabilityType.RESOURCES.value
        }
        
        # Add config-based capabilities
        config = getattr(self, 'config', {})
        
        # Subscription support
        if getattr(self, '_supports_subscriptions', False):
            capabilities.add(ServerCapabilityType.SUBSCRIPTIONS.value)
            
        # Streaming support    
        if getattr(self, '_supports_streaming', False):
            capabilities.add(ServerCapabilityType.STREAMING.value)
            
        # Notifications support
        if getattr(self, '_supports_notifications', False):
            capabilities.add(ServerCapabilityType.NOTIFICATIONS.value)
            
        # Examine other server features for additional capabilities
        if hasattr(self, '_supports_prompts') and getattr(self, '_supports_prompts'):
            capabilities.add(ServerCapabilityType.PROMPTS.value)
            
        # Add batch operations capability if supported
        if hasattr(self, '_supports_batch_operations') and getattr(self, '_supports_batch_operations'):
            capabilities.add(ServerCapabilityType.BATCH_OPERATIONS.value)
            
        return capabilities

    def _setup_routes(self, app: FastAPI):
        """
        [Function intent]
        Sets up minimal FastAPI routes for the initial HTTP server.
        
        [Design principles]
        Minimal route registration for quick server startup.
        Health endpoint for server status monitoring.
        
        [Implementation details]
        Only registers the /health endpoint initially.
        Other routes will be registered dynamically by components as they become ready.
        """
        self.logger.debug("Setting up initial HTTP routes...")
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint for the MCP server."""
            # Get initialization status from the component tracking
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

        # Register capability negotiation endpoint
        self._register_negotiation_endpoint(app)
        
        # Register session middleware
        self._register_session_middleware(app)
    
    def _register_negotiation_endpoint(self, app: FastAPI):
        """
        [Function intent]
        Registers the capability negotiation endpoint for MCP protocol compliance.
        
        [Design principles]
        Standard MCP negotiation protocol implementation.
        Session creation and management.
        
        [Implementation details]
        Creates a FastAPI POST endpoint for negotiation.
        Processes client capabilities and creates a session.
        Returns server capabilities and available tools/resources.
        
        Args:
            app: FastAPI application to register with
            
        Returns:
            None
        """
        self.logger.debug("Registering MCP capability negotiation endpoint...")
        
        @app.post("/mcp/negotiate")
        async def negotiate_capabilities(request: Request, negotiation: NegotiationRequest):
            """
            MCP capability negotiation endpoint.
            Processes client capability declaration and establishes a session.
            """
            self.logger.info(f"Received capability negotiation from {negotiation.client_name} v{negotiation.client_version}")
            
            try:
                # Process client capabilities
                client_capabilities = set(negotiation.supported_capabilities)
                
                # Extract auth context from request if present
                auth_context = self._extract_auth_context(request)
                
                # Create session
                session = self._session_manager.create_session(
                    client_name=negotiation.client_name,
                    client_version=negotiation.client_version,
                    capabilities=client_capabilities,
                    auth_context=auth_context
                )
                
                # Prepare capability details
                capability_details = {}
                for capability in self._server_capabilities:
                    metadata = get_capability_metadata(capability)
                    capability_details[capability] = CapabilityDetail(
                        name=capability,
                        version=metadata.get("version", "1.0"),
                        description=metadata.get("description", "")
                    )
                
                # Prepare response with server capabilities
                response = NegotiationResponse(
                    server_name=self.name,
                    server_version=self.version,
                    supported_capabilities=list(self._server_capabilities),
                    available_tools=list(self._registered_tools.keys()),
                    available_resources=list(self._registered_resources.keys()),
                    capability_details=capability_details
                )
                
                self.logger.debug(f"Created session {session.id} for client {negotiation.client_name}")
                
                # Return response with session ID in header
                return JSONResponse(
                    content=response.dict(),
                    headers={"X-MCP-Session-ID": session.id}
                )
                
            except Exception as e:
                self.logger.error(f"Error during capability negotiation: {str(e)}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Negotiation failed: {str(e)}"}
                )
    
    def _register_session_middleware(self, app: FastAPI):
        """
        [Function intent]
        Registers middleware to handle session validation for all MCP endpoints.
        
        [Design principles]
        Consistent session handling across all requests.
        Capability enforcement based on session information.
        
        [Implementation details]
        Creates a FastAPI middleware to extract and validate session IDs.
        Handles anonymous sessions for backward compatibility.
        Enforces capability requirements for specific endpoints.
        
        Args:
            app: FastAPI application to register with
            
        Returns:
            None
        """
        self.logger.debug("Registering MCP session middleware...")
        
        @app.middleware("http")
        async def session_middleware(request: Request, call_next):
            """
            Middleware to handle session validation and capability enforcement.
            """
            # Skip session check for negotiation endpoint
            if request.url.path == "/mcp/negotiate" or not request.url.path.startswith("/mcp/"):
                return await call_next(request)
            
            # Get session ID from header
            session_id = request.headers.get("X-MCP-Session-ID")
            
            if not session_id:
                # If negotiation is required but no session ID provided, reject the request
                if self.require_negotiation:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Missing session ID. Please negotiate capabilities first."}
                    )
                else:
                    # For backward compatibility, create an anonymous session
                    session = create_anonymous_session()
                    self.logger.debug(f"Created anonymous session {session.id} for backward compatibility")
            else:
                # Validate session
                session = self._session_manager.get_session(session_id)
                if not session:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid or expired session ID. Please negotiate capabilities again."}
                    )
            
            # Attach session to request state for handlers
            request.state.session = session
            
            # Check capabilities for specific endpoints
            path = request.url.path
            
            if path.startswith("/mcp/tool/") and "sampling" in self._server_capabilities:
                if not session.has_capability(ClientCapabilityType.SAMPLING.value):
                    return JSONResponse(
                        status_code=403,
                        content={"error": f"Client does not support required capability: {ClientCapabilityType.SAMPLING.value}"}
                    )
                    
            if path.startswith("/mcp/subscription/") and "subscriptions" in self._server_capabilities:
                if not session.has_capability(ClientCapabilityType.NOTIFICATIONS.value):
                    return JSONResponse(
                        status_code=403,
                        content={"error": f"Client does not support required capability: {ClientCapabilityType.NOTIFICATIONS.value}"}
                    )
            
            # Continue with request
            return await call_next(request)

    def _extract_auth_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        [Function intent]
        Extracts authentication information from the request for session context.
        
        [Design principles]
        Flexible authentication extraction for various auth mechanisms.
        
        [Implementation details]
        Examines request headers and parameters for auth data.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Optional[Dict[str, Any]]: Authentication context if available, None otherwise
        """
        # Extract any authentication information from the request
        auth_context = {}
        
        # JWT Token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_context["bearer_token"] = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            auth_context["api_key"] = api_key
            
        # Return None if no auth information was found
        return auth_context if auth_context else None

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

    def _check_server_availability(self, max_attempts=10, delay=0.5):
        """
        Test if the HTTP server is available by attempting to connect to its port.
        
        Args:
            max_attempts: Maximum number of connection attempts
            delay: Delay between attempts in seconds
            
        Returns:
            bool: True if server is accepting connections, False otherwise
        """
        for attempt in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)  # Short timeout for quick feedback
                    self.logger.debug(f"Attempting to connect to {self.host}:{self.port} (attempt {attempt+1}/{max_attempts})")
                    result = s.connect_ex((self.host, self.port))
                    if result == 0:  # Port is open and accepting connections
                        self.logger.debug(f"Successfully connected to {self.host}:{self.port}")
                        return True
            except Exception as e:
                self.logger.debug(f"Connection test failed: {e}")
            
            # Wait before next attempt
            time.sleep(delay)
        
        return False

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
            self.logger.info(f"Starting HTTP server subsystem on {self.host}:{self.port} with {workers} worker(s)...")
            
            # Start server in a non-blocking thread to allow for connection verification
            startup_thread = threading.Thread(target=lambda: self._server.run())
            startup_thread.daemon = True
            startup_thread.start()
            
            # Check if the server started successfully and is accepting connections
            if self._check_server_availability():
                self.logger.info(f"HTTP server subsystem successfully started and is accepting connections on {self.host}:{self.port}")
            else:
                self.logger.error(f"HTTP server subsystem appears to be running but is not accepting connections on {self.host}:{self.port}")
            
            # Wait for the server to complete its run
            startup_thread.join()
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
            
        Returns:
            None
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

    def register_router(self, router: APIRouter, prefix: str = ""):
        with self._router_lock:
            self.logger.info(f"Registering router with prefix '{prefix}'")
            self._app.include_router(router, prefix=prefix)
            # Track registration for informational purposes
            router_key = f"router:{prefix or 'root'}"
            self._registered_routes[router_key] = {
                "type": "router",
                "prefix": prefix,
                "registered_at": time.time()
            }
            self.logger.debug(f"Router registered with prefix '{prefix}'")

    def register_get_route(self, path: str, handler: RouteHandlerFunc, **kwargs):
        """
        [Function intent]
        Registers a GET route handler with the server.
        
        [Design principles]
        Dynamic route registration for component-specific endpoints.
        Flexible parameter passing to support various FastAPI route options.
        
        [Implementation details]
        Uses FastAPI's app.get to register the handler with the path.
        Thread-synchronized to prevent race conditions.
        Tracks registration for management purposes.
        
        Args:
            path: URL path for the endpoint
            handler: Function to handle requests to this endpoint
            **kwargs: Additional parameters to pass to FastAPI's route decorator
            
        Returns:
            None
        """
        with self._router_lock:
            self.logger.info(f"Registering GET route: {path}")
            self._app.get(path, **kwargs)(handler)
            # Track registration
            route_key = f"GET:{path}"
            self._registered_routes[route_key] = {
                "type": "GET",
                "path": path,
                "registered_at": time.time()
            }
            self.logger.debug(f"GET route registered: {path}")

    def register_post_route(self, path: str, handler: RouteHandlerFunc, **kwargs):
        """
        [Function intent]
        Registers a POST route handler with the server.
        
        [Design principles]
        Dynamic route registration for component-specific endpoints.
        Flexible parameter passing to support various FastAPI route options.
        
        [Implementation details]
        Uses FastAPI's app.post to register the handler with the path.
        Thread-synchronized to prevent race conditions.
        Tracks registration for management purposes.
        
        Args:
            path: URL path for the endpoint
            handler: Function to handle requests to this endpoint
            **kwargs: Additional parameters to pass to FastAPI's route decorator
            
        Returns:
            None
        """
        with self._router_lock:
            self.logger.info(f"Registering POST route: {path}")
            self._app.post(path, **kwargs)(handler)
            # Track registration
            route_key = f"POST:{path}"
            self._registered_routes[route_key] = {
                "type": "POST",
                "path": path,
                "registered_at": time.time()
            }
            self.logger.debug(f"POST route registered: {path}")

    def unregister_route(self, method: str, path: str) -> bool:
        """
        [Function intent]
        Unregisters a previously registered route.
        
        [Design principles]
        Dynamic route lifecycle management for clean component shutdown.
        Graceful handling of missing routes.
        
        [Implementation details]
        Modifies FastAPI's internal routing table to remove the route.
        Thread-synchronized to prevent race conditions.
        Updates tracking information.
        
        Args:
            method: HTTP method of the route (e.g., "GET", "POST")
            path: URL path of the route
            
        Returns:
            bool: True if the route was unregistered, False if not found
        """
        with self._router_lock:
            route_key = f"{method}:{path}"
            if route_key not in self._registered_routes:
                self.logger.warning(f"Route not found for unregistration: {method} {path}")
                return False
                
            # Remove from FastAPI's routes
            # This requires finding the route in FastAPI's routes list and removing it
            for i, route in enumerate(self._app.routes):
                if getattr(route, "path", None) == path and getattr(route, "methods", None) and method in route.methods:
                    self._app.routes.pop(i)
                    self._registered_routes.pop(route_key)
                    self.logger.info(f"Unregistered route: {method} {path}")
                    return True
                    
            # If we get here, the route wasn't found in FastAPI's routes
            self.logger.warning(f"Route found in tracking but not in FastAPI routes: {method} {path}")
            self._registered_routes.pop(route_key, None)  # Clean up tracking anyway
            return False

    # MCP-specific registration API

    def register_mcp_tool(self, tool: MCPTool):
        """
        [Function intent]
        Registers an MCP tool with the server.
        
        [Design principles]
        Dynamic tool registration for component-provided functionality.
        Direct use of MCPTool objects with standardized interface.
        
        [Implementation details]
        Stores the tool object in the internal registry.
        Creates a FastAPI route for the tool if not already registered.
        Thread-synchronized to prevent race conditions.
        
        Args:
            tool: MCPTool instance to register
            
        Returns:
            None
        """
        with self._router_lock:
            tool_name = tool.name
            self.logger.info(f"Registering MCP tool: {tool_name}")
            
            # Store the tool object
            self._registered_tools[tool_name] = tool
            
            # Create FastAPI route for this tool if not already registered
            route_key = f"POST:/mcp/tool/{tool_name}"
            if route_key not in self._registered_routes:
                # Define the route handler
                async def tool_endpoint(request: Request, tool_data: Dict[str, Any] = Body({})):
                    # Extract headers from FastAPI request
                    headers = dict(request.headers)
                    
                    # Get session from request state (set by middleware)
                    session = getattr(request.state, "session", None)
                    
                    try:
                        # Call the tool's handler method with session
                        result = tool.handle_json_rpc(tool_data, session=session)
                        
                        # Check if this is a streaming response
                        if isinstance(result, dict) and "_streaming_handler" in result:
                            # Get streaming handler and details
                            handler = result["_streaming_handler"]
                            req = result["_request"]
                            sess = result["_session"]
                            
                            # Determine content type based on requested format
                            stream_format = None
                            content_type = "application/x-ndjson"  # Default
                            
                            # Extract streaming format from request if specified
                            if isinstance(req, dict) and isinstance(req.get("params"), dict):
                                format_str = req["params"].get("stream_format")
                                if format_str:
                                    try:
                                        from src.dbp.mcp_server.mcp.streaming import StreamFormat
                                        stream_format = StreamFormat(format_str)
                                        if stream_format == StreamFormat.EVENT_STREAM:
                                            content_type = "text/event-stream"
                                    except (ValueError, ImportError):
                                        pass
                            
                            # Create streaming response
                            self.logger.info(f"Streaming response for tool {tool_name} initiated")
                            generator = handler.handle_streaming_request(req, sess, stream_format)
                            
                            # Use streaming response handler
                            from src.dbp.mcp_server.mcp.streaming_tool import StreamingResponse
                            streaming_response = StreamingResponse(
                                generator=generator,
                                content_type=content_type
                            )
                            return streaming_response.create_response()
                        
                        # Regular JSON response
                        return JSONResponse(content=result)
                    except Exception as e:
                        self.logger.error(f"Error handling tool {tool_name}: {str(e)}", exc_info=True)
                        return JSONResponse(
                            content={"error": str(e), "type": type(e).__name__},
                            status_code=500
                        )
                
                # Register the route
                self._app.post(f"/mcp/tool/{tool_name}")(tool_endpoint)
                
                # Track registration
                self._registered_routes[route_key] = {
                    "type": "POST",
                    "path": f"/mcp/tool/{tool_name}",
                    "registered_at": time.time()
                }
                
            self.logger.debug(f"MCP tool registered: {tool_name}")

    def unregister_mcp_tool(self, tool: Union[MCPTool, str]) -> bool:
        """
        [Function intent]
        Unregisters a previously registered MCP tool.
        
        [Design principles]
        Complete lifecycle management for MCP tools.
        Clean removal of routes and handlers.
        
        [Implementation details]
        Removes the handler from the internal registry.
        Unregisters the corresponding FastAPI route.
        Thread-synchronized to prevent race conditions.
        
        Args:
            tool_name: Name of the MCP tool to unregister
            
        Returns:
            bool: True if the tool was unregistered, False if not found
        """
        with self._router_lock:
            tool_name = tool.name if isinstance(tool, MCPTool) else tool
            
            if tool_name not in self._registered_tools:
                self.logger.warning(f"MCP tool not found for unregistration: {tool_name}")
                return False
                
            # Remove from tools registry
            self._registered_tools.pop(tool_name)
            
            # Remove the route
            path = f"/mcp/tool/{tool_name}"
            self.unregister_route("POST", path)
            
            self.logger.info(f"Unregistered MCP tool: {tool_name}")
            return True

    def register_mcp_resource(self, resource_name: str, handler: ResourceHandlerFunc):
        """
        [Function intent]
        Registers an MCP resource handler with the server.
        
        [Design principles]
        Dynamic resource registration for component-provided functionality.
        Standardized MCP resource interface with callback mechanism.
        Capability-aware resource access with session support.
        
        [Implementation details]
        Stores the handler in the internal registry.
        Creates a FastAPI route for the resource if not already registered.
        Thread-synchronized to prevent race conditions.
        
        Args:
            resource_name: Name of the MCP resource
            handler: Function to handle resource requests
            
        Returns:
            None
        """
        with self._router_lock:
            self.logger.info(f"Registering MCP resource: {resource_name}")
            
            # Store the resource handler
            self._registered_resources[resource_name] = handler
            
            # Create FastAPI route for this resource if not already registered
            route_key = f"GET:/mcp/resource/{resource_name}/{{resource_id:path}}"
            if route_key not in self._registered_routes:
                # Define the route handler
                async def resource_endpoint(request: Request, resource_id: str = Path(...)):
                    # Extract query parameters and headers from FastAPI request
                    query_params = dict(request.query_params)
                    headers = dict(request.headers)
                    
                    # Get session from request state (set by middleware)
                    session = getattr(request.state, "session", None)
                    
                    try:
                        # Call the registered handler with session
                        result = handler(resource_id, query_params, headers, session=session)
                        return JSONResponse(content=result)
                    except Exception as e:
                        self.logger.error(f"Error handling resource {resource_name}: {str(e)}", exc_info=True)
                        return JSONResponse(
                            content={"error": str(e), "type": type(e).__name__},
                            status_code=500
                        )
                
                # Register the route
                self._app.get(f"/mcp/resource/{resource_name}/{{resource_id:path}}")(resource_endpoint)
                
                # Track registration
                self._registered_routes[route_key] = {
                    "type": "GET",
                    "path": f"/mcp/resource/{resource_name}/{{resource_id:path}}",
                    "registered_at": time.time()
                }
                
            self.logger.debug(f"MCP resource registered: {resource_name}")

    def unregister_mcp_resource(self, resource_name: str) -> bool:
        """
        [Function intent]
        Unregisters a previously registered MCP resource.
        
        [Design principles]
        Complete lifecycle management for MCP resources.
        Clean removal of routes and handlers.
        
        [Implementation details]
        Removes the handler from the internal registry.
        Unregisters the corresponding FastAPI route.
        Thread-synchronized to prevent race conditions.
        
        Args:
            resource_name: Name of the MCP resource to unregister
            
        Returns:
            bool: True if the resource was unregistered, False if not found
        """
        with self._router_lock:
            if resource_name not in self._registered_resources:
                self.logger.warning(f"MCP resource not found for unregistration: {resource_name}")
                return False
                
            # Remove from resources registry
            self._registered_resources.pop(resource_name)
            
            # Remove the route - this is a bit trickier as it uses a path parameter
            path = f"/mcp/resource/{resource_name}/{{resource_id:path}}"
            self.unregister_route("GET", path)
            
            self.logger.info(f"Unregistered MCP resource: {resource_name}")
            return True
            
    def cleanup_sessions(self) -> int:
        """
        [Function intent]
        Cleans up expired sessions to free resources.
        
        [Design principles]
        Periodic maintenance for memory management.
        
        [Implementation details]
        Delegates to the session manager's cleanup method.
        
        Returns:
            int: Number of expired sessions removed
        """
        return self._session_manager.cleanup_expired_sessions()
    
    def get_session_count(self) -> int:
        """
        [Function intent]
        Gets the current count of active sessions.
        
        [Design principles]
        Simple status monitoring capability.
        
        [Implementation details]
        Delegates to session manager's count method.
        
        Returns:
            int: Count of active sessions
        """
        return self._session_manager.get_session_count()
