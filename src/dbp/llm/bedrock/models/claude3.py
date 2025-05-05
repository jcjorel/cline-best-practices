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
# This client adds Claude-specific features for parameter handling while maintaining 
# the streaming-first and async approach required by the LangChain/LangGraph integration. 
# Supports Claude 3.5 and Claude 3.7 model variants with focused implementation on 
# core functionality.
###############################################################################
# [Source file design principles]
# - Claude-specific parameter optimization
# - Specialized message formatting for Claude
# - Clean extension of BedrockBase
# - Asynchronous streaming interface
# - Support for Claude 3.5+ model variants
# - KISS approach focusing on core functionality
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
# 2025-05-05T11:08:00Z : Removed all reasoning functionality by CodeAssistant
# * Removed all reasoning-related methods
# * Cleaned up implementation for better maintainability
# * Simplified parameter handling and processing
# * Applied KISS approach to reduce code complexity
# 2025-05-05T01:30:13Z : Updated _get_system_content method signature by CodeAssistant
# * Modified method to accept system_prompt parameter
# * Added handling for directly provided system prompts
# * Enhanced implementation to handle different system prompt types
# * Updated method documentation to reflect the changes
# 2025-05-05T00:39:00Z : Updated method names for abstract class compatibility by CodeAssistant
# * Renamed _format_messages_internal to _format_messages
# * Renamed _format_model_kwargs_internal to _format_model_kwargs
# * No functional changes, only method renaming for abstract method implementation
# 2025-05-04T23:45:00Z : Refactored to use template method pattern for request preparation by CodeAssistant
# * Removed duplicated stream_chat implementation
# * Added standardized parameter handling through internal methods
# * Implemented _format_messages_internal, _format_model_kwargs_internal
# * Added _get_system_content and _get_model_specific_params methods
###############################################################################

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Union, cast

from ..enhanced_base import EnhancedBedrockBase
from ..client_common import (
    ConverseStreamProcessor, BedrockMessageConverter, 
    BedrockErrorMapper, InferenceParameterFormatter
)
from ...common.streaming import (
    StreamingResponse, TextStreamingResponse, IStreamable
)
from ...common.exceptions import LLMError, InvocationError, UnsupportedFeatureError


