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
# Implements the MCPServerComponent class, the main entry point for the MCP
# server integration within the DBP application framework. It conforms to the
# Component protocol, initializes the MCP server and its dependencies (adapter,
# auth, registries, handlers), registers tools and resources, and manages the
# server's lifecycle (start/stop).
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Encapsulates the entire MCP server logic.
# - Declares dependencies on core DBP components needed by its tools/resources.
# - Initializes and wires together internal MCP server parts in `initialize`.
# - Registers concrete MCP tools and resources.
# - Provides methods to start and stop the actual server process.
# - Design Decision: Component Facade for MCP Server (2025-04-15)
#   * Rationale: Integrates the MCP server functionality cleanly into the application's component lifecycle.
#   * Alternatives considered: Running the MCP server as a separate process (harder integration).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and various DBP system components.
# - Requires all helper classes within the `mcp_server` package.
# - Assumes configuration for the MCP server is available via InitializationContext.
# - Relies on placeholder implementations for the actual web server and tool/resource logic.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/core/component.py
# - All other files in src/dbp/mcp_server/
###############################################################################
# [GenAI tool change history]
# 2025-04-20T01:35:42Z : Completed dependency injection refactoring by CodeAssistant
# * Removed dependencies property
# * Made dependencies parameter required in initialize method
# * Updated documentation for dependency injection pattern
# 2025-04-20T00:31:26Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter
# * Enhanced method documentation for dependency injection
# * Updated import statements to include Dict type
# 2025-04-17T23:39:00Z : Updated to use strongly-typed configuration by CodeAssistant
# * Modified initialize() to use InitializationContext with proper typing
# * Updated configuration access to use context.get_typed_config() instead of string-based keys
# * Added the required documentation sections for the initialize method
# 2025-04-17T11:54:21Z : Added directory creation for required paths by CodeAssistant
# * Integrated with fs_utils to ensure required directories exist
# * Added validation of configuration values from config_manager
# * Removed hardcoded default values in server configuration
# 2025-04-15T16:38:29Z : Updated component to use centralized exceptions by CodeAssistant
# * Modified imports to use exceptions from centralized exceptions module
# * Removed local ComponentNotInitializedError class definition
# 2025-04-15T10:54:40Z : Initial creation of MCPServerComponent by CodeAssistant
# * Implemented Component protocol, initialization, tool/resource registration, and server start/stop.
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

# Imports for internal MCP server services
try:
    from .exceptions import (
        ComponentNotInitializedError, ComponentNotFoundError,
        AuthenticationError, AuthorizationError
    )
    from .adapter import SystemComponentAdapter
    from .auth import AuthenticationProvider
    from .error_handler import ErrorHandler
    from .registry import ToolRegistry, ResourceProvider
    from .server import MCPServer # The actual server class (placeholder web framework)
    from .mcp_protocols import MCPTool, MCPResource # Base classes
    # Import concrete tools and resources
    from .tools import (
        GeneralQueryTool, CommitMessageTool  # Only the documented tools from DESIGN.md
    )
    from .resources import (
        DocumentationResource, CodeMetadataResource, InconsistencyResource,
        RecommendationResource # Add others as implemented
    )
    # Import dependencies needed by this component
    from ..consistency_analysis.component import ConsistencyAnalysisComponent
    from ..recommendation_generator.component import RecommendationGeneratorComponent
    from ..doc_relationships.component import DocRelationshipsComponent
    from ..llm_coordinator.component import LLMCoordinatorComponent
    # Import JobManager if needed directly (though likely via adapter)
    # from ..llm_coordinator.job_manager import JobManager
except ImportError as e:
    logging.getLogger(__name__).error(f"MCPServerComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    SystemComponentAdapter = object
    ComponentNotFoundError = Exception
    AuthenticationProvider = object
    AuthenticationError = Exception
    AuthorizationError = Exception
    ErrorHandler = object
    ToolRegistry = object
    ResourceProvider = object
    MCPServer = object
    MCPTool = object
    MCPResource = object
    AnalyzeDocumentConsistencyTool = object
    GenerateRecommendationsTool = object
    ApplyRecommendationTool = object
    GeneralQueryTool = object
    DocumentationResource = object
    CodeMetadataResource = object
    InconsistencyResource = object
    RecommendationResource = object
    ConsistencyAnalysisComponent = object
    RecommendationGeneratorComponent = object
    DocRelationshipsComponent = object
    LLMCoordinatorComponent = object
    # JobManager = object


logger = logging.getLogger(__name__)

class MCPServerComponent(Component):
    """
    DBP system component responsible for running the MCP server and exposing
    system functionality via MCP tools and resources.
    """
    _initialized: bool = False
    _server: Optional[MCPServer] = None
    _adapter: Optional[SystemComponentAdapter] = None # Keep adapter reference

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "mcp_server"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
        """
        [Function intent]
        Initializes the MCP Server component, setting up the server instance,
        registries, handlers, and registering tools/resources.
        
        [Implementation details]
        Uses the strongly-typed configuration for component setup.
        Sets the _initialized flag when initialization succeeds.
        
        [Design principles]
        Explicit initialization with strong typing.
        Dependency injection for improved performance and testability.
        Type-safe configuration access.
        
        Args:
            context: Initialization context with configuration and resources
            dependencies: Dictionary of pre-resolved dependencies {name: component_instance}
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get component-specific configuration using typed config
            config = context.get_typed_config()
            mcp_config = config.mcp_server

            # Create adapter to access other components safely
            context_for_adapter = context  # Use the provided context directly
            self._adapter = SystemComponentAdapter(context_for_adapter, self.logger.getChild("adapter"))

            # Instantiate MCP sub-components
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
                # Import directory creation utilities
                from ..core.fs_utils import ensure_directories_exist, create_dbp_gitignore
                
                # Create directories relative to Git root
                ensure_directories_exist(required_directories)
                self.logger.info("Required directories created or verified successfully")
                
                # Create .gitignore file in base directory to exclude database files and logs
                if create_dbp_gitignore(base_dir):
                    self.logger.info(f"Created or verified .gitignore file in {base_dir}")
                else:
                    self.logger.warning(f"Failed to create .gitignore file in {base_dir}")
                    
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
                name=config.mcp_server.server_name,
                description=config.mcp_server.server_description,
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
            self.logger.info(f"Component '{self.name}' initialized successfully.")

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
        Instantiates and registers only the officially documented MCP tools.
        
        [Implementation details]
        Creates instances of the two authorized tool classes (dbp_general_query and dbp_commit_message)
        and registers them with the MCP tool registry.
        
        [Design principles]
        Documentation as Source of Truth - only tools documented in DESIGN.md are registered.
        Explicit over implicit - clearly defines which tools are allowed to be registered.
        """
        if not self._adapter: raise RuntimeError("Adapter not initialized.")
        self.logger.debug("Registering authorized MCP tools...")

        # Only register the two tools documented in DESIGN.md
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
        
        self.logger.info(f"Registered {count}/{len(tools_to_register)} documented MCP tools.")


    def _register_resources(self, resource_provider: ResourceProvider):
        """Instantiates and registers all MCP resources."""
        if not self._adapter: raise RuntimeError("Adapter not initialized.")
        self.logger.debug("Registering MCP resources...")

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
        self.logger.info(f"Registered {count}/{len(resources_to_register)} MCP resources.")


    def start_server(self):
        """Starts the underlying MCP server process."""
        if not self.is_initialized or not self._server:
            raise ComponentNotInitializedError(self.name)
        if self._server.is_running:
             self.logger.warning("MCP server is already running.")
             return
        self._server.start()

    def stop_server(self):
        """Stops the underlying MCP server process."""
        if not self.is_initialized or not self._server:
            self.logger.warning(f"Attempted to stop MCP server component '{self.name}' but it's not initialized or server is missing.")
            return
        if not self._server.is_running:
             self.logger.warning("MCP server is not running.")
             return
        self._server.stop()

    def shutdown(self) -> None:
        """Shuts down the MCP server component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        self.stop_server() # Ensure server is stopped
        self._server = None
        self._adapter = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized
