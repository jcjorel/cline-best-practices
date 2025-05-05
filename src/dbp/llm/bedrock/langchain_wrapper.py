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
# Provides an enhanced wrapper around LangChain's ChatBedrockConverse class with
# advanced error handling, automatic retries, and text extraction utilities to ensure
# reliable and clean communication with AWS Bedrock models.
###############################################################################
# [Source file design principles]
# - DRY implementation with minimal code duplication
# - Enhanced error handling beyond LangChain's default implementation
# - Unified error classification across sync and async operations
# - Transparent operation to LangChain users
# - Minimal method overrides for future compatibility
# - Clean text extraction for all model responses
###############################################################################
# [Source file constraints]
# - Must maintain full compatibility with LangChain's ChatBedrockConverse
# - Must handle all AWS Bedrock specific exceptions properly
# - Must integrate seamlessly with client_factory.py
# - Must preserve all LangChain functionality while enhancing reliability
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# system:asyncio
# system:functools
# system:inspect
# system:logging
# system:random
# system:time
# system:orjson
# system:langchain_aws.chat_models.bedrock_converse
###############################################################################
# [GenAI tool change history]
# 2025-05-05T15:25:36Z : Added text extraction and streaming methods by CodeAssistant
# * Added extract_text_from_chunk method for clean text extraction from any model responses
# * Implemented stream_text and astream_text methods for text-only streaming
# * Made text extraction model-agnostic (works with any model, not just Claude)
# 2025-05-05T13:20:00Z : Created EnhancedChatBedrockConverse wrapper by CodeAssistant
# * Implemented subclass of LangChain's ChatBedrockConverse with maximum DRY principles
# * Created unified error handling and retry mechanism for all methods
# * Used single-source error classifier for consistency
###############################################################################

import asyncio
import functools
import inspect
import logging
import random
import sys
import time
from typing import Any, Callable, ClassVar, Dict, List, Optional, TypeVar, Union, cast, AsyncIterator, Iterator

import botocore.exceptions
import orjson
from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseMessage

from ..common.exceptions import ClientError, InvocationError, LLMError, ModelNotAvailableError, StreamingError


# Type variables for generic functions
F = TypeVar('F', bound=Callable)


