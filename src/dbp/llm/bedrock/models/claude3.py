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
# Implements a specialized client for Anthropic's Claude 3.5+ models on Amazon Bedrock.
# This client adds Claude-specific features like reasoning support and parameter
# handling while maintaining the streaming-first and async approach required by
# the LangChain/LangGraph integration. Supports Claude 3.5 and Claude 3.7 model variants.
###############################################################################
# [Source file design principles]
# - Claude-specific parameter optimization
# - Reasoning support for enhanced outputs
# - Specialized message formatting for Claude
# - Clean extension of BedrockBase
# - Asynchronous streaming interface
# - Support for Claude 3.5+ model variants
###############################################################################
# [Source file constraints]
# - Must be compatible with Claude 3.5 and newer models only
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
# 2025-05-02T23:11:00Z : Refactored to use shared stream processing method by CodeAssistant
# * Removed duplicated _process_converse_stream_events method
# * Now using _process_converse_stream from EnhancedBedrockBase
# * Improved code DRYness and maintainability
# 2025-05-02T13:08:00Z : Enhanced with capability-based API integration by CodeAssistant
# * Updated to extend EnhancedBedrockBase instead of BedrockBase
# * Added capability registration for reasoning and structured output
# * Implemented capability handlers for unified API access
# * Integrated with capability discovery system
# 2025-05-02T12:55:00Z : Updated to support only Claude 3.5+ models by Cline
# * Removed older Claude 3 models from supported models list
# * Updated documentation to reflect focus on Claude 3.5+ models only
# * Changed model validation to only accept Claude 3.5 and newer
###############################################################################

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Union, cast

from ..enhanced_base import EnhancedBedrockBase, ModelCapability
from ..client_common import (
    ConverseStreamProcessor, BedrockMessageConverter, 
    BedrockErrorMapper, InferenceParameterFormatter
)
from ...common.streaming import (
    StreamingResponse, TextStreamingResponse, IStreamable
)
from ...common.exceptions import LLMError, InvocationError


