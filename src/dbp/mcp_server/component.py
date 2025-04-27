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
# Implements the MCPServerComponent class using FastMCP library.
# This component maintains the same interface as the original but replaces the
# homemade MCP implementation with FastMCP for better compliance with the MCP specification.
###############################################################################
# [Source file design principles]
# - Maintains the Component protocol interface (`src/dbp/core/component.py`).
# - Preserves integration with config_manager.
# - Uses FastMCP for MCP protocol implementation.
# - Maintains the same lifecycle management API.
# - Provides clear logging for operation.
# - Simplifies component implementation by delegating to MCPServer class.
###############################################################################
# [Source file constraints]
# - Must maintain the same interface as the original component.
# - Should maintain integration with config_manager.
# - Must provide clear log messages during operation.
# - Must use FastMCP for MCP protocol implementation.
###############################################################################
# [Dependencies]
# codebase:doc/DESIGN.md
# codebase:src/dbp/core/component.py
# codebase:src/dbp/core/fs_utils.py
# codebase:src/dbp/config/config_manager.py
# codebase:src/dbp/mcp_server/server.py
# system:fastmcp
###############################################################################
# [GenAI tool change history]
# 2025-04-27T17:26:00Z : Updated ComponentNotInitializedError import by CodeAssistant
# * Removed local ComponentNotInitializedError class definition
# * Added import for ComponentNotInitializedError from core.exceptions
# * Improved code organization by using centralized exception definitions
# 2025-04-27T00:16:00Z : Replaced homemade MCP implementation with FastMCP by CodeAssistant
# * Completely replaced the homemade MCP implementation with FastMCP
# * Removed register_mcp_tool and register_mcp_resource methods
# * Modified component to use MCPServer class from server.py
# * Added wait_for_server_exit() method for __main__.py
# * Removed start_server() method
# * Simplified component implementation
# 2025-04-26T02:05:00Z : Removed _register_resources method by CodeAssistant
# * Removed _register_resources method as resources are registered by external components
# * Updated initialization to no longer call _register_resources
# * Made code more compliant with the distributed MCP resource registration concept
# 2025-04-26T02:00:00Z : Removed _register_tools method by CodeAssistant
# * Removed _register_tools method as it's not needed - tools are registered by external components
# * Updated initialization to no longer call _register_tools
# * Made code more compliant with the distributed MCP tool registration concept
###############################################################################

import logging
import os
from typing import Dict, Optional

# Core component imports
from ..core.component import Component, InitializationContext
from ..core.fs_utils import ensure_directories_exist
from ..core.exceptions import ComponentNotInitializedError

# Import MCPServer class
from .server import MCPServer

logger = logging.getLogger(__name__)

