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
# Implements concrete MCPResource classes that expose DBP system data via the
# Model Context Protocol. Each resource class handles requests for specific
# data URIs (e.g., documentation, code metadata, inconsistencies) by interacting
# with the core DBP components through the SystemComponentAdapter.
###############################################################################
# [Source file design principles]
# - Each class inherits from `MCPResource`.
# - Each class defines logic within its `get` method to retrieve and format data.
# - Uses `SystemComponentAdapter` to access underlying DBP functionality and data.
# - Handles `resource_id` and `params` to filter or specify the requested data.
# - Includes basic error handling.
# - Placeholder logic used for complex data retrieval and formatting.
###############################################################################
# [Source file constraints]
# - Depends on `mcp_protocols.py` for `MCPResource` base class.
# - Depends on `adapter.py` for `SystemComponentAdapter`.
# - Depends on various core DBP components and data models.
# - Placeholder `get` methods need to be replaced with actual data retrieval logic.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/API.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
# - src/dbp/mcp_server/mcp_protocols.py
# - src/dbp/mcp_server/adapter.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T16:39:48Z : Updated resources to use centralized exceptions by CodeAssistant
# * Modified imports to use exceptions from centralized exceptions module
# * Removed local ResourceNotFoundError class definition
# * Kept ResourceAccessError for specific resource access issues
# 2025-04-15T10:53:00Z : Initial creation of MCP resource classes by CodeAssistant
# * Implemented placeholder resources for documentation, code metadata, inconsistencies, recommendations.
###############################################################################

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# Assuming necessary imports
try:
    from .mcp_protocols import MCPResource
    from .exceptions import (
        ComponentNotFoundError, ResourceNotFoundError, 
        ExecutionError, ConfigurationError, MalformedRequestError
    )
    from .adapter import SystemComponentAdapter
    # Import specific component types for type hints if possible
    from ..doc_relationships.component import DocRelationshipsComponent
    from ..metadata_extraction.component import MetadataExtractionComponent # Or Memory Cache?
    from ..consistency_analysis.component import ConsistencyAnalysisComponent
    from ..recommendation_generator.component import RecommendationGeneratorComponent
