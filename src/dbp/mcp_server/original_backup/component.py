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
# Implements a minimized version of the MCPServerComponent class for progressive
# integration testing. This component maintains the same interface as the original
# but avoids dependencies on other system components except config_manager.
# It allows the MCP server to run in standalone mode, serving requests with
# standardized error responses.
###############################################################################
# [Source file design principles]
# - Maintains the Component protocol interface (`src/dbp/core/component.py`).
# - Preserves integration with config_manager.
# - Minimizes dependencies on other system components.
# - Returns standardized error responses for tools/resources in standalone mode.
# - Provides clear logging for standalone mode operation.
# - Design Decision: Standalone Component (2025-04-25)
#   * Rationale: Enables MCP server testing with minimal dependencies.
#   * Alternatives considered: Dynamic component loading (more complex, harder to isolate).
###############################################################################
# [Source file constraints]
# - Must maintain the same interface as the original component.
# - Should maintain integration with config_manager.
# - Should not attempt to access unavailable components.
# - Must provide clear log messages when operating in standalone mode.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# system:- src/dbp/core/component.py
# system:- src/dbp/core/fs_utils.py
# system:- src/dbp/config/config_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-04-25T00:16:00Z : Created minimized component by CodeAssistant
# * Created standalone version of MCPServerComponent for progressive integration testing
# * Commented out dependencies on other system components while preserving config_manager integration
# * Added clear logging for standalone mode operation
###############################################################################

import logging
import os
from typing import Dict, List, Optional, Any

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    from ..core.fs_utils import ensure_directory_exists, ensure_directories_exist
    Config = Any # Placeholder
    MCPServerConfig = Any # Placeholder
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for MCPServerComponent.", exc_info=True)
    class Component: pass
    class InitializationContext: pass
    Config = Any
    MCPServerConfig = Any

# Imports for internal MCP server services with minimized dependencies
try:
    # Import local exceptions or create placeholders
    try:
        from .exceptions import (
            ComponentNotInitializedError, ComponentNotFoundError,
            AuthenticationError, AuthorizationError
        )
    except ImportError:
        # Define local versions if not available
        class ComponentNotInitializedError(Exception):
            """Exception raised when a component is accessed before initialization."""
            def __init__(self, component_name: str = "unknown"):
                self.component_name = component_name
                super().__init__(f"Component not initialized: '{component_name}'")
                
        class ComponentNotFoundError(Exception):
            """Exception raised when a component is not found or not initialized."""
            def __init__(self, component_name: str = "unknown"):
                self.component_name = component_name
                super().__init__(f"Component not found or not initialized: '{component_name}'")
                
        class AuthenticationError(Exception):
            """Exception raised during authentication failures."""
            pass
            
        class AuthorizationError(Exception):
            """Exception raised during authorization failures."""
            pass
    
    # Import adapter and MCP server components
    # Use the minimized version from the minimized_mcp directory for these imports
    from .adapter import SystemComponentAdapter
    from .auth import AuthenticationProvider
    from .error_handler import ErrorHandler
    from .registry import ToolRegistry, ResourceProvider
    from .server import MCPServer
    from .mcp_protocols import MCPTool, MCPResource
    
    # Import tools and resources - use minimized versions
    from .tools import (
        GeneralQueryTool, CommitMessageTool
    )
    from .resources import (
        DocumentationResource, CodeMetadataResource, InconsistencyResource,
        RecommendationResource
    )
    
    # DO NOT import other components - commented out to minimize dependencies
    # Only config_manager should be imported when needed through the adapter
    """
    from ..consistency_analysis.component import ConsistencyAnalysisComponent
    from ..recommendation_generator.component import RecommendationGeneratorComponent
    from ..doc_relationships.component import DocRelationshipsComponent
    from ..llm_coordinator.component import LLMCoordinatorComponent
    """
