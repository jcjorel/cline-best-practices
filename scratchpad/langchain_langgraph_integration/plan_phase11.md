# Phase 11: LangGraph Integration

This phase implements the integration between our custom Bedrock clients and the LangGraph ecosystem. It focuses on creating state management, graph builders, and node definitions to enable the construction of sophisticated agent workflows with our LLM implementations.

## Objectives

1. Implement LangGraph state management
2. Create graph builder utilities
3. Build reusable node definitions
4. Implement message passing and state handling

## StateManager Implementation

Create the LangGraph state management in `src/dbp/llm/langgraph/state.py`:

```python
import logging
import uuid
from typing import Dict, Any, List, Optional, TypeVar, Generic, Type
from pydantic import BaseModel, create_model

class StateManager:
    """
    [Class intent]
    Manages state for LangGraph workflows. This class provides a central
    repository for state management, enabling stateful agent workflows
    with proper persistence and retrieval.
    
    [Design principles]
    - Clean state management interface
    - Support for typed state models
    - Efficient state transitions
    - Support for state persistence
    
    [Implementation details]
    - Uses Pydantic models for type-safe state
    - Manages state creation and transitions
    - Provides history tracking
    - Supports state serialization
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Initialize the state manager.
        
        [Design principles]
        - Minimal initialization
        - Support for customization
        
        [Implementation details]
        - Sets up logging
        - Initializes state storage
        
        Args:
            logger: Optional custom logger instance
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._states = {}
        self._history = {}
    
    def create_state(
        self, 
        state_id: Optional[str] = None, 
        initial_values: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        [Method intent]
        Create a new state instance with optional initial values.
        
        [Design principles]
        - Simple state creation
        - Support for initial values
        - Unique state identification
        
        [Implementation details]
        - Generates unique ID if not provided
        - Initializes state with provided values
        - Sets up history tracking
        
        Args:
            state_id: Optional ID for the state
            initial_values: Optional initial state values
            
        Returns:
            str: State ID
        """
        # Generate UUID if not provided
        if state_id is None:
            state_id = str(uuid.uuid4())
        
        # Create initial state
        self._states[state_id] = initial_values or {}
        
        # Initialize history
        self._history[state_id] = []
        
        self.logger.debug(f"Created state {state_id}")
        return state_id
    
    def get_state(self, state_id: str) -> Dict[str, Any]:
        """
        [Method intent]
        Get the current state for a given state ID.
        
        [Design principles]
        - Simple state access
        - Error handling
        
        [Implementation details]
        - Validates state existence
        - Returns state copy to prevent untracked modification
        
        Args:
            state_id: State ID to retrieve
            
        Returns:
            Dict[str, Any]: Current state
            
        Raises:
            KeyError: If state_id doesn't exist
        """
        if state_id not in self._states:
            raise KeyError(f"State {state_id} not found")
        
        # Return copy to prevent untracked modification
        return self._states[state_id].copy()
    
    def update_state(
        self, 
        state_id: str, 
        updates: Dict[str, Any], 
        track_history: bool = True
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Update an existing state with new values.
        
        [Design principles]
        - Clean state transition
        - Optional history tracking
        - Support for partial updates
        
        [Implementation details]
        - Validates state existence
        - Tracks previous state in history if enabled
        - Merges updates with existing state
        
        Args:
            state_id: State ID to update
            updates: State updates to apply
            track_history: Whether to record this update in history
            
        Returns:
            Dict[str, Any]: Updated state
            
        Raises:
            KeyError: If state_id doesn't exist
        """
        if state_id not in self._states:
            raise KeyError(f"State {state_id} not found")
        
        # Track history if enabled
        if track_history:
            self._history[state_id].append(self._states[state_id].copy())
        
        # Update state
        self._states[state_id].update(updates)
        
        self.logger.debug(f"Updated state {state_id}")
        return self._states[state_id].copy()
    
    def get_history(self, state_id: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Get the history of state transitions for a given state ID.
        
        [Design principles]
        - Support for state debugging
        - Complete history access
        
        [Implementation details]
        - Validates state existence
        - Returns history copy to prevent modification
        
        Args:
            state_id: State ID to retrieve history for
            
        Returns:
            List[Dict[str, Any]]: List of historical states
            
        Raises:
            KeyError: If state_id doesn't exist
        """
        if state_id not in self._history:
            raise KeyError(f"State {state_id} not found")
        
        # Return copy to prevent modification
        return self._history[state_id].copy()
    
    def delete_state(self, state_id: str) -> None:
        """
        [Method intent]
        Delete a state and its history.
        
        [Design principles]
        - Support for state cleanup
        - Complete removal of state data
        
        [Implementation details]
        - Validates state existence
        - Removes state and history
        
        Args:
            state_id: State ID to delete
            
        Raises:
            KeyError: If state_id doesn't exist
        """
        if state_id not in self._states:
            raise KeyError(f"State {state_id} not found")
        
        # Remove state and history
        del self._states[state_id]
        del self._history[state_id]
        
        self.logger.debug(f"Deleted state {state_id}")
```

