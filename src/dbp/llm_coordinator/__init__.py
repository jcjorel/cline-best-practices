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
# Initializes the LLM Coordinator module and exports its key components.
# This module serves as the central coordination point for LLM functionality,
# providing a consistent interface for agent creation and execution.
###############################################################################
# [Source file design principles]
# - Clean module exports
# - Clear component visibility
# - Simplified import paths
###############################################################################
# [Source file constraints]
# - Must not contain implementation logic, only exports
# - Must maintain backward compatibility
# - Must provide a clean API surface
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm_coordinator/component.py
# codebase:src/dbp/llm_coordinator/agent_manager.py
# codebase:src/dbp/llm_coordinator/tools/__init__.py
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:42:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created initial exports for LLM Coordinator module
# * Added component and tools exports
###############################################################################

"""
LLM Coordinator module for centralized LLM management.

This module provides components for orchestrating interactions between LLMs
and the rest of the application, including MCP tool integration.
"""

from .component import LlmCoordinatorComponent
from .agent_manager import AgentManager
from .tools import GeneralQueryTool

__all__ = [
    "LlmCoordinatorComponent",
    "AgentManager",
    "GeneralQueryTool",
]
