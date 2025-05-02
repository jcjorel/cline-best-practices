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
# Implements a specialized client for Anthropic's Claude models on Amazon Bedrock.
# This client adds Claude-specific features like reasoning support and parameter
# handling while maintaining the streaming-first and async approach required by
# the LangChain/LangGraph integration.
###############################################################################
# [Source file design principles]
# - Claude-specific parameter optimization
# - Reasoning support for enhanced outputs
# - Specialized message formatting for Claude
# - Clean extension of BedrockBase
# - Asynchronous streaming interface
# - Support for all Claude model variants
###############################################################################
# [Source file constraints]
# - Must be compatible with all Claude models (3 Haiku, Sonnet, Opus, etc.)
# - Must use only the Converse API for all interactions
# - Must maintain fully asynchronous interface
# - Must optimize parameters for Claude model capabilities
# - Must handle Claude-specific response formats correctly
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/base.py
# codebase:src/dbp/llm/bedrock/client_common.py
# codebase:src/dbp/llm/common/streaming.py
# codebase:src/dbp/llm/common/exceptions.py
# codebase:doc/design/LLM_COORDINATION.md
# system:json
# system:asyncio
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:19:00Z : Implemented for LangChain/LangGraph integration by CodeAssistant
# * Created Claude-specific client with reasoning support
# * Implemented async streaming interface using Converse API
# * Added support for all Claude model variants
# * Optimized parameters and format handling for Claude
###############################################################################

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Union, cast

from ..base import BedrockBase
from ..client_common import (
    ConverseStreamProcessor, BedrockMessageConverter, 
    BedrockErrorMapper, InferenceParameterFormatter
)
from ...common.streaming import (
    StreamingResponse, TextStreamingResponse, IStreamable
)
from ...common.exceptions import LLMError, InvocationError


