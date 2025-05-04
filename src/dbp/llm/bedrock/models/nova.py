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
# Implements Amazon Bedrock Nova model support for the LLM module. This provides
# the specific implementation details for interacting with the Nova family of models
# through the Converse API, handling their unique parameters and response formats.
###############################################################################
# [Source file design principles]
# - Model-specific implementation for Nova models
# - Follows the core Bedrock client interface
# - Handles Nova-specific parameters and formatting
# - Provides proper streaming support for Nova responses
# - Uses LangChain integration for compatibility
###############################################################################
# [Source file constraints]
# - Must only use the Converse API
# - Must handle Nova-specific parameters and formatting
# - Must properly implement parameter validation
# - Must support both text and structured responses
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/llm/common/streaming.py
# codebase:src/dbp/llm/bedrock/base.py
# codebase:src/dbp/llm/bedrock/client_common.py
# system:typing
# system:asyncio
# system:json
# system:base64
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-04T23:45:00Z : Refactored to use template method pattern for request preparation by CodeAssistant
# * Removed duplicated stream_chat implementation
# * Added standardized parameter handling through internal methods
# * Implemented _format_messages_internal, _format_model_kwargs_internal
# * Added _get_system_content and _get_model_specific_params methods
# * Updated process_multimodal_message to use _prepare_request
# 2025-05-04T23:12:00Z : Refactored to use direct model details for capability checking by CodeAssistant
# * Removed ModelCapability enum dependencies
# * Added Nova-specific capability check methods
# * Updated handler registration to use string-based identifiers
# * Improved error handling and propagation
# 2025-05-04T11:30:00Z : Added prompt caching support by CodeAssistant
# * Added capability detection for prompt caching
# * Dynamically registers PROMPT_CACHING capability when supported
# * Added support for Bedrock prompt caching with Nova models
# 2025-05-02T13:06:00Z : Enhanced with capability-based API integration by CodeAssistant
# * Updated to extend EnhancedBedrockBase instead of BedrockBase
# * Added capability registration for model features
# * Implemented capability handlers for features like multimodal, summarization
# * Added support for unified capability-based API access
###############################################################################

"""
Amazon Bedrock Nova model implementation.
"""

import logging
import json
import asyncio
import base64
import botocore.exceptions
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


