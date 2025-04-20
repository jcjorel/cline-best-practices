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
# Implements the RelationshipGraph class, which provides an in-memory graph
# representation of the relationships between documentation files using the
# networkx library. It allows adding, removing, and querying relationships.
###############################################################################
# [Source file design principles]
# - Uses `networkx.MultiDiGraph` to allow multiple directed edges (relationships)
#   between the same two documents (nodes).
# - Nodes represent document paths (strings).
# - Edges represent relationships and store attributes like type, topic, scope.
# - Provides methods for graph manipulation and querying (add, remove, get neighbors, find paths).
# - Thread-safe operations using RLock.
# - Design Decision: Use networkx Library (2025-04-15)
#   * Rationale: Powerful and standard library for graph manipulation and analysis in Python, providing efficient algorithms.
#   * Alternatives considered: Custom graph implementation (complex, error-prone).
###############################################################################
# [Source file constraints]
# - Requires the `networkx` library (`pip install networkx`).
# - The entire graph is held in memory; performance may degrade for extremely large numbers of documents and relationships.
# - Assumes node identifiers (document paths) are unique strings.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
# - src/dbp/doc_relationships/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:18:10Z : Initial creation of RelationshipGraph class by CodeAssistant
# * Implemented graph operations using networkx.MultiDiGraph. Added query methods.
###############################################################################

import logging
import threading
from typing import List, Dict, Any, Optional, Tuple, Set

# Try to import networkx
try:
    import networkx
except ImportError:
    logging.getLogger(__name__).critical("The 'networkx' library is required for RelationshipGraph. Please install it (`pip install networkx`).")
    # Define a dummy class if networkx is not available to allow module loading
    class MultiDiGraph:
        def add_node(self, *args, **kwargs): pass
        def add_edge(self, *args, **kwargs): pass
        def remove_node(self, *args, **kwargs): pass
        def remove_edge(self, *args, **kwargs): pass
        def nodes(self): return []
        def edges(self, *args, **kwargs): return []
        def degree(self, *args, **kwargs): return 0
        def out_edges(self, *args, **kwargs): return []
        def in_edges(self, *args, **kwargs): return []
        def subgraph(self, *args, **kwargs): return self
        def get_edge_data(self, *args, **kwargs): return {}
    networkx = type('obj', (object,), {'MultiDiGraph': MultiDiGraph, 'NetworkXError': Exception, 'all_simple_paths': lambda *args, **kwargs: []})()


logger = logging.getLogger(__name__)

class RelationshipGraph:
    """
    Manages an in-memory graph representation of document relationships
    using the networkx library.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the RelationshipGraph."""
        self.logger = logger_override or logger
        # Use MultiDiGraph to allow multiple relationship types between the same two docs
        self.graph = networkx.MultiDiGraph()
        self._lock = threading.RLock() # Ensure thread safety for graph modifications
        self.logger.debug("RelationshipGraph initialized.")

    def add_relationship(
        self,
        source: str,
        target: str,
        relationship_type: str,
        topic: Optional[str] = None,
        scope: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Adds a directed relationship (edge) between two documents (nodes) to the graph.

        Args:
            source: The path of the source document node.
            target: The path of the target document node.
            relationship_type: The type of the relationship (e.g., 'depends on').
            topic: Optional subject matter of the relationship.
            scope: Optional scope of the relationship.
            metadata: Optional dictionary of additional attributes for the relationship.
        """
        if not source or not target or not relationship_type:
             self.logger.warning("Attempted to add relationship with missing source, target, or type.")
             return

        with self._lock:
            # Add nodes if they don't exist (networkx handles this automatically, but explicit add allows attributes)
            if source not in self.graph:
                self.graph.add_node(source, path=source) # Add path attribute to node
            if target not in self.graph:
                self.graph.add_node(target, path=target)

            # Prepare edge attributes
            edge_attrs = metadata or {}
            edge_attrs['relationship_type'] = relationship_type
            if topic: edge_attrs['topic'] = topic
            if scope: edge_attrs['scope'] = scope

            # Add the edge with attributes
            # Using add_edge allows multiple edges if key is different, or updates if key exists.
            # For MultiDiGraph, add_edge adds a new edge each time unless a key is specified.
            # Let's add a new edge each time, allowing multiple relations of same type if needed.
            self.graph.add_edge(source, target, **edge_attrs)
            self.logger.debug(f"Added relationship to graph: '{source}' --[{relationship_type}]--> '{target}'")

    def remove_relationship(self, source: str, target: str, relationship_type: Optional[str] = None, key: Optional[Any] = None):
        """
        Removes relationships (edges) between two documents.

        Args:
            source: The path of the source document node.
            target: The path of the target document node.
            relationship_type: If specified, only remove edges with this relationship type.
            key: If specified (for MultiDiGraph), remove only the specific edge with this key.
        """
        with self._lock:
            if not self.graph.has_edge(source, target):
                self.logger.debug(f"No edge found between '{source}' and '{target}' to remove.")
                return

            edges_to_remove = []
            if key is not None:
                 # Remove specific edge by key
                 if self.graph.has_edge(source, target, key=key):
                      edges_to_remove.append((source, target, key))
                 else:
                      self.logger.warning(f"Edge key {key} not found between '{source}' and '{target}'.")
            else:
                 # Find all edges between source and target matching the type (if specified)
                 for k, data in self.graph.get_edge_data(source, target, default={}).items():
                      if relationship_type is None or data.get('relationship_type') == relationship_type:
                           edges_to_remove.append((source, target, k))

            if not edges_to_remove:
                 self.logger.debug(f"No matching edges found to remove between '{source}' and '{target}' (type: {relationship_type}).")
                 return

            # Remove the identified edges
            for u, v, k in edges_to_remove:
                try:
                    self.graph.remove_edge(u, v, key=k)
                    self.logger.info(f"Removed relationship from graph: '{u}' --[{relationship_type or 'any'}]--> '{v}' (key={k})")
                except networkx.NetworkXError as e:
                     self.logger.error(f"Error removing edge ({u}, {v}, key={k}): {e}")

            # Optional: Remove nodes if they become isolated (degree 0)
            # self._remove_isolated_node(source)
            # self._remove_isolated_node(target)

    def _remove_isolated_node(self, node: str):
         """Removes a node if it has no incoming or outgoing edges."""
         if node in self.graph and self.graph.degree(node) == 0:
              try:
                   self.graph.remove_node(node)
                   self.logger.debug(f"Removed isolated node from graph: {node}")
              except networkx.NetworkXError as e:
                   self.logger.error(f"Error removing isolated node {node}: {e}")


    def get_relationships(self, source: Optional[str] = None, target: Optional[str] = None, relationship_type: Optional[str] = None) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Retrieves relationships matching the criteria.

        Args:
            source: Optional source document path.
            target: Optional target document path.
            relationship_type: Optional relationship type to filter by.

        Returns:
            A list of tuples, each containing (source_path, target_path, attributes_dict).
        """
        with self._lock:
            edges_data = []
            edges_iterator = self.graph.edges(data=True, keys=False) # Don't need keys here

            if source and target:
                 edge_data_dict = self.graph.get_edge_data(source, target, default={})
                 for key, data in edge_data_dict.items():
                      if relationship_type is None or data.get('relationship_type') == relationship_type:
                           edges_data.append((source, target, data))
            elif source:
                 for u, v, data in self.graph.out_edges(source, data=True):
                      if relationship_type is None or data.get('relationship_type') == relationship_type:
                           edges_data.append((u, v, data))
            elif target:
                 for u, v, data in self.graph.in_edges(target, data=True):
                      if relationship_type is None or data.get('relationship_type') == relationship_type:
                           edges_data.append((u, v, data))
            else: # Neither source nor target specified
                 for u, v, data in edges_iterator:
                      if relationship_type is None or data.get('relationship_type') == relationship_type:
                           edges_data.append((u, v, data))

            return edges_data

    def get_neighbors(self, node: str, mode: str = 'all') -> Set[str]:
        """
        Gets the neighbors (successors, predecessors, or both) of a node.

        Args:
            node: The document path (node identifier).
            mode: 'successors' (nodes pointed to), 'predecessors' (nodes pointing to),
                  or 'all' (default).

        Returns:
            A set of neighbor node paths.
        """
        with self._lock:
            if node not in self.graph:
                return set()
            if mode == 'successors':
                return set(self.graph.successors(node))
            elif mode == 'predecessors':
                return set(self.graph.predecessors(node))
            elif mode == 'all':
                return set(self.graph.successors(node)) | set(self.graph.predecessors(node))
            else:
                self.logger.warning(f"Invalid mode '{mode}' for get_neighbors. Use 'successors', 'predecessors', or 'all'.")
                return set()

    def find_paths(self, source: str, target: str, max_length: Optional[int] = None) -> List[List[str]]:
        """
        Finds all simple paths (no repeated nodes) between source and target nodes.

        Args:
            source: The starting node path.
            target: The ending node path.
            max_length: The maximum length (number of edges) for paths.

        Returns:
            A list of paths, where each path is a list of node paths.
        """
        with self._lock:
            if source not in self.graph or target not in self.graph:
                return []
            try:
                paths = list(networkx.all_simple_paths(
                    self.graph, source=source, target=target, cutoff=max_length
                ))
                return paths
            except networkx.NetworkXError as e:
                self.logger.error(f"Error finding paths between '{source}' and '{target}': {e}")
                return []

    def get_graph_stats(self) -> Dict[str, int]:
         """Returns basic statistics about the graph."""
         with self._lock:
              return {
                   "num_nodes": self.graph.number_of_nodes(),
                   "num_edges": self.graph.number_of_edges(),
              }

    def clear(self):
         """Removes all nodes and edges from the graph."""
         with self._lock:
              self.graph.clear()
              self.logger.info("Relationship graph cleared.")
