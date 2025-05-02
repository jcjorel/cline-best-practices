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
# Provides utility functions for LangChain integration, including tool conversion,
# tracing setup, and common helper functions. These utilities support seamless
# integration between our components and the LangChain ecosystem.
###############################################################################
# [Source file design principles]
# - Clean utility function design
# - Minimal dependencies
# - Error handling and graceful fallbacks
# - Consistent interface
# - Support for both synchronous and asynchronous modes
###############################################################################
# [Source file constraints]
# - Must not introduce unnecessary dependencies
# - Must handle missing optional dependencies gracefully
# - Must provide useful error messages
# - Must maintain compatibility with different LangChain versions
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/tool_registry.py
# codebase:src/dbp/llm/common/exceptions.py
# system:logging
# system:typing
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:30:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created utility functions for tool conversion
# * Added tracing callback management
# * Added helper functions for LangChain integration
###############################################################################

"""
Utility functions for LangChain integration.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable

from langchain_core.callbacks import CallbackManager, AsyncCallbackManager
from langchain_core.tools import BaseTool

from ..common.tool_registry import ToolRegistry
from ..common.exceptions import ToolError

def convert_registry_tools_to_langchain(
    tool_registry: ToolRegistry,
    tags: Optional[List[str]] = None
) -> List[BaseTool]:
    """
    [Function intent]
    Convert tools from our ToolRegistry to LangChain tools.
    
    [Design principles]
    - Seamless tool conversion
    - Support for filtering by tags
    - Clean interface
    
    [Implementation details]
    - Retrieves tools from registry
    - Converts to LangChain format
    - Handles tool metadata
    
    Args:
        tool_registry: Our tool registry instance
        tags: Optional list of tags to filter tools
        
    Returns:
        List[BaseTool]: List of LangChain tools
    """
    if tags:
        # Get tools with specified tags
        langchain_tools = tool_registry.get_langchain_tools(tags)
    else:
        # Get all tools
        langchain_tools = tool_registry.get_langchain_tools()
        
    return langchain_tools

def create_tracing_callback_manager(
    session_id: str,
    async_mode: bool = False,
    handlers: Optional[List[Any]] = None
) -> Union[CallbackManager, AsyncCallbackManager]:
    """
    [Function intent]
    Create a LangChain callback manager with tracing enabled.
    
    [Design principles]
    - Support for LangChain tracing
    - Simple interface
    - Synchronous and asynchronous support
    
    [Implementation details]
    - Creates appropriate callback manager type
    - Configures with session ID for tracing
    - Sets up default handlers
    
    Args:
        session_id: Unique session ID for tracing
        async_mode: Whether to create an async callback manager
        handlers: Optional list of additional callback handlers
        
    Returns:
        Union[CallbackManager, AsyncCallbackManager]: Configured callback manager
    """
    try:
        # Import LangChain tracing
        from langchain_core.tracers import LangChainTracer
        from langchain_core.callbacks import StdOutCallbackHandler
        
        # Create tracer
        tracer = LangChainTracer(session_id=session_id)
        
        # Create callback handler list
        all_handlers = [tracer, StdOutCallbackHandler()]
        if handlers:
            all_handlers.extend(handlers)
        
        # Create manager based on mode
        if async_mode:
            return AsyncCallbackManager(handlers=all_handlers)
        else:
            return CallbackManager(handlers=all_handlers)
            
    except ImportError:
        # Tracing not available, return minimal manager
        logger = logging.getLogger("LangChainUtils")
        logger.warning("LangChain tracing components not available, creating basic callback manager")
        
        if handlers:
            if async_mode:
                return AsyncCallbackManager(handlers=handlers)
            else:
                return CallbackManager(handlers=handlers)
        else:
            if async_mode:
                return AsyncCallbackManager()
            else:
                return CallbackManager()

def format_chat_history(
    history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    [Function intent]
    Format chat history for LangChain consumption, ensuring consistent format.
    
    [Design principles]
    - Consistent message format
    - Graceful handling of various input formats
    - Clean interface
    
    [Implementation details]
    - Normalizes message roles
    - Handles different input formats
    - Ensures consistent output
    
    Args:
        history: List of chat messages
        
    Returns:
        List[Dict[str, str]]: Formatted chat history
    """
    formatted_history = []
    
    for message in history:
        # Ensure we have proper role and content keys
        if not isinstance(message, dict):
            continue
            
        # Get role and content, with fallbacks
        role = message.get("role", "user")
        content = message.get("content", "")
        
        # Normalize role names
        if role.lower() in ["user", "human"]:
            role = "user"
        elif role.lower() in ["assistant", "ai", "bot"]:
            role = "assistant"
        elif role.lower() in ["system"]:
            role = "system"
        
        # Add formatted message
        formatted_history.append({
            "role": role,
            "content": content
        })
    
    return formatted_history

def create_streaming_callback(
    on_new_token: Callable[[str], None], 
    async_mode: bool = False
) -> Any:
    """
    [Function intent]
    Create a callback handler for streaming tokens from LangChain.
    
    [Design principles]
    - Simple token streaming
    - Support for synchronous and asynchronous modes
    - Minimal implementation
    
    [Implementation details]
    - Creates appropriate callback handler
    - Configures with token handler
    - Returns handler instance
    
    Args:
        on_new_token: Function to call for each new token
        async_mode: Whether to create an async callback handler
        
    Returns:
        Any: Configured callback handler
    """
    try:
        # Import necessary components
        if async_mode:
            from langchain_core.callbacks.base import AsyncCallbackHandler
            
            class AsyncTokenStreamingHandler(AsyncCallbackHandler):
                """Async callback handler for token streaming."""
                
                def __init__(self, on_new_token):
                    """Initialize with token handler."""
                    self.on_new_token = on_new_token
                
                async def on_llm_new_token(self, token: str, **kwargs):
                    """Process new token."""
                    self.on_new_token(token)
            
            return AsyncTokenStreamingHandler(on_new_token)
        else:
            from langchain_core.callbacks.base import BaseCallbackHandler
            
            class TokenStreamingHandler(BaseCallbackHandler):
                """Callback handler for token streaming."""
                
                def __init__(self, on_new_token):
                    """Initialize with token handler."""
                    self.on_new_token = on_new_token
                
                def on_llm_new_token(self, token: str, **kwargs):
                    """Process new token."""
                    self.on_new_token(token)
            
            return TokenStreamingHandler(on_new_token)
    
    except ImportError:
        # Fallback with warning
        logger = logging.getLogger("LangChainUtils")
        logger.warning("Failed to create streaming callback handler, LangChain components not available")
        return None
