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
# Implements a minimized version of the SystemComponentAdapter class for progressive 
# integration testing. This adapter returns mock components or error responses instead 
# of trying to access the actual DBP system components, allowing the MCP server to run
# with minimal dependencies.
###############################################################################
# [Source file design principles]
# - Provides a simplified interface that mimics the original SystemComponentAdapter.
# - Returns mock components or null objects instead of real components.
# - Logs clear messages indicating operation in "standalone mode".
# - Maintains the same interface as the original adapter for compatibility.
# - Design Decision: Mock Component Adapter (2025-04-25)
#   * Rationale: Enables MCP server testing with minimal dependencies.
#   * Alternatives considered: Dynamic component loading (more complex, harder to isolate)
###############################################################################
# [Source file constraints]
# - Must maintain the same interface as the original adapter.
# - Should not attempt to access unavailable components.
# - Must provide clear log messages when operating in standalone mode.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# system:- src/dbp/core/component.py
###############################################################################
# [GenAI tool change history]
# 2025-04-25T00:10:00Z : Created minimized adapter by CodeAssistant
# * Created standalone version of SystemComponentAdapter for progressive integration testing
# * Implemented mock component returns instead of actual component access
# * Added clear logging for standalone mode operation
###############################################################################

import logging
from typing import Optional, Any, Type, TypeVar, cast

# Attempting to import core components, but prepared for them to be missing
try:
    from ..core.component import Component, InitializationContext
    # Import exceptions
    try:
        from .exceptions import ComponentNotFoundError
    except ImportError:
        # Define a local version if not available
        class ComponentNotFoundError(Exception):
            """Exception raised when a component is not found or not initialized."""
            def __init__(self, component_name: str = "unknown"):
                self.component_name = component_name
                super().__init__(f"Component not found or not initialized: '{component_name}'")
except ImportError:
    logging.getLogger(__name__).warning("Core component imports failed, using mock implementations.")
    # Mock implementations for core classes
    class Component:
        """Mock Component base class."""
        @property
        def name(self) -> str:
            return "mock_component"

        @property
        def is_initialized(self) -> bool:
            return True

        def initialize(self, context, dependencies=None):
            pass

        def shutdown(self):
            pass

    class InitializationContext:
        """Mock InitializationContext."""
        def get_component(self, name: str) -> Component:
            raise KeyError(f"Component '{name}' not found in mock context.")
        
        def get_typed_config(self):
            return Any()

    class ComponentNotFoundError(Exception):
        """Exception raised when a component is not found or not initialized."""
        def __init__(self, component_name: str = "unknown"):
            self.component_name = component_name
            super().__init__(f"Component not found or not initialized: '{component_name}'")

logger = logging.getLogger(__name__)

# Mock component classes for when actual components are not available
class MockComponent(Component):
    """Base class for mock components that simulate component functionality."""
    
    def __init__(self, name: str):
        self._name = name
        self._initialized = True
        
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized

class MockConsistencyAnalysisComponent(MockComponent):
    """Mock implementation of ConsistencyAnalysisComponent."""
    
    def analyze_document_consistency(self, document_paths=None, **kwargs):
        logger.info("[MOCK] ConsistencyAnalysisComponent.analyze_document_consistency called")
        return {
            "status": "error",
            "message": "Running in standalone mode - ConsistencyAnalysisComponent not available",
            "error_code": "COMPONENT_UNAVAILABLE"
        }

class MockRecommendationGeneratorComponent(MockComponent):
    """Mock implementation of RecommendationGeneratorComponent."""
    
    def generate_recommendations(self, **kwargs):
        logger.info("[MOCK] RecommendationGeneratorComponent.generate_recommendations called")
        return {
            "status": "error",
            "message": "Running in standalone mode - RecommendationGeneratorComponent not available",
            "error_code": "COMPONENT_UNAVAILABLE"
        }

class MockDocRelationshipsComponent(MockComponent):
    """Mock implementation of DocRelationshipsComponent."""
    
    def get_relationships(self, document_path=None, **kwargs):
        logger.info("[MOCK] DocRelationshipsComponent.get_relationships called")
        return {
            "status": "error",
            "message": "Running in standalone mode - DocRelationshipsComponent not available",
            "error_code": "COMPONENT_UNAVAILABLE"
        }

class MockLLMCoordinatorComponent(MockComponent):
    """Mock implementation of LLMCoordinatorComponent."""
    
    def process_request(self, request):
        logger.info("[MOCK] LLMCoordinatorComponent.process_request called")
        return type('MockResponse', (), {
            'results': {
                "status": "error",
                "message": "Running in standalone mode - LLMCoordinatorComponent not available",
                "error_code": "COMPONENT_UNAVAILABLE"
            },
            'metadata': {},
            'budget_info': {}
        })