except ImportError as e:
    logging.getLogger(__name__).error(f"MCP Resources ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    class MCPResource:
        def __init__(self, name, description, logger): self.name=name; self.description=description; self.logger=logger
        def get(self, resource_id, params, auth_context): return {}
    SystemComponentAdapter = object
    ComponentNotFoundError = Exception
    ResourceNotFoundError = ValueError
    ExecutionError = RuntimeError
    ConfigurationError = ValueError
    MalformedRequestError = ValueError
    DocRelationshipsComponent = object
    MetadataExtractionComponent = object
    ConsistencyAnalysisComponent = object
    RecommendationGeneratorComponent = object


logger = logging.getLogger(__name__)

# --- Base Exception for Resource Errors ---
class ResourceAccessError(Exception):
    """Custom exception for errors during resource access."""
    pass

# --- Concrete Resource Implementations ---

class DocumentationResource(MCPResource):
    """Exposes documentation files and their relationships via MCP."""

    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="documentation", # URI prefix: /resource/documentation/...
            description="Access documentation files, content, and relationships.",
            logger_override=logger_override
        )
        self.adapter = adapter
        # Get component eagerly or lazily in get? Lazy is safer during init.
        # self.doc_rel_component: DocRelationshipsComponent = adapter.doc_relationships

    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handles GET requests for documentation resources.

        Args:
            resource_id: The specific document path relative to project root (e.g., 'DESIGN.md', 'core/component.py')
                         or a sub-resource like 'relationships' or 'mermaid'. If None, lists documents.
            params: Query parameters (e.g., ?include_content=true, ?relationship_type=depends_on).
            auth_context: Authentication context.

        Returns:
            A dictionary containing the requested documentation data.
        """
        self.logger.info(f"Accessing resource '{self.name}', ID: '{resource_id}', Params: {params}")
        try:
            # Get the necessary component lazily
            doc_rel_component: DocRelationshipsComponent = self.adapter.doc_relationships

            if resource_id is None:
                # List documentation files (placeholder)
                # Need access to file listing, maybe via adapter or FileAccessService?
                self.logger.warning("Listing documentation files not fully implemented.")
                # Example: return {"files": ["doc/DESIGN.md", "doc/API.md"], "count": 2}
                return {"message": "Listing documentation files not implemented yet."}

            elif resource_id == "relationships":
                doc_path = params.get("document_path")
                if not doc_path: raise ValueError("'document_path' parameter is required for relationships resource.")
                rels = doc_rel_component.get_related_documents(doc_path)
                return {"document_path": doc_path, "relationships": [r.__dict__ for r in rels]}

            elif resource_id == "mermaid":
                paths = params.get("document_paths") # Optional list of paths
                diagram = doc_rel_component.get_mermaid_diagram(paths)
                return {"diagram": diagram, "filter_paths": paths}

            else:
                # Assume resource_id is a document path
                # TODO: Need a way to read file content, perhaps via adapter -> FileAccessService
                self.logger.warning(f"Accessing specific document content/metadata for '{resource_id}' not fully implemented.")
                # Example: Check existence and return basic info
                # abs_path = self.adapter.resolve_path(resource_id) # Needs adapter method
                # if os.path.isfile(abs_path):
                #     return {"path": resource_id, "exists": True, "message": "Content retrieval not implemented"}
                # else:
                #     raise ResourceNotFoundError(f"Documentation file not found: {resource_id}")
                return {"path": resource_id, "message": "Document metadata/content retrieval not implemented yet."}

        except ComponentNotFoundError as e:
             self.logger.error(f"Dependency error accessing resource '{self.name}': {e}")
             raise ResourceAccessError(f"Internal component error: {e}") from e
        except FileNotFoundError as e: # Catch specific file errors if reading files
             self.logger.error(f"File not found for resource '{self.name}/{resource_id}': {e}")
             raise ResourceNotFoundError(str(e)) from e
        except Exception as e:
            self.logger.error(f"Error accessing resource '{self.name}/{resource_id}': {e}", exc_info=True)
            raise ResourceAccessError(f"Failed to access documentation resource: {e}") from e


class CodeMetadataResource(MCPResource):
    """Exposes extracted code metadata via MCP."""

    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="code_metadata", # URI prefix: /resource/code_metadata/...
            description="Access extracted metadata (functions, classes, headers) for code files.",
            logger_override=logger_override
        )
        self.adapter = adapter
        # self.metadata_component: MetadataExtractionComponent = adapter.metadata_extraction # Or MemoryCache?

    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handles GET requests for code metadata.

        Args:
            resource_id: The specific code file path relative to project root. If None, could list files with metadata.
            params: Query parameters (e.g., ?query_type=functions).
            auth_context: Authentication context.

        Returns:
            A dictionary containing the requested code metadata.
        """
        self.logger.info(f"Accessing resource '{self.name}', ID: '{resource_id}', Params: {params}")
        if not resource_id:
             raise ValueError("A specific code file path (resource_id) is required.")

        try:
            # Get metadata from cache or extraction component via adapter
            # Assuming MemoryCache is the primary source
            cache_component = self.adapter.memory_cache
            # Need project ID - how is this determined in MCP context? Assume from config or param?
            # Placeholder: Assume project ID 1
            project_id = params.get("project_id", 1) # Example: Get project ID from params or default
            metadata = cache_component.get_metadata(resource_id, project_id=project_id)

            if not metadata:
                 raise ResourceNotFoundError(f"Metadata not found for code file: {resource_id}")

            # Return the full metadata object (or filter based on params?)
            # Convert Pydantic model to dict for JSON response
            return metadata.dict()

        except ComponentNotFoundError as e:
             self.logger.error(f"Dependency error accessing resource '{self.name}': {e}")
             raise ResourceAccessError(f"Internal component error: {e}") from e
        except Exception as e:
            self.logger.error(f"Error accessing resource '{self.name}/{resource_id}': {e}", exc_info=True)
            raise ResourceAccessError(f"Failed to access code metadata resource: {e}") from e


