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
# Provides a builder for creating LangGraph workflow graphs with our LLM
# implementations. This enables the creation of sophisticated agent workflows
# with proper state management, node definitions, and edge routing.
###############################################################################
# [Source file design principles]
# - Simplified graph creation interface
# - Integration with our LLM clients
# - Support for common workflow patterns
# - Clean composition of graph components
# - Fluent interface for method chaining
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with LangGraph's interfaces
# - Must integrate with our state management
# - Must support all LangGraph graph features
# - Must provide a clean, self-contained API
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/langchain/adapters.py
# codebase:src/dbp/llm/langgraph/state.py
# system:logging
# system:typing
# system:langgraph.graph
# system:langgraph.checkpoint
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:33:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Implemented GraphBuilder for LangGraph workflow creation
# * Added methods for creating graphs and adding nodes/edges
# * Added graph compilation and configuration utilities
###############################################################################

"""
Builder for LangGraph workflow graphs.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Union, Type, cast

# Import LangGraph components if available
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint import MemorySaver, Checkpointer
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Define placeholder for type checking when LangGraph is not available
    class StateGraph:
        """Placeholder StateGraph class when LangGraph is not available."""
        pass
    class END:
        """Placeholder END constant when LangGraph is not available."""
        pass
    class MemorySaver:
        """Placeholder MemorySaver class when LangGraph is not available."""
        pass
    class Checkpointer:
        """Placeholder Checkpointer class when LangGraph is not available."""
        pass
    LANGGRAPH_AVAILABLE = False

from ..common.base import ModelClientBase
from ..langchain.adapters import LangChainLLMAdapter
from .state import StateManager, StateError

class GraphBuilderError(Exception):
    """Base exception for graph builder errors."""
    pass

class GraphBuilder:
    """
    [Class intent]
    Builds LangGraph workflow graphs with our LLM implementations.
    This builder simplifies the creation of agent workflows using LangGraph,
    providing helper methods for common graph patterns and node definitions.
    
    [Design principles]
    - Simplified graph creation
    - Integration with our LLM clients
    - Support for common workflow patterns
    - Stateful workflow management
    
    [Implementation details]
    - Creates LangGraph StateGraph instances
    - Manages node definitions
    - Handles state transitions
    - Provides factory methods for common patterns
    """
    
    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the graph builder.
        
        [Design principles]
        - Optional state manager integration
        - Support for customization
        
        [Implementation details]
        - Sets up state manager (creates if not provided)
        - Initializes logging
        - Checks for LangGraph availability
        
        Args:
            state_manager: Optional state manager instance
            logger: Optional custom logger instance
            
        Raises:
            ImportError: If LangGraph is not available
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is not available. Please install it with 'pip install langgraph'.")
            
        self.state_manager = state_manager or StateManager()
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def create_graph(
        self,
        state_schema: Optional[Dict[str, Type]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> StateGraph:
        """
        [Method intent]
        Create a new LangGraph StateGraph.
        
        [Design principles]
        - Simple graph creation
        - Support for typed state schemas
        - Clean interface
        
        [Implementation details]
        - Creates StateGraph with provided schema
        - Sets up with memory saver for state persistence
        - Configures with best practices
        
        Args:
            state_schema: Optional schema for state typing
            name: Optional name for the graph
            description: Optional description of the graph
            
        Returns:
            StateGraph: New LangGraph StateGraph instance
        """
        # Create state schema
        if state_schema:
            # Use provided schema
            graph = StateGraph(state_schema)
        else:
            # Create with generic Dict state
            graph = StateGraph()
        
        # Set metadata if provided
        if name:
            graph.name = name
        if description:
            graph.description = description
        
        self.logger.debug(f"Created new StateGraph{' with schema' if state_schema else ''}")
        return graph
    
    def add_node(
        self,
        graph: StateGraph,
        name: str,
        node_fn: Callable,
        node_config: Optional[Dict[str, Any]] = None
    ) -> StateGraph:
        """
        [Method intent]
        Add a node to a LangGraph StateGraph.
        
        [Design principles]
        - Simple node addition
        - Support for node configuration
        - Fluent interface
        
        [Implementation details]
        - Adds node with function and configuration
        - Returns graph for method chaining
        
        Args:
            graph: StateGraph to add node to
            name: Name for the node
            node_fn: Node function
            node_config: Optional configuration for the node
            
        Returns:
            StateGraph: Updated graph
        """
        try:
            if node_config:
                graph.add_node(name, node_fn, node_config)
            else:
                graph.add_node(name, node_fn)
            
            self.logger.debug(f"Added node '{name}' to graph")
            return graph
        except Exception as e:
            raise GraphBuilderError(f"Failed to add node '{name}': {str(e)}")
    
    def add_conditional_edges(
        self,
        graph: StateGraph,
        source: str,
        condition_fn: Callable,
        destinations: Dict[Any, str],
        default_destination: Optional[str] = None
    ) -> StateGraph:
        """
        [Method intent]
        Add conditional edges from a source node to multiple destinations.
        
        [Design principles]
        - Support for complex workflows
        - Clean routing definition
        - Default routing support
        
        [Implementation details]
        - Adds conditional edge from source node
        - Sets up routing based on condition function
        - Configures default route if provided
        
        Args:
            graph: StateGraph to add edges to
            source: Source node name
            condition_fn: Function that determines routing
            destinations: Mapping of condition results to destination nodes
            default_destination: Optional default destination
            
        Returns:
            StateGraph: Updated graph
        """
        try:
            # Add conditional edge
            if default_destination:
                graph.add_conditional_edges(
                    source,
                    condition_fn,
                    destinations,
                    default=default_destination
                )
            else:
                graph.add_conditional_edges(
                    source,
                    condition_fn,
                    destinations
                )
            
            self.logger.debug(f"Added conditional edges from '{source}'")
            return graph
        except Exception as e:
            raise GraphBuilderError(f"Failed to add conditional edges from '{source}': {str(e)}")
    
    def add_edge(
        self,
        graph: StateGraph,
        source: str,
        destination: Union[str, List[str]]
    ) -> StateGraph:
        """
        [Method intent]
        Add a direct edge between nodes.
        
        [Design principles]
        - Simple edge definition
        - Support for both single and multiple destinations
        - Fluent interface
        
        [Implementation details]
        - Adds edge(s) from source to destination(s)
        - Handles both string and list destinations
        
        Args:
            graph: StateGraph to add edge to
            source: Source node name
            destination: Destination node name(s)
            
        Returns:
            StateGraph: Updated graph
        """
        try:
            graph.add_edge(source, destination)
            
            if isinstance(destination, list):
                dest_str = ", ".join(destination)
            else:
                dest_str = destination
                
            self.logger.debug(f"Added edge from '{source}' to '{dest_str}'")
            return graph
        except Exception as e:
            raise GraphBuilderError(f"Failed to add edge from '{source}': {str(e)}")
    
    def set_entry_point(
        self,
        graph: StateGraph,
        entry_point: str
    ) -> StateGraph:
        """
        [Method intent]
        Set the entry point for a graph.
        
        [Design principles]
        - Simple entry point configuration
        - Fluent interface
        
        [Implementation details]
        - Sets the entry point node for the graph
        
        Args:
            graph: StateGraph to configure
            entry_point: Entry point node name
            
        Returns:
            StateGraph: Updated graph
        """
        try:
            graph.set_entry_point(entry_point)
            
            self.logger.debug(f"Set entry point to '{entry_point}'")
            return graph
        except Exception as e:
            raise GraphBuilderError(f"Failed to set entry point to '{entry_point}': {str(e)}")
    
    def compile(
        self,
        graph: StateGraph,
        checkpointer: Optional[Any] = None,
        thread_safe: bool = True,
        debug: bool = False,
        **kwargs
    ) -> Any:
        """
        [Method intent]
        Compile a graph into a runnable workflow.
        
        [Design principles]
        - Simple graph compilation
        - Support for state persistence
        - Customizable configuration
        
        [Implementation details]
        - Compiles graph with checkpointer if provided
        - Handles additional compilation options
        
        Args:
            graph: StateGraph to compile
            checkpointer: Optional checkpointer for state persistence
            thread_safe: Whether the compiled graph should be thread-safe
            debug: Enable debug mode for compiled graph
            **kwargs: Additional compilation options
            
        Returns:
            Any: Compiled graph runnable
        """
        try:
            # Use memory saver if no checkpointer provided
            if not checkpointer:
                checkpointer = MemorySaver()
                
            # Compile graph
            runnable = graph.compile(
                checkpointer=checkpointer,
                thread_safe=thread_safe,
                debug=debug,
                **kwargs
            )
            
            self.logger.debug(f"Compiled graph{' with debug mode' if debug else ''}")
            return runnable
        except Exception as e:
            raise GraphBuilderError(f"Failed to compile graph: {str(e)}")
    
    def create_memory_checkpointer(self) -> MemorySaver:
        """
        [Method intent]
        Create a memory-based checkpointer for graph state.
        
        [Design principles]
        - Simple checkpointer creation
        - Clean interface
        
        [Implementation details]
        - Creates a MemorySaver instance
        
        Returns:
            MemorySaver: Memory-based checkpointer
        """
        return MemorySaver()
    
    def create_fixed_branch_node(
        self,
        branches: Dict[str, str]
    ) -> Callable:
        """
        [Method intent]
        Create a router node function for fixed branching.
        
        [Design principles]
        - Simple fixed-route creation
        - Support for predefined branching
        
        [Implementation details]
        - Creates a function that routes based on state values
        - Uses predefined branch mappings
        
        Args:
            branches: Mapping of state values to branch names
            
        Returns:
            Callable: Router function for the graph
        """
        def branch_router(state: Dict[str, Any]) -> str:
            branch_key = state.get("branch", None)
            if branch_key and branch_key in branches:
                return branches[branch_key]
            return list(branches.values())[0] if branches else "END"
        
        return branch_router
    
    def create_conditional_branch_node(
        self,
        condition_fn: Callable[[Dict[str, Any]], str]
    ) -> Callable:
        """
        [Method intent]
        Create a router node function for conditional branching.
        
        [Design principles]
        - Support for dynamic branching
        - Clean interface
        
        [Implementation details]
        - Wraps a condition function for graph routing
        - Handles errors with default routing
        
        Args:
            condition_fn: Function that determines routing
            
        Returns:
            Callable: Router function for the graph
        """
        def conditional_router(state: Dict[str, Any]) -> str:
            try:
                return condition_fn(state)
            except Exception as e:
                self.logger.error(f"Error in conditional router: {str(e)}")
                return "END"
        
        return conditional_router
