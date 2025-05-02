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
# Initialize the LangChain integration module, which provides adapters and utilities
# for integrating custom LLM clients with the LangChain ecosystem. This module
# enables seamless use of our LLM implementations with LangChain's components.
###############################################################################
# [Source file design principles]
# - Clean organization of LangChain integration components
# - Convenient imports for essential functionality
# - Minimal dependencies for core functionality
# - Support for both LangChain and LangGraph ecosystems
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with LangChain's interfaces
# - Must not create circular dependencies
# - Must export only necessary components
# - Must be self-contained for core functionality
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/common/exceptions.py
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:25:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created LangChain integration module
# * Added exports for adapters and factories
###############################################################################

"""
LangChain integration for DBP LLM module.

This module provides adapters and utilities for using DBP LLM clients
with the LangChain ecosystem, enabling seamless integration with
chains, agents, and other LangChain components.
"""

# Core adapter imports
from .adapters import LangChainLLMAdapter
from .chat_adapters import LangChainChatAdapter
from .capability_adapters import CapabilityAwareLLMAdapter

# Factory utilities
from .factories import LangChainFactory

# Integration utilities
from .utils import convert_registry_tools_to_langchain, create_tracing_callback_manager

__all__ = [
    # Adapters
    "LangChainLLMAdapter",
    "LangChainChatAdapter",
    "CapabilityAwareLLMAdapter",
    
    # Factories
    "LangChainFactory",
    
    # Utilities
    "convert_registry_tools_to_langchain",
    "create_tracing_callback_manager",
]
