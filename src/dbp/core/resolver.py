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
# Implements the DependencyResolver class, responsible for analyzing component
# dependencies registered in the ComponentRegistry and determining a valid
# initialization order using topological sorting. It also detects circular
# dependencies.
###############################################################################
# [Source file design principles]
# - Uses Kahn's algorithm (or a similar graph traversal algorithm) for topological sorting.
# - Clearly identifies and raises a `CircularDependencyError` if cycles are detected.
# - Retrieves component dependency information from the ComponentRegistry.
# - Produces a linear ordering of component names for initialization.
# - Design Decision: Topological Sort for Dependency Resolution (2025-04-15)
#   * Rationale: Standard algorithm for ordering items based on dependencies, guarantees a valid sequence if one exists, and reliably detects cycles.
#   * Alternatives considered: Manual ordering (error-prone), Recursive initialization (can hide cycles).
###############################################################################
# [Source file constraints]
# - Depends on `registry.py` for the ComponentRegistry.
# - Assumes components correctly declare their dependencies via the `dependencies` property.
# - Relies on component names being consistent between registration and dependency declarations.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - scratchpad/dbp_implementation_plan/plan_component_init.md
# - src/dbp/core/registry.py
# - src/dbp/core/component.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:48:00Z : Initial creation of DependencyResolver class by CodeAssistant
# * Implemented topological sort algorithm and circular dependency detection.
###############################################################################

import logging
from typing import List, Dict, Set
from collections import deque

# Assuming registry.py and component.py are accessible
try:
    from .registry import ComponentRegistry
    from .component import Component # Needed for type hints if accessing component instances
except ImportError:
    # Define placeholders if run standalone or structure differs
    ComponentRegistry = object
    Component = object

logger = logging.getLogger(__name__)

class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected among components."""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        message = f"Circular dependency detected: {' -> '.join(cycle)}"
        super().__init__(message)

class DependencyResolver:
    """
    Resolves component dependencies using topological sorting to determine
    a valid initialization order. Detects circular dependencies.
    """

    def __init__(self, registry: ComponentRegistry):
        """
        Initializes the DependencyResolver.

        Args:
            registry: The ComponentRegistry containing the components/factories.
        """
        if not isinstance(registry, ComponentRegistry):
             # Basic type check, replace ComponentRegistry with actual class if possible
             logger.warning("DependencyResolver initialized with potentially incorrect registry type.")
        self.registry = registry
        self._component_cache: Dict[str, Component] = {} # Cache instantiated components

    def _get_component(self, name: str) -> Component:
        """Helper to get component instance, caching results."""
        if name not in self._component_cache:
             try:
                  # Use registry.get() which handles factory instantiation
                  self._component_cache[name] = self.registry.get(name)
             except KeyError:
                  logger.error(f"Dependency '{name}' listed but not found in registry.")
                  raise KeyError(f"Component '{name}' not found in registry, required as a dependency.")
             except Exception as e:
                  logger.error(f"Failed to get or instantiate component '{name}': {e}", exc_info=True)
                  raise RuntimeError(f"Could not retrieve dependency component '{name}'.") from e
        return self._component_cache[name]


    def resolve(self) -> List[str]:
        """
        Performs topological sorting to find a valid initialization order.

        Returns:
            A list of component names in a valid initialization order.

        Raises:
            CircularDependencyError: If a circular dependency is detected.
            KeyError: If a declared dependency is not registered.
            RuntimeError: If a component factory fails during dependency resolution.
        """
        logger.info("Resolving component initialization order...")
        self._component_cache = {} # Clear cache for fresh resolution
        all_names = self.registry.get_all_names()
        if not all_names:
            logger.info("No components registered, nothing to resolve.")
            return []

        # --- Build Dependency Graph ---
        # Adjacency list: component -> list of components that depend on it (successors)
        adj: Dict[str, Set[str]] = {name: set() for name in all_names}
        # In-degree count: component -> number of components it depends on (predecessors)
        in_degree: Dict[str, int] = {name: 0 for name in all_names}

        logger.debug(f"Building dependency graph for components: {all_names}")
        for name in all_names:
            try:
                # Get component instance (this might trigger factory)
                component = self._get_component(name)
                dependencies = component.dependencies
                logger.debug(f"Component '{name}' dependencies: {dependencies}")

                for dep_name in dependencies:
                    if dep_name not in all_names:
                        logger.error(f"Component '{name}' declares unregistered dependency: '{dep_name}'")
                        raise KeyError(f"Dependency '{dep_name}' for component '{name}' not found in registry.")

                    # Add edge from dependency to current component
                    if name not in adj[dep_name]:
                        adj[dep_name].add(name)
                        in_degree[name] += 1

            except (KeyError, RuntimeError, TypeError) as e:
                 # Catch errors during component retrieval or accessing dependencies
                 logger.error(f"Error processing dependencies for component '{name}': {e}", exc_info=True)
                 raise # Re-raise critical errors

        # --- Topological Sort (Kahn's Algorithm) ---
        # Queue of nodes with in-degree 0 (no prerequisites)
        queue = deque([name for name in all_names if in_degree[name] == 0])
        init_order: List[str] = [] # The final initialization order

        logger.debug(f"Initial queue (in-degree 0): {list(queue)}")

        while queue:
            component_name = queue.popleft()
            init_order.append(component_name)
            logger.debug(f"Adding '{component_name}' to initialization order.")

            # Process successors (components that depend on the current one)
            # Sort successors for deterministic ordering (optional but good practice)
            successors = sorted(list(adj[component_name]))
            for successor in successors:
                in_degree[successor] -= 1
                logger.debug(f"Decremented in-degree for '{successor}' to {in_degree[successor]}.")
                if in_degree[successor] == 0:
                    queue.append(successor) # Add to queue when all dependencies are met

        # --- Check for Cycles ---
        if len(init_order) != len(all_names):
            # If the order length doesn't match total components, there's a cycle.
            # Identifying the exact cycle requires a more complex graph traversal (e.g., DFS).
            # For now, list components with remaining in-degrees.
            remaining = [name for name in all_names if in_degree[name] > 0]
            logger.error(f"Circular dependency detected. Components involved (or dependent on cycle): {remaining}")
            # Attempt to find one cycle using DFS (optional, can be complex)
            cycle = self._find_cycle(adj, in_degree)
            raise CircularDependencyError(cycle if cycle else remaining)

        logger.info(f"Resolved initialization order: {init_order}")
        return init_order

    def _find_cycle(self, adj: Dict[str, Set[str]], in_degree: Dict[str, int]) -> List[str]:
        """Attempts to find one cycle in the graph using DFS (helper for error reporting)."""
        # This is a simplified cycle detection, might not find the smallest cycle.
        path: List[str] = []
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()

        nodes_in_cycle = {node for node, degree in in_degree.items() if degree > 0}
        if not nodes_in_cycle: return [] # Should not happen if called after length check

        # Start DFS from a node involved in the cycle
        start_node = next(iter(nodes_in_cycle))

        def dfs(node):
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)

            # Sort neighbors for deterministic results
            neighbors = sorted(list(adj.get(node, set())))
            for neighbor in neighbors:
                if neighbor not in visited:
                    found_cycle = dfs(neighbor)
                    if found_cycle:
                        return found_cycle
                elif neighbor in recursion_stack:
                    # Cycle detected
                    cycle_start_index = path.index(neighbor)
                    return path[cycle_start_index:]

            path.pop()
            recursion_stack.remove(node)
            return None

        cycle = dfs(start_node)
        return cycle if cycle else list(nodes_in_cycle) # Fallback if DFS fails