class ClaudeClient(EnhancedBedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Claude 3.5+ models.
    This client adds Claude-specific features like reasoning support and
    parameter handling while maintaining the streaming-focused approach.
    
    [Design principles]
    - Claude-specific parameter optimization
    - Reasoning support for enhanced outputs
    - Specialized message formatting for Claude
    - Clean extension of BedrockBase
    
    [Implementation details]
    - Supports Claude 3.5+ model variants
    - Implements Claude-specific parameter mapping
    - Adds specialized reasoning support
    - Optimizes default parameters for Claude
    """
    
    # Supported Claude models - helps with validation
    # Only supporting Claude 3.5+ models as per requirements
    _CLAUDE_MODELS = [
        "anthropic.claude-3-5-haiku-20241022-v1:0", 
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-7-sonnet-20250219-v1:0"
    ]
    
    # Set the class-level SUPPORTED_MODELS for model discovery
    SUPPORTED_MODELS = _CLAUDE_MODELS
    
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
        max_retries: int = 3,  # Default to 3 retries
        timeout: int = 30,     # Default to 30 seconds timeout
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = False,
        preferred_regions: Optional[List[str]] = None
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
        is_claude_model = any(model_id.startswith(model) for model in self._CLAUDE_MODELS)
        
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
            logger=logger or logging.getLogger("ClaudeClient"),
            use_model_discovery=use_model_discovery,
            preferred_regions=preferred_regions
        )
        
        # Initialize fields for additional parameters
        self._system_content = None
        self._claude_specific_params = {}
        
        # Register Claude capabilities
        self.register_capabilities([
            ModelCapability.SYSTEM_PROMPT,
            ModelCapability.REASONING,
            ModelCapability.STRUCTURED_OUTPUT
        ])
        
        # Register capability handlers
        self.register_handler(
            ModelCapability.REASONING,
            self._handle_reasoning
        )
        self.register_handler(
            ModelCapability.STRUCTURED_OUTPUT,
            self._handle_structured_output
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
                # For simple text, we use the direct 'text' key without a 'type' field
                formatted_msg["content"] = [{"text": content}]
            elif isinstance(content, list):
                # For multimodal content, convert each item to proper format
                formatted_content = []
                for item in content:
                    # If the item already has the right format (no 'type' field), use as is
                    if isinstance(item, dict) and ("text" in item or "image" in item):
                        formatted_content.append(item)
                    # If it has a 'type' field, convert to proper format
                    elif isinstance(item, dict) and "type" in item:
                        if item["type"] == "text":
                            formatted_content.append({"text": item.get("text", "")})
                        elif item["type"] == "image":
                            formatted_content.append({
                                "image": item.get("image", {})
                            })
                    else:
                        self.logger.warning(f"Unsupported content item: {item}")
                
                formatted_msg["content"] = formatted_content
            else:
                raise ValueError(f"Unsupported content format: {type(content)}")
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages
    
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters specifically for Claude models in Bedrock Converse API format.
        
        [Design principles]
        - Claude-specific parameter mapping
        - Support for reasoning feature
        - Parameter validation and defaults
        - Proper separation of common and model-specific parameters
        
        [Implementation details]
        - Separates common parameters for inferenceConfig
        - Places Claude-specific parameters in additionalModelRequestFields
        - Supports reasoning configuration
        - Provides Claude-optimized defaults
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Converse API's inferenceConfig field
        """
        # Common parameters for inferenceConfig
        inference_config = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokens": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P)
        }
        
        # Add stop sequences if provided
        if "stop_sequences" in kwargs:
            inference_config["stopSequences"] = kwargs["stop_sequences"]
        
        # System content should not be part of inferenceConfig but a separate field
        system_content = None
        if "system" in kwargs:
            system_content = kwargs["system"]
        elif kwargs.get("use_reasoning", False):
            system_content = "Use step-by-step reasoning to solve this problem."
        
        # Claude-specific parameters for additionalModelRequestFields
        claude_specific_params = {}
        if "anthropic_version" in kwargs:
            claude_specific_params["anthropicVersion"] = kwargs["anthropic_version"]
        else:
            # Use a recent anthropic version by default
            claude_specific_params["anthropicVersion"] = "bedrock-2023-05-31"
            
        if "top_k" in kwargs:
            claude_specific_params["topK"] = kwargs["top_k"]
        
        # Only return inferenceConfig, system and additionalModelRequestFields will be
        # handled separately when making the API call
        result = inference_config
        
        # Store additional fields for later use
        if system_content:
            self._system_content = system_content
        if claude_specific_params:
            self._claude_specific_params = claude_specific_params
            
        return result
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response from Claude models using the Bedrock Converse API with streaming.
        This method properly handles the Converse API structure including system prompts
        and model-specific parameters.
        
        [Design principles]
        - Streaming as the standard interaction pattern
        - Support for model-specific parameters
        - Clean handling of Converse API structure
        - Proper separation of common and model-specific parameters
        
        [Implementation details]
        - Uses Converse API exclusively
        - Properly formats messages, system content and parameters
        - Handles Claude-specific streaming response format
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Model-specific parameters
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        # Validate initialization
        if not self.is_initialized():
            await self.initialize()
        
        # Format messages for Bedrock
        formatted_messages = self._format_messages(messages)
        
        # Format model kwargs
        inference_config = self._format_model_kwargs(kwargs)
        
        # Prepare the request for Converse API
        request = {
            "modelId": self.model_id,
            "messages": formatted_messages,
            "inferenceConfig": inference_config
        }
        
        # Add system content if provided
        if hasattr(self, '_system_content') and self._system_content:
            # Format system content without 'type' field - Claude expects plain 'text' key
            request["system"] = {"text": self._system_content}
            # Clear for next call
            self._system_content = None
        
        # Add Claude-specific parameters if any
        if hasattr(self, '_claude_specific_params') and self._claude_specific_params:
            request["additionalModelRequestFields"] = self._claude_specific_params
            # Clear for next call
            self._claude_specific_params = {}
        
        # Stream response
        try:
            # Make streaming API call - run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self._bedrock_runtime.converse_stream(**request)
            )
            stream = response["stream"]
            
            # Use the shared method from EnhancedBedrockBase to process the stream
            async for chunk in self._process_converse_stream(stream):
                yield chunk
                
        except Exception as e:
            if isinstance(e, LLMError):
                raise e
            raise LLMError(f"Failed to stream chat response: {str(e)}", e)
    
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
    
    async def _handle_reasoning(
        self,
        content: str,
        **kwargs
    ) -> Union[str, AsyncIterator[Dict[str, Any]]]:
        """
        [Method intent]
        Process content with reasoning through the capability API.
        This is a handler for the REASONING capability.
        
        [Design principles]
        - Clean mapping to reasoning capabilities
        - Support for streaming or complete results
        - Consistent response format
        
        [Implementation details]
        - Adapts content for reasoning methods
        - Uses appropriate system prompt
        - Delegates to specialized reasoning methods
        
        Args:
            content: The text content to process with reasoning
            **kwargs: Additional parameters including stream flag
            
        Returns:
            Union[str, AsyncIterator[Dict[str, Any]]]: 
                Either complete text or streaming chunks
            
        Raises:
            ValueError: If content format is invalid
            LLMError: If reasoning processing fails
        """
        # Extract the text from various content formats
        if not isinstance(content, str):
            if isinstance(content, dict) and "text" in content:
                content = content["text"]
            else:
                raise ValueError("Reasoning requires text content")
        
        # Set reasoning parameters
        kwargs["use_reasoning"] = True
        
        # Check if streaming is requested
        if kwargs.get("stream", False):
            # Return a streaming response
            return self.stream_generate_with_reasoning(content, **kwargs)
        else:
            # Return a complete response
            return await self.get_completion_with_reasoning(content, **kwargs)
    
    async def _handle_structured_output(
        self,
        content: str,
        format_instructions: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Process content to generate structured output through the capability API.
        This is a handler for the STRUCTURED_OUTPUT capability.
        
        [Design principles]
        - Support for structured data extraction
        - Clean formatting instructions
        - Consistent structured return format
        
        [Implementation details]
        - Uses specialized system prompts for structured output
        - Processes and parses the response
        - Returns structured data dictionary
        
        Args:
            content: The text content to process
            format_instructions: Optional instructions for output formatting
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Structured output data
            
        Raises:
            ValueError: If content format is invalid
            LLMError: If structured output processing fails
        """
        # Extract the text from various content formats
        if not isinstance(content, str):
            if isinstance(content, dict) and "text" in content:
                content = content["text"]
            else:
                raise ValueError("Structured output requires text content")
        
        # If format instructions are provided, use them
        if format_instructions:
            kwargs["system"] = format_instructions
        
        # Use the structured reasoning method
        return await self.get_structured_reasoning_response(content, **kwargs)
    
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
