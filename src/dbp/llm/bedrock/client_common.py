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
# Provides common utilities and functions for Amazon Bedrock clients that are
# shared across different model implementations. This includes response and
# request formatting, streaming response processing, and error mapping that
# are specific to the Bedrock Converse API but not tied to a particular model.
###############################################################################
# [Source file design principles]
# - Clean separation of common functionality from model-specific code
# - Consistent error handling and response processing
# - Utilities for working with streaming responses
# - Reusable components for all Bedrock model clients
# - Support for asynchronous operations
# - Standardized message and response formats
###############################################################################
# [Source file constraints]
# - Must not contain model-specific parameters or logic
# - Must be compatible with all Bedrock foundation models
# - Must focus only on common functionality
# - Must support the Converse API format
# - Must maintain stateless utilities
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/llm/common/streaming.py
# codebase:src/dbp/llm/bedrock/base.py
# system:json
# system:asyncio
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:16:00Z : Enhanced for LangChain/LangGraph integration by CodeAssistant
# * Implemented Converse API response processing
# * Added async streaming helpers
# * Created standardized format conversion utilities
# * Added specialized error mapping
# 2025-05-02T07:15:00Z : Refactored and moved to bedrock directory by Cline
# * Relocated from src/dbp/llm/bedrock_client_common.py to current location
# * Updated imports to reflect new directory structure
###############################################################################

"""
Common utilities for Amazon Bedrock clients using the Converse API.
"""

import json
import asyncio
from typing import Dict, Any, List, AsyncIterator, Optional, Union, Callable, Tuple

from ..common.exceptions import (
    LLMError, ClientError, ModelNotAvailableError, 
    InvocationError, StreamingError, AuthenticationError, 
    RateLimitError
)
from ..common.streaming import StreamingResponse, TextStreamingResponse