class EnhancedChatBedrockConverse(ChatBedrockConverse):
    """
    [Class intent]
    Extends ChatBedrockConverse to provide enhanced error handling, automatic retries,
    and clean text extraction for AWS Bedrock models across all provider types.
    
    [Design principles]
    - Minimal method overrides with decorator-based enhancement
    - Unified error classification for consistency
    - Automatic retry with configurable parameters
    - Model-agnostic text extraction
    
    [Implementation details]
    - Uses metaclass to apply enhancements to key methods
    - Maintains full compatibility with LangChain API
    - Handles both sync and async methods consistently
    - Provides specialized text-only streaming methods
    """

    # Default retry configuration
    DEFAULT_MAX_RETRIES: ClassVar[int] = 7
    DEFAULT_BASE_DELAY: ClassVar[float] = 10.0
    DEFAULT_MAX_DELAY: ClassVar[float] = 120.0
    
    def __init__(
        self,
        **kwargs
    ):
        """
        [Method intent]
        Initialize the enhanced ChatBedrockConverse with retry configuration.
        
        [Design principles]
        - Full compatibility with parent class
        - Simple parameter configuration
        
        [Implementation details]
        - Extracts and stores our custom parameters before passing the rest to parent
        - Sets up retry configuration as class attributes
        - Configures logging
        
        Args:
            **kwargs: All arguments for ChatBedrockConverse
        """
        # Extract our custom parameters from kwargs
        # This prevents them from being passed to parent class which would cause validation errors
        custom_params = {}
        for param in ['max_retries', 'base_delay', 'max_delay', 'logger']:
            if param in kwargs:
                custom_params[param] = kwargs.pop(param)
                
        # Initialize the parent class with cleaned kwargs
        super().__init__(**kwargs)
        
        # Get or create a logger
        logger = custom_params.get("logger", logging.getLogger(__name__))
        
        # Ensure the logger level is at least WARNING (higher number = less verbose)
        # If the level is NOTSET (0) or less than WARNING (30), set it to WARNING
        if logger.level < logging.WARNING or logger.level == 0:
            logger.setLevel(logging.WARNING)
            
        # Store our custom parameters in a separate dict to avoid Pydantic validation issues
        # Use Python's object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, "_retry_config", {
            "max_retries": custom_params.get("max_retries", self.DEFAULT_MAX_RETRIES),
            "base_delay": custom_params.get("base_delay", self.DEFAULT_BASE_DELAY),
            "max_delay": custom_params.get("max_delay", self.DEFAULT_MAX_DELAY),
            "logger": logger
        })

    def _classify_bedrock_error(self, error: botocore.exceptions.ClientError) -> Exception:
        """
        [Method intent]
        Classify AWS Bedrock errors into appropriate custom exceptions.
        
        [Design principles]
        - Single source of error classification
        - Consistent error handling across methods
        
        [Implementation details]
        - Maps AWS error codes to custom exceptions
        - Preserves original error message and exception
        - Returns appropriate exception instance
        
        Args:
            error: The original AWS ClientError
            
        Returns:
            Exception: The appropriate custom exception
        """
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        # Handle different types of AWS Bedrock errors
        if error_code == "AccessDeniedException":
            return ClientError(f"Access denied to Bedrock API: {error_message}", error)
        elif error_code == "ValidationException":
            return InvocationError(f"Invalid request to Bedrock API: {error_message}", error)
        elif error_code == "ThrottlingException" and "Too many requests" not in error_message:
            # "Too many requests" throttling is handled separately with retries
            return InvocationError(f"Request throttled by Bedrock: {error_message}", error)
        elif error_code == "ServiceQuotaExceededException":
            return InvocationError(f"Service quota exceeded: {error_message}", error)
        elif error_code == "ModelTimeoutException":
            return InvocationError(f"Model inference timeout: {error_message}", error)
        elif error_code == "ModelErrorException":
            return InvocationError(f"Model error during inference: {error_message}", error)
        elif error_code == "ModelNotReadyException":
            return ModelNotAvailableError(f"Model not ready: {error_message}", error)
        else:
            # Default case for unknown errors
            return LLMError(f"Bedrock API error: {error_code} - {error_message}", error)

    def _with_bedrock_retry(self, func: F) -> F:
        """
        [Method intent]
        Wrap a function with Bedrock throttling retry logic.
        
        [Design principles]
        - Handle both sync and async functions
        - Consistent retry behavior
        - Clear error propagation
        
        [Implementation details]
        - Detects function type at runtime
        - Applies appropriate retry logic
        - Handles throttling errors with exponential backoff
        
        Args:
            func: Function to wrap with retry logic
            
        Returns:
            Wrapped function with retry capability
        """
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            retry_count = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except botocore.exceptions.ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    
                    if error_code == "ThrottlingException" and "Too many requests" in error_message:
                        retry_count += 1
                        
                        max_retries = self._retry_config["max_retries"]
                        if retry_count <= max_retries:
                            # Calculate backoff with jitter
                            base_delay = self._retry_config["base_delay"]
                            max_delay = self._retry_config["max_delay"]
                            delay = min(max_delay, base_delay * (2 ** (retry_count - 1)))
                            jitter = random.uniform(0.8, 1.0)
                            delay_with_jitter = delay * jitter
                            
                            # Log retry attempt
                            logger = self._retry_config["logger"]
                            warning_msg = f"Request throttled: {error_message}. Retry {retry_count}/{max_retries} in {delay_with_jitter:.2f}s"
                            # Double log: once through the logger
                            logger.warning(warning_msg)
                            
                            # Wait before retry
                            time.sleep(delay_with_jitter)
                            continue
                    
                    # For non-throttling or max-retries-exceeded cases, classify and raise
                    if error_code == "ThrottlingException" and retry_count > self._retry_config["max_retries"]:
                        raise InvocationError(
                            f"Request throttled (max retries exceeded): {error_message}", 
                            e
                        )
                    
                    # For other AWS errors, classify and raise
                    raise self._classify_bedrock_error(e)
                except Exception as e:
                    # Pass through our custom exceptions
                    if isinstance(e, (ClientError, InvocationError, ModelNotAvailableError, LLMError)):
                        raise e
                    
                    # Wrap other exceptions
                    raise LLMError(f"Bedrock error: {str(e)}", e)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_count = 0
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except botocore.exceptions.ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    
                    if error_code == "ThrottlingException" and "Too many requests" in error_message:
                        retry_count += 1
                        
                        max_retries = self._retry_config["max_retries"]
                        if retry_count <= max_retries:
                            # Calculate backoff with jitter
                            base_delay = self._retry_config["base_delay"]
                            max_delay = self._retry_config["max_delay"]
                            delay = min(max_delay, base_delay * (2 ** (retry_count - 1)))
                            jitter = random.uniform(0.8, 1.0)
                            delay_with_jitter = delay * jitter
                            
                            # Log retry attempt
                            logger = self._retry_config["logger"]
                            warning_msg = f"Request throttled: {error_message}. Retry {retry_count}/{max_retries} in {delay_with_jitter:.2f}s" 
                            # Double log: once through the logger
                            logger.warning(warning_msg)
                            
                            # Async wait before retry
                            await asyncio.sleep(delay_with_jitter)
                            continue
                    
                    # For non-throttling or max-retries-exceeded cases, classify and raise
                    if error_code == "ThrottlingException" and retry_count > self._retry_config["max_retries"]:
                        raise InvocationError(
                            f"Request throttled (max retries exceeded): {error_message}", 
                            e
                        )
                    
                    # For other AWS errors, classify and raise
                    raise self._classify_bedrock_error(e)
                except Exception as e:
                    # Pass through our custom exceptions
                    if isinstance(e, (ClientError, InvocationError, ModelNotAvailableError, StreamingError)):
                        raise e
                    
                    # Wrap other exceptions - use StreamingError for async methods
                    raise StreamingError(f"Bedrock streaming error: {str(e)}", e)
        
        # Check if the function is a coroutine function
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    # Override key methods with retry-enhanced versions
    def _generate(self, *args, **kwargs):
        return self._with_bedrock_retry(super()._generate)(*args, **kwargs)
    
    def _agenerate(self, *args, **kwargs):
        return self._with_bedrock_retry(super()._agenerate)(*args, **kwargs)
    
    def _stream(self, *args, **kwargs):
        return self._with_bedrock_retry(super()._stream)(*args, **kwargs)
    
    def _astream(self, *args, **kwargs):
        return self._with_bedrock_retry(super()._astream)(*args, **kwargs)
        
    @staticmethod
    def extract_text_from_chunk(content):
        """
        [Method intent]
        Extract clean text content from any model's streaming response chunks in any format.
        
        [Design principles]
        - Handle any response format from any model (dict, string, list)
        - Skip metadata-only chunks that don't contain actual text content
        - Use orjson for high-performance JSON parsing when needed
        - Pure functional approach with no side effects
        
        [Implementation details]
        - Handles dictionary, string, and list formats directly
        - Detects and processes JSON string representations
        - Skips metadata-only chunks (e.g., {'index': 0})
        - Provides robust extraction with minimal error risk
        
        Args:
            content: Content from model in any format (dict, string, list)
            
        Returns:
            str: Clean text content without JSON structure or empty string if no text content
        """
        # Handle empty content
        if not content:
            return ""
        
        # Handle list content by processing each item
        if isinstance(content, list):
            result = ""
            for item in content:
                if item is not None:
                    result += EnhancedChatBedrockConverse.extract_text_from_chunk(item)
            return result
        
        # Handle dictionary content
        if isinstance(content, dict):
            # Check for text field (used by many models)
            if "text" in content:
                return content["text"]
            # Check for content field (used by some models)
            elif "content" in content:
                return content["content"]
            # For Amazon models using 'completion' field
            elif "completion" in content:
                return content["completion"]
            # For Anthropic models using 'delta' structure
            elif "delta" in content and isinstance(content["delta"], dict):
                if "text" in content["delta"]:
                    return content["delta"]["text"]
                elif "content" in content["delta"]:
                    return content["delta"]["content"]
            return ""
        
        # Handle string content
        if isinstance(content, str):
            # If it looks like a JSON object, try to parse it
            if content.startswith("{") and content.endswith("}"):
                try:
                    # Convert Python dict notation to proper JSON if needed
                    json_content = content.replace("'", '"')
                    parsed_dict = orjson.loads(json_content)
                    
                    # Use recursive call to handle the parsed dictionary
                    return EnhancedChatBedrockConverse.extract_text_from_chunk(parsed_dict)
                except Exception:
                    # If parsing fails, return original content
                    return content
            return content
        
        # For any other type, convert to string and return
        return str(content) if content is not None else ""
        
    def stream_text(self, messages: List[BaseMessage], **kwargs) -> Iterator[str]:
        """
        [Method intent]
        Stream clean text responses from the model without additional metadata or structure.
        
        [Design principles]
        - Provide a simpler interface for text-only responses
        - Filter out non-text elements from responses
        - Maintain compatibility with LangChain's stream method
        
        [Implementation details]
        - Wraps the standard stream method
        - Uses extract_text_from_chunk to get clean text
        - Returns a generator yielding only text strings
        
        Args:
            messages: List of BaseMessage objects representing conversation history
            **kwargs: Additional arguments to pass to the model
            
        Returns:
            Iterator[str]: A generator yielding clean text strings
            
        Raises:
            Same exceptions as the underlying stream method
        """
        for chunk in self.stream(messages, **kwargs):
            content = chunk.content
            clean_text = self.extract_text_from_chunk(content)
            if clean_text:
                yield clean_text
    
    async def astream_text(self, messages: List[BaseMessage], **kwargs) -> AsyncIterator[str]:
        """
        [Method intent]
        Asynchronously stream clean text responses from the model without additional metadata or structure.
        
        [Design principles]
        - Provide a simpler interface for text-only responses
        - Filter out non-text elements from responses
        - Maintain compatibility with LangChain's astream method
        
        [Implementation details]
        - Wraps the standard astream method
        - Uses extract_text_from_chunk to get clean text
        - Returns an async generator yielding only text strings
        
        Args:
            messages: List of BaseMessage objects representing conversation history
            **kwargs: Additional arguments to pass to the model
            
        Returns:
            AsyncIterator[str]: An async generator yielding clean text strings
            
        Raises:
            Same exceptions as the underlying astream method
        """
        async for chunk in self.astream(messages, **kwargs):
            content = chunk.content
            clean_text = self.extract_text_from_chunk(content)
            if clean_text:
                yield clean_text
