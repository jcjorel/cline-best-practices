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
# Doc Relationships package for the Documentation-Based Programming system.
# Defines and analyzes relationships between documentation files.
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


# src/dbp/doc_relationships/__init__.py

"""
Documentation Relationships package for the Documentation-Based Programming system.

Analyzes, stores, and queries relationships between documentation files,
enabling consistency checks and impact analysis.

Key components:
- DocRelationshipsComponent: The main component conforming to the core framework.
- RelationshipGraph: In-memory graph representation of relationships.
- RelationshipRepository: Persistence layer for relationships.
- RelationshipAnalyzer: Extracts relationships from document content.
- ImpactAnalyzer: Determines the impact of changes based on relationships.
- ChangeDetector: Identifies specific changes and their impacts.
- GraphVisualization: Generates Mermaid diagrams of the relationship graph.
- QueryInterface: Provides methods for querying relationships.
- Data Models: Defines structures like DocumentRelationship, DocImpact, etc.
"""

# Expose key classes and data models for easier import
from .data_models import DocumentRelationship, DocImpact, DocChangeImpact
from .graph import RelationshipGraph
from .repository import RelationshipRepository, RepositoryError
from .analyzer import RelationshipAnalyzer
from .impact_analyzer import ImpactAnalyzer
from .change_detector import ChangeDetector
from .visualization import GraphVisualization
from .query_interface import QueryInterface
from .component import DocRelationshipsComponent, ComponentNotInitializedError

__all__ = [
    # Main Component
    "DocRelationshipsComponent",
    # Core Classes (Expose interfaces/facades)
    "RelationshipGraph",
    "RelationshipRepository",
    "RelationshipAnalyzer",
    "ImpactAnalyzer",
    "ChangeDetector",
    "GraphVisualization",
    "QueryInterface",
    # Data Models
    "DocumentRelationship",
    "DocImpact",
    "DocChangeImpact",
    # Exceptions
    "RepositoryError",
    "ComponentNotInitializedError",
]
