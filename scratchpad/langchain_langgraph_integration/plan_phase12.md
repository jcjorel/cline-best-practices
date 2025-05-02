# Phase 12: LLM Coordinator Implementation

This phase implements the LLM Coordinator component that serves as the bridge between the MCP server and our LLM infrastructure. It focuses on creating the agent manager and implementing the general query tool that can be used by MCP clients.

## Objectives

1. Create the LLM Coordinator Agent Manager
2. Implement the DBP General Query MCP Tool
3. Build the MCP integration layer
4. Develop the coordinator workflow

## AgentManager Implementation

Create the agent manager in `src/dbp/llm_coordinator/agent_manager.py`:

```python
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
from src.dbp.llm_coordinator.exceptions import CoordinationError

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
        try:
            # Get registries
            self._config_registry = self.get_dependency(ConfigRegistry)
            self._tool_registry = self.get_dependency(ToolRegistry)
            
            # Get model clients
            from src.dbp.llm.bedrock.models.claude3 import ClaudeClient
            from src.dbp.llm.bedrock.models.nova import NovaClient
            
            # Create model clients - exact instantiation will depend on component setup
            self._model_clients = {
                "claude": await self._create_claude_client(),
                "nova": await self._create_nova_client()
            }
            
            # Set default model
            self._default_model = "claude"
            
            # Create graph builder
            from src.dbp.llm.langgraph.builder import GraphBuilder
            self._graph_builder = GraphBuilder()
            
            self.logger.info("Agent manager initialized")
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
            CoordinationError: If client creation fails
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
            raise CoordinationError(f"Failed to create Claude client: {str(e)}")
    
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
            CoordinationError: If client creation fails
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
            raise CoordinationError(f"Failed to create Nova client: {str(e)}")
    
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
        try:
            # Get model client
            model_name = model or self._default_model
            if model_name not in self._model_clients:
                raise CoordinationError(f"Model '{model_name}' not available")
                
            model_client = self._model_clients[model_name]
            
            # Prepare context
            full_context = context or {}
            
            # Stream response directly for simple queries
            if stream:
                async for chunk in model_client.stream_chat([
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ]):
                    yield chunk
            else:
                # For non-streaming, collect response
                response_chunks = []
                async for chunk in model_client.stream_chat([
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ]):
                    response_chunks.append(chunk)
                    
                # Return complete response
                yield {
                    "type": "complete_response",
                    "content": "".join([
                        chunk.get("delta", {}).get("text", "") 
                        for chunk in response_chunks 
                        if "delta" in chunk
                    ])
                }
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
        # This is a placeholder for different agent workflows
        # Actual implementation will depend on specific workflows
        if workflow_name == "general_query":
            # Delegate to execute_general_query
            query = input_data.get("query", "")
            context = input_data.get("context", {})
            model = input_data.get("model", None)
            
            async for chunk in self.execute_general_query(query, context, model, stream):
                yield chunk
        else:
            raise CoordinationError(f"Unknown workflow: {workflow_name}")
```

## GeneralQueryTool Implementation

Create the general query MCP tool in `src/dbp/llm_coordinator/general_query_tool.py`:

```python
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterator, Union

from src.dbp.mcp_server.mcp_tool import McpTool
from src.dbp.llm_coordinator.agent_manager import AgentManager
from src.dbp.llm_coordinator.exceptions import CoordinationError

class GeneralQueryTool(McpTool):
    """
    [Class intent]
    Provides a general query tool for the MCP server, enabling clients
    to interact with LLMs through a consistent interface. This tool
    serves as the primary endpoint for LLM-based functionality.
    
    [Design principles]
    - MCP integration for external accessibility
    - Streaming-first approach
    - Delegation to AgentManager for processing
    - Context-aware query handling
    
    [Implementation details]
    - Registers with MCP server for discovery
    - Delegates to AgentManager for LLM coordination
    - Handles streaming responses
    - Provides proper error handling and reporting
    """
    
    def __init__(
        self,
        agent_manager: AgentManager,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the general query tool with an agent manager.
        
        [Design principles]
        - Component composition
        - Clean dependency injection
        - Proper logging setup
        
        [Implementation details]
        - Sets up agent manager reference
        - Initializes logging
        - Configures tool schema
        
        Args:
            agent_manager: Agent manager instance
            logger: Optional custom logger instance
        """
        # Initialize base class
        super().__init__(
            name="dbp_general_query",
            description="Execute general queries using LLMs with optional context",
            schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query text to process"
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional context information"
                    },
                    "model": {
                        "type": "string",
                        "description": "Optional model to use (default: claude)"
                    },
                    "stream": {
                        "type": "boolean",
                        "description": "Whether to stream the response (default: true)"
                    }
                },
                "required": ["query"]
            },
            logger=logger or logging.getLogger("GeneralQueryTool")
        )
        
        self.agent_manager = agent_manager
    
    async def execute(self, parameters: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Execute the general query tool with the provided parameters.
        
        [Design principles]
        - Streaming execution
        - Clean parameter handling
        - Error handling
        
        [Implementation details]
        - Extracts parameters
        - Delegates to AgentManager
        - Streams response chunks
        - Handles errors with appropriate responses
        
        Args:
            parameters: Tool parameters including query and options
            
        Yields:
            Dict[str, Any]: Response chunks
            
        Raises:
            Exception: If execution fails
        """
        try:
            # Extract parameters
            query = parameters.get("query", "")
            context = parameters.get("context", {})
            model = parameters.get("model")
            stream = parameters.get("stream", True)
            
            if not query:
                yield {"error": "Query is required"}
                return
            
            # Execute query via agent manager
            async for chunk in self.agent_manager.execute_general_query(
                query=query,
                context=context,
                model=model,
                stream=stream
            ):
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Error executing general query: {str(e)}")
            yield {"error": str(e)}
```

## Coordinator Component Implementation

Create the coordinator component in `src/dbp/llm_coordinator/component.py`:

```python
import logging
from typing import Dict, Any, List, Optional

from src.dbp.core.component import Component
from src.dbp.llm.common.config_registry import ConfigRegistry
from src.dbp.llm.common.tool_registry import ToolRegistry
from src.dbp.llm_coordinator.agent_manager import AgentManager
from src.dbp.llm_coordinator.general_query_tool import GeneralQueryTool
from src.dbp.mcp_server.component import McpServerComponent

class LlmCoordinatorComponent(Component):
    """
    [Class intent]
    Coordinates LLM functionality within the application, providing
    centralized management of LLM-based features and integration with
    the MCP server for external access.
    
    [Design principles]
    - Component-based architecture
    - Clean dependency management
    - MCP integration for external accessibility
    - Centralized LLM coordination
    
    [Implementation details]
    - Manages AgentManager lifecycle
    - Registers MCP tools for external access
    - Handles component dependencies
    - Provides clean startup and shutdown
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the LLM coordinator component with configuration.
        
        [Design principles]
        - Clean component initialization
        - Configuration-driven setup
        - Proper logging
        
        [Implementation details]
        - Initializes as a system component
        - Sets up configuration with defaults
        - Prepares for dependency resolution
        
        Args:
            config: Optional configuration dictionary
            logger: Optional custom logger instance
        """
        # Initialize as component
        super().__init__("llm_coordinator", config, logger)
        
        # Will be initialized during start()
        self._agent_manager = None
        self._general_query_tool = None
    
    async def _initialize(self) -> None:
        """
        [Method intent]
        Initialize the coordinator during component startup.
        
        [Design principles]
        - Component lifecycle integration
        - Clean dependency resolution
        - Proper initialization order
        
        [Implementation details]
        - Creates agent manager
        - Registers MCP tools
        - Sets up dependencies
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Get dependencies
            config_registry = self.get_dependency(ConfigRegistry)
            tool_registry = self.get_dependency(ToolRegistry)
            mcp_server = self.get_dependency(McpServerComponent)
            
            # Create agent manager
            self._agent_manager = AgentManager(
                config=self.config.get("agent_manager", {}),
                logger=self.logger.getChild("agent_manager")
            )
            
            # Register agent manager as component
            self.register_subcomponent(self._agent_manager)
            
            # Initialize agent manager
            await self._agent_manager.start()
            
            # Create general query tool
            self._general_query_tool = GeneralQueryTool(
                agent_manager=self._agent_manager,
                logger=self.logger.getChild("general_query_tool")
            )
            
            # Register tool with MCP server
            mcp_server.register_tool(self._general_query_tool)
            
            self.logger.info("LLM coordinator initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM coordinator: {str(e)}")
            raise
    
    async def _shutdown(self) -> None:
        """
        [Method intent]
        Clean up resources during component shutdown.
        
        [Design principles]
        - Clean resource management
        - Proper component lifecycle
        
        [Implementation details]
        - Stops agent manager
        - Releases resources
        
        Raises:
            Exception: If shutdown fails
        """
        try:
            # Shutdown agent manager
            if self._agent_manager:
                await self._agent_manager.stop()
            
            self.logger.info("LLM coordinator shut down")
        except Exception as e:
            self.logger.error(f"Error during LLM coordinator shutdown: {str(e)}")
            raise
```

## Implementation Steps

1. **Create Agent Manager**
   - Implement `AgentManager` in `src/dbp/llm_coordinator/agent_manager.py`
   - Add model client management
   - Create workflow execution methods
   - Implement general query execution

2. **Create General Query Tool**
   - Implement `GeneralQueryTool` in `src/dbp/llm_coordinator/general_query_tool.py`
   - Add MCP tool integration
   - Implement streaming response handling
   - Create parameter validation

3. **Implement Coordinator Component**
   - Create `LlmCoordinatorComponent` in `src/dbp/llm_coordinator/component.py`
   - Add lifecycle management
   - Implement tool registration
   - Set up dependency management

4. **MCP Integration**
   - Register tools with MCP server
   - Add streaming response support
   - Implement error handling
   - Create context extraction utilities

## Notes

- The coordinator acts as a bridge between the MCP server and LLM infrastructure
- All interactions maintain the streaming-first approach
- The agent manager provides a central point for LLM coordination
- MCP tools enable external access to LLM functionality

## Next Steps

After completing this phase:

1. Update the requirements.txt file with all required dependencies
2. Perform a consistency check across all components
3. Create unit tests for key functionality
4. Begin implementation of the plan