except ImportError as e:
    logging.getLogger(__name__).error(f"MCPServerComponent ImportError: {e}. Using mock implementations.", exc_info=True)
    # Mock implementations for essential classes
    class SystemComponentAdapter:
        """Mock adapter"""
        def __init__(self, context=None, logger_override=None): pass
    
    class ComponentNotFoundError(Exception): pass
    class ComponentNotInitializedError(Exception): pass
    class AuthenticationError(Exception): pass
    class AuthorizationError(Exception): pass
    class ErrorHandler: 
        """Mock error handler"""
        def __init__(self, logger_override=None): pass
    
    class ToolRegistry:
        """Mock tool registry"""
        def __init__(self, logger_override=None): pass
        def register_tool(self, tool): pass
    
    class ResourceProvider:
        """Mock resource provider"""
        def __init__(self, logger_override=None): pass
        def register_resource(self, resource): pass
    
    class MCPServer:
        """Mock MCP server"""
        def __init__(self, host, port, name, description, version, tool_registry,
                     resource_provider, auth_provider=None, error_handler=None, 
                     logger_override=None):
            self.is_running = False
            self.config = {}
        def start(self): 
            self.is_running = True
        def stop(self): 
            self.is_running = False
    
    class MCPTool:
        """Mock MCPTool"""
        def __init__(self, name=None, description=None, logger_override=None): pass
    
    class MCPResource:
        """Mock MCPResource"""
        def __init__(self, name=None, description=None, logger_override=None): pass
    
    # Mock tools and resources
    class GeneralQueryTool:
        """Mock tool"""
        def __init__(self, adapter=None, logger_override=None): 
            self.name = "dbp_general_query"
    
    class CommitMessageTool:
        """Mock tool"""
        def __init__(self, adapter=None, logger_override=None): 
            self.name = "dbp_commit_message"
    
    class DocumentationResource:
        """Mock resource"""
        def __init__(self, adapter=None, logger_override=None): 
            self.name = "documentation"
    
    class CodeMetadataResource:
        """Mock resource"""
        def __init__(self, adapter=None, logger_override=None): 
            self.name = "code_metadata"
    
    class InconsistencyResource:
        """Mock resource"""
        def __init__(self, adapter=None, logger_override=None): 
            self.name = "inconsistencies"
    
    class RecommendationResource:
        """Mock resource"""
        def __init__(self, adapter=None, logger_override=None):
            self.name = "recommendations"


logger = logging.getLogger(__name__)

