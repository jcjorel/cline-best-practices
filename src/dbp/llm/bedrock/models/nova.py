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
# 2025-05-02T13:06:00Z : Enhanced with capability-based API integration by CodeAssistant
# * Updated to extend EnhancedBedrockBase instead of BedrockBase
# * Added capability registration for model features
# * Implemented capability handlers for features like multimodal, summarization
# * Added support for unified capability-based API access
# 2025-05-02T12:32:00Z : Fixed implementation to target actual Nova models by CodeAssistant
# * Updated model IDs from Titan to correct Nova models
# * Restructured parameter formatting for Nova's API format
# * Added multimodal support specific to Nova models
# * Updated message formatting for Converse API structure
###############################################################################

"""
Amazon Bedrock Nova model implementation.
"""

import logging
import json
import asyncio
import base64
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
        max_retries: int = BedrockBase.DEFAULT_RETRIES,
        timeout: int = BedrockBase.DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the Nova client with model validation and Nova-specific defaults.
        
        [Design principles]
        - Strong model validation
        - Nova-specific configuration
        - Clean delegation to base class
        
        [Implementation details]
        - Validates that model_id is a Nova model
        - Sets up Nova-specific logging
        - Initializes with Nova defaults
        
        Args:
            model_id: Nova model ID (e.g., "amazon.titan-text-express-v1")
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            
        Raises:
            ValueError: If model_id is not a supported Nova model
        """
        # Validate model is a Nova model
        base_model_id = model_id.split(":")[0]
        is_nova_model = any(model in base_model_id for model in self._NOVA_MODELS)
        
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
            logger=logger or logging.getLogger("NovaClient")
        )
        
        # Register Nova capabilities
        self.register_capabilities([
            ModelCapability.SYSTEM_PROMPT,
            ModelCapability.KEYWORD_EXTRACTION,
            ModelCapability.SUMMARIZATION
        ])
        
        # Register model-specific capabilities
        base_model = model_id.split(":")[0].lower()
        
        # Check for Pro, Premier, or Lite models which support multimodal input
        if any(mm in base_model for mm in ["nova-pro", "nova-premier", "nova-lite"]):
            self.register_capabilities([
                ModelCapability.MULTIMODAL,
                ModelCapability.IMAGE_INPUT
            ])
            
            # Register capability handlers
            self.register_handler(
                ModelCapability.MULTIMODAL,
                self._handle_multimodal_content
            )
            self.register_handler(
                ModelCapability.KEYWORD_EXTRACTION,
                self._handle_keyword_extraction
            )
            self.register_handler(
                ModelCapability.SUMMARIZATION,
                self._handle_summarization
            )
            
        # Nova Reel supports video input
        if "nova-reel" in base_model:
            self.register_capability(ModelCapability.VIDEO_INPUT)
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        [Method intent]
        Format messages specifically for Nova models using the Converse API format.
        
        [Design principles]
        - Nova-specific message formatting
        - Support for system messages
        - Handle content format variations
        
        [Implementation details]
        - Creates properly structured messages array
        - Separates system prompts into dedicated field
        - Handles content format variations
        
        Args:
            messages: List of message objects in standard format
            
        Returns:
            Dict[str, Any]: Message payload formatted for Nova's Converse API
        """
        formatted_messages = []
        system_prompts = []
        
        # Process all messages
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Handle system messages separately for Nova
            if role == "system":
                system_text = content if isinstance(content, str) else json.dumps(content)
                system_prompts.append({"text": system_text})
                continue
                
            # Map role names to Nova expected roles
            if role == "user":
                nova_role = "user"
            elif role == "assistant":
                nova_role = "assistant" 
            else:
                self.logger.warning(f"Unsupported role '{role}' for Nova, using 'user' as default")
                nova_role = "user"
            
            # Format for Nova's expected structure
            # Handle content formatting
            msg_text = content if isinstance(content, str) else json.dumps(content)
            formatted_messages.append({
                "role": nova_role,
                "text": msg_text
            })
        
        # Build the result with messages array
        result = {"messages": formatted_messages}
        
        # Add system prompts if present
        if system_prompts:
            result["system"] = system_prompts
        
        return result
    
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters specifically for Nova models using the Converse API format.
        
        [Design principles]
        - Nova-specific parameter mapping
        - Parameter validation and defaults
        - Support for Nova-specific features
        
        [Implementation details]
        - Maps standard parameters to Nova's inferenceConfig structure
        - Provides Nova-optimized defaults
        - Handles additional parameters like stopSequences
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Nova Converse API
        """
        # Nova uses inferenceConfig for parameters
        inference_config = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokens": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P)
        }
        
        # Add stop sequences if provided
        if "stop_sequences" in kwargs:
            inference_config["stopSequences"] = kwargs["stop_sequences"]
            
        # Return in Nova's expected format with inferenceConfig object
        return {"inferenceConfig": inference_config}
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Stream a conversational response from a Nova model.
        
        [Design principles]
        - Proper Nova API integration
        - Efficient streaming implementation
        - Correct error handling
        
        [Implementation details]
        - Formats messages for Nova's Converse API
        - Handles parameter formatting
        - Properly streams response chunks
        
        Args:
            messages: List of message dictionaries with role and content
            **kwargs: Additional parameters for the model
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        # Format messages and parameters for Nova
        formatted_payload = self._format_messages(messages)
        model_params = self._format_model_kwargs(kwargs)
        
        # Combine into full Nova payload
        formatted_payload.update(model_params)
        
        # Log the request if debug enabled
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Nova stream_chat payload: {json.dumps(formatted_payload)}")
        
        # Stream response from API
        try:
            # Use the ConverseStream API
            response_stream = await self.client.converse_stream(
                model_id=self.model_id,
                converse_mode="STREAMING",
                content_type="application/json",
                accept="application/json",
                body=json.dumps(formatted_payload)
            )
            
            # Initialize response processor
            processor = ConverseStreamProcessor(
                response_stream=response_stream,
                model_id=self.model_id
            )
            
            # Stream the response chunks
            async for chunk in processor.stream():
                yield chunk
                
        except Exception as e:
            # Map AWS errors to our exception types
            error = BedrockErrorMapper.map_error(e)
            self.logger.error(f"Error in stream_chat: {str(error)}")
            raise error

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
        
        [Implementation details]
        - Supports both text and media inputs (images/videos)
        - Properly encodes media for Nova's API
        - Uses streaming for efficient response handling
        
        Args:
            text: The text prompt
            images: Optional list of images (paths or bytes)
            videos: Optional list of videos (paths or bytes)
            **kwargs: Additional parameters for the model
            
        Yields:
            Dict[str, Any]: Response chunks from Nova
            
        Raises:
            ValueError: If model doesn't support multimodal inputs
            LLMError: If processing fails
        """
        # Only Pro, Premier, and Lite support multimodal inputs
        base_model_id = self.model_id.split(":")[0]
        if not any(mm in base_model_id for mm in ["nova-pro", "nova-premier", "nova-lite"]):
            raise ValueError(f"Model {self.model_id} does not support multimodal inputs")
        
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
        
        # Process videos if provided
        if videos:
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
        
        # Create message in Nova format
        formatted_payload = {
            "messages": [{
                "role": "user",
                "content": message_content
            }]
        }
        
        # Add model parameters
        model_params = self._format_model_kwargs(kwargs)
        formatted_payload.update(model_params)
        
        # Log the request if debug enabled
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Nova multimodal request prepared (content types: {[item['type'] for item in message_content]})")
        
        # Stream response
        try:
            # Use the ConverseStream API
            response_stream = await self.client.converse_stream(
                model_id=self.model_id,
                converse_mode="STREAMING",
                content_type="application/json",
                accept="application/json",
                body=json.dumps(formatted_payload)
            )
            
            # Initialize response processor
            processor = ConverseStreamProcessor(
                response_stream=response_stream,
                model_id=self.model_id
            )
            
            # Stream the response chunks
            async for chunk in processor.stream():
                yield chunk
                
        except Exception as e:
            # Map AWS errors to our exception types
            error = BedrockErrorMapper.map_error(e)
            self.logger.error(f"Error in multimodal processing: {str(error)}")
            raise error
    
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
    
    async def _handle_multimodal_content(
        self,
        content: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Process multimodal content through the Nova capabilities API.
        This is a handler for the MULTIMODAL capability.
        
        [Design principles]
        - Clean mapping to multimodal API
        - Support for both text and media inputs
        - Consistent streaming response
        
        [Implementation details]
        - Adapts the content format for process_multimodal_message
        - Extracts images and text from mixed content
        - Delegates to specialized processing method
        
        Args:
            content: Multimodal content to process
            **kwargs: Additional parameters
            
        Yields:
            Dict[str, Any]: Streaming response chunks
            
        Raises:
            ValueError: If content format is invalid
            LLMError: If processing fails
        """
        # Extract text and images based on content format
        text = ""
        images = []
        videos = []
        
        if isinstance(content, str):
            # Simple text input
            text = content
        elif isinstance(content, dict):
            # Structured input with text and possibly images
            if "text" in content:
                text = content["text"]
            if "images" in content:
                images = content["images"]
            if "videos" in content:
                videos = content["videos"]
        elif isinstance(content, list):
            # List of content blocks
            for item in content:
                if isinstance(item, str):
                    text += item + "\n"
                elif isinstance(item, dict):
                    if item.get("type") == "text":
                        text += item.get("text", "") + "\n"
                    elif item.get("type") == "image":
                        images.append(item.get("data"))
                    elif item.get("type") == "video":
                        videos.append(item.get("data"))
        else:
            raise ValueError(f"Unsupported content format: {type(content)}")
        
        # Process the multimodal content
        async for chunk in self.process_multimodal_message(
            text=text,
            images=images if images else None,
            videos=videos if videos else None,
            **kwargs
        ):
            yield chunk
    
    async def _handle_keyword_extraction(
        self,
        content: str,
        max_results: int = 10,
        **kwargs
    ) -> List[str]:
        """
        [Method intent]
        Extract keywords from text content through the capability API.
        This is a handler for the KEYWORD_EXTRACTION capability.
        
        [Design principles]
        - Clean mapping to keyword extraction API
        - Support for standard parameters
        - Direct result return
        
        [Implementation details]
        - Converts content format for extract_keywords
        - Handles parameter mapping
        - Returns structured keyword list
        
        Args:
            content: Text content to extract keywords from
            max_results: Maximum keywords to return
            **kwargs: Additional parameters
            
        Returns:
            List[str]: Extracted keywords
            
        Raises:
            ValueError: If content format is invalid
            LLMError: If extraction fails
        """
        if not isinstance(content, str):
            if isinstance(content, dict) and "text" in content:
                content = content["text"]
            else:
                raise ValueError("Keyword extraction requires text content")
                
        # Delegate to specialized method
        return await self.extract_keywords(
            text=content,
            max_results=max_results
        )
    
    async def _handle_summarization(
        self,
        content: str,
        max_length: int = 200,
        focus_on: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        [Method intent]
        Summarize text content through the capability API.
        This is a handler for the SUMMARIZATION capability.
        
        [Design principles]
        - Clean mapping to summarization API
        - Support for standard parameters
        - Direct result return
        
        [Implementation details]
        - Converts content format for summarize_text
        - Handles parameter mapping
        - Returns summarized text
        
        Args:
            content: Text content to summarize
            max_length: Maximum length of summary
            focus_on: Optional aspect to focus on
            **kwargs: Additional parameters
            
        Returns:
            str: Summarized text
            
        Raises:
            ValueError: If content format is invalid
            LLMError: If summarization fails
        """
        if not isinstance(content, str):
            if isinstance(content, dict) and "text" in content:
                content = content["text"]
            else:
                raise ValueError("Summarization requires text content")
                
        # Delegate to specialized method
        return await self.summarize_text(
            text=content,
            max_length=max_length,
            focus_on=focus_on
        )
    
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
