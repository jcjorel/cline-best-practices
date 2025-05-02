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
# Provides chat model adapters for integrating custom LLM clients with LangChain's
# chat interfaces. This enables seamless use of our LLM implementations within
# LangChain's chat-based chains and agents, supporting conversation history
# and specialized message types.
###############################################################################
# [Source file design principles]
# - Clean adaptation between our API and LangChain's chat interface
# - Streaming-first approach with callback integration
# - Proper handling of message formats and conversation history
# - Consistent error handling and reporting
# - Complete chat-model semantics
###############################################################################
# [Source file constraints]
# - Must implement LangChain's BaseChatModel interface correctly
# - Must handle all message types (system, human, AI, chat)
# - Must preserve conversation history semantics
# - Must integrate properly with streaming responses and callbacks
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/common/exceptions.py
# system:asyncio
# system:typing
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:27:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Implemented LangChainChatAdapter for chat-based integration
# * Added message format conversion utilities
# * Added streaming with callback integration
###############################################################################

"""
Chat adapters for integrating custom LLM clients with LangChain's chat interfaces.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable, Type, Mapping

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import (
    BaseMessage, AIMessage, HumanMessage, SystemMessage, ChatMessage
)
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from ..common.base import ModelClientBase
from ..common.exceptions import LLMError

class LangChainChatAdapter(BaseChatModel):
    """
    [Class intent]
    Adapts our custom LLM clients to LangChain's Chat Model interface.
    This adapter enables our LLM implementations to work with LangChain's
    chat-oriented components, supporting conversation history and specialized
    chat-based chains and agents.
    
    [Design principles]
    - Specialized for chat interactions
    - Support for conversation history
    - Streaming-first approach for efficiency
    - Clean message format conversion
    
    [Implementation details]
    - Implements BaseChatModel for LangChain compatibility
    - Converts between our message format and LangChain's
    - Handles streaming responses with callback integration
    - Preserves model configuration options
    """
    
    model_client: ModelClientBase
    client_kwargs: Dict[str, Any]
    streaming: bool = True
    
    def __init__(
        self,
        model_client: ModelClientBase,
        streaming: bool = True,
        **kwargs
    ):
        """
        [Method intent]
        Initialize the LangChain Chat adapter with a model client.
        
        [Design principles]
        - Simple initialization with our model client
        - Support for LangChain-specific configuration
        - Clean separation of concerns
        
        [Implementation details]
        - Stores model client for delegation
        - Passes LangChain-specific kwargs to parent class
        - Sets up logging for adapter operations
        
        Args:
            model_client: Instance of our model client
            streaming: Whether to use streaming by default
            **kwargs: Additional arguments for LangChain
        """
        # Initialize our adapter fields
        self.model_client = model_client
        self.client_kwargs = {}
        self.streaming = streaming
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set standard LangChain fields
        self.model_client_class = model_client.__class__.__name__
        self.model_id = model_client.model_id
        
        # Initialize parent
        super().__init__(**kwargs)
    
    @property
    def _llm_type(self) -> str:
        """Return type name for LangChain registry."""
        return f"DBP-Chat-{self.model_client_class}"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        [Method intent]
        Generate completions for chat messages using synchronous interface.
        
        [Design principles]
        - Adaptation to LangChain's synchronous interface
        - Proper callback integration
        - Support for stop sequences
        
        [Implementation details]
        - Uses asyncio to run async methods in sync context
        - Delegates to _agenerate for actual implementation
        - Handles LangChain callbacks
        
        Args:
            messages: List of chat messages
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            ChatResult: LangChain result container
        """
        # Use asyncio to run async method in sync context
        return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        [Method intent]
        Generate completions for chat messages using asynchronous interface.
        
        [Design principles]
        - Streaming as primary interaction pattern
        - Proper error handling and reporting
        - Message format conversion
        
        [Implementation details]
        - Converts LangChain messages to our format
        - Uses streaming and collects results
        - Handles LangChain callbacks for each chunk
        - Converts our format to LangChain's ChatResult
        
        Args:
            messages: List of chat messages
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            ChatResult: LangChain result container
        """
        # Start LangChain callbacks for the overall operation
        if run_manager:
            await run_manager.on_llm_start(
                {"name": self._llm_type},
                [m.content for m in messages],
                invocation_params=kwargs,
            )
        
        try:
            # Convert LangChain messages to our format
            formatted_messages = self._convert_messages_to_client_format(messages)
            
            # Prepare parameters
            model_kwargs = self.client_kwargs.copy()
            model_kwargs.update(kwargs)
            if stop:
                model_kwargs["stop_sequences"] = stop
            
            # Stream response
            response = await self._process_chat_stream(
                formatted_messages, run_manager, **model_kwargs
            )
            
            # Create chat result
            chat_generation = ChatGeneration(message=response)
            result = ChatResult(generations=[chat_generation], llm_output={"model_id": self.model_id})
            
            # Handle completion callback
            if run_manager:
                await run_manager.on_llm_end({"generations": [[chat_generation]]})
                
            return result
            
        except Exception as e:
            # Log error
            self.logger.error(f"Error in chat generation: {str(e)}")
            
            # Handle callback for error
            if run_manager:
                await run_manager.on_llm_error(str(e))
            
            # Create error message
            error_message = AIMessage(content=f"Error: {str(e)}")
            chat_generation = ChatGeneration(message=error_message)
            
            # Return minimal chat result
            return ChatResult(generations=[chat_generation], llm_output={"error": str(e)})
    
    async def _process_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        run_manager: Optional[AsyncCallbackManagerForLLMRun],
        **kwargs
    ) -> AIMessage:
        """
        [Method intent]
        Process chat messages with streaming and callbacks.
        
        [Design principles]
        - Streaming focused for efficiency
        - Complete callback integration
        - Proper error handling
        
        [Implementation details]
        - Streams response chunks from model client
        - Sends each chunk to LangChain callbacks
        - Builds complete response for final ChatResult
        - Handles errors with appropriate responses
        
        Args:
            messages: Formatted messages for our client
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            AIMessage: LangChain AI message response
        """
        # Initialize before streaming
        full_text = ""
        stop_reason = None
        
        try:
            # Initialize model client if not already done
            if not self.model_client.is_initialized():
                await self.model_client.initialize()
            
            # Stream chat from our client
            async for chunk in self.model_client.stream_chat(messages, **kwargs):
                # Extract text chunk if available
                if "delta" in chunk and "text" in chunk["delta"]:
                    chunk_text = chunk["delta"]["text"]
                    full_text += chunk_text
                    
                    # Send chunk to callback if available
                    if run_manager:
                        await run_manager.on_llm_new_token(chunk_text)
                        
                # Check for stop reason
                if chunk.get("type") == "message_stop" and "stop_reason" in chunk:
                    stop_reason = chunk["stop_reason"]
            
            # Create AIMessage with appropriate metadata
            additional_kwargs = {}
            if stop_reason:
                additional_kwargs["stop_reason"] = stop_reason
                
            return AIMessage(content=full_text, additional_kwargs=additional_kwargs)
            
        except Exception as e:
            # Log error
            self.logger.error(f"Error in chat generation: {str(e)}")
            
            # Return error message
            return AIMessage(content=f"Error: {str(e)}", additional_kwargs={"error": str(e)})
    
    def _convert_messages_to_client_format(
        self,
        messages: List[BaseMessage]
    ) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Convert LangChain messages to our client's format.
        
        [Design principles]
        - Clean format conversion
        - Support for all message types
        - Error handling for unsupported types
        
        [Implementation details]
        - Maps LangChain message types to roles
        - Extracts content from messages
        - Handles special message types
        
        Args:
            messages: List of LangChain messages
            
        Returns:
            List[Dict[str, Any]]: Messages in our client format
        """
        result = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            elif isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, ChatMessage):
                # Map custom roles
                role = message.role
            else:
                # Unknown message type
                self.logger.warning(f"Unknown message type: {type(message)}")
                role = "user"
            
            # Create message in our format
            result.append({
                "role": role,
                "content": message.content
            })
        
        return result
