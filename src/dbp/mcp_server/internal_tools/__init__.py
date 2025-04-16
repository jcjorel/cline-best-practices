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
# Exports the internal tool classes for use by public MCP tools.
# This module is not intended to be used directly by MCP clients.
###############################################################################
# [Source file design principles]
# - Simple exports to make internal tools available to public tools
# - No direct functionality, just re-exports
# - Clear documentation of internal status
###############################################################################
# [Source file constraints]
# - Only for use by public tools in tools.py
# - Not to be exposed directly to MCP clients
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/mcp_tools_refactoring_plan/plan_overview.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T09:25:00Z : Created internal tools package by CodeAssistant
# * Added exports for internal tool classes
###############################################################################

"""
Internal MCP tools for use by public tools.
This module is not intended to be used directly by MCP clients.
"""

from .base import (
    InternalMCPTool,
    InternalToolError,
    InternalToolValidationError,
    InternalToolExecutionError
)

from .consistency import InternalConsistencyAnalysisTool
from .recommendations import (
    InternalRecommendationsGeneratorTool,
    InternalRecommendationApplicatorTool,
    RecommendationNotFoundError
)
from .relationships import InternalDocumentRelationshipsTool
from .visualization import InternalMermaidDiagramTool

__all__ = [
    # Base classes
    'InternalMCPTool',
    'InternalToolError',
    'InternalToolValidationError',
    'InternalToolExecutionError',
    
    # Tool implementations
    'InternalConsistencyAnalysisTool',
    'InternalRecommendationsGeneratorTool',
    'InternalRecommendationApplicatorTool',
    'InternalDocumentRelationshipsTool',
    'InternalMermaidDiagramTool',
    
    # Exceptions
    'RecommendationNotFoundError',
]