class InconsistencyResource(MCPResource):
    """Exposes detected inconsistency records via MCP."""

    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="inconsistencies", # URI prefix: /resource/inconsistencies/...
            description="Access detected consistency issues between code and documentation.",
            logger_override=logger_override
        )
        self.adapter = adapter
        # self.consistency_component: ConsistencyAnalysisComponent = adapter.consistency_analysis

    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handles GET requests for inconsistency records.

        Args:
            resource_id: Specific inconsistency ID (if requesting one) or None (to list/filter).
            params: Query parameters for filtering (e.g., ?status=open&severity=high&file_path=...).
            auth_context: Authentication context.

        Returns:
            A dictionary containing a single inconsistency or a list of inconsistencies.
        """
        self.logger.info(f"Accessing resource '{self.name}', ID: '{resource_id}', Params: {params}")
        try:
            consistency_component: ConsistencyAnalysisComponent = self.adapter.consistency_analysis

            if resource_id:
                # Get specific inconsistency by ID
                record = consistency_component.get_inconsistencies(id=resource_id, limit=1) # Assuming get_inconsistencies handles ID filter
                if not record:
                     raise ResourceNotFoundError(f"Inconsistency not found: {resource_id}")
                return record[0].__dict__ # Convert dataclass to dict
            else:
                # List/filter inconsistencies
                # Extract filters from params
                filters = {
                     k: v for k, v in params.items()
                     if k in ["file_path", "severity", "status", "limit"] # Allowed filters
                }
                # Convert severity/status strings back to enums if needed by the component
                if 'severity' in filters: filters['severity'] = InconsistencySeverity(filters['severity'])
                if 'status' in filters: filters['status'] = InconsistencyStatus(filters['status'])
                if 'limit' in filters: filters['limit'] = int(filters['limit'])

                records = consistency_component.get_inconsistencies(**filters)
                return {
                    "inconsistencies": [rec.__dict__ for rec in records],
                    "count": len(records),
                    "filters_applied": filters
                }

        except (ComponentNotFoundError, ValueError, TypeError) as e: # Catch specific errors
             self.logger.error(f"Error accessing resource '{self.name}': {e}")
             raise ResourceAccessError(f"Error processing inconsistency request: {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error accessing resource '{self.name}': {e}", exc_info=True)
            raise ResourceAccessError(f"Failed to access inconsistency resource: {e}") from e


class RecommendationResource(MCPResource):
    """Exposes generated recommendations via MCP."""

    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="recommendations", # URI prefix: /resource/recommendations/...
            description="Access generated recommendations for fixing inconsistencies.",
            logger_override=logger_override
        )
        self.adapter = adapter
        # self.recommendation_component: RecommendationGeneratorComponent = adapter.recommendation_generator

    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handles GET requests for recommendation records.

        Args:
            resource_id: Specific recommendation ID or None to list/filter.
            params: Query parameters for filtering (e.g., ?status=pending&severity=high).
            auth_context: Authentication context.

        Returns:
            A dictionary containing a single recommendation or a list of recommendations.
        """
        self.logger.info(f"Accessing resource '{self.name}', ID: '{resource_id}', Params: {params}")
        try:
            recommender: RecommendationGeneratorComponent = self.adapter.recommendation_generator

            if resource_id:
                # Get specific recommendation by ID
                record = recommender.get_recommendations(id=resource_id, limit=1) # Assuming get_recommendations handles ID filter
                if not record:
                     raise ResourceNotFoundError(f"Recommendation not found: {resource_id}")
                return record[0].__dict__ # Convert dataclass to dict
            else:
                # List/filter recommendations
                filters = {
                     k: v for k, v in params.items()
                     if k in ["inconsistency_id", "status", "severity", "limit"] # Allowed filters
                }
                # Convert status/severity strings back to enums if needed
                if 'status' in filters: filters['status'] = RecommendationStatus(filters['status'])
                if 'severity' in filters: filters['severity'] = RecommendationSeverity(filters['severity'])
                if 'limit' in filters: filters['limit'] = int(filters['limit'])

                records = recommender.get_recommendations(**filters)
                return {
                    "recommendations": [rec.__dict__ for rec in records],
                    "count": len(records),
                    "filters_applied": filters
                }

        except (ComponentNotFoundError, ValueError, TypeError) as e:
             self.logger.error(f"Error accessing resource '{self.name}': {e}")
             raise ResourceAccessError(f"Error processing recommendation request: {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error accessing resource '{self.name}': {e}", exc_info=True)
            raise ResourceAccessError(f"Failed to access recommendation resource: {e}") from e
