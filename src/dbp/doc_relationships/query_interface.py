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
# Implements the QueryInterface class, providing a simplified API for querying
# the document relationship graph managed by RelationshipGraph. It allows
# retrieving related documents and dependency chains.
###############################################################################
# [Source file design principles]
# - Provides a high-level query interface over the RelationshipGraph.
# - Offers methods for common queries like finding related documents or dependency chains.
# - Translates graph query results into more user-friendly data structures (e.g., lists of DocumentRelationship).
# - Delegates complex graph traversal to the RelationshipGraph instance.
# - Design Decision: Dedicated Query Interface (2025-04-15)
#   * Rationale: Separates the query logic from the core graph management, providing a cleaner API for consumers.
#   * Alternatives considered: Exposing RelationshipGraph directly (more complex for simple queries).
###############################################################################
# [Source file constraints]
# - Depends on `RelationshipGraph` and `DocumentRelationship` data model.
# - Query performance depends on the underlying graph implementation (networkx).
# - Assumes the graph is populated with relevant relationship data.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/doc_relationships/graph.py
# - src/dbp/doc_relationships/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:24:00Z : Initial creation of QueryInterface class by CodeAssistant
# * Implemented methods for querying related documents and dependency chains.
###############################################################################

import logging
from typing import List, Optional, Dict, Any, Tuple

# Assuming graph and data_models are accessible
try:
    from .graph import RelationshipGraph
    from .data_models import DocumentRelationship
except ImportError:
    logging.getLogger(__name__).error("Failed to import dependencies for QueryInterface.", exc_info=True)
    # Placeholders
    RelationshipGraph = object
    DocumentRelationship = object

logger = logging.getLogger(__name__)

class QueryInterface:
    """
    Provides a simplified interface for querying the document relationship graph.
    """

    def __init__(self, relationship_graph: RelationshipGraph, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the QueryInterface.

        Args:
            relationship_graph: The RelationshipGraph instance to query.
            logger_override: Optional logger instance.
        """
        self.relationship_graph = relationship_graph
        self.logger = logger_override or logger
        self.logger.debug("QueryInterface initialized.")

    def get_related_documents(self, document_path: str, relationship_type: Optional[str] = None) -> List[DocumentRelationship]:
        """
        Retrieves all documents directly related to the given document path,
        optionally filtering by relationship type. This includes both outgoing
        and incoming relationships.

        Args:
            document_path: The path of the document to query relationships for.
            relationship_type: If specified, only returns relationships of this type.

        Returns:
            A list of DocumentRelationship objects representing the direct connections.
        """
        self.logger.debug(f"Querying related documents for '{document_path}' (type: {relationship_type or 'any'}).")
        relationships: List[DocumentRelationship] = []

        if document_path not in self.relationship_graph.graph:
             self.logger.warning(f"Document '{document_path}' not found in graph for querying relationships.")
             return []

        try:
            # Get outgoing relationships
            outgoing_rels = self.relationship_graph.get_relationships(
                source=document_path, relationship_type=relationship_type
            )
            for source, target, attrs in outgoing_rels:
                relationships.append(DocumentRelationship(
                    source_document=source,
                    target_document=target,
                    relationship_type=attrs.get('relationship_type', 'unknown'),
                    topic=attrs.get('topic'),
                    scope=attrs.get('scope'),
                    metadata=attrs.get('metadata', {})
                    # id, created_at, updated_at are not relevant for query results
                ))

            # Get incoming relationships
            incoming_rels = self.relationship_graph.get_relationships(
                target=document_path, relationship_type=relationship_type
            )
            for source, target, attrs in incoming_rels:
                 # Avoid duplicating if relationship is bidirectional and type matches
                 # (though typically relationships are directed)
                 is_duplicate = any(r.source_document == source and r.target_document == target and r.relationship_type == attrs.get('relationship_type') for r in relationships)
                 if not is_duplicate:
                      relationships.append(DocumentRelationship(
                           source_document=source,
                           target_document=target,
                           relationship_type=attrs.get('relationship_type', 'unknown'),
                           topic=attrs.get('topic'),
                           scope=attrs.get('scope'),
                           metadata=attrs.get('metadata', {})
                      ))

            self.logger.info(f"Found {len(relationships)} related documents for '{document_path}'.")
            return relationships

        except Exception as e:
            self.logger.error(f"Error querying related documents for '{document_path}': {e}", exc_info=True)
            return []


    def get_dependency_chain(self, document_path: str, max_depth: int = 5) -> List[List[DocumentRelationship]]:
        """
        Finds dependency chains starting from the specified document.
        This traces outgoing "depends on" relationships up to a maximum depth.

        Args:
            document_path: The starting document path.
            max_depth: The maximum number of steps (dependencies) to trace.

        Returns:
            A list of dependency chains. Each chain is a list of DocumentRelationship
            objects representing the path from the starting document.
        """
        self.logger.debug(f"Querying dependency chain for '{document_path}' (max_depth: {max_depth}).")
        all_chains: List[List[DocumentRelationship]] = []

        if document_path not in self.relationship_graph.graph:
             self.logger.warning(f"Document '{document_path}' not found in graph for dependency chain query.")
             return []

        # Use DFS or BFS approach to find chains. Let's use DFS.
        stack: List[Tuple[str, List[DocumentRelationship]]] = [(document_path, [])] # (current_node, current_path_relationships)

        while stack:
            current_node, current_chain = stack.pop()

            # Check depth
            if len(current_chain) >= max_depth:
                continue

            # Find direct dependencies of the current node
            direct_deps = self.relationship_graph.get_relationships(
                source=current_node, relationship_type="depends on"
            )

            if not direct_deps:
                 # If this node has no further dependencies and the chain is not empty, add it
                 if current_chain:
                      all_chains.append(current_chain)
                 continue # End of this path

            for source, target, attrs in direct_deps:
                 # Create relationship object for this step
                 step_relationship = DocumentRelationship(
                      source_document=source,
                      target_document=target,
                      relationship_type="depends on",
                      topic=attrs.get("topic"),
                      scope=attrs.get("scope"),
                      metadata=attrs.get("metadata", {})
                 )

                 new_chain = current_chain + [step_relationship]

                 # Avoid cycles within this specific path traversal
                 nodes_in_new_chain = {rel.source_document for rel in new_chain} | {new_chain[-1].target_document}
                 if target in nodes_in_new_chain and target != new_chain[-1].target_document: # Basic cycle check for this path
                      self.logger.warning(f"Cycle detected in dependency path involving {target}. Stopping this path.")
                      all_chains.append(new_chain) # Add the chain up to the cycle
                      continue

                 # Push the next step onto the stack
                 stack.append((target, new_chain))


        # If no chains were found starting with dependencies, return empty list
        # (The initial node itself doesn't form a chain)
        self.logger.info(f"Found {len(all_chains)} dependency chains for '{document_path}'.")
        return all_chains