class MCPServerComponent(Component):
    """
    [Class intent]
    DBP system component responsible for running the MCP server using FastMCP.
    This component provides MCP protocol support through FastMCP while maintaining
    the same interface as the original component.
    
    [Design principles]
    - Uses FastMCP for MCP protocol implementation
    - Maintains the Component protocol interface
    - Preserves integration with config_manager
    - Provides clean API for server lifecycle management
    
    [Implementation details]
    - Creates and manages MCPServer instance
    - Handles component lifecycle
    - Provides methods for server management
    """
    _initialized: bool = False
    _server: Optional[MCPServer] = None

    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of the component.
        
        [Design principles]
        Consistent component identification.
        
        [Implementation details]
        Returns a static string identifier.
        
        Returns:
            str: The component name
        """
        return "mcp_server"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component] = None) -> None:
        """
        [Function intent]
        Initializes the MCP Server component with FastMCP integration.

        [Design principles]
        Explicit initialization with minimal dependencies.
        Clear logging of initialization progress.
        Progressive initialization with detailed status tracking.

        [Implementation details]
        Creates an MCPServer instance with the provided configuration.
        Sets up required directories and configuration.
        Starts the server.

        Args:
            context: Initialization context with configuration and resources
            dependencies: Dictionary of pre-resolved dependencies (only config_manager may be used)
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}' with FastMCP integration")
        
        try:
            # Get component-specific configuration using typed config
            config = context.get_typed_config()
            
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
                raise ValueError(error_msg)

            # Create required directories
            self.logger.info(f"Ensuring required directories exist using base directory: {base_dir}")
            required_directories = [
                logs_dir,
                os.path.dirname(pid_file),
                os.path.dirname(cli_config_file)
            ]

            # Create all directories
            try:
                # Create directories relative to Git root
                ensure_directories_exist(required_directories)
                self.logger.info("Required directories created or verified successfully")

            except RuntimeError as e:
                self.logger.error(f"Failed to resolve paths from Git root: {e}")
                raise RuntimeError(f"Failed to set up directories: {e}") from e
            except OSError as e:
                self.logger.error(f"Failed to create required directories: {e}")
                raise RuntimeError(f"Failed to create required directories: {e}") from e

            # Create the MCPServer instance
            self._server = MCPServer(
                name=config.mcp_server.server_name,
                description=config.mcp_server.server_description,
                version=config.mcp_server.server_version,
                host=config.mcp_server.host,
                port=config.mcp_server.port,
                workers=config.mcp_server.workers
            )
            
            # Start the server
            self._server.start()
            
            # Store configuration for later use
            self.config = config
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def wait_for_server_exit(self):
        """
        [Function intent]
        Waits indefinitely until the server is stopped.
        This method is intended to be called from __main__.py to keep the process running.

        [Design principles]
        - Blocking wait for server exit
        - Replaces the previous start_server() method
        - Non-blocking server startup with blocking wait
        
        [Implementation details]
        - Delegates to MCPServer.wait_for_exit()
        - Verifies component is initialized
        
        Returns:
            None
            
        Raises:
            RuntimeError: If component is not initialized
        """
        if not self.is_initialized or not self._server:
            raise RuntimeError(f"Component '{self.name}' not initialized")
            
        self.logger.info("Waiting for MCP server to exit")
        self._server.wait_for_exit()
        self.logger.info("MCP server exited")

    def stop_server(self):
        """
        [Function intent]
        Stops the MCP server.

        [Design principles]
        - Clean server shutdown
        - Maintains the same interface as the original component
        
        [Implementation details]
        - Delegates to MCPServer.stop()
        - Verifies component is initialized
        
        Returns:
            None
            
        Raises:
            RuntimeError: If component is not initialized
        """
        if not self.is_initialized or not self._server:
            raise RuntimeError(f"Component '{self.name}' not initialized")
            
        self.logger.info("Stopping MCP server")
        self._server.stop()
        self.logger.info("MCP server stopped")

    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the MCP server component.

        [Design principles]
        - Clean component shutdown
        - Maintains the same interface as the original component
        
        [Implementation details]
        - Stops the server
        - Cleans up resources
        
        Returns:
            None
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        if self._server:
            self._server.stop()
        self._server = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """
        [Function intent]
        Returns True if the component is initialized.
        
        [Design principles]
        - Simple state checking
        
        [Implementation details]
        - Returns the _initialized flag
        
        Returns:
            bool: True if initialized, False otherwise
        """
        return self._initialized
        
    @property
    def mcp(self):
        """
        [Function intent]
        Returns the FastMCP instance.
        
        [Design principles]
        - Provides access to the underlying FastMCP instance
        - Enables direct tool and resource registration using decorators
        
        [Implementation details]
        - Returns the FastMCP instance from the MCPServer
        
        Returns:
            FastMCP: The FastMCP instance
            
        Raises:
            RuntimeError: If component is not initialized
        """
        if not self.is_initialized or not self._server:
            raise RuntimeError(f"Component '{self.name}' not initialized")
            
        return self._server.mcp