## GraphBuilder Implementation

Create the LangGraph builder in `src/dbp/llm/langgraph/builder.py`:

```python
import logging
from typing import Dict, Any, List, Optional, Callable, Union, Type

# Import LangGraph components
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

from src.dbp.llm.common.base import ModelClientBase
from src.dbp.llm.langchain.adapters import LangChainLLMAdapter
from src.dbp.llm.langgraph.state import StateManager

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
        
        Args:
            state_manager: Optional state manager instance
            logger: Optional custom logger instance
        """
        self.state_manager = state_manager or StateManager()
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def create_graph(
        self,
        state_schema: Optional[Dict[str, Type]] = None
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
        if node_config:
            graph.add_node(name, node_fn, node_config)
        else:
            graph.add_node(name, node_fn)
        
        self.logger.debug(f"Added node {name} to graph")
        return graph
    
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
        
        self.logger.debug(f"Added conditional edges from {source}")
        return graph
    
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
        graph.add_edge(source, destination)
        
        if isinstance(destination, list):
            dest_str = ", ".join(destination)
        else:
            dest_str = destination
            
        self.logger.debug(f"Added edge from {source} to {dest_str}")
        return graph
    
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
        graph.set_entry_point(entry_point)
        
        self.logger.debug(f"Set entry point to {entry_point}")
        return graph
    
    def compile(
        self,
        graph: StateGraph,
        checkpointer: Optional[Any] = None,
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
            **kwargs: Additional compilation options
            
        Returns:
            Any: Compiled graph runnable
        """
        # Use memory saver if no checkpointer provided
        if not checkpointer:
            checkpointer = MemorySaver()
            
        # Compile graph
        runnable = graph.compile(checkpointer=checkpointer, **kwargs)
        
        self.logger.debug("Compiled graph")
        return runnable
```

## NodeDefinitions Implementation

Create common node definitions in `src/dbp/llm/langgraph/nodes.py`:

