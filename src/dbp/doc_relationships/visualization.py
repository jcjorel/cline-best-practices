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
# Implements the GraphVisualization class, responsible for generating visual
# representations of the document relationship graph, specifically using the
# Mermaid diagram syntax (flowchart TD).
###############################################################################
# [Source file design principles]
# - Takes a RelationshipGraph instance as input.
# - Generates Mermaid flowchart syntax (graph TD).
# - Creates safe node IDs from document paths suitable for Mermaid.
# - Includes node labels (basenames) and edge labels (relationship types).
# - Optionally filters the graph to a subset of nodes before generation.
# - Applies basic styling using Mermaid class definitions.
# - Design Decision: Mermaid Syntax Output (2025-04-15)
#   * Rationale: Mermaid is widely supported in Markdown viewers (like VS Code), providing an easy way to visualize the graph without complex dependencies.
#   * Alternatives considered: Generating image files (requires graphics libraries), Using other graph viz libraries (e.g., graphviz - requires external installation).
###############################################################################
# [Source file constraints]
# - Depends on `RelationshipGraph`.
# - Node ID generation might produce collisions for very similarly named files in different directories (uses basename).
# - Visualization clarity can decrease for very large or densely connected graphs.
# - Assumes relationship types are suitable for direct use as edge labels.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
# - src/dbp/doc_relationships/graph.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:23:25Z : Initial creation of GraphVisualization class by CodeAssistant
# * Implemented Mermaid diagram generation logic.
###############################################################################

import logging
import os
import re
from typing import Optional, List, Set

# Assuming graph is accessible
try:
    from .graph import RelationshipGraph
except ImportError:
    logging.getLogger(__name__).error("Failed to import RelationshipGraph for GraphVisualization.")
    # Placeholder
    RelationshipGraph = object

logger = logging.getLogger(__name__)

class GraphVisualization:
    """
    Generates visual representations of the document relationship graph,
    currently supporting Mermaid flowchart syntax.
    """

    def __init__(self, relationship_graph: RelationshipGraph, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the GraphVisualization service.

        Args:
            relationship_graph: The RelationshipGraph instance containing the data.
            logger_override: Optional logger instance.
        """
        self.relationship_graph = relationship_graph
        self.logger = logger_override or logger
        self.logger.debug("GraphVisualization initialized.")

    def generate_mermaid_diagram(self, document_paths: Optional[List[str]] = None, include_isolated: bool = False) -> str:
        """
        Generates a Mermaid diagram string (flowchart TD) representing the
        document relationships.

        Args:
            document_paths: An optional list of document paths (nodes) to include.
                            If None, the entire graph is visualized.
            include_isolated: If True, includes nodes even if they have no relationships
                              within the selected subgraph (or full graph). Default False.

        Returns:
            A string containing the Mermaid diagram definition.
        """
        self.logger.info(f"Generating Mermaid diagram. Node filter: {document_paths is not None}, Include isolated: {include_isolated}")

        try:
            # Determine the graph to use (full or subgraph)
            graph_to_render = self.relationship_graph.graph # Get the networkx graph instance
            nodes_to_render: Optional[Set[str]] = None

            if document_paths:
                 # Filter nodes present in the main graph
                 nodes_in_graph = {node for node in document_paths if node in graph_to_render}
                 if not nodes_in_graph:
                      self.logger.warning("None of the specified document paths found in the graph.")
                      return "```mermaid\ngraph TD;\n    subgraph Error\n        NoNodes[No specified nodes found in graph]\n    end\n```"
                 # Create the subgraph view
                 graph_to_render = graph_to_render.subgraph(nodes_in_graph)
                 nodes_to_render = nodes_in_graph # Keep track for isolated node handling
                 self.logger.debug(f"Rendering subgraph with {len(nodes_in_graph)} specified nodes.")


            # Start Mermaid diagram definition
            mermaid_lines = ["```mermaid", "graph TD;"] # TD = Top Down

            # Define node styles (optional)
            # mermaid_lines.append("    classDef doc fill:#eee,stroke:#333,stroke-width:1px;")
            # mermaid_lines.append("    classDef coreDoc fill:#f9f,stroke:#f0f,stroke-width:2px;")

            processed_nodes: Set[str] = set()

            # Add edges and implicitly define nodes involved
            for u, v, data in graph_to_render.edges(data=True):
                source_id = self._safe_node_id(u)
                target_id = self._safe_node_id(v)
                rel_type = data.get('relationship_type', 'related')
                # Sanitize label text for Mermaid if needed (quotes, etc.)
                edge_label = self._sanitize_mermaid_label(rel_type)

                # Define nodes with labels if not already done
                if u not in processed_nodes:
                     source_label = self._sanitize_mermaid_label(os.path.basename(u))
                     mermaid_lines.append(f"    {source_id}[\"{source_label}\"];")
                     processed_nodes.add(u)
                if v not in processed_nodes:
                     target_label = self._sanitize_mermaid_label(os.path.basename(v))
                     mermaid_lines.append(f"    {target_id}[\"{target_label}\"];")
                     processed_nodes.add(v)

                # Add the edge
                mermaid_lines.append(f"    {source_id} -- \"{edge_label}\" --> {target_id};")

            # Add isolated nodes if requested and rendering full graph or subgraph
            if include_isolated:
                 nodes_in_scope = nodes_to_render if nodes_to_render is not None else set(graph_to_render.nodes())
                 for node in nodes_in_scope:
                      if node not in processed_nodes:
                           node_id = self._safe_node_id(node)
                           node_label = self._sanitize_mermaid_label(os.path.basename(node))
                           mermaid_lines.append(f"    {node_id}[\"{node_label}\"];")
                           processed_nodes.add(node) # Mark as processed

            # Add styling (example)
            # core_docs = ["DESIGN.md", "DATA_MODEL.md"] # Example core docs
            # for node in processed_nodes:
            #     node_id = self._safe_node_id(node)
            #     if os.path.basename(node) in core_docs:
            #          mermaid_lines.append(f"    class {node_id} coreDoc;")
            #     else:
            #          mermaid_lines.append(f"    class {node_id} doc;")


            mermaid_lines.append("```")
            self.logger.info(f"Mermaid diagram generated with {len(processed_nodes)} nodes and {graph_to_render.number_of_edges()} edges.")
            return "\n".join(mermaid_lines)

        except Exception as e:
            self.logger.error(f"Failed to generate Mermaid diagram: {e}", exc_info=True)
            return "```mermaid\ngraph TD;\n    Error[Error generating graph]\n```"


    def _safe_node_id(self, node_path: str) -> str:
        """
        Generates a safe node ID for Mermaid from a file path.
        Tries to create a relatively readable ID based on the filename.

        Args:
            node_path: The document file path.

        Returns:
            A string safe for use as a Mermaid node ID.
        """
        # Use basename and remove extension
        node_name = Path(node_path).stem
        # Replace common problematic characters (spaces, dots, slashes, etc.) with underscores
        # Keep alphanumeric and underscores
        safe_id = re.sub(r'\W|^(?=\d)', '_', node_name) # Replace non-alphanumeric, ensure starts with non-digit

        # Add hash for very long names or potential collisions (optional)
        # if len(safe_id) > 30:
        #     hash_part = hashlib.md5(node_path.encode()).hexdigest()[:6]
        #     safe_id = safe_id[:24] + "_" + hash_part

        # Ensure it's not empty
        if not safe_id:
             return f"node_{hash(node_path) % 10000}" # Fallback to hash

        return safe_id

    def _sanitize_mermaid_label(self, label: str) -> str:
         """Sanitizes text to be used as a label within Mermaid quotes."""
         if not label: return ""
         # Escape quotes and potentially other characters Mermaid might misinterpret
         return label.replace('"', '#quot;') # Mermaid specific escape for quotes