class ConverseStreamProcessor:
    """
    [Class intent]
    Processes and transforms Bedrock Converse API streaming responses into
    standardized formats. This class handles the conversion of raw Bedrock
    response events into structured data or text streams.
    
    [Design principles]
    - Clean transformation of raw API responses
    - Support for different output formats
    - Consistent event processing
    - Support for text and structured output
    
    [Implementation details]
    - Processes messageStart, contentBlockStart, contentBlockDelta events
    - Accumulates content for complete message reconstruction
    - Maps between different response formats
    - Handles stop reasons correctly
    """
    
    @staticmethod
    async def process_to_text(stream: AsyncIterator[Dict[str, Any]]) -> AsyncIterator[str]:
        """
        [Method intent]
        Process a Converse stream into a simple text stream, yielding
        only text chunks as they arrive.
        
        [Design principles]
        - Simple text-only output
        - Clean streaming interface
        - Easy integration with text-based consumers
        
        [Implementation details]
        - Extracts text from contentBlockDelta events
        - Skips all metadata and control events
        - Yields raw text chunks
        
        Args:
            stream: Raw stream from Bedrock Converse API
            
        Yields:
            str: Individual text chunks
            
        Raises:
            StreamingError: If processing fails
        """
        try:
            async for event in stream:
                if "contentBlockDelta" in event and "delta" in event["contentBlockDelta"]:
                    delta = event["contentBlockDelta"]["delta"]
                    if "text" in delta:
                        yield delta["text"]
        except Exception as e:
            raise StreamingError(f"Error processing stream to text: {str(e)}", e)
    
    @staticmethod
    async def process_to_langchain_deltas(stream: AsyncIterator[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Process a Converse stream into a format compatible with LangChain,
        using a delta-based format similar to OpenAI's streaming format.
        
        [Design principles]
        - LangChain compatibility
        - Structured delta events
        - Metadata preservation
        
        [Implementation details]
        - Converts Bedrock events to LangChain delta format
        - Includes role information
        - Preserves stop reason data
        
        Args:
            stream: Raw stream from Bedrock Converse API
            
        Yields:
            Dict[str, Any]: LangChain compatible delta chunks
            
        Raises:
            StreamingError: If processing fails
        """
        try:
            # Track complete message to reconstruct finish reason
            complete_message = None
            role = None
            
            # Process all events
            async for event in stream:
                # Handle message start (role)
                if "messageStart" in event:
                    role = event["messageStart"].get("role")
                    yield {
                        "choices": [{
                            "delta": {"role": role},
                            "finish_reason": None,
                            "index": 0
                        }]
                    }
                
                # Handle content delta (text)
                elif "contentBlockDelta" in event and "delta" in event["contentBlockDelta"]:
                    delta = event["contentBlockDelta"]["delta"]
                    if "text" in delta:
                        yield {
                            "choices": [{
                                "delta": {"content": delta["text"]},
                                "finish_reason": None,
                                "index": 0
                            }]
                        }
                
                # Handle message stop (finish reason)
                elif "messageStop" in event:
                    stop_reason = event["messageStop"].get("stopReason")
                    # Map Bedrock stop reasons to LangChain/OpenAI format
                    finish_reason = "stop"
                    if stop_reason == "MAX_TOKENS":
                        finish_reason = "length"
                    elif stop_reason == "CONTENT_FILTERED":
                        finish_reason = "content_filter"
                        
                    yield {
                        "choices": [{
                            "delta": {},
                            "finish_reason": finish_reason,
                            "index": 0
                        }]
                    }
        except Exception as e:
            raise StreamingError(f"Error processing stream to LangChain deltas: {str(e)}", e)
    
    @staticmethod
    async def accumulate_complete_response(stream: AsyncIterator[Dict[str, Any]]) -> Dict[str, Any]:
        """
        [Method intent]
        Accumulate all chunks from a Converse stream to build a complete
        response, including full text and metadata.
        
        [Design principles]
        - Complete response reconstruction
        - Preservation of all metadata
        - Synchronous return for non-streaming use cases
        
        [Implementation details]
        - Collects and accumulates all response text
        - Tracks metadata like role and stop reason
        - Returns a structured complete response
        
        Args:
            stream: Raw stream from Bedrock Converse API
            
        Returns:
            Dict[str, Any]: Complete response with full content
            
        Raises:
            LLMError: If accumulation fails
        """
        try:
            result = {
                "role": None,
                "content": "",
                "stop_reason": None,
                "model_id": None
            }
            
            async for event in stream:
                # Handle message start (role)
                if "messageStart" in event:
                    result["role"] = event["messageStart"].get("role")
                    if "modelId" in event["messageStart"]:
                        result["model_id"] = event["messageStart"].get("modelId")
                
                # Handle content delta (text)
                elif "contentBlockDelta" in event and "delta" in event["contentBlockDelta"]:
                    delta = event["contentBlockDelta"]["delta"]
                    if "text" in delta:
                        result["content"] += delta["text"]
                
                # Handle message stop (finish reason)
                elif "messageStop" in event:
                    result["stop_reason"] = event["messageStop"].get("stopReason")
            
            return result
        except Exception as e:
            raise LLMError(f"Error accumulating complete response: {str(e)}", e)


class BedrockMessageConverter:
    """
    [Class intent]
    Converts between different message formats for the Bedrock Converse API.
    This includes transformations between standard chat formats and the
    specific format required by Bedrock's API.
    
    [Design principles]
    - Flexible format conversions
    - Support for multiple input formats
    - Clean handling of content structures
    - Preservation of message semantics
    
    [Implementation details]
    - Converts between message formats
    - Handles content structure variations
    - Supports text and structured content
    """
    
    @staticmethod
    def to_bedrock_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Convert standard message format to Bedrock Converse API format.
        
        [Design principles]
        - Consistent format conversion
        - Support for various input structures
        - Reliable handling of edge cases
        
        [Implementation details]
        - Converts text content to required content blocks
        - Preserves role information
        - Handles both string and structured content
        
        Args:
            messages: Standard message list with role/content pairs
            
        Returns:
            List[Dict[str, Any]]: Messages formatted for Bedrock API
        """
        return [
            {
                "role": msg["role"],
                "content": [
                    {
                        "text": msg["content"]
                    }
                ] if isinstance(msg["content"], str) else msg["content"]
            }
            for msg in messages
        ]
    
    @staticmethod
    def from_bedrock_message(message: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Convert a Bedrock Converse API message to standard format.
        
        [Design principles]
        - Clean conversion to standard format
        - Text content extraction
        - Structured content handling
        
        [Implementation details]
        - Extracts text from content blocks
        - Preserves role information
        - Handles structured content
        
        Args:
            message: Bedrock API message format
            
        Returns:
            Dict[str, Any]: Standard message with role/content
        """
        role = message.get("role", "assistant")
        content_blocks = message.get("content", [])
        
        # Extract text from content blocks
        if content_blocks:
            # Simple case: just one text block
            if len(content_blocks) == 1 and "text" in content_blocks[0]:
                return {
                    "role": role,
                    "content": content_blocks[0]["text"]
                }
            else:
                # Multiple blocks or non-text content
                content = []
                for block in content_blocks:
                    if "text" in block:
                        content.append(block["text"])
                    else:
                        # Keep structured content as-is
                        content.append(block)
                
                # If all content is text, join it
                if all(isinstance(c, str) for c in content):
                    return {
                        "role": role,
                        "content": "".join(content)
                    }
                # Otherwise, keep the structured format
                return {
                    "role": role,
                    "content": content
                }
        else:
            # Empty content
            return {
                "role": role,
                "content": ""
            }


class BedrockErrorMapper:
    """
    [Class intent]
    Maps Bedrock API errors to consistent exception types used in the
    application. This ensures that API-specific errors are translated to
    meaningful exceptions with detailed information.
    
    [Design principles]
    - Consistent error classification
    - Detailed error information
    - Clean error handling interface
    
    [Implementation details]
    - Maps error codes to exception types
    - Provides context for debugging
    - Handles all known error codes
    """
    
    @staticmethod
    def map_api_error(error_code: str, error_message: str, original_error: Exception) -> Exception:
        """
        [Method intent]
        Map a Bedrock API error to an appropriate exception type.
        
        [Design principles]
        - Consistent error mappings
        - Classification of error types
        - Clear error messages
        
        [Implementation details]
        - Maps known error codes to specific exceptions
        - Includes original error as cause
        - Provides descriptive messages
        
        Args:
            error_code: Bedrock API error code
            error_message: Error message from the API
            original_error: The original exception
            
        Returns:
            Exception: Mapped exception with appropriate type
        """
        if error_code == "AccessDeniedException":
            return AuthenticationError(f"Access denied to Bedrock API: {error_message}", original_error)
        elif error_code == "ValidationException":
            return InvocationError(f"Invalid request to Bedrock API: {error_message}", original_error)
        elif error_code == "ThrottlingException":
            return RateLimitError(f"Request throttled by Bedrock API: {error_message}", original_error)
        elif error_code == "ServiceQuotaExceededException":
            return RateLimitError(f"Service quota exceeded: {error_message}", original_error)
        elif error_code == "ModelTimeoutException":
            return InvocationError(f"Model inference timeout: {error_message}", original_error)
        elif error_code == "ModelErrorException":
            return InvocationError(f"Model error during inference: {error_message}", original_error)
        elif error_code == "ModelNotReadyException":
            return ModelNotAvailableError(f"Model not ready: {error_message}", original_error)
        elif error_code == "ResourceNotFoundException":
            return ModelNotAvailableError(f"Resource not found: {error_message}", original_error)
        else:
            return LLMError(f"Bedrock API error: {error_code} - {error_message}", original_error)


class InferenceParameterFormatter:
    """
    [Class intent]
    Formats inference parameters for the Bedrock Converse API, handling
    the conversion from standard parameter names to API-specific formats.
    
    [Design principles]
    - Consistent parameter formatting
    - Support for different parameter sets
    - Parameter validation
    
    [Implementation details]
    - Maps standard parameters to API formats
    - Provides sensible defaults
    - Validates parameter combinations
    """
    
    @staticmethod
    def format_common_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format common parameters for the Bedrock Converse API.
        
        [Design principles]
        - Consistent parameter formatting
        - Parameter name normalization
        - Support for all common parameters
        
        [Implementation details]
        - Converts parameter names to API format
        - Provides sensible defaults
        - Handles type conversions
        
        Args:
            params: Parameters with standard names
            
        Returns:
            Dict[str, Any]: Parameters formatted for Bedrock API
        """
        # Common parameter mapping
        result = {}
        
        # Map common parameters
        if "temperature" in params:
            result["temperature"] = float(params["temperature"])
            
        if "max_tokens" in params:
            result["maxTokens"] = int(params["max_tokens"])
            
        if "top_p" in params:
            result["topP"] = float(params["top_p"])
            
        if "top_k" in params:
            result["topK"] = int(params["top_k"])
            
        if "stop_sequences" in params:
            result["stopSequences"] = params["stop_sequences"]
            
        return result