```python
import logging
from typing import Dict, Any, List, Optional, Callable, Union, TypeVar, Type

from langchain_core.language_models import BaseLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentAction, AgentFinish

from src.dbp.llm.common.base import ModelClientBase
from src.dbp.llm.langchain.adapters import LangChainLLMAdapter

# Type definitions for state
State = Dict[str, Any]

def create_agent_node(
    model_client: ModelClientBase,
    system_prompt: str,
    output_parser: Optional[Callable] = None,
    logger: Optional[logging.Logger] = None
) -> Callable[[State], State]:
    """
    [Function intent]
    Create a reusable agent node function for use in a LangGraph.
    
    [Design principles]
    - Simplified agent node creation
    - Integration with our model clients
    - Support for custom output parsing
    
    [Implementation details]
    - Creates LLM adapter for model client
    - Sets up system prompt and parsing
    - Returns a function that processes state
    
    Args:
        model_client: Our model client instance
        system_prompt: System prompt for the agent
        output_parser: Optional function to parse agent output
        logger: Optional logger instance
        
    Returns:
        Callable[[State], State]: Node function for LangGraph
    """
    # Set up logger
    node_logger = logger or logging.getLogger("AgentNode")
    
    # Create LLM adapter
    llm_adapter = LangChainLLMAdapter(model_client)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    
    def agent_node(state: State) -> State:
        """Agent node function."""
        try:
            # Get input from state
            input_text = state.get("input", "")
            context = state.get("context", {})
            
            # Prepare full input
            full_input = {
                "input": input_text,
                **context
            }
            
            # Generate response
            chain = prompt | llm_adapter
            response = chain.invoke(full_input)
            
            # Parse output if parser provided
            if output_parser:
                parsed_output = output_parser(response)
                return {**state, "output": parsed_output}
            
            # Return raw response
            return {**state, "output": response}
        except Exception as e:
            node_logger.error(f"Error in agent node: {str(e)}")
            return {**state, "error": str(e)}
    
    return agent_node

def create_router_node(
    options: List[str],
    logger: Optional[logging.Logger] = None
) -> Callable[[State], str]:
    """
    [Function intent]
    Create a router condition function for use with conditional edges.
    
    [Design principles]
    - Simple routing logic
    - Support for common patterns
    - Clean interface
    
    [Implementation details]
    - Returns a function that determines routing
    - Handles state examination for decision
    - Provides routing based on output or action
    
    Args:
        options: List of possible routing options
        logger: Optional logger instance
        
    Returns:
        Callable[[State], str]: Router condition function
    """
    # Set up logger
    node_logger = logger or logging.getLogger("RouterNode")
    
    def router_condition(state: State) -> str:
        """Router condition function."""
        try:
            # Check for explicit routing
            if "next" in state:
                next_node = state["next"]
                if next_node in options or next_node == "END":
                    return next_node
            
            # Check for agent action
            output = state.get("output", {})
            if isinstance(output, AgentAction):
                return output.tool
            elif isinstance(output, AgentFinish):
                return "END"
            elif isinstance(output, dict) and "action" in output:
                action = output["action"]
                if action in options:
                    return action
            
            # Default to first option or END
            return options[0] if options else "END"
        except Exception as e:
            node_logger.error(f"Error in router node: {str(e)}")
            return options[0] if options else "END"
    
    return router_condition

def create_tool_node(
    tool_function: Callable,
    output_key: str = "tool_result",
    logger: Optional[logging.Logger] = None
) -> Callable[[State], State]:
    """
    [Function intent]
    Create a tool execution node function for use in a LangGraph.
    
    [Design principles]
    - Simple tool execution
    - Clean state management
    - Error handling
    
    [Implementation details]
    - Creates a function that executes a tool
    - Handles tool input extraction
    - Manages state updates with tool results
    
    Args:
        tool_function: Tool function to execute
        output_key: Key to store result in state
        logger: Optional logger instance
        
    Returns:
        Callable[[State], State]: Node function for LangGraph
    """
    # Set up logger
    node_logger = logger or logging.getLogger("ToolNode")
    
    def tool_node(state: State) -> State:
        """Tool execution node function."""
        try:
            # Get tool input from state
            tool_input = state.get("tool_input", {})
            if isinstance(tool_input, str):
                # Try to interpret as single argument
                result = tool_function(tool_input)
            elif isinstance(tool_input, dict):
                # Use as kwargs
                result = tool_function(**tool_input)
            else:
                # Default empty call
                result = tool_function()
            
            # Update state with result
            return {**state, output_key: result}
        except Exception as e:
            node_logger.error(f"Error in tool node: {str(e)}")
            return {**state, "error": str(e)}
    
    return tool_node

def memory_node(state: State) -> State:
    """
    [Function intent]
    Update memory with current interaction.
    
    [Design principles]
    - Simple memory management
    - Clean interface
    - Standard memory format
    
    [Implementation details]
    - Extracts input and output from state
    - Updates memory list with new interaction
    - Manages memory size
    
    Args:
        state: Current state
        
    Returns:
        State: Updated state with memory
    """
    # Extract input and output
    current_input = state.get("input", "")
    current_output = state.get("output", "")
    
    # Get or initialize memory
    memory = state.get("memory", [])
    
    # Add current interaction to memory
    if current_input and current_output:
        memory.append({
            "input": current_input,
            "output": current_output
        })
    
    # Limit memory size if needed (keep last 10)
    if len(memory) > 10:
        memory = memory[-10:]
    
    # Update state
    return {**state, "memory": memory}

def summarize_node(
    model_client: ModelClientBase,
    logger: Optional[logging.Logger] = None
) -> Callable[[State], State]:
    """
    [Function intent]
    Create a node that summarizes the current state.
    
    [Design principles]
    - State summarization capability
    - Integration with our model clients
    - Clean interface
    
    [Implementation details]
    - Creates LLM adapter for model client
    - Extracts relevant state information
    - Generates summary of interaction
    
    Args:
        model_client: Our model client instance
        logger: Optional logger instance
        
    Returns:
        Callable[[State], State]: Node function for LangGraph
    """
    # Set up logger
    node_logger = logger or logging.getLogger("SummarizeNode")
    
    # Create LLM adapter
    llm_adapter = LangChainLLMAdapter(model_client)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize the following interaction history:"),
        ("human", "{memory}")
    ])
    
    def summarize_node_fn(state: State) -> State:
        """Summarize node function."""
        try:
            # Get memory from state
            memory = state.get("memory", [])
            
            # If no memory, return state unchanged
            if not memory:
                return state
            
            # Format memory for summarization
            memory_text = "\n\n".join([
                f"Input: {item['input']}\nOutput: {item['output']}"
                for item in memory
            ])
            
            # Generate summary
            chain = prompt | llm_adapter
            summary = chain.invoke({"memory": memory_text})
            
            # Update state
            return {**state, "summary": summary}
        except Exception as e:
            node_logger.error(f"Error in summarize node: {str(e)}")
            return {**state, "error": str(e)}
    
    return summarize_node_fn
```

## Implementation Steps

1. **State Management**
   - Implement `StateManager` in `src/dbp/llm/langgraph/state.py`
   - Create state persistence and history tracking
   - Add state validation and typing support

2. **Graph Builder**
   - Create `GraphBuilder` in `src/dbp/llm/langgraph/builder.py`
   - Implement methods for graph construction
   - Add edge and node management capabilities
   - Create graph compilation utilities

3. **Node Definitions**
   - Implement common node types in `src/dbp/llm/langgraph/nodes.py`
   - Create agent node factory function
   - Implement tool execution node
   - Create router and memory node functions

4. **Integration Utilities**
   - Add utilities for connecting with LangChain adapters
   - Create state type definitions
   - Implement checkpointing integration

## Notes

- The LangGraph integration builds on top of the LangChain integration from Phase 10
- All components focus on streaming for consistent performance
- The state management system provides a clean interface for persistent state
- Node definitions provide reusable components for common patterns

## Next Steps

After completing this phase:
1. Proceed to Phase 12 (LLM Coordinator Implementation)
2. Implement the MCP general query tool
3. Create agent manager for LLM coordination
