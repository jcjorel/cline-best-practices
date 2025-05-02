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
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:22:00Z : Implemented for LangChain/LangGraph integration by CodeAssistant
# * Created NovaClient for Amazon Titan models
# * Implemented Converse API with async/streaming support
# * Added Nova-specific parameter handling and response formatting
# * Added model validation for Nova model variants
# 2025-05-02T10:49:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created placeholder for Nova model implementation
###############################################################################

"""
Amazon Bedrock Nova model implementation.
"""

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


class NovaClient(BedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Nova (Amazon Titan) models.
    This client adds Nova-specific features and parameter handling while
    maintaining the streaming-focused approach.
    
    [Design principles]
    - Nova-specific parameter optimization
    - Specialized message formatting for Nova models
    - Clean extension of BedrockBase
    - Streaming-only interface
    
    [Implementation details]
    - Supports all Nova model variants
    - Implements Nova-specific parameter mapping
    - Optimizes default parameters for Nova
    - Handles Nova's response format
    """
    
    # Supported Nova models - helps with validation
    _NOVA_MODELS = [
        "amazon.titan-text-lite-v1",
        "amazon.titan-text-express-v1",
        "amazon.titan-embed-text-v1",
        "amazon.titan-text-premier-v1",
        "amazon.titan-tg1-medium",
        "amazon.titan-tg1-lite"
    ]
    
    # Default Nova parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TOP_P = 0.9
    DEFAULT_TOP_K = 250
    
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
        is_nova_model = any(base_model_id.startswith(model) for model in self._NOVA_MODELS)
        
        if not is_nova_model:
            raise ValueError(f"Model {model_id} is not a supported Nova model")
        
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
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Nova models.
        
        [Design principles]
        - Nova-specific message formatting
        - Support for system messages
        - Handle content format variations
        
        [Implementation details]
        - Properly formats system messages for Nova
        - Handles content blocks for different content types
        - Ensures proper message role mapping
        
        Args:
            messages: List of message objects in standard format
            
        Returns:
            List[Dict[str, Any]]: Messages formatted for Nova API
        """
        formatted_messages = []
        system_message = None
        
        # First pass to find system message if present
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"])
                break
        
        # Now process all messages
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Skip system message as we'll handle it separately
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
            
            # Format for Nova's expected structure
            formatted_msg = {"role": nova_role}
            
            # Handle content formatting
            if isinstance(content, str):
                formatted_msg["content"] = content
            else:
                # Currently Nova doesn't support complex content, convert to string
                try:
                    formatted_msg["content"] = json.dumps(content)
                except (TypeError, ValueError):
                    self.logger.warning(f"Failed to convert complex content to string for Nova, using str() fallback")
                    formatted_msg["content"] = str(content)
            
            formatted_messages.append(formatted_msg)
        
        # If we have a system message, add it as a special message at the beginning
        if system_message:
            # Nova expects system prompts to be included with the first user message
            # Check if we have a user message we can prepend to
            for msg in formatted_messages:
                if msg["role"] == "user":
                    # Prepend system message to the first user message
                    msg["content"] = f"[SYSTEM]\n{system_message}\n\n[USER]\n{msg['content']}"
                    break
            else:
                # No user message found, add one
                formatted_messages.insert(0, {
                    "role": "user",
                    "content": f"[SYSTEM]\n{system_message}\n\n[USER]\nHello"
                })
        
        return formatted_messages
    
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters specifically for Nova models.
        
        [Design principles]
        - Nova-specific parameter mapping
        - Parameter validation and defaults
        - Support for Nova-specific features
        
        [Implementation details]
        - Maps standard parameters to Nova-specific names
        - Adds Nova-specific parameters
        - Provides Nova-optimized defaults
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Nova API
        """
        # Start with basic parameters
        formatted_kwargs = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokenCount": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P),
        }
        
        # Add Nova-specific parameters
        if "top_k" in kwargs:
            formatted_kwargs["topK"] = int(kwargs["top_k"])
        else:
            formatted_kwargs["topK"] = self.DEFAULT_TOP_K
            
        if "stop_sequences" in kwargs:
            formatted_kwargs["stopSequences"] = kwargs["stop_sequences"]
            
        # Handle additional Nova parameters
        if "return_likelihood" in kwargs:
            formatted_kwargs["returnLikelihood"] = kwargs["return_likelihood"]
            
        if "do_sample" in kwargs:
            formatted_kwargs["doSample"] = bool(kwargs["do_sample"])
            
        if "typical_p" in kwargs:
            formatted_kwargs["typicalP"] = float(kwargs["typical_p"])
            
        return formatted_kwargs
    
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