class MCPServerComponent(Component):
    """
    Minimized version of the DBP system component responsible for running the MCP server.
    This version operates in standalone mode with minimal dependencies.
    """
    _initialized: bool = False
    _server: Optional[MCPServer] = None
    _adapter: Optional[SystemComponentAdapter] = None
    _standalone_mode = True  # Flag indicating we're running in standalone mode

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "mcp_server"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component] = None) -> None:
        """
        [Function intent]
        Initializes the MCP Server component in standalone mode, setting up a minimized
        server with mock tools and resources.

        [Implementation details]
        Uses the configuration for directory setup but avoids initializing actual component
        dependencies other than config_manager.

        [Design principles]
        Explicit initialization with minimal dependencies.
        Clear logging of standalone operation mode.

        Args:
            context: Initialization context with configuration and resources
            dependencies: Dictionary of pre-resolved dependencies (only config_manager may be used)
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.warning(f"Initializing component '{self.name}' in STANDALONE MODE with minimal dependencies")

        try:
            # Get component-specific configuration using typed config
            config = context.get_typed_config()
            mcp_config = config.mcp_server

            # Create adapter to access config_manager safely (other components will be mocked)
            self._adapter = SystemComponentAdapter(context, self.logger.getChild("adapter"))

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
            db_path = config.database.path

            if not base_dir or not logs_dir or not pid_file or not cli_config_file or not db_path:
                missing = []
                if not base_dir: missing.append('general.base_dir')
                if not logs_dir: missing.append('mcp_server.logs_dir')
                if not pid_file: missing.append('mcp_server.pid_file')
                if not cli_config_file: missing.append('mcp_server.cli_config_file')
                if not db_path: missing.append('database.path')
                error_msg = f"Missing required configuration values: {', '.join(missing)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            # Create required directories
            self.logger.info(f"Ensuring required directories exist using base directory: {base_dir}")
            required_directories = [
                logs_dir,
                os.path.dirname(pid_file),
                os.path.dirname(cli_config_file),
                os.path.dirname(db_path)
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

            # Create the MCP server instance with FastAPI/Uvicorn
            self._server = MCPServer(
                host=config.mcp_server.host,
                port=int(config.mcp_server.port),
                name=f"{config.mcp_server.server_name} (STANDALONE MODE)",
                description=f"{config.mcp_server.server_description} - Running with minimal dependencies for progressive integration testing",
                version=config.mcp_server.server_version,
                tool_registry=tool_registry,
                resource_provider=resource_provider,
                auth_provider=auth_provider,
                error_handler=error_handler,
                logger_override=self.logger.getChild("server_instance")
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

            # Register tools and resources
            self._register_tools(tool_registry)
            self._register_resources(resource_provider)

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully in STANDALONE MODE.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _register_tools(self, tool_registry: ToolRegistry):
        """
        [Function intent]
        Registers standalone mode versions of the MCP tools that return error responses.

        [Implementation details]
        Creates instances of the two authorized tools that are configured to return
        standardized error responses indicating standalone mode operation.

        [Design principles]
        Maintains the same interface as the original but with minimal dependencies.
        """
        if not self._adapter: raise RuntimeError("Adapter not initialized.")
        self.logger.info("[STANDALONE MODE] Registering authorized MCP tools...")

        # Register the two tools documented in DESIGN.md - they will return error responses in standalone mode
        tools_to_register = [
            GeneralQueryTool(self._adapter, self.logger.getChild("tool_general_query")),
            CommitMessageTool(self._adapter, self.logger.getChild("tool_commit_message")),
        ]

        count = 0
        for tool_instance in tools_to_register:
            try:
                tool_registry.register_tool(tool_instance)
                count += 1
            except (ValueError, TypeError) as e:
                self.logger.error(f"Failed to register MCP tool '{getattr(tool_instance, 'name', 'unknown')}': {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error registering MCP tool '{getattr(tool_instance, 'name', 'unknown')}': {e}", exc_info=True)

        self.logger.info(f"[STANDALONE MODE] Registered {count}/{len(tools_to_register)} MCP tools.")


    def _register_resources(self, resource_provider: ResourceProvider):
        """
        [Function intent]
        Registers standalone mode versions of MCP resources that return error responses.

        [Implementation details]
        Creates instances of MCP resources that are configured to return standardized error
        responses indicating standalone mode operation.

        [Design principles]
        Maintains the same interface as the original but with minimal dependencies.
        """
        if not self._adapter: raise RuntimeError("Adapter not initialized.")
        self.logger.info("[STANDALONE MODE] Registering MCP resources...")

        resources_to_register = [
            DocumentationResource(self._adapter, self.logger.getChild("res_docs")),
            CodeMetadataResource(self._adapter, self.logger.getChild("res_code_meta")),
            InconsistencyResource(self._adapter, self.logger.getChild("res_inconsistencies")),
            RecommendationResource(self._adapter, self.logger.getChild("res_recommendations")),
        ]

        count = 0
        for resource_instance in resources_to_register:
             try:
                  resource_provider.register_resource(resource_instance)
                  count += 1
             except (ValueError, TypeError) as e:
                  self.logger.error(f"Failed to register MCP resource '{getattr(resource_instance, 'name', 'unknown')}': {e}")
             except Exception as e:
                  self.logger.error(f"Unexpected error registering MCP resource '{getattr(resource_instance, 'name', 'unknown')}': {e}", exc_info=True)
        self.logger.info(f"[STANDALONE MODE] Registered {count}/{len(resources_to_register)} MCP resources.")


    def start_server(self):
        """
        [Function intent]
        Starts the underlying MCP server process in standalone mode.

        [Implementation details]
        Delegates to the MCPServer instance while providing clear logging about standalone operation.

        [Design principles]
        Maintains the same interface as the original component.
        """
        if not self.is_initialized or not self._server:
            raise ComponentNotInitializedError(self.name)
        if self._server.is_running:
             self.logger.warning("[STANDALONE MODE] MCP server is already running.")
             return
        self.logger.info("[STANDALONE MODE] Starting MCP server...")
        self._server.start()
        self.logger.info("[STANDALONE MODE] MCP server started successfully. Server will return error responses for all tool/resource requests.")

    def stop_server(self):
        """
        [Function intent]
        Stops the underlying MCP server process.

        [Implementation details]
        Delegates to the MCPServer instance while providing clear logging about standalone operation.

        [Design principles]
        Maintains the same interface as the original component.
        """
        if not self.is_initialized or not self._server:
            self.logger.warning(f"[STANDALONE MODE] Attempted to stop MCP server component '{self.name}' but it's not initialized or server is missing.")
            return
        if not self._server.is_running:
             self.logger.warning("[STANDALONE MODE] MCP server is not running.")
             return
        self.logger.info("[STANDALONE MODE] Stopping MCP server...")
        self._server.stop()
        self.logger.info("[STANDALONE MODE] MCP server stopped successfully.")

    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the MCP server component.

        [Implementation details]
        Stops the server and cleans up resources while providing clear logging about standalone operation.

        [Design principles]
        Maintains the same interface as the original component.
        """
        self.logger.info(f"[STANDALONE MODE] Shutting down component '{self.name}'...")
        self.stop_server() # Ensure server is stopped
        self._server = None
        self._adapter = None
        self._initialized = False
        self.logger.info(f"[STANDALONE MODE] Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized
