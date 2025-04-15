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
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
# - src/dbp/core/component.py
# - All other files in src/dbp/mcp_server/
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:54:40Z : Initial creation of MCPServerComponent by CodeAssistant
# * Implemented Component protocol, initialization, tool/resource registration, and server start/stop.
###############################################################################

import logging
from typing import List, Optional, Any

# Core component imports
try:
    from ..core.component import Component, InitializationContext
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
    from .adapter import SystemComponentAdapter, ComponentNotFoundError
    from .auth import AuthenticationProvider, AuthenticationError, AuthorizationError
    from .error_handler import ErrorHandler
    from .registry import ToolRegistry, ResourceProvider
    from .server import MCPServer # The actual server class (placeholder web framework)
    from .mcp_protocols import MCPTool, MCPResource # Base classes
    # Import concrete tools and resources
    from .tools import (
        AnalyzeDocumentConsistencyTool, GenerateRecommendationsTool, ApplyRecommendationTool,
        GeneralQueryTool # Add others as implemented
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

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

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

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Depends on all components whose functionality is exposed via tools/resources
        return [
            "consistency_analysis",
            "recommendation_generator",
            "doc_relationships",
            "llm_coordinator",
            "metadata_extraction", # Needed by adapter/resources
            "memory_cache",        # Needed by adapter/resources
            # Add config_manager_comp if needed directly
        ]

    def initialize(self, context: InitializationContext):
        """
        Initializes the MCP Server component, setting up the server instance,
        registries, handlers, and registering tools/resources.

        Args:
            context: The initialization context.
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get component-specific configuration
            mcp_config = context.config.get(self.name, {}) # Assumes dict-like config

            # Create adapter to access other components safely
            self._adapter = SystemComponentAdapter(context, self.logger.getChild("adapter"))

            # Instantiate MCP sub-components
            auth_provider = AuthenticationProvider(config=mcp_config, logger_override=self.logger.getChild("auth")) if mcp_config.get('auth_enabled') else None
            error_handler = ErrorHandler(logger_override=self.logger.getChild("error_handler"))
            tool_registry = ToolRegistry(logger_override=self.logger.getChild("tool_registry"))
            resource_provider = ResourceProvider(logger_override=self.logger.getChild("resource_provider"))

            # Create the MCP server instance (placeholder web framework)
            self._server = MCPServer(
                host=mcp_config.get('host', '0.0.0.0'),
                port=int(mcp_config.get('port', 6231)),
                name=mcp_config.get('server_name', 'dbp-mcp-server'),
                description=mcp_config.get('server_description', 'MCP Server for DBP'),
                version=mcp_config.get('server_version', '1.0.0'),
                tool_registry=tool_registry,
                resource_provider=resource_provider,
                auth_provider=auth_provider,
                error_handler=error_handler,
                logger_override=self.logger.getChild("server_instance")
            )

            # Register tools and resources
            self._register_tools(tool_registry)
            self._register_resources(resource_provider)

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

            # Optionally start the server immediately after initialization?
            # Or provide a separate start method? Let's use a separate start method.
            # self.start_server()

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _register_tools(self, tool_registry: ToolRegistry):
        """Instantiates and registers all MCP tools."""
        if not self._adapter: raise RuntimeError("Adapter not initialized.")
        self.logger.debug("Registering MCP tools...")

        tools_to_register = [
            AnalyzeDocumentConsistencyTool(self._adapter, self.logger.getChild("tool_analyze_consistency")),
            GenerateRecommendationsTool(self._adapter, self.logger.getChild("tool_gen_recs")),
            ApplyRecommendationTool(self._adapter, self.logger.getChild("tool_apply_rec")),
            GeneralQueryTool(self._adapter, self.logger.getChild("tool_general_query")),
            # Add other tools from plan:
            # AnalyzeDocumentRelationshipsTool(self._adapter, self.logger.getChild("tool_analyze_rels")),
            # GenerateMermaidDiagramTool(self._adapter, self.logger.getChild("tool_gen_mermaid")),
            # ExtractDocumentContextTool(self._adapter, self.logger.getChild("tool_extract_doc")),
            # ExtractCodebaseContextTool(self._adapter, self.logger.getChild("tool_extract_code")),
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
        self.logger.info(f"Registered {count}/{len(tools_to_register)} MCP tools.")


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
