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
# Defines the base classes and interfaces for LLM tools within the coordinator.
# Provides a foundation for implementing both LangChain-compatible and custom tools
# that can be registered with the tool registry and used by LLMs.
###############################################################################
# [Source file design principles]
# - Clean separation between tool interface and implementation
# - Compatibility with LangChain tool specifications
# - Support for both synchronous and asynchronous execution
# - Strong type checking and validation
###############################################################################
# [Source file constraints]
# - Must remain compatible with LangChain tool specifications
# - Must provide both sync and async interfaces
# - Must validate inputs against schemas
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/llm/common/tool_registry.py
# system:typing
# system:pydantic
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T10:47:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created placeholder for base tool classes
###############################################################################

"""
Base classes for LLM tools used by the coordinator.
"""

from typing import Any, Dict, Optional, Type, List, Union
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool as LangChainBaseTool

from src.dbp.llm.common.exceptions import ToolError


# This file will be implemented in Phase 12
# Placeholder for tool base classes
