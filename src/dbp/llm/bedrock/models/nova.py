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
# 2025-05-05T01:30:50Z : Updated _get_system_content method signature by CodeAssistant
# * Modified method to accept system_prompt parameter
# * Added handling for directly provided system prompts
# * Enhanced implementation to support various system prompt types
# * Updated method documentation to reflect the changes
# 2025-05-05T00:38:00Z : Updated method names for abstract class compatibility by CodeAssistant
# * Renamed _format_messages_internal to _format_messages
# * Renamed _format_model_kwargs_internal to _format_model_kwargs
# * No functional changes, only method renaming for abstract method implementation
# 2025-05-04T23:45:00Z : Refactored to use template method pattern for request preparation by CodeAssistant
# * Removed duplicated stream_chat implementation
# * Added standardized parameter handling through internal methods
# * Implemented _format_messages_internal, _format_model_kwargs_internal
# * Added _get_system_content and _get_model_specific_params methods
# * Updated process_multimodal_message to use _prepare_request
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
        
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Nova models.
        
        [Design principles]
        - Nova-specific message formatting
        - Consistent return type (List)
        - Simple handling of different message types
        
        [Implementation details]
        - Maps role names properly
        - Handles content format variations
        - Skips system messages (handled separately via system_prompt)
        
        Args:
            messages: List of message objects
            
        Returns:
            List[Dict[str, Any]]: Formatted messages for Nova
        """
        formatted_messages = []
        
        # Process all messages
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Skip system messages - they're now handled through system_prompt
            if role == "system":
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
            
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
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
        
    def _get_system_content(self, system_prompt: Any = None) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get system content for Nova requests formatted for the Bedrock API.
        
        [Design principles]
        - Nova-specific system content format with correct API key
        - Clean conversion of different input types
        - Returns complete dict ready for API request
        
        [Implementation details]
        - Processes system_prompt into Nova's expected format
        - Returns properly formatted dictionary with "system" key
        - Handles various input types (string, dict, list, other)
        - Returns None if no system prompt is set
        
        Args:
            system_prompt: Raw system prompt data from set_system_prompt()
            
        Returns:
            Optional[Dict[str, Any]]: Complete system content dict or None
                                     (will be merged into the API request)
        """
        # Return None if no system prompt
        if system_prompt is None:
            return None
            
        # Format based on the type into an array of SystemContentBlock objects
        system_blocks = []
        
        if isinstance(system_prompt, str):
            # Simple string becomes a text block
            system_blocks = [{"text": system_prompt}]
        elif isinstance(system_prompt, dict) and "text" in system_prompt:
            # Dictionary with text field is extracted properly
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
        
        # Return the properly formatted dictionary according to AWS documentation
        # system parameter must be an array of SystemContentBlock objects
        return {"system": system_blocks}

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
    
