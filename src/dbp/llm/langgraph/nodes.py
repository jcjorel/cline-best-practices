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
# Provides reusable node definitions for LangGraph workflows. These node
# functions can be used to build sophisticated agent workflows with our LLM
# implementations, handling common patterns like agent reasoning, routing,
# tool execution, and memory management.
###############################################################################
# [Source file design principles]
# - Reusable node function patterns
# - Integration with our LLM clients
# - Clean state management
# - Support for common workflow patterns
# - Consistent error handling
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with LangGraph's node function interface
# - Must handle state properly with immutable update patterns
# - Must provide proper error handling and fallbacks
# - Must integrate cleanly with our LLM adapters
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/langchain/adapters.py
# codebase:src/dbp/llm/common/exceptions.py
# system:logging
# system:typing
# system:langchain_core
# system:langgraph.graph
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:35:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Implemented reusable node definitions for LangGraph workflows
# * Added agent, router, tool, memory, and summarizer nodes
# * Integrated with our LLM client adapters
###############################################################################

"""
Reusable node definitions for LangGraph workflows.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable, Union, TypeVar, Type, cast

# Import conditionally to handle missing dependencies
try:
    from langchain_core.language_models import BaseLLM
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    
    # Try to import agent components if available
    try:
        from langchain.agents import AgentAction, AgentFinish
        AGENT_COMPONENTS_AVAILABLE = True
    except ImportError:
        AGENT_COMPONENTS_AVAILABLE = False
        
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    AGENT_COMPONENTS_AVAILABLE = False
    # Define placeholders for type checking
    class BaseLLM:
        """Placeholder BaseLLM class."""
        pass
    class AgentAction:
        """Placeholder AgentAction class."""
        pass
    class AgentFinish:
        """Placeholder AgentFinish class."""
        pass

from ..common.base import ModelClientBase
from ..langchain.adapters import LangChainLLMAdapter

# Type definition for state
State = Dict[str, Any]

# Node creation exception
class NodeCreationError(Exception):
    """Exception raised when node creation fails."""
    pass

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
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is required for agent nodes. Please install it with 'pip install langchain'")
    
    # Set up logger
    node_logger = logger or logging.getLogger("AgentNode")
    
    try:
        # Create LLM adapter
        llm_adapter = LangChainLLMAdapter(model_client)
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        
        def agent_node(state: State) -> State:
            """Agent node function."""
            try:
                # Get input from state
                input_text = state.get("input", "")
                context = state.get("context", {})
                memory = state.get("memory", [])
                
                # Prepare full input
                full_input = {
                    "input": input_text,
                    **context
                }
                
                # Add memory to input if available
                if memory:
                    memory_text = "\n\n".join([
                        f"User: {item.get('input', '')}\nAssistant: {item.get('output', '')}"
                        for item in memory
                    ])
                    full_input["memory"] = memory_text
                
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
    except Exception as e:
        raise NodeCreationError(f"Failed to create agent node: {str(e)}")

def create_router_node(
    options: List[str],
    end_condition: Optional[Callable[[Any], bool]] = None,
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
        end_condition: Optional function to check for end condition
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
            
            # Check if we should end
            if end_condition and end_condition(state):
                return "END"
            
            # Check for agent action if LangChain agent components are available
            if AGENT_COMPONENTS_AVAILABLE:
                output = state.get("output", {})
                if isinstance(output, AgentAction):
                    # Use tool name as next node
                    tool = output.tool
                    if tool in options:
                        return tool
                elif isinstance(output, AgentFinish):
                    return "END"
            
            # Check for action in output dictionary
            output = state.get("output", {})
            if isinstance(output, dict) and "action" in output:
                action = output["action"]
                if action in options:
                    return action
                elif action == "finish" or action == "end":
                    return "END"
            
            # Default to first option or END
            return options[0] if options else "END"
        except Exception as e:
            node_logger.error(f"Error in router node: {str(e)}")
            return options[0] if options else "END"
    
    return router_condition

def create_tool_node(
    tool_function: Callable,
    input_key: str = "tool_input",
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
        input_key: Key to extract tool input from state
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
            tool_input = state.get(input_key, {})
            
            # Handle agent action format
            if AGENT_COMPONENTS_AVAILABLE and "output" in state:
                output = state["output"]
                if isinstance(output, AgentAction):
                    tool_input = output.tool_input
            
            # Extract input from output dict if needed
            if tool_input == {} and isinstance(state.get("output", {}), dict):
                output_dict = state["output"]
                if "tool_input" in output_dict:
                    tool_input = output_dict["tool_input"]
                elif "input" in output_dict:
                    tool_input = output_dict["input"]
            
            # Execute tool based on input type
            if isinstance(tool_input, str):
                # Try to parse as JSON
                try:
                    parsed_input = json.loads(tool_input)
                    if isinstance(parsed_input, dict):
                        result = tool_function(**parsed_input)
                    else:
                        result = tool_function(tool_input)
                except (json.JSONDecodeError, TypeError):
                    # Use as single argument
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
    memory_key: str = "memory",
    summary_key: str = "summary",
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
        memory_key: Key to access memory in state
        summary_key: Key to store summary in state
        logger: Optional logger instance
        
    Returns:
        Callable[[State], State]: Node function for LangGraph
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is required for summarize nodes. Please install it with 'pip install langchain'")
    
    # Set up logger
    node_logger = logger or logging.getLogger("SummarizeNode")
    
    # Create LLM adapter
    llm_adapter = LangChainLLMAdapter(model_client)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize the following interaction history briefly:"),
        ("human", "{memory_text}")
    ])
    
    def summarize_node_fn(state: State) -> State:
        """Summarize node function."""
        try:
            # Get memory from state
            memory = state.get(memory_key, [])
            
            # If no memory, return state unchanged
            if not memory:
                return state
            
            # Format memory for summarization
            if isinstance(memory, list):
                if all(isinstance(item, dict) for item in memory):
                    # List of interaction dicts
                    memory_text = "\n\n".join([
                        f"Input: {item.get('input', '')}\nOutput: {item.get('output', '')}"
                        for item in memory
                    ])
                else:
                    # List of strings
                    memory_text = "\n".join(str(item) for item in memory)
            else:
                # Direct string
                memory_text = str(memory)
            
            # Generate summary
            chain = prompt | llm_adapter
            summary = chain.invoke({"memory_text": memory_text})
            
            # Update state
            return {**state, summary_key: summary}
        except Exception as e:
            node_logger.error(f"Error in summarize node: {str(e)}")
            return {**state, "error": str(e)}
    
    return summarize_node_fn

def input_parser_node(
    parser_function: Callable[[str], Any],
    input_key: str = "input",
    output_key: str = "parsed_input",
    logger: Optional[logging.Logger] = None
) -> Callable[[State], State]:
    """
    [Function intent]
    Create a node that parses input using a custom parser function.
    
    [Design principles]
    - Flexible input parsing
    - Clean state management
    - Error handling
    
    [Implementation details]
    - Uses provided parser function
    - Updates state with parsed input
    - Handles parsing errors
    
    Args:
        parser_function: Function to parse input
        input_key: Key to access input in state
        output_key: Key to store parsed input in state
        logger: Optional logger instance
        
    Returns:
        Callable[[State], State]: Node function for LangGraph
    """
    # Set up logger
    node_logger = logger or logging.getLogger("InputParserNode")
    
    def parser_node(state: State) -> State:
        """Parser node function."""
        try:
            # Get input from state
            input_value = state.get(input_key, "")
            
            # Skip if no input
            if not input_value:
                return state
            
            # Parse input
            parsed_input = parser_function(input_value)
            
            # Update state
            return {**state, output_key: parsed_input}
        except Exception as e:
            node_logger.error(f"Error parsing input: {str(e)}")
            return {**state, "error": f"Failed to parse input: {str(e)}"}
    
    return parser_node
