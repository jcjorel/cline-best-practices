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