class MockMetadataExtractionComponent(MockComponent):
    """Mock implementation of MetadataExtractionComponent."""
    
    def extract_metadata(self, file_path=None, **kwargs):
        logger.info("[MOCK] MetadataExtractionComponent.extract_metadata called")
        return {
            "status": "error",
            "message": "Running in standalone mode - MetadataExtractionComponent not available",
            "error_code": "COMPONENT_UNAVAILABLE"
        }

class MockMemoryCacheComponent(MockComponent):
    """Mock implementation of MemoryCacheComponent."""
    
    def get_cached_item(self, key, **kwargs):
        logger.info("[MOCK] MemoryCacheComponent.get_cached_item called")
        return None
    
    def set_cached_item(self, key, value, **kwargs):
        logger.info("[MOCK] MemoryCacheComponent.set_cached_item called")
        return False


class SystemComponentAdapter:
    """
    Provides a mock interface for MCP tools and resources to access
    system components. In this minimized version, it returns mock components
    instead of actual system components.
    """

    def __init__(self, context: InitializationContext, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the SystemComponentAdapter.

        Args:
            context: The InitializationContext containing the component registry.
            logger_override: Optional logger instance.
        """
        self.context = context
        self.logger = logger_override or logger
        self.logger.warning("SystemComponentAdapter initialized in STANDALONE MODE - returning mock components only")

    def get_component(self, name: str) -> Component:
        """
        Retrieves a mock system component by its name.
        In standalone mode, this always returns a mock component.

        Args:
            name: The unique name of the component to retrieve.

        Returns:
            A mock component instance.

        Raises:
            ComponentNotFoundError: If the component name is not supported even as a mock.
        """
        self.logger.info(f"[STANDALONE MODE] Requesting component: '{name}'")
        
        # Map of component names to their mock implementations
        mock_components = {
            "consistency_analysis": MockConsistencyAnalysisComponent("consistency_analysis"),
            "recommendation_generator": MockRecommendationGeneratorComponent("recommendation_generator"),
            "doc_relationships": MockDocRelationshipsComponent("doc_relationships"),
            "llm_coordinator": MockLLMCoordinatorComponent("llm_coordinator"),
            "metadata_extraction": MockMetadataExtractionComponent("metadata_extraction"),
            "memory_cache": MockMemoryCacheComponent("memory_cache"),
        }
        
        # First try to get from mock components
        if name in mock_components:
            mock_component = mock_components[name]
            self.logger.info(f"[STANDALONE MODE] Returning mock component for '{name}'")
            return mock_component
            
        # If not a known mock, try the context (for config_manager, etc.)
        try:
            # Try to get an actual component from the context
            # This will only work for components that are actually initialized
            # like config_manager which we want to preserve
            component = self.context.get_component(name)
            
            if component and component.is_initialized:
                self.logger.info(f"[STANDALONE MODE] Retrieved actual component: '{name}'")
                return component
                
            self.logger.error(f"[STANDALONE MODE] Component '{name}' found but is not initialized.")
            raise ComponentNotFoundError(component_name=name)
            
        except KeyError:
            # If we don't have a mock and it's not in the context, raise an error
            self.logger.error(f"[STANDALONE MODE] No mock or actual component available for '{name}'")
            raise ComponentNotFoundError(component_name=name)
        except Exception as e:
            # Catch other potential errors
            self.logger.error(f"[STANDALONE MODE] Unexpected error retrieving component '{name}': {e}", exc_info=True)
            raise ComponentNotFoundError(component_name=name) from e

    # --- Mock properties for commonly accessed components ---

    @property
    def database_repositories(self):
        """
        Provides mock access to the database repositories.
        
        Returns:
            A mock object simulating repositories module.
        """
        self.logger.info("[STANDALONE MODE] Accessing mock database_repositories")
        return type('MockRepositories', (), {})

    @property
    def consistency_analysis(self):
        """Provides mock access to the ConsistencyAnalysisComponent."""
        return self.get_component("consistency_analysis")

    @property
    def recommendation_generator(self):
        """Provides mock access to the RecommendationGeneratorComponent."""
        return self.get_component("recommendation_generator")

    @property
    def doc_relationships(self):
        """Provides mock access to the DocRelationshipsComponent."""
        return self.get_component("doc_relationships")

    @property
    def llm_coordinator(self):
        """Provides mock access to the LLMCoordinatorComponent."""
        return self.get_component("llm_coordinator")

    @property
    def metadata_extraction(self):
        """Provides mock access to the MetadataExtractionComponent."""
        return self.get_component("metadata_extraction")

    @property
    def memory_cache(self):
        """Provides mock access to the MemoryCacheComponent."""
        return self.get_component("memory_cache")
