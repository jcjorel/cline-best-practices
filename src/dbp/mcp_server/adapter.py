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
# Implements the SystemComponentAdapter class, which acts as a facade or bridge
# between the MCP server layer (tools, resources) and the core DBP system
# components (consistency analysis, recommendation generator, etc.). It uses the
# InitializationContext to retrieve initialized component instances safely.
###############################################################################
# [Source file design principles]
# - Provides a single point of access to underlying system components for MCP handlers.
# - Uses the InitializationContext's component registry to retrieve components by name.
# - Ensures that requested components are initialized before returning them.
# - Includes error handling for cases where components are missing or not ready.
# - Design Decision: Adapter Facade (2025-04-15)
#   * Rationale: Decouples the MCP server implementation from the specific details of how core components are structured and accessed, promoting modularity.
#   * Alternatives considered: MCP tools/resources directly accessing the component registry (tighter coupling).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework (`InitializationContext`, `Component`).
# - Relies on components being correctly registered and initialized by the core framework.
# - Assumes component names used for retrieval match the names used during registration.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
# - src/dbp/core/component.py
# - src/dbp/core/registry.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:49:00Z : Initial creation of SystemComponentAdapter by CodeAssistant
# * Implemented component retrieval logic using InitializationContext.
###############################################################################

import logging
from typing import Optional, Any

# Assuming core components are accessible
try:
    from ..core.component import Component, InitializationContext
    from ..core.registry import ComponentRegistry # For type hint clarity
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for SystemComponentAdapter.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    class ComponentRegistry: pass # Placeholder

logger = logging.getLogger(__name__)

class ComponentNotFoundError(Exception):
    """Exception raised when a requested component is not found or not initialized."""
    def __init__(self, component_name: str, message: Optional[str] = None):
        self.component_name = component_name
        super().__init__(message or f"Component '{component_name}' not found or not initialized.")


class SystemComponentAdapter:
    """
    Provides a controlled interface for MCP tools and resources to access
    initialized DBP system components via the InitializationContext.
    """

    def __init__(self, context: InitializationContext, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the SystemComponentAdapter.

        Args:
            context: The InitializationContext containing the component registry.
            logger_override: Optional logger instance.
        """
        if not isinstance(context, InitializationContext):
             logger.warning("SystemComponentAdapter initialized with potentially incorrect context type.")
        self.context = context
        self.logger = logger_override or logger
        # Eagerly retrieve commonly used components or retrieve on demand? Retrieve on demand for now.
        # self.job_manager = self._get_component_internal("job_management") # Example eager load
        self.logger.debug("SystemComponentAdapter initialized.")

    def get_component(self, name: str) -> Component:
        """
        Retrieves an initialized system component by its registered name.

        Args:
            name: The unique name of the component to retrieve.

        Returns:
            The initialized component instance.

        Raises:
            ComponentNotFoundError: If the component is not found or not initialized.
        """
        self.logger.debug(f"Requesting component: '{name}'")
        try:
            # Use the context's get_component method which handles registry access
            component = self.context.get_component(name)

            # Double-check initialization status
            if not component or not component.is_initialized:
                 self.logger.error(f"Component '{name}' found but is not initialized.")
                 raise ComponentNotFoundError(name, f"Component '{name}' is not initialized.")

            self.logger.debug(f"Successfully retrieved initialized component: '{name}'")
            return component
        except KeyError:
            # get_component already logs and raises KeyError, re-raise as specific error
            raise ComponentNotFoundError(name) from None # Raise specific error, chain None
        except Exception as e:
             # Catch other potential errors during retrieval or is_initialized check
             self.logger.error(f"Unexpected error retrieving component '{name}': {e}", exc_info=True)
             raise ComponentNotFoundError(name, f"Unexpected error retrieving component '{name}'.") from e

    # --- Convenience properties/methods for commonly accessed components ---
    # These can be added to provide typed access and reduce boilerplate in tools/resources

    @property
    def consistency_analysis(self) -> Any: # Replace Any with actual component type
         """Provides access to the ConsistencyAnalysisComponent."""
         return self.get_component("consistency_analysis")

    @property
    def recommendation_generator(self) -> Any: # Replace Any with actual component type
         """Provides access to the RecommendationGeneratorComponent."""
         return self.get_component("recommendation_generator")

    @property
    def doc_relationships(self) -> Any: # Replace Any with actual component type
         """Provides access to the DocRelationshipsComponent."""
         return self.get_component("doc_relationships")

    @property
    def llm_coordinator(self) -> Any: # Replace Any with actual component type
         """Provides access to the LLMCoordinatorComponent."""
         return self.get_component("llm_coordinator")

    @property
    def metadata_extraction(self) -> Any: # Replace Any with actual component type
         """Provides access to the MetadataExtractionComponent."""
         return self.get_component("metadata_extraction")

    @property
    def memory_cache(self) -> Any: # Replace Any with actual component type
         """Provides access to the MemoryCacheComponent."""
         return self.get_component("memory_cache")

    # Add other component accessors as needed
