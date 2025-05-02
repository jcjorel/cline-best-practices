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
# Implements the Agent Manager for orchestrating LLM-based agents. This component
# serves as the central coordination point for LLM functionality, managing client
# instances, executing queries, and coordinating workflows for sophisticated tasks.
###############################################################################
# [Source file design principles]
# - Component-based design for system integration
# - Streaming-first approach for all interactions
# - Coordination of LLM agents for complex tasks
# - Clean separation of concerns
# - Graceful error handling
###############################################################################
# [Source file constraints]
# - Must integrate with core component system
# - Must support concurrent execution
# - Must provide proper state management
# - Must handle streaming responses
###############################################################################
# [Dependencies]
# codebase:src/dbp/core/component.py
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/common/config_registry.py
# codebase:src/dbp/llm/common/tool_registry.py
# codebase:src/dbp/llm/langgraph/builder.py
# codebase:src/dbp/llm/langgraph/nodes.py
# codebase:src/dbp/llm_coordinator/exceptions.py
# system:logging
# system:asyncio
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:38:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created AgentManager component for LLM coordination
# * Added model client management and initialization
# * Implemented general query and workflow execution
###############################################################################

"""
Agent manager for LLM coordination.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterator, Union

from src.dbp.core.component import Component
from src.dbp.llm.common.base import ModelClientBase
from src.dbp.llm.common.config_registry import ConfigRegistry
from src.dbp.llm.common.tool_registry import ToolRegistry
from src.dbp.llm.langgraph.builder import GraphBuilder
from src.dbp.llm.langgraph.nodes import create_agent_node, create_router_node, create_tool_node
from src.dbp.llm_coordinator.exceptions import (
    CoordinationError,
    ModelNotAvailableError,
    WorkflowExecutionError,
    AgentInitializationError
)


class AgentManager(Component):
    """
    [Class intent]
    Manages LLM agents and orchestrates their interactions within the application.
    This component serves as the central coordination point for LLM-based functionality,
    providing a consistent interface for agent creation, configuration, and execution.
    
    [Design principles]
    - Component-based design for system integration
    - Coordination of LLM agents for complex tasks
    - Tool-based agent extensibility
    - Streaming-first approach for all interactions
    
    [Implementation details]
    - Integrates with LangChain and LangGraph for agent workflows
    - Manages agent state and configuration
    - Handles tool registration and execution
    - Implements proper error handling and reporting
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the agent manager with configuration.
        
        [Design principles]
        - Component lifecycle management
        - Configuration-driven initialization
        - Clean error handling
        
        [Implementation details]
        - Initializes as a system component
        - Sets up configuration with defaults
        - Prepares registries and clients
        
        Args:
            config: Optional configuration dictionary
            logger: Optional custom logger instance
        """
        # Initialize as component
        super().__init__("agent_manager", config, logger)
        
        # Will be initialized during start()
        self._config_registry = None
        self._tool_registry = None
        self._model_clients = {}
        self._graph_builder = None
        self._default_model = None
        self._initialized = False
    
    async def _initialize(self) -> None:
        """
        [Method intent]
        Initialize the agent manager during component startup.
        
        [Design principles]
        - Component lifecycle integration
        - Clean dependency resolution
        - Proper initialization order
        
        [Implementation details]
        - Gets required dependencies
        - Initializes registries and clients
        - Sets up graph builder
        - Configures default model
        
        Raises:
            CoordinationError: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Get registries
            self._config_registry = self.get_dependency(ConfigRegistry)
            self._tool_registry = self.get_dependency(ToolRegistry)
            
            # Get model clients
            try:
                # Create model clients
                self._model_clients = {
                    "claude": await self._create_claude_client(),
                    "nova": await self._create_nova_client()
                }
                
                # Set default model
                self._default_model = self.config.get("default_model", "claude")
                
            except ImportError as e:
                self.logger.warning(f"Could not initialize all model clients: {str(e)}")
                # Set available models as default if needed
                if not self._model_clients:
                    raise AgentInitializationError("model_clients", "No model clients available")
                if self._default_model not in self._model_clients:
                    self._default_model = next(iter(self._model_clients.keys()))
            
            # Create graph builder
            self._graph_builder = GraphBuilder()
            
            self._initialized = True
            self.logger.info("Agent manager initialized with models: " + ", ".join(self._model_clients.keys()))
        except Exception as e:
            raise CoordinationError(f"Failed to initialize agent manager: {str(e)}")
    
    async def _create_claude_client(self) -> ModelClientBase:
        """
        [Method intent]
        Create a Claude model client.
        
        [Design principles]
        - Clean model instantiation
        - Configuration-based setup
        
        [Implementation details]
        - Gets model ID from configuration
        - Creates and initializes Claude client
        - Sets up with appropriate parameters
        
        Returns:
            ModelClientBase: Initialized Claude client
            
        Raises:
            AgentInitializationError: If client creation fails
        """
        try:
            from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
            
            # Get model ID from config
            model_id = self.config.get("claude_model_id", "anthropic.claude-3-haiku-20240307-v1:0")
            
            # Create client
            client = ClaudeClient(model_id=model_id)
            
            # Initialize client
            await client.initialize()
            
            return client
        except Exception as e:
            self.logger.error(f"Failed to create Claude client: {str(e)}")
            raise AgentInitializationError("claude", str(e))
    
    async def _create_nova_client(self) -> ModelClientBase:
        """
        [Method intent]
        Create a Nova model client.
        
        [Design principles]
        - Clean model instantiation
        - Configuration-based setup
        
        [Implementation details]
        - Gets model ID from configuration
        - Creates and initializes Nova client
        - Sets up with appropriate parameters
        
        Returns:
            ModelClientBase: Initialized Nova client
            
        Raises:
            AgentInitializationError: If client creation fails
        """
        try:
            from src.dbp.llm.bedrock.models.nova import NovaClient
            
            # Get model ID from config
            model_id = self.config.get("nova_model_id", "amazon.titan-text-express-v1")
            
            # Create client
            client = NovaClient(model_id=model_id)
            
            # Initialize client
            await client.initialize()
            
            return client
        except Exception as e:
            self.logger.error(f"Failed to create Nova client: {str(e)}")
            raise AgentInitializationError("nova", str(e))
    
    async def execute_general_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        stream: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Execute a general query using the most appropriate LLM agent.
        
        [Design principles]
        - Streaming-first approach
        - Context-aware processing
        - Flexible model selection
        
        [Implementation details]
        - Selects appropriate model based on query and context
        - Uses agent workflow for processing
        - Returns streaming response
        
        Args:
            query: User query text
            context: Optional context information
            model: Optional specific model to use
            stream: Whether to stream the response
            
        Yields:
            Dict[str, Any]: Response chunks
            
        Raises:
            CoordinationError: If execution fails
        """
        if not self._initialized:
            await self._initialize()
        
        try:
            # Get model client
            model_name = model or self._default_model
            if model_name not in self._model_clients:
                available_models = list(self._model_clients.keys())
                raise ModelNotAvailableError(model_name, available_models)
                
            model_client = self._model_clients[model_name]
            
            # Prepare context
            full_context = context or {}
            
            # Construct system message with context if needed
            system_message = "You are a helpful assistant."
            if full_context:
                system_message += "\n\nContext information:\n"
                for key, value in full_context.items():
                    if isinstance(value, str):
                        system_message += f"\n{key}: {value}"
                    else:
                        try:
                            system_message += f"\n{key}: {json.dumps(value)}"
                        except:
                            system_message += f"\n{key}: [Complex data]"
            
            # Stream response
            if stream:
                async for chunk in model_client.stream_chat([
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ]):
                    yield chunk
            else:
                # For non-streaming, collect response
                response_chunks = []
                async for chunk in model_client.stream_chat([
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ]):
                    response_chunks.append(chunk)
                    
                # Combine chunks for complete response
                combined_text = ""
                for chunk in response_chunks:
                    if "delta" in chunk and "text" in chunk["delta"]:
                        combined_text += chunk["delta"]["text"]
                        
                # Return complete response
                yield {
                    "type": "complete_response",
                    "content": combined_text
                }
        except ModelNotAvailableError as e:
            # Re-raise model errors
            raise e
        except Exception as e:
            raise CoordinationError(f"Failed to execute general query: {str(e)}")
    
    async def execute_agent_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        stream: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Execute a predefined agent workflow.
        
        [Design principles]
        - Reusable workflow execution
        - Streaming-first approach
        - Flexible workflow configuration
        
        [Implementation details]
        - Selects workflow by name
        - Creates and executes workflow graph
        - Handles workflow state
        
        Args:
            workflow_name: Name of the workflow to execute
            input_data: Input data for the workflow
            stream: Whether to stream the response
            
        Yields:
            Dict[str, Any]: Response chunks
            
        Raises:
            CoordinationError: If workflow execution fails
        """
        if not self._initialized:
            await self._initialize()
        
        try:
            # Map workflow name to execution function
            if workflow_name == "general_query":
                # Delegate to execute_general_query
                query = input_data.get("query", "")
                context = input_data.get("context", {})
                model = input_data.get("model", None)
                
                if not query:
                    raise WorkflowExecutionError(workflow_name, "Query is required", input_data)
                
                async for chunk in self.execute_general_query(query, context, model, stream):
                    yield chunk
                    
            elif workflow_name == "tool_use":
                # Example workflow for tool-using agent
                # This is a placeholder implementation
                query = input_data.get("query", "")
                tools = input_data.get("tools", [])
                model_name = input_data.get("model", self._default_model)
                
                if not query:
                    raise WorkflowExecutionError(workflow_name, "Query is required", input_data)
                
                if model_name not in self._model_clients:
                    available_models = list(self._model_clients.keys())
                    raise ModelNotAvailableError(model_name, available_models)
                
                # For now, just return a message that tool use is not yet implemented
                yield {
                    "type": "delta",
                    "delta": {
                        "text": "Tool-using agent workflow is not yet implemented. This will be part of future development."
                    }
                }
                
            else:
                raise WorkflowExecutionError(workflow_name, "Unknown workflow", input_data)
                
        except (ModelNotAvailableError, WorkflowExecutionError) as e:
            # Re-raise specific errors
            raise e
        except Exception as e:
            raise CoordinationError(f"Failed to execute workflow '{workflow_name}': {str(e)}")
    
    async def create_graph_workflow(
        self,
        name: str,
        model_client: ModelClientBase,
        nodes: Dict[str, Any],
        entry_point: str
    ):
        """
        [Method intent]
        Create a reusable graph-based workflow.
        
        [Design principles]
        - Graph-based workflow definition
        - Reusable component creation
        - Clean interface for complex workflows
        
        [Implementation details]
        - Creates LangGraph workflow using builder
        - Configures nodes and edges
        - Sets up workflow state management
        
        Args:
            name: Workflow name
            model_client: Model client to use
            nodes: Node definitions
            entry_point: Entry point node name
            
        Returns:
            Any: Compiled workflow graph
            
        Raises:
            CoordinationError: If workflow creation fails
        """
        if not self._initialized:
            await self._initialize()
            
        try:
            # Create graph using builder
            graph = self._graph_builder.create_graph(name=name)
            
            # Add nodes and edges based on configuration
            # This is a placeholder - actual implementation would be more complex
            
            # Return compiled graph
            return self._graph_builder.compile(graph)
        except Exception as e:
            raise CoordinationError(f"Failed to create graph workflow: {str(e)}")
    
    async def get_available_models(self) -> List[str]:
        """
        [Method intent]
        Get list of available model clients.
        
        [Design principles]
        - Simple utility method
        - Dynamic model availability
        
        [Implementation details]
        - Returns list of initialized model names
        
        Returns:
            List[str]: List of available model names
        """
        if not self._initialized:
            await self._initialize()
            
        return list(self._model_clients.keys())