class NovaClient(EnhancedBedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Nova models.
    This client adds Nova-specific features and parameter handling while
    maintaining the streaming-focused approach for multimodal understanding capabilities.
    
    [Design principles]
    - Nova-specific parameter optimization
    - Specialized message formatting for Nova models
    - Clean extension of BedrockBase
    - Streaming-only interface
    - Multimodal capabilities support
    
    [Implementation details]
    - Supports all Nova model variants (Lite, Micro, Pro, Premier, Reel)
    - Implements Nova-specific parameter mapping for Converse API
    - Optimizes default parameters for Nova models
    - Handles Nova's response format
    - Provides multimodal support for image and video inputs
    """
    
    # Supported Nova models - helps with validation
    _NOVA_MODELS = [
        "amazon.nova-lite-v1:0",
        "amazon.nova-micro-v1:0",
        "amazon.nova-pro-v1:0",
        "amazon.nova-premier-v1:0",
        "amazon.nova-reel-v1:0"
    ]
    
    # Public attribute for model discovery
    SUPPORTED_MODELS = _NOVA_MODELS
    
    # Nova models context window sizes
    CONTEXT_WINDOW_SIZES = {
        "nova-micro": 128000,   # 128K tokens
        "nova-pro": 300000,     # 300K tokens
        "nova-lite": 300000,    # 300K tokens (estimated)
        "nova-premier": 1000000  # 1M tokens
    }
    
    # Default Nova parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 5000  # Maximum output tokens for Nova models
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
        Initialize the Nova client with model validation and Nova-specific defaults.
        
        [Design principles]
        - Strong model validation
        - Nova-specific configuration
        - Clean delegation to base class
        - Direct error propagation
        
        [Implementation details]
        - Validates that model_id is a Nova model
        - Sets up Nova-specific logging
        - Initializes with Nova defaults

        Args:
            model_id: Nova model ID (e.g., "amazon.nova-lite-v1:0")
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
            ValueError: If model_id is not a supported Nova model
            ModelNotAvailableError: If the model is not available or accessible
            AWSClientError: If there are AWS client issues
            LLMError: If there are other errors fetching model details
        """
        # Validate model is a Nova model
        base_model_id = model_id.split(":")[0]
        # Fix the validation logic to check if the base_model_id equals any of the supported model IDs
        is_nova_model = any(model.split(":")[0] == base_model_id for model in self._NOVA_MODELS)
        
        if not is_nova_model:
            raise ValueError(f"Model {model_id} is not a supported Nova model. Supported models: {', '.join(self._NOVA_MODELS)}")
        
        # Initialize base class
        super().__init__(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            credentials=credentials,
            max_retries=max_retries,
            timeout=timeout,
            logger=logger or logging.getLogger("NovaClient"),
            use_model_discovery=use_model_discovery,
            preferred_regions=preferred_regions,
            inference_profile_arn=inference_profile_arn
        )
        
        # Store inference profile ARN if provided (for future use)
        self._inference_profile_arn = inference_profile_arn
    
    def supports_multimodal(self) -> bool:
        """
        [Method intent]
        Check if this Nova model supports multimodal inputs.
        
        [Design principles]
        - Direct capability checking
        - Nova variant-specific feature
        - Clean boolean interface
        
        [Implementation details]
        - Checks model ID for Pro, Premier, or Lite variants
        
        Returns:
            bool: True if the model supports multimodal inputs (images)
        """
        model_id_lower = self.model_id.lower()
        return any(variant in model_id_lower for variant in ["nova-pro", "nova-premier", "nova-lite"])

    def supports_video_input(self) -> bool:
        """
        [Method intent]
        Check if this Nova model supports video input.
        
        [Design principles]
        - Direct capability checking
        - Nova variant-specific feature
        - Clean boolean interface
        
        [Implementation details]
        - Checks if model is Nova Reel variant
        
        Returns:
            bool: True if the model supports video input
        """
        return "nova-reel" in self.model_id.lower()

    def supports_keyword_extraction(self) -> bool:
        """
        [Method intent]
        Check if this Nova model supports keyword extraction.
        
        [Design principles]
        - Direct capability checking
        - Nova-specific feature
        - Clean boolean interface
        
        [Implementation details]
        - All Nova models support keyword extraction
        
        Returns:
            bool: True as all Nova models support keyword extraction
        """
        return True

    def supports_summarization(self) -> bool:
        """
        [Method intent]
        Check if this Nova model supports text summarization.
        
        [Design principles]
        - Direct capability checking
        - Nova-specific feature
        - Clean boolean interface
        
        [Implementation details]
        - All Nova models support summarization
        
        Returns:
            bool: True as all Nova models support summarization
        """
        return True

    def supports_system_prompt(self) -> bool:
        """
        [Method intent]
        Check if this Nova model supports system prompts.
        
        [Design principles]
        - Direct capability checking
        - Nova-specific feature
        - Clean boolean interface
        
        [Implementation details]
        - All Nova models support system prompts
        
        Returns:
            bool: True as all Nova models support system prompts
        """
        return True
    
    def _format_messages_internal(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Nova models.
        
        [Design principles]
        - Nova-specific message formatting
        - Consistent return type (List)
        - Proper extraction of system prompts
        
        [Implementation details]
        - Maps role names properly
        - Handles content format variations
        - Extracts system prompts for separate handling
        
        Args:
            messages: List of message objects
            
        Returns:
            List[Dict[str, Any]]: Formatted messages for Nova
        """
        formatted_messages = []
        self._pending_system_prompts = []
        
        # Process all messages
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Handle system messages separately for Nova
            if role == "system":
                system_text = content if isinstance(content, str) else json.dumps(content)
                self._pending_system_prompts.append({"text": system_text})
                continue
                
            # Map role names to Nova expected roles
            if role == "user":
                nova_role = "user"
            elif role == "assistant":
                nova_role = "assistant" 
            else:
                self.logger.warning(f"Unsupported role '{role}' for Nova, using 'user' as default")
                nova_role = "user"
            
            # Format for Nova
            if isinstance(content, str):
                # For simple text, wrap in a list with a text object
                formatted_messages.append({
                    "role": nova_role,
                    "content": [{"text": content}]
                })
            else:
                # For other content types, use as is if it's a list, otherwise wrap
                content_list = content if isinstance(content, list) else [{"text": json.dumps(content)}]
                formatted_messages.append({
                    "role": nova_role,
                    "content": content_list
                })
        
        return formatted_messages
    
    def _handle_bedrock_error(self, error: Exception, operation_name: str):
        """
        [Method intent]
        Handle Bedrock API errors consistently, mapping them to appropriate exception types.
        
        [Design principles]
        - Centralized error handling following DRY principles
        - Consistent error mapping and logging
        - Proper API error classification
        
        [Implementation details]
        - Maps boto3/botocore errors to application exceptions
        - Logs errors with context information
        - Preserves original error details
        
        Args:
            error: The error that occurred
            operation_name: Name of the operation that failed, for context
            
        Raises:
            LLMError: Rethrows appropriate mapped exception
        """
        if isinstance(error, botocore.exceptions.ClientError):
            # Map AWS errors to our exception types
            if "Error" in error.response:
                error_code = error.response["Error"].get("Code", "UnknownError")
                error_message = error.response["Error"].get("Message", str(error))
                mapped_error = BedrockErrorMapper.map_api_error(error_code, error_message, error)
                self.logger.error(f"Error in {operation_name}: {str(mapped_error)}")
                raise mapped_error
            else:
                self.logger.error(f"Error in {operation_name}: {str(error)}")
                raise LLMError(f"Failed in {operation_name}: {str(error)}", error)
        else:
            self.logger.error(f"Error in {operation_name}: {str(error)}")
            raise LLMError(f"Failed in {operation_name}: {str(error)}", error)
            
    def _format_model_kwargs_internal(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters for Nova's inferenceConfig.
        
        [Design principles]
        - Nova-specific parameter formatting
        - Consistent return type (Dict for inferenceConfig)
        - Parameter validation and defaults
        
        [Implementation details]
        - Maps standard parameters to Nova's format
        - Provides Nova-optimized defaults
        - Includes caching configuration if enabled
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Nova's inferenceConfig
        """
        # Nova parameters for inferenceConfig
        inference_config = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokens": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
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
        
    def _get_system_content(self) -> Optional[List[Dict[str, Any]]]:
        """
        [Method intent]
        Get system content for Nova requests.
        
        [Design principles]
        - Nova-specific system content format
        - Clear extraction of pending system prompts
        - Cleans up after use
        
        [Implementation details]
        - Returns system prompts in Nova's expected format
        - Clears pending prompts after use
        
        Returns:
            Optional[List[Dict[str, Any]]]: Nova formatted system content or None
        """
        if hasattr(self, '_pending_system_prompts') and self._pending_system_prompts:
            system_prompts = self._pending_system_prompts
            self._pending_system_prompts = []
            return system_prompts
        return None

    def _get_model_specific_params(self) -> Dict[str, Any]:
        """
        [Method intent]
        Get Nova-specific parameters for requests.
        
        [Design principles]
        - Nova-specific parameter extraction
        - Consistent implementation
        
        [Implementation details]
        - Currently returns empty dict as Nova has no specific params
        - In place for future Nova-specific parameters
        
        Returns:
            Dict[str, Any]: Nova-specific parameters or empty dict
        """
        # Currently Nova doesn't have model-specific params in additionalModelRequestFields
        return {}

    async def stream_generate_with_options(
        self, 
        prompt: str, 
        options: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response using a single prompt with specialized options.
        
        [Design principles]
        - Support for Nova-specific features
        - Streamlined interface for common use cases
        - Unified parameter handling
        
        [Implementation details]
        - Converts prompt to messages format
        - Passes options directly to the model
        - Maintains streaming behavior
        
        Args:
            prompt: The text prompt to send to the model
            options: Nova-specific options
            
        Yields:
            Dict[str, Any]: Response chunks from Nova
            
        Raises:
            LLMError: If generation fails
        """
        # Convert to messages format
        messages = [{"role": "user", "content": prompt}]
        
        # Stream chat with the provided options
        async for chunk in self.stream_chat(messages, **options):
            yield chunk
    
            
    async def process_multimodal_message(
        self,
        text: str,
        images: List[Union[str, bytes]] = None,
        videos: List[Union[str, bytes]] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Process a multimodal message with text and media inputs using Nova's capabilities.
        
        [Design principles]
        - Support for Nova's multimodal features
        - Clean media processing and encoding
        - Unified streaming response interface
        - Direct error propagation
        
        [Implementation details]
        - Supports both text and media inputs (images/videos)
        - Properly encodes media for Nova's API
        - Uses streaming for efficient response handling
        - Throws error if model doesn't support multimodal
        
        Args:
            text: The text prompt
            images: Optional list of images (paths or bytes)
            videos: Optional list of videos (paths or bytes)
            **kwargs: Additional parameters for the model
            
        Yields:
            Dict[str, Any]: Response chunks from Nova
            
        Raises:
            UnsupportedFeatureError: If model doesn't support multimodal inputs
            ValueError: If inputs are invalid
            LLMError: If processing fails
        """
        # Check if model supports multimodal
        if not self.supports_multimodal():
            raise UnsupportedFeatureError(f"Model {self.model_id} does not support multimodal inputs")
        
        # Prepare the multimodal message
        message_content = []
        
        # Add text content if provided
        if text:
            message_content.append({
                "type": "text",
                "text": text
            })
        
        # Process images if provided
        if images:
            for img in images:
                # Handle image encoding logic
                if isinstance(img, str):
                    # Assume it's a file path, load and encode
                    with open(img, "rb") as f:
                        img_bytes = f.read()
                    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                else:
                    # Assume it's already bytes
                    img_b64 = base64.b64encode(img).decode('utf-8')
                    
                message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",  # Assume JPEG, could be detected
                        "data": img_b64
                    }
                })
        
        # Process videos if provided - but only for Nova Reel
        if videos:
            # Check if model supports video input
            if not self.supports_video_input():
                raise UnsupportedFeatureError(f"Model {self.model_id} does not support video inputs")
                
            for video in videos:
                # Handle video encoding logic
                if isinstance(video, str):
                    # Assume it's a file path, load and encode
                    with open(video, "rb") as f:
                        video_bytes = f.read()
                    video_b64 = base64.b64encode(video_bytes).decode('utf-8')
                else:
                    # Assume it's already bytes
                    video_b64 = base64.b64encode(video).decode('utf-8')
                    
                message_content.append({
                    "type": "video",
                    "source": {
                        "type": "base64",
                        "media_type": "video/mp4",  # Assume MP4, could be detected
                        "data": video_b64
                    }
                })
        
        # Convert multimodal message to standard message format for _prepare_request
        messages = [{
            "role": "user",
            "content": message_content
        }]
        
        # Prepare the request using the template method
        request_payload = self._prepare_request(messages, kwargs)
        
        # Log the request if debug enabled
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Nova multimodal request prepared (content types: {[item['type'] for item in message_content]})")
        
        # Stream response
        try:
            # Make streaming API call - run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.bedrock_runtime.converse_stream(**request_payload)
            )
            
            # Get the stream from the response
            stream = response.get("stream")
            
            # Use the shared method from EnhancedBedrockBase to process the stream
            async for chunk in self._process_converse_stream(stream):
                yield chunk
                
        except Exception as e:
            self._handle_bedrock_error(e, "multimodal processing")
    
    async def extract_keywords(
        self, 
        text: str, 
        max_results: int = 10
    ) -> List[str]:
        """
        [Method intent]
        Extract keywords from a text using Nova's capabilities.
        
        [Design principles]
        - Specialized utility for common Nova use case
        - Simple interface for keyword extraction
        - Structured return format
        
        [Implementation details]
        - Uses a specialized prompt and system message
        - Processes the response to extract keywords
        - Returns a clean list of keywords
        
        Args:
            text: Text to extract keywords from
            max_results: Maximum number of keywords to return
            
        Returns:
            List[str]: Extracted keywords
            
        Raises:
            LLMError: If extraction fails
        """
        # Set up a system message for keyword extraction
        system_message = f"""
        Extract up to {max_results} important keywords from the provided text.
        Return only the keywords, one per line, with no numbering or extra formatting.
        Focus on the most relevant and important concepts in the text.
        """
        
        # Set up the conversation
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ]
        
        # Generate with low temperature for more consistent results
        result = ""
        async for chunk in self.stream_chat(messages, temperature=0.1, max_tokens=256):
            if "delta" in chunk and "text" in chunk["delta"]:
                result += chunk["delta"]["text"]
        
        # Process the response into a list of keywords
        try:
            keywords = [keyword.strip() for keyword in result.split("\n") if keyword.strip()]
            # Limit to max_results
            return keywords[:max_results]
        except Exception as e:
            raise LLMError(f"Failed to process keyword extraction response: {str(e)}", e)
    
    
    async def summarize_text(
        self, 
        text: str, 
        max_length: int = 200, 
        focus_on: Optional[str] = None
    ) -> str:
        """
        [Method intent]
        Generate a concise summary of a text using Nova's capabilities.
        
        [Design principles]
        - Specialized utility for common Nova use case
        - Configurable summary length and focus
        - Simple interface for text summarization
        
        [Implementation details]
        - Uses a specialized prompt and system message
        - Configures the model for summarization task
        - Processes and returns the complete summary
        
        Args:
            text: Text to summarize
            max_length: Maximum length of the summary in words
            focus_on: Optional aspect to focus on in the summary
            
        Returns:
            str: Generated summary
            
        Raises:
            LLMError: If summarization fails
        """
        # Set up a system message for summarization
        system_message = f"""
        Summarize the provided text in {max_length} words or less.
        {"Focus on aspects related to: " + focus_on if focus_on else ""}
        The summary should be concise but capture the main points of the text.
        """
        
        # Set up the conversation
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ]
        
        # Generate with moderate temperature for good summaries
        result = ""
        async for chunk in self.stream_chat(messages, temperature=0.3, max_tokens=max_length*2):
            if "delta" in chunk and "text" in chunk["delta"]:
                result += chunk["delta"]["text"]
        
        return result.strip()
