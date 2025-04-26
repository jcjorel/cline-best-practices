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
# Implements a version of the MCPServerComponent class for progressive
# integration testing. This component maintains the same interface as the original
# but avoids dependencies on other system components except config_manager.
# It allows the MCP server to serve requests with standardized error responses.
###############################################################################
# [Source file design principles]
# - Maintains the Component protocol interface (`src/dbp/core/component.py`).
# - Preserves integration with config_manager.
# - Minimizes dependencies on other system components.
# - Returns standardized error responses for tools/resources.
# - Provides clear logging for operation.
###############################################################################
# [Source file constraints]
# - Must maintain the same interface as the original component.
# - Should maintain integration with config_manager.
# - Should not attempt to access unavailable components.
# - Must provide clear log messages during operation.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# system:- src/dbp/core/component.py
# system:- src/dbp/core/fs_utils.py
# system:- src/dbp/config/config_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-04-26T02:05:00Z : Removed _register_resources method by CodeAssistant
# * Removed _register_resources method as resources are registered by external components
# * Updated initialization to no longer call _register_resources
# * Made code more compliant with the distributed MCP resource registration concept
# 2025-04-26T02:00:00Z : Removed _register_tools method by CodeAssistant
# * Removed _register_tools method as it's not needed - tools are registered by external components
# * Updated initialization to no longer call _register_tools
# * Made code more compliant with the distributed MCP tool registration concept
# 2025-04-25T17:25:00Z : Implemented signal-based server control mechanism by CodeAssistant
# * Modified start_server to wait indefinitely until explicitly stopped via stop_server()
# * Added thread synchronization using threading.Event for clean start/stop coordination
# * Improved error handling with fail-fast approach that raises exceptions for invalid states
# * Updated HTTP server shutdown to stop properly when stop signal is received
# 2025-04-25T17:05:00Z : Added server HTTP connectivity verification in start_server method by CodeAssistant
# * Modified start_server to test and verify HTTP connectivity before returning
# * Added prominent visual log message when server is ready to serve requests
# * Implemented timeout-based testing to ensure server is actually working
# * Added error handling to stop server if connectivity test fails
###############################################################################

import logging
import os
from typing import Dict, List, Optional, Any

# Core component imports
from ..core.component import Component, InitializationContext
from ..core.fs_utils import ensure_directory_exists, ensure_directories_exist
Config = Any # Placeholder
MCPServerConfig = Any # Placeholder

# Imports for internal MCP server services with minimized dependencies
# Import adapter and MCP server components
# Use the minimized version from the minimized_mcp directory for these imports
from .adapter import SystemComponentAdapter
from .auth import AuthenticationProvider
from .error_handler import ErrorHandler
from .registry import ToolRegistry, ResourceProvider
from .server import MCPServer
from .mcp_protocols import MCPTool, MCPResource
from .exceptions import ComponentNotInitializedError, ComponentNotFoundError, AuthenticationError, AuthorizationError
    

logger = logging.getLogger(__name__)