class ClaudeClient(BedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Claude models.
    This client adds Claude-specific features like reasoning support and
    parameter handling while maintaining the streaming-focused approach.
    
    [Design principles]
    - Claude-specific parameter optimization
    - Reasoning support for enhanced outputs
    - Specialized message formatting for Claude
    - Clean extension of BedrockBase
    
    [Implementation details]
    - Supports all Claude model variants (Claude 3 Haiku, Sonnet, Opus, etc.)
    - Implements Claude-specific parameter mapping
    - Adds specialized reasoning support
    - Optimizes default parameters for Claude
    """
    
    # Supported Claude models - helps with validation
    _CLAUDE_MODELS = [
        "anthropic.claude-3-haiku-20240307-v1",
        "anthropic.claude-3-sonnet-20240229-v1",
        "anthropic.claude-3-opus-20240229-v1",
        "anthropic.claude-3-5-sonnet-20240620-v1",
        "anthropic.claude-instant-v1",
        "anthropic.claude-v2",
        "anthropic.claude-v2:1"
    ]
    
    # Default Claude parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TOP_P = 0.9
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = BedrockBase.DEFAULT_RETRIES,
        timeout: int = BedrockBase.DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the Claude client with model validation and Claude-specific defaults.
        
        [Design principles]
        - Strong model validation
        - Claude-specific configuration
        - Clean delegation to base class
        
        [Implementation details]
        - Validates that model_id is a Claude model
        - Sets up Claude-specific logging
        - Initializes with Claude defaults
        
        Args:
            model_id: Claude model ID (e.g., "anthropic.claude-3-haiku-20240307-v1:0")
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            
        Raises:
            ValueError: If model_id is not a supported Claude model
        """
        # Validate model is a Claude model
        base_model_id = model_id.split(":")[0]
        is_claude_model = any(base_model_id.startswith(model) for model in self._CLAUDE_MODELS)
        
        if not is_claude_model:
            raise ValueError(f"Model {model_id} is not a supported Claude model")
        
        # Initialize base class
        super().__init__(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            credentials=credentials,
            max_retries=max_retries,
            timeout=timeout,
            logger=logger or logging.getLogger("ClaudeClient")
        )
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Claude models.
        
        [Design principles]
        - Claude-specific message formatting
        - Support for system messages
        - Handle content format variations
        
        [Implementation details]
        - Properly formats system messages for Claude
        - Handles content blocks for different content types
        - Ensures proper message role mapping
        
        Args:
            messages: List of message objects in standard format
            
        Returns:
            List[Dict[str, Any]]: Messages formatted for Claude API
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Format for Claude's expected structure
            formatted_msg = {"role": role}
            
            # Handle content formatting
            if isinstance(content, str):
                formatted_msg["content"] = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                # Assume already in correct format for multimodal
                formatted_msg["content"] = content
            else:
                raise ValueError(f"Unsupported content format: {type(content)}")
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages
    
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters specifically for Claude models.
        
        [Design principles]
        - Claude-specific parameter mapping
        - Support for reasoning feature
        - Parameter validation and defaults
        
        [Implementation details]
        - Maps standard parameters to Claude-specific names
        - Adds Claude-specific parameters
        - Supports reasoning configuration
        - Provides Claude-optimized defaults
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Claude API
        """
        # Start with basic parameters
        formatted_kwargs = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokens": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P)
        }
        
        # Add stop sequences if provided
        if "stop_sequences" in kwargs:
            formatted_kwargs["stopSequences"] = kwargs["stop_sequences"]
            
        # Add Claude-specific parameters
        if "anthropic_version" in kwargs:
            formatted_kwargs["anthropicVersion"] = kwargs["anthropic_version"]
        else:
            # Use a recent anthropic version by default
            formatted_kwargs["anthropicVersion"] = "bedrock-2023-05-31"
            
        # Add reasoning configuration if requested
        use_reasoning = kwargs.get("use_reasoning", False)
        if use_reasoning:
            # Using system parameter for reasoning
            if "system" not in kwargs:
                formatted_kwargs["system"] = "Use step-by-step reasoning to solve this problem."
                
        # Add system parameter if provided and not already set
        if "system" in kwargs and "system" not in formatted_kwargs:
            formatted_kwargs["system"] = kwargs["system"]
        
        return formatted_kwargs
    
    async def stream_chat_with_reasoning(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Stream a chat with reasoning enabled, which instructs Claude to show its work.
        
        [Design principles]
        - Simple interface for reasoning-enabled chats
        - Maintain streaming semantics
        - Parameter consistency with base methods
        
        [Implementation details]
        - Sets reasoning flag in parameters
        - Delegates to stream_chat with updated parameters
        - Preserves streaming behavior
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Additional parameters
            
        Yields:
            Dict[str, Any]: Response chunks from Claude
            
        Raises:
            LLMError: If chat generation fails
        """
        # Enable reasoning
        kwargs["use_reasoning"] = True
        
        # Delegate to stream_chat with reasoning enabled
        async for chunk in self.stream_chat(messages, **kwargs):
            yield chunk
    
    async def stream_generate_with_reasoning(
        self, 
        prompt: str, 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response with reasoning enabled, using a single prompt.
        
        [Design principles]
        - Simple interface for single-prompt reasoning
        - Maintain streaming semantics
        - Clean delegation to chat interface
        
        [Implementation details]
        - Converts prompt to messages format
        - Delegates to stream_chat_with_reasoning
        - Preserves streaming behavior
        
        Args:
            prompt: The text prompt to send to the model
            **kwargs: Additional parameters
            
        Yields:
            Dict[str, Any]: Response chunks from Claude
            
        Raises:
            LLMError: If generation fails
        """
        # Convert to messages format
        messages = [{"role": "user", "content": prompt}]
        
        # Delegate to chat with reasoning
        async for chunk in self.stream_chat_with_reasoning(messages, **kwargs):
            yield chunk
    
    async def get_completion_with_reasoning(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """
        [Method intent]
        Get a complete response with reasoning for a single prompt.
        
        [Design principles]
        - Simplify getting complete responses with reasoning
        - Still use streaming internally to avoid blocking
        - Return full text for ease of use
        
        [Implementation details]
        - Uses streaming internally to avoid blocking
        - Accumulates chunks into complete response
        - Returns final complete text
        
        Args:
            prompt: The text prompt to send to Claude
            **kwargs: Additional parameters
            
        Returns:
            str: Complete response text from Claude
            
        Raises:
            LLMError: If generation fails
        """
        result = ""
        
        # Use streaming internally, but collect into a single result
        try:
            async for chunk in self.stream_generate_with_reasoning(prompt, **kwargs):
                if "delta" in chunk and "text" in chunk["delta"]:
                    result += chunk["delta"]["text"]
                    
            return result
        except Exception as e:
            raise LLMError(f"Failed to get completion with reasoning: {str(e)}", e)
    
    async def get_structured_reasoning_response(
        self, 
        prompt: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Get a structured response with reasoning steps clearly separated.
        
        [Design principles]
        - Support use cases requiring structured reasoning output
        - Clean separation of reasoning steps and final answer
        - Prescriptive prompt engineering for consistent structure
        
        [Implementation details]
        - Uses a specially crafted system prompt for structured output
        - Adds specific instructions for format
        - Parses the response into a structured format
        
        Args:
            prompt: The text prompt to send to Claude
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Structured response with reasoning and answer
            
        Raises:
            LLMError: If generation or parsing fails
        """
        # Add system prompt for structured reasoning
        system_prompt = """
        When responding, use the following structure:
        1. First, provide your step-by-step reasoning process under a "Reasoning" heading
        2. Then, provide your final answer under a "Answer" heading
        
        Example format:
        
        Reasoning:
        [Your step-by-step thought process here]
        
        Answer:
        [Your concise final answer here]
        """
        
        kwargs["system"] = system_prompt
        
        # Get the complete response
        response_text = await self.get_completion_with_reasoning(prompt, **kwargs)
        
        # Parse the response into a structured format
        try:
            # Split on headings
            parts = response_text.split("Reasoning:")
            if len(parts) < 2:
                # Fallback if format wasn't followed
                return {
                    "reasoning": "",
                    "answer": response_text.strip()
                }
            
            reasoning_and_answer = parts[1].strip()
            answer_parts = reasoning_and_answer.split("Answer:")
            
            if len(answer_parts) < 2:
                # No Answer heading found
                return {
                    "reasoning": reasoning_and_answer.strip(),
                    "answer": ""
                }
            
            reasoning = answer_parts[0].strip()
            answer = answer_parts[1].strip()
            
            return {
                "reasoning": reasoning,
                "answer": answer
            }
        except Exception as e:
            raise LLMError(f"Failed to parse structured reasoning response: {str(e)}", e)
