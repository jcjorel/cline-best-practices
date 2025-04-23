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
# Implements the ImpactAnalyzer class, responsible for analyzing the potential
# impact of changes in one document on other related documents within the project,
# based on the relationships stored in the RelationshipGraph.
###############################################################################
# [Source file design principles]
# - Uses the RelationshipGraph to traverse document dependencies.
# - Identifies direct impacts (e.g., documents impacted by the changed doc) and
#   reverse impacts (e.g., documents that depend on the changed doc).
# - Can potentially identify indirect/transitive impacts.
# - Populates DocImpact data structures with findings.
# - Design Decision: Graph Traversal for Impact Analysis (2025-04-15)
#   * Rationale: Leverages the graph structure to efficiently find related documents.
#   * Alternatives considered: Querying database repeatedly (less efficient).
###############################################################################
# [Source file constraints]
# - Depends on `RelationshipGraph` and `DocImpact` data model.
# - The accuracy and completeness of the impact analysis depend entirely on the
#   accuracy and completeness of the relationships stored in the graph.
# - Transitive impact analysis can become complex and computationally expensive.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/DOCUMENT_RELATIONSHIPS.md
# system:- src/dbp/doc_relationships/graph.py
# system:- src/dbp/doc_relationships/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:22:00Z : Initial creation of ImpactAnalyzer class by CodeAssistant
# * Implemented logic to find direct and reverse impacts using the graph. Added placeholder for indirect impacts.
###############################################################################

import logging
from typing import List, Optional, Dict, Any

# Assuming graph and data_models are accessible
try:
    from .graph import RelationshipGraph
    from .data_models import DocImpact
except ImportError:
    logging.getLogger(__name__).error("Failed to import dependencies for ImpactAnalyzer.", exc_info=True)
    # Placeholders
    RelationshipGraph = object
    DocImpact = object

logger = logging.getLogger(__name__)

class ImpactAnalyzer:
    """
    Analyzes the potential impact of changes in a given document on other
    documents within the project, based on the relationship graph.
    """

    def __init__(self, relationship_graph: RelationshipGraph, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ImpactAnalyzer.

        Args:
            relationship_graph: The RelationshipGraph instance containing document links.
            logger_override: Optional logger instance.
        """
        self.relationship_graph = relationship_graph
        self.logger = logger_override or logger
        self.logger.debug("ImpactAnalyzer initialized.")

    def analyze_impact(self, changed_document_path: str, max_depth: int = 3) -> List[DocImpact]:
        """
        Analyzes and returns a list of documents potentially impacted by changes
        to the specified document.

        Args:
            changed_document_path: The path of the document that has changed.
            max_depth: Maximum depth for searching indirect impacts (currently placeholder).

        Returns:
            A list of DocImpact objects describing potential impacts.
        """
        self.logger.info(f"Analyzing impact of changes to: {changed_document_path}")
        impacts: List[DocImpact] = []

        if changed_document_path not in self.relationship_graph.graph:
             self.logger.warning(f"Document '{changed_document_path}' not found in the relationship graph. Cannot analyze impact.")
             return []

        # 1. Direct Impacts (Documents that the changed document *impacts*)
        # Uses outgoing edges with type 'impacts'
        direct_impact_rels = self.relationship_graph.get_relationships(
            source=changed_document_path, relationship_type="impacts"
        )
        for _, target, attrs in direct_impact_rels:
            impact = DocImpact(
                source_document=changed_document_path,
                target_document=target,
                impact_type="direct",
                impact_level="high", # Assume direct impact is high
                relationship_type="impacts",
                topic=attrs.get("topic"),
                scope=attrs.get("scope")
            )
            impacts.append(impact)
            self.logger.debug(f"Direct impact found: {changed_document_path} -> {target}")

        # 2. Reverse Impacts (Documents that *depend on* the changed document)
        # Uses incoming edges with type 'depends on'
        reverse_impact_rels = self.relationship_graph.get_relationships(
            target=changed_document_path, relationship_type="depends on"
        )
        for source, _, attrs in reverse_impact_rels:
            impact = DocImpact(
                source_document=changed_document_path, # The changed doc is the source of impact
                target_document=source, # The doc that depends on it is the target of impact
                impact_type="reverse_dependency",
                impact_level="high", # Assume dependency implies high impact
                relationship_type="depends on",
                topic=attrs.get("topic"),
                scope=attrs.get("scope")
            )
            impacts.append(impact)
            self.logger.debug(f"Reverse dependency impact found: {source} depends on {changed_document_path}")

        # 3. Indirect/Transitive Impacts (Placeholder)
        # Find documents that depend on the documents identified in step 2.
        # This requires graph traversal (e.g., BFS or DFS up to max_depth).
        # For simplicity, this placeholder only goes one level deep.
        if max_depth > 1:
             directly_impacted_by_reverse = {imp.target_document for imp in impacts if imp.impact_type == "reverse_dependency"}
             for intermediate_doc in directly_impacted_by_reverse:
                  secondary_reverse_rels = self.relationship_graph.get_relationships(
                       target=intermediate_doc, relationship_type="depends on"
                  )
                  for secondary_source, _, attrs in secondary_reverse_rels:
                       # Avoid adding self-impact or already listed impacts
                       if secondary_source != changed_document_path and not any(imp.target_document == secondary_source for imp in impacts):
                            impact = DocImpact(
                                 source_document=changed_document_path,
                                 target_document=secondary_source,
                                 impact_type="indirect_dependency",
                                 impact_level="medium", # Assume indirect is medium impact
                                 relationship_type="depends on (transitive)",
                                 topic=attrs.get("topic"),
                                 scope=attrs.get("scope")
                            )
                            impacts.append(impact)
                            self.logger.debug(f"Indirect dependency impact found: {secondary_source} -> {intermediate_doc} -> {changed_document_path}")


        self.logger.info(f"Found {len(impacts)} potential impacts for changes in {changed_document_path}")
        # TODO: Add deduplication if the same target can be impacted via multiple paths?
        return impacts