class MCPServerComponent(Component):
    """
    Minimized version of the DBP system component responsible for running the MCP server.
    This version operates with minimal dependencies.
    """
    _initialized: bool = False
    _server: Optional[MCPServer] = None
    _adapter: Optional[SystemComponentAdapter] = None
    _stop_requested = False  # Signal to stop server operations
    _server_ready = False    # Signal that server is ready to serve requests
    _stop_event = None       # Thread synchronization event for signaling stop

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "mcp_server"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component] = None) -> None:
        """
        [Function intent]
        Initializes the MCP Server component with minimized dependencies,
        setting up a server instance ready for external tool registration.

        [Implementation details]
        Uses the configuration for directory setup but avoids initializing actual component
        dependencies other than config_manager. Updates initialization status that's exposed
        through the health API to provide detailed progress information.

        [Design principles]
        Explicit initialization with minimal dependencies.
        Clear logging of initialization progress.
        Progressive initialization with detailed status tracking.

        Args:
            context: Initialization context with configuration and resources
            dependencies: Dictionary of pre-resolved dependencies (only config_manager may be used)
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.warning(f"Initializing component '{self.name}' with minimal dependencies")
        
        # Initialize status tracking for health endpoint
        self._init_status = {
            'state': 'initializing',
            'current_step': 'setup',
            'total_steps': 5,  # setup, config, directories, components, server
            'message': 'Starting MCP server initialization',
            'completed_steps': [],
            'error': None
        }
        
        try:
            # Update status to configuration step
            self._update_init_status('config', 'Loading configuration')
            # Get component-specific configuration using typed config
            config = context.get_typed_config()
            mcp_config = config.mcp_server

            # Create adapter to access config_manager safely (other components will be mocked)
            self._adapter = SystemComponentAdapter(context, self.logger.getChild("adapter"))

            # Update status to creating components
            self._update_init_status('components', 'Creating MCP server components')
            
            # Instantiate MCP sub-components with minimal functionality
            auth_provider = AuthenticationProvider(config=mcp_config, logger_override=self.logger.getChild("auth")) if mcp_config.auth_enabled else None
            error_handler = ErrorHandler(logger_override=self.logger.getChild("error_handler"))
            tool_registry = ToolRegistry(logger_override=self.logger.getChild("tool_registry"))
            resource_provider = ResourceProvider(logger_override=self.logger.getChild("resource_provider"))

            # Get configuration values using typed configuration
            base_dir = config.general.base_dir
            logs_dir = config.mcp_server.logs_dir
            pid_file = config.mcp_server.pid_file
            cli_config_file = config.mcp_server.cli_config_file

            # Check for required configuration values
            if not base_dir or not logs_dir or not pid_file or not cli_config_file:
                missing = []
                if not base_dir: missing.append('general.base_dir')
                if not logs_dir: missing.append('mcp_server.logs_dir')
                if not pid_file: missing.append('mcp_server.pid_file')
                if not cli_config_file: missing.append('mcp_server.cli_config_file')
                error_msg = f"Missing required configuration values: {', '.join(missing)}"
                self.logger.error(error_msg)
                
                # Update status to failure 
                self._update_init_status('failed', f'Missing configuration: {", ".join(missing)}', error=error_msg)
                
                raise ValueError(error_msg)

            # Update status to creating directories
            self._update_init_status('directories', 'Creating required directories')
            
            # Create required directories
            self.logger.info(f"Ensuring required directories exist using base directory: {base_dir}")
            required_directories = [
                logs_dir,
                os.path.dirname(pid_file),
                os.path.dirname(cli_config_file)
                # Database path removed to minimize dependencies
            ]

            # Create all directories
            try:
                # Create directories relative to Git root
                ensure_directories_exist(required_directories)
                self.logger.info("Required directories created or verified successfully")

            except RuntimeError as e:
                self.logger.error(f"Failed to resolve paths from Git root: {e}")
                # Update status to failure
                self._update_init_status('failed', 'Failed to resolve directory paths', error=str(e))
                raise RuntimeError(f"Failed to set up directories: {e}") from e
            except OSError as e:
                self.logger.error(f"Failed to create required directories: {e}")
                # Update status to failure
                self._update_init_status('failed', 'Failed to create directories', error=str(e))
                raise RuntimeError(f"Failed to create required directories: {e}") from e

            # Update status to creating server
            self._update_init_status('server', 'Creating MCP server instance')
            
            # Create the MCP server instance with FastAPI/Uvicorn
            self._server = MCPServer(
                host=config.mcp_server.host,
                port=int(config.mcp_server.port),
                name=config.mcp_server.server_name,
                description=f"{config.mcp_server.server_description} - Running with minimal dependencies for progressive integration testing",
                version=config.mcp_server.server_version,
                logger_override=self.logger.getChild("server_instance"),
                # Add capability negotiation parameters with default values
                require_negotiation=False,  # For backward compatibility
                session_timeout_seconds=3600  # Default 1 hour session timeout
            )

            # Set the server configuration for FastAPI/Uvicorn settings
            self._server.config = {
                "workers": config.mcp_server.workers,
                "enable_cors": config.mcp_server.enable_cors,
                "cors_origins": config.mcp_server.cors_origins,
                "cors_methods": config.mcp_server.cors_methods,
                "cors_headers": config.mcp_server.cors_headers,
                "cors_allow_credentials": config.mcp_server.cors_allow_credentials,
                "keep_alive": config.mcp_server.keep_alive,
                "graceful_shutdown_timeout": config.mcp_server.graceful_shutdown_timeout
            }

            # Share initialization status with server instance 
            self._server._init_status = self._init_status

            # Update status to ready state
            self._update_init_status('ready', 'MCP server initialization complete')
            
            # Record startup time for uptime calculation
            import time
            self._server._startup_time = time.time()
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             # Update status to failure
             self._update_init_status('failed', f'Missing dependency: {e}', error=str(e))
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            # Update status to failure
            self._update_init_status('failed', 'Initialization failed', error=str(e))
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def start_server(self):
        """
        [Function intent]
        Starts the underlying MCP server process and waits indefinitely until explicitly stopped.

        [Implementation details]
        Delegates to the MCPServer instance while providing clear logging.
        Performs HTTP connectivity tests to ensure the server is actually working.
        Uses a threading.Event as a synchronization mechanism to block until stop_server() is called.

        [Design principles]
        Maintains the same interface as the original component.
        Implements proper verification to ensure server is actually operational.
        Uses signal-based blocking to keep the server thread active until explicitly stopped.
        """
        if not self.is_initialized or not self._server:
            raise ComponentNotInitializedError(self.name)
        if self._server.is_running:
             self.logger.warning("MCP server is already running.")
             return
        
        # Reset status flags
        self._stop_requested = False
        self._server_ready = False
        
        # Create stop event for synchronization if it doesn't exist
        import threading
        if self._stop_event is None:
            self._stop_event = threading.Event()
        else:
            self._stop_event.clear()  # Reset the event
             
        self.logger.info("Starting MCP server...")
        self._server.start()
        
        # Test server connectivity to ensure it's actually working
        self.logger.info("Testing HTTP server connectivity...")
        
        import time
        import socket
        import requests
        from urllib.parse import urljoin
        
        # Get configuration values from the adapter's context
        config = self._adapter.context.get_typed_config()
        host = config.mcp_server.host
        port = config.mcp_server.port
        timeout = config.initialization.timeout_seconds
        
        # Set up connectivity test parameters
        server_url = f"http://{host}:{port}"
        health_endpoint = urljoin(server_url, "/health")
        
        # Try to connect to the server with timeout
        server_working = False
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # First check if port is accepting connections
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex((host, int(port)))
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
        
        # Check if server test was successful
        if not server_working:
            error_msg = f"HTTP server failed connectivity test after {timeout} seconds"
            self.logger.error(error_msg)
            
            # Stop the server since it's not functioning properly
            try:
                self._server.stop()
            except Exception as e:
                self.logger.error(f"Failed to stop non-responsive server: {e}")
            
            # Clear the stop event since we're not going to wait
            self._stop_event.set()
                
            raise RuntimeError(error_msg)
            
        # Server is verified as working
        self.logger.info("=== MCP SERVER READY ===")
        self.logger.info(f"MCP server is now ready to serve HTTP requests on {host}:{port}")
        self.logger.info("======================")
        self.logger.info("MCP server started successfully and verified operational. Server will return error responses for externally requested tools/resources.")
        
        # Set server ready flag
        self._server_ready = True
        
        # Wait indefinitely until stop_server() is called
        self.logger.info("Waiting for stop signal. Call stop_server() to terminate.")
        self._stop_event.wait()
        self.logger.info("Stop signal received. Stopping HTTP server...")
        
        # Actually stop the HTTP server - fail fast by raising exceptions
        if self._server.is_running:
            self._server.stop()
            self.logger.info("HTTP server stopped successfully after receiving stop signal.")
        
        # Reset status flags
        self._server_ready = False
        
        self.logger.info("Server operation completed.")

    def stop_server(self):
        """
        [Function intent]
        Signals the server to stop by setting the stop event.

        [Implementation details]
        Sets the stop event to unlock start_server() which will handle actual server shutdown.
        Provides clear logging during operation.

        [Design principles]
        Maintains the same interface as the original component.
        Uses event-based signaling for clean thread synchronization.
        Follows fail-fast principle by raising exceptions for invalid states.
        """
        if not self.is_initialized:
            raise ComponentNotInitializedError(self.name)
            
        # Signal the stop event to unlock start_server() which will handle the actual shutdown
        self.logger.info("Signaling server to stop...")
        
        # Set the stop requested flag
        self._stop_requested = True
        
        # Signal the stop event to unlock start_server()
        if self._stop_event:
            self._stop_event.set()
            self.logger.info("Stop signal sent successfully.")
        else:
            raise RuntimeError(f"No active server event to signal for component '{self.name}'")

    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the MCP server component.

        [Implementation details]
        Stops the server and cleans up resources while providing clear logging.

        [Design principles]
        Maintains the same interface as the original component.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        self.stop_server() # Ensure server is stopped
        self._server = None
        self._adapter = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    def _update_init_status(self, step: str, message: str, error: str = None):
        """
        [Function intent]
        Updates the initialization status of the MCP server for health endpoint reporting.
        
        [Implementation details]
        Tracks initialization progress by updating the _init_status dictionary with 
        the current step, message, and any error information. Also maintains a list 
        of completed steps to show initialization progress.
        
        [Design principles]
        Detailed status tracking for observability.
        Progressive status updates for client-side progress monitoring.
        Centralizes all status updates for consistency.
        
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
            self.logger.info(f"MCP server is now ready to serve HTTP requests on {getattr(self._server, 'host', 'localhost')}:{getattr(self._server, 'port', '?')}")
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
            
        # Update the server instance's copy of the status if it exists
        if hasattr(self, '_server') and self._server and hasattr(self._server, '_init_status'):
            self._server._init_status = self._init_status
            
        # Log the status update
        if error:
            self.logger.error(f"Server initialization status: {step} - {message} - ERROR: {error}")
        else:
            self.logger.info(f"Server initialization status: {step} - {message}")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized
