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
# - src/dbp/core/system.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T22:55:41Z : Fixed import path for component registry by CodeAssistant
# * Updated import from non-existent core.registry to core.system
# * Updated reference documentation to point to system.py instead of registry.py
# 2025-04-15T16:42:09Z : Updated adapter to use centralized exceptions by CodeAssistant
# * Modified imports to use ComponentNotFoundError from exceptions module
# * Removed local ComponentNotFoundError class definition
# 2025-04-15T10:49:00Z : Initial creation of SystemComponentAdapter by CodeAssistant
# * Implemented component retrieval logic using InitializationContext.
###############################################################################

import logging
from typing import Optional, Any, Type, TypeVar, cast

# Assuming core components are accessible
try:
    from ..core.component import Component, InitializationContext
    from ..core.system import ComponentSystem  # Component registry is in system.py
    from .exceptions import ComponentNotFoundError
    
    # Import component types for proper type annotations
    from ..consistency_analysis.component import ConsistencyAnalysisComponent
    from ..recommendation_generator.component import RecommendationGeneratorComponent
    from ..doc_relationships.component import DocRelationshipsComponent
    from ..llm_coordinator.component import LLMCoordinatorComponent
    from ..metadata_extraction.component import MetadataExtractionComponent
    from ..memory_cache.component import MemoryCacheComponent
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for SystemComponentAdapter.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    class ComponentSystem: pass # Placeholder
    class ComponentNotFoundError(Exception): pass
    
    # Placeholder component types
    class ConsistencyAnalysisComponent(Component): pass
    class RecommendationGeneratorComponent(Component): pass
    class DocRelationshipsComponent(Component): pass
    class LLMCoordinatorComponent(Component): pass
    class MetadataExtractionComponent(Component): pass
    class MemoryCacheComponent(Component): pass

logger = logging.getLogger(__name__)


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
                 raise ComponentNotFoundError(component_name=name)

            self.logger.debug(f"Successfully retrieved initialized component: '{name}'")
            return component
        except KeyError:
            # get_component already logs and raises KeyError, re-raise as specific error
            raise ComponentNotFoundError(component_name=name) from None # Raise specific error, chain None
        except Exception as e:
             # Catch other potential errors during retrieval or is_initialized check
             self.logger.error(f"Unexpected error retrieving component '{name}': {e}", exc_info=True)
             raise ComponentNotFoundError(component_name=name) from e

    # --- Convenience properties/methods for commonly accessed components ---
    # These can be added to provide typed access and reduce boilerplate in tools/resources
    
    @property
    def database_repositories(self):
        """
        Provides access to the database repositories.
        
        Returns:
            A module containing all repository classes:
            - BaseRepository
            - DocumentRepository
            - ProjectRepository
            - RelationshipRepository
            - FunctionRepository
            - ClassRepository
            - InconsistencyRepository
            - RecommendationRepository
            - DeveloperDecisionRepository
            - DesignDecisionRepository
            - ChangeRecordRepository
        """
        # Import the repositories module directly when needed
        try:
            from ..database import repositories
            return repositories
        except ImportError as e:
            self.logger.error(f"Failed to import repositories module: {e}")
            raise ComponentNotFoundError("database_repositories") from e

    @property
    def consistency_analysis(self) -> ConsistencyAnalysisComponent:
         """Provides access to the ConsistencyAnalysisComponent."""
         return cast(ConsistencyAnalysisComponent, self.get_component("consistency_analysis"))

    @property
    def recommendation_generator(self) -> RecommendationGeneratorComponent:
         """Provides access to the RecommendationGeneratorComponent."""
         return cast(RecommendationGeneratorComponent, self.get_component("recommendation_generator"))

    @property
    def doc_relationships(self) -> DocRelationshipsComponent:
         """Provides access to the DocRelationshipsComponent."""
         return cast(DocRelationshipsComponent, self.get_component("doc_relationships"))

    @property
    def llm_coordinator(self) -> LLMCoordinatorComponent:
         """Provides access to the LLMCoordinatorComponent."""
         return cast(LLMCoordinatorComponent, self.get_component("llm_coordinator"))

    @property
    def metadata_extraction(self) -> MetadataExtractionComponent:
         """Provides access to the MetadataExtractionComponent."""
         return cast(MetadataExtractionComponent, self.get_component("metadata_extraction"))

    @property
    def memory_cache(self) -> MemoryCacheComponent:
         """Provides access to the MemoryCacheComponent."""
         return cast(MemoryCacheComponent, self.get_component("memory_cache"))

    # Add other component accessors as needed
