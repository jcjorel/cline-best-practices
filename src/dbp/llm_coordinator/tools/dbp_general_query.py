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
# Implements a general query MCP tool for interacting with LLMs. This tool enables
# external MCP clients to execute queries against the LLM infrastructure with
# streaming support and context-aware processing.
###############################################################################
# [Source file design principles]
# - MCP integration for external accessibility
# - Streaming-first approach
# - Delegation to AgentManager for processing
# - Clean error handling and reporting
# - Context-aware query processing
###############################################################################
# [Source file constraints]
# - Must implement MCP tool interface correctly
# - Must support streaming responses
# - Must provide proper parameter validation
# - Must handle error conditions gracefully
###############################################################################
# [Dependencies]
# codebase:src/dbp/mcp_server/adapter.py
# codebase:src/dbp/llm_coordinator/agent_manager.py
# codebase:src/dbp/llm_coordinator/exceptions.py
# system:logging
# system:asyncio
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:40:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created GeneralQueryTool for MCP integration
# * Added streaming response handling
# * Implemented parameter validation
###############################################################################

"""
General query MCP tool for LLM interaction.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, AsyncIterator

from src.dbp.mcp_server.adapter import McpTool
from src.dbp.llm_coordinator.agent_manager import AgentManager
from src.dbp.llm_coordinator.exceptions import CoordinationError, ModelNotAvailableError, WorkflowExecutionError


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
                        "description": "Optional context information to include with the query"
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
            # Log execution request
            self.logger.debug(f"Executing general query tool with parameters: {parameters}")
            
            # Extract parameters
            query = parameters.get("query", "")
            context = parameters.get("context", {})
            model = parameters.get("model")
            stream = parameters.get("stream", True)
            
            # Validate parameters
            if not query:
                self.logger.error("Query parameter is required")
                yield {"error": "Query parameter is required"}
                return
            
            # Execute query via agent manager
            try:
                async for chunk in self.agent_manager.execute_general_query(
                    query=query,
                    context=context,
                    model=model,
                    stream=stream
                ):
                    # Forward response chunks
                    yield chunk
            except ModelNotAvailableError as e:
                # Handle model not available error
                self.logger.error(f"Model not available: {e}")
                yield {
                    "error": str(e),
                    "available_models": e.details.get("available_models", [])
                }
            except CoordinationError as e:
                # Handle coordination error
                self.logger.error(f"Coordination error: {e}")
                yield {"error": str(e)}
                
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(f"Error executing general query: {str(e)}", exc_info=True)
            yield {"error": f"Internal error: {str(e)}"}
    
    @property
    def health_status(self) -> Dict[str, Any]:
        """
        [Method intent]
        Get the health status of the tool.
        
        [Design principles]
        - Simple health reporting
        - Component status integration
        
        [Implementation details]
        - Checks agent manager status
        - Reports availability of models
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Get available models (non-blocking check)
            available_models = list(self.agent_manager._model_clients.keys()) \
                if hasattr(self.agent_manager, '_model_clients') else []
            
            return {
                "status": "healthy" if available_models else "degraded",
                "available_models": available_models
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