class ClaudeClient(EnhancedBedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Claude 3.5+ models.
    This client adds Claude-specific features for parameter handling while
    maintaining the streaming-focused approach.
    
    [Design principles]
    - Claude-specific parameter optimization
    - Specialized message formatting for Claude
    - Clean extension of BedrockBase
    - Simple and maintainable implementation
    
    [Implementation details]
    - Supports Claude 3.5+ model variants
    - Implements Claude-specific parameter mapping
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
        preferred_regions: Optional[List[str]] = None,
        inference_profile_arn: Optional[str] = None
    ):
        """
        [Method intent]
        Initialize the Claude client with model validation and Claude-specific defaults.
        
        [Design principles]
        - Strong model validation
        - Claude-specific configuration
        - Clean delegation to base class
        - Direct error propagation
        
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
            use_model_discovery: Whether to discover model availability
            preferred_regions: List of preferred regions for model discovery
            inference_profile_arn: Optional inference profile ARN to use

        Raises:
            ValueError: If model_id is not a supported Claude model
            ModelNotAvailableError: If the model is not available or accessible
            AWSClientError: If there are AWS client issues
            LLMError: If there are other errors fetching model details
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
            preferred_regions=preferred_regions,
            inference_profile_arn=inference_profile_arn
        )
        
        # Store inference profile ARN if provided (for future use)
        self._inference_profile_arn = inference_profile_arn
        
        # Initialize fields for additional parameters
        self._system_content = None
        self._claude_specific_params = {}
        
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Claude models.
        
        [Design principles]
        - Claude-specific message formatting
        - Consistent return type (List)
        - No side effects
        
        [Implementation details]
        - Properly formats all message types for Claude
        - Handles content format variations
        - Preserves special Claude message structure
        - Skips system messages (handled separately via set_system_prompt)
        
        Args:
            messages: List of message objects
            
        Returns:
            List[Dict[str, Any]]: Claude-formatted messages
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Skip system messages - they're handled separately via set_system_prompt
            if role == "system":
                continue
                
            # Format for Claude's expected structure
            formatted_msg = {"role": role}
                
            # Handle content formatting
            if isinstance(content, str):
                formatted_msg["content"] = [{"text": content}]
            elif isinstance(content, list):
                # Format multimodal content for Claude
                formatted_content = []
                for item in content:
                    if isinstance(item, dict) and ("text" in item or "image" in item):
                        formatted_content.append(item)
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
                formatted_msg["content"] = [{"text": json.dumps(content)}]
                
            formatted_messages.append(formatted_msg)
        
        return formatted_messages

    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters for Claude API.
        
        [Design principles]
        - Claude-specific parameter formatting
        - Consistent return type
        - Clean parameter handling
        - Simple and maintainable implementation
        
        [Implementation details]
        - Maps standard parameters to Claude API format
        - Handles Claude-specific parameters separately
        - Supports prompt caching
        
        Args:
            kwargs: Combined parameters
            
        Returns:
            Dict[str, Any]: Formatted inferenceConfig for Claude
        """
        # Extract and store Claude-specific parameters
        self._pending_claude_params = {}
                
        # Only extract top_k parameter if provided
        if "top_k" in kwargs:
            self._pending_claude_params["topK"] = kwargs["top_k"]
        
        # Format common inference parameters
        inference_config = {
            "maxTokens": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P)
        }
        
        # Add stop sequences if provided
        if "stop_sequences" in kwargs:
            inference_config["stopSequences"] = kwargs["stop_sequences"]
        
        # Add caching if enabled
        caching_enabled = kwargs.get("enable_caching") or getattr(self, '_prompt_caching_enabled', False)
        if caching_enabled:
            inference_config["caching"] = {
                "cachingState": "ENABLED"
            }
        
        return inference_config

    def _get_system_content(self, system_prompt: Any = None) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get system content for Claude requests formatted for the Bedrock API.
        
        [Design principles]
        - Claude-specific system content format with correct API key
        - Clear extraction of pending system content
        - Handles direct system prompt parameter
        - Cleans up after use
        - Returns complete dict ready for API request
        
        [Implementation details]
        - Processes directly provided system_prompt if available
        - Falls back to pending system prompts if system_prompt is None
        - Returns properly formatted system content following AWS documentation
        - Clears pending content after use
        
        Args:
            system_prompt: Raw system prompt data from set_system_prompt()
            
        Returns:
            Optional[Dict[str, Any]]: Complete system content dict or None
                                     (will be merged into the API request)
        """
        # Get system content from provided system_prompt or _pending_system_content
        
        # If system_prompt is provided directly, use it
        if system_prompt is not None:
            # Handle different formats of system prompts
            if isinstance(system_prompt, str):
                # Simple string becomes a text block
                system_blocks = [{"text": system_prompt}]
            elif isinstance(system_prompt, dict) and "text" in system_prompt:
                # Dictionary with text field is already in proper format
                system_blocks = [{"text": system_prompt["text"]}]
            elif isinstance(system_prompt, list):
                # Handle list format properly
                system_blocks = []
                for item in system_prompt:
                    if isinstance(item, dict) and "text" in item:
                        system_blocks.append({"text": item["text"]})
                    else:
                        system_blocks.append({"text": str(item)})
            else:
                # Convert other types to string
                system_blocks = [{"text": str(system_prompt)}]
        
        # Fall back to pending system content
        elif hasattr(self, '_pending_system_content') and self._pending_system_content:
            content_text = self._pending_system_content
            self._pending_system_content = None
            system_blocks = [{"text": content_text}]
        else:
            # Return None if no system content
            return None
        
        # Return the properly formatted dictionary according to AWS documentation
        # system parameter must be an array of SystemContentBlock objects
        return {"system": system_blocks}

    def _get_model_specific_params(self) -> Dict[str, Any]:
        """
        [Method intent]
        Get Claude-specific parameters for requests.
        
        [Design principles]
        - Claude-specific parameter extraction
        - Clear state management
        - Cleans up after use
        
        [Implementation details]
        - Returns stored Claude-specific parameters
        - Clears pending parameters after use
        
        Returns:
            Dict[str, Any]: Claude-specific parameters or empty dict
        """
        if hasattr(self, '_pending_claude_params') and self._pending_claude_params:
            params = self._pending_claude_params
            self._pending_claude_params = {}
            return params
        return {}
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response from the model for a chat conversation using streaming.
        
        [Design principles]
        - Simple, straightforward implementation
        - Consistent with base implementation
        - Clean delegation pattern
        
        [Implementation details]
        - Directly delegates to parent implementation
        - Maintains Claude-specific parameter handling
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Model-specific parameters
                
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        # Delegate to parent implementation
        async for chunk in super().stream_chat(messages, **kwargs):
            yield chunk
    
    async def _process_stream_chunk(
        self, 
        chunk: Dict[str, Any],
        has_special_content_types: bool = False
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Process a streaming chunk.
        
        [Design principles]
        - Simple pass-through implementation
        - Minimal processing overhead
        
        [Implementation details]
        - Basic pass-through of chunks
        - Parameter preserved for API compatibility
        
        Args:
            chunk: The raw chunk from the response stream
            has_special_content_types: Whether to expect special content types
            
        Returns:
            Dict[str, Any]: Processed chunk, unmodified
        """
        # Simple pass-through implementation - no special processing needed
        return chunk
