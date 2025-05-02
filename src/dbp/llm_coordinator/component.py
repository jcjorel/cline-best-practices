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
# Implements the LLM Coordinator Component that orchestrates LLM functionality
# within the application. This component provides centralized management of LLM-based
# features and integrates with the MCP server for external access to LLM capabilities.
###############################################################################
# [Source file design principles]
# - Component-based architecture
# - Clean dependency management
# - MCP integration for external accessibility
# - Centralized LLM coordination
# - Proper lifecycle management
###############################################################################
# [Source file constraints]
# - Must integrate with core component system
# - Must handle component dependencies properly
# - Must provide clean startup and shutdown
# - Must register tools with MCP server
###############################################################################
# [Dependencies]
# codebase:src/dbp/core/component.py
# codebase:src/dbp/llm/common/config_registry.py
# codebase:src/dbp/llm/common/tool_registry.py
# codebase:src/dbp/llm_coordinator/agent_manager.py
# codebase:src/dbp/llm_coordinator/tools/dbp_general_query.py
# codebase:src/dbp/mcp_server/component.py
# system:logging
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:42:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created LlmCoordinatorComponent for LLM functionality orchestration
# * Added integration with MCP server for external tool access
# * Implemented component lifecycle management
###############################################################################

"""
Coordinator component for LLM functionality.
"""

import logging
from typing import Dict, Any, List, Optional

from src.dbp.core.component import Component
from src.dbp.llm.common.config_registry import ConfigRegistry
from src.dbp.llm.common.tool_registry import ToolRegistry
from src.dbp.llm_coordinator.agent_manager import AgentManager
from src.dbp.llm_coordinator.tools.dbp_general_query import GeneralQueryTool
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
