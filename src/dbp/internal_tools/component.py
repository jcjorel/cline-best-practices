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
# Implements the InternalToolsComponent class, conforming to the core Component
# protocol. This component encapsulates the specialized internal LLM tools,
# initializing their dependencies (context assemblers, LLM interfaces, response
# handlers, execution engine) and registering the tool execution functions with
# the LLM Coordinator's ToolRegistry.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Declares dependency on the `llm_coordinator` component to access its ToolRegistry.
# - Initializes all internal tool parts (assemblers, LLMs, handlers, engine).
# - Registers the actual tool execution methods from the engine with the coordinator's registry.
# - Acts as a container and initializer for the internal tools subsystem.
# - Design Decision: Dedicated Component for Internal Tools (2025-04-15)
#   * Rationale: Groups the implementation of all specialized tools under a single manageable component within the application framework.
#   * Alternatives considered: Implementing tools directly within the coordinator (less modular).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and the `llm_coordinator` component.
# - Requires all helper classes within the `internal_tools` package to be implemented.
# - Assumes configuration for internal tools is available via InitializationContext.
# - Placeholder logic exists in the execution engine and LLM interfaces.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/INTERNAL_LLM_TOOLS.md
# - scratchpad/dbp_implementation_plan/plan_internal_tools.md
# - src/dbp/core/component.py
# - src/dbp/llm_coordinator/component.py (Dependency)
# - All other files in src/dbp/internal_tools/
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:15:55Z : Initial creation of InternalToolsComponent by CodeAssistant
# * Implemented Component protocol methods, initialization of internal parts, and tool registration logic.
###############################################################################

import logging
from typing import List, Optional, Any

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    # Import config type if defined, else use Any
    # from ..config import AppConfig, InternalToolsConfig # Example
    Config = Any
    InternalToolsConfig = Any # Placeholder
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for InternalToolsComponent.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    Config = Any
    InternalToolsConfig = Any

# Imports for internal tool services
try:
    from .execution_engine import InternalToolExecutionEngine, InternalToolError
    # Import LLMCoordinatorComponent to access its registry
    from ..llm_coordinator.component import LLMCoordinatorComponent
    from ..llm_coordinator.tool_registry import ToolRegistry # For type hint
except ImportError as e:
    logging.getLogger(__name__).error(f"InternalToolsComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    InternalToolExecutionEngine = object
    InternalToolError = Exception
    LLMCoordinatorComponent = object
    ToolRegistry = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class InternalToolsComponent(Component):
    """
    DBP system component responsible for providing and managing the specialized
    internal LLM tools used by the LLM Coordinator.
    """
    _initialized: bool = False
    _execution_engine: Optional[InternalToolExecutionEngine] = None

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "internal_tools"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Depends on the LLM Coordinator to register tools with its registry.
        # Also implicitly depends on config.
        # Add other dependencies if the execution engine or its parts need them (e.g., database, cache).
        return ["llm_coordinator"]

    def initialize(self, context: InitializationContext):
        """
        Initializes the Internal Tools component, including the execution engine,
        and registers the tools with the LLM Coordinator.

        Args:
            context: The initialization context.
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger # Use logger from context
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get internal tools specific configuration
            tools_config = context.config.get(self.name, {}) # Assumes dict-like config

            # Get dependent LLM Coordinator component to access its registry
            llm_coordinator_comp = context.get_component("llm_coordinator")
            if not isinstance(llm_coordinator_comp, LLMCoordinatorComponent):
                 # This check might fail if using placeholder types
                 self.logger.warning("LLM Coordinator component type mismatch or placeholder used.")
                 # Attempt to access registry anyway, assuming duck typing or correct placeholder structure
                 # raise TypeError("Dependency 'llm_coordinator' is not a valid LLMCoordinatorComponent instance.")

            # Access the ToolRegistry from the coordinator component
            # This assumes the coordinator component exposes its registry. Adjust if needed.
            if not hasattr(llm_coordinator_comp, '_tool_registry') or llm_coordinator_comp._tool_registry is None:
                 raise RuntimeError("LLM Coordinator component does not have an initialized '_tool_registry'.")
            tool_registry: ToolRegistry = llm_coordinator_comp._tool_registry


            # Instantiate the execution engine (which internally creates assemblers, LLMs, etc.)
            self._execution_engine = InternalToolExecutionEngine(
                 config=tools_config,
                 logger_override=self.logger.getChild("engine")
            )

            # Register the execution methods as tools in the coordinator's registry
            self._register_tools(tool_registry)

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except AttributeError as e:
             self.logger.error(f"Initialization failed: Could not access required attribute, possibly on a dependency: {e}", exc_info=True)
             self._initialized = False
             raise RuntimeError(f"Attribute error during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _register_tools(self, tool_registry: ToolRegistry):
        """Registers the internal tool execution methods with the provided ToolRegistry."""
        if not self._execution_engine:
             raise RuntimeError("Execution engine not initialized before registering tools.")

        self.logger.debug("Registering internal LLM tools with LLM Coordinator...")
        try:
            # Map tool names to their execution methods in the engine
            tool_map = {
                "coordinator_get_codebase_context": self._execution_engine.execute_codebase_context_tool,
                "coordinator_get_codebase_changelog_context": self._execution_engine.execute_codebase_changelog_tool,
                "coordinator_get_documentation_context": self._execution_engine.execute_documentation_context_tool,
                "coordinator_get_documentation_changelog_context": self._execution_engine.execute_documentation_changelog_tool,
                "coordinator_get_expert_architect_advice": self._execution_engine.execute_expert_architect_advice_tool,
            }
            for name, func in tool_map.items():
                tool_registry.register_tool(name, func) # Register with the coordinator's registry
            self.logger.info(f"Registered {len(tool_map)} internal tools with LLM Coordinator.")
        except Exception as e:
             self.logger.error(f"Failed to register internal tools with LLM Coordinator: {e}", exc_info=True)
             raise RuntimeError("Failed to register essential internal tools.") from e

    def shutdown(self) -> None:
        """Performs cleanup for the internal tools component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        # Add cleanup logic here if the execution engine or its parts need explicit shutdown
        if self._execution_engine and hasattr(self._execution_engine, 'shutdown'):
             try:
                  self._execution_engine.shutdown()
             except Exception as e:
                  self.logger.error(f"Error shutting down execution engine: {e}", exc_info=True)

        self._execution_engine = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # Note: This component likely doesn't need public methods other than the standard
    # Component protocol methods, as its primary role is to initialize and register
    # the tools used by the LLM Coordinator.
