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
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/API.md
# other:- src/dbp/mcp_server/mcp_protocols.py
# other:- src/dbp/mcp_server/adapter.py
###############################################################################
# [GenAI tool change history]
# 2025-05-02T00:36:49Z : Removed InconsistencyResource class by CodeAssistant
# * Removed the entire InconsistencyResource class that relied on consistency_analysis component
# 2025-05-02T00:35:53Z : Removed consistency analysis references by CodeAssistant
# * Removed ConsistencyAnalysisComponent import
# * Removed ConsistencyAnalysisComponent from placeholder classes
# 2025-05-01T23:55:00Z : Removed RecommendationResource class by CodeAssistant
# * Removed recommendation_generator related imports and functionality
# * Removed RecommendationResource class as it is no longer needed
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


logger = logging.getLogger(__name__)

# --- Base Exception for Resource Errors ---
class ResourceAccessError(Exception):
    """Custom exception for errors during resource access."""
    pass

# --- Concrete Resource Implementations ---

class CodeMetadataResource(MCPResource):
    """Exposes extracted code metadata via MCP."""

    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="code_metadata", # URI prefix: /resource/code_metadata/...
            description="Access extracted metadata (functions, classes, headers) for code files.",
            logger_override=logger_override
        )
        self.adapter = adapter

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
            # Note: metadata_extraction component has been removed
            # Return a stub response since the component is no longer available
            return {
                "status": "unavailable",
                "message": "Metadata extraction component has been removed from the system",
                "file_path": resource_id
            }

        except ComponentNotFoundError as e:
             self.logger.error(f"Dependency error accessing resource '{self.name}': {e}")
             raise ResourceAccessError(f"Internal component error: {e}") from e
        except Exception as e:
            self.logger.error(f"Error accessing resource '{self.name}/{resource_id}': {e}", exc_info=True)
            raise ResourceAccessError(f"Failed to access code metadata resource: {e}") from e
