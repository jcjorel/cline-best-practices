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
# - KISS principle: Keep implementation simple and maintainable
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
# system:logging
# system:random
# system:time
# system:orjson
# system:langchain_aws.chat_models.bedrock_converse
###############################################################################
# [GenAI tool change history]
# 2025-05-05T23:08:00Z : Removed extract_text_from_chunk static method by CodeAssistant
# * Completely removed the static extract_text_from_chunk method
# * Now relying exclusively on model-specific _extract_text_from_chunk implementations
# * Ensures clean separation of concerns with model-specific text extraction
# * Each model family now fully responsible for handling its own response format
# 2025-05-05T22:58:00Z : Made class abstract with abstract extract_text method by CodeAssistant
# * Made EnhancedChatBedrockConverse an abstract class using abc.ABC
# * Changed _extract_text_from_chunk to an abstract instance method
# * Removed the mixed implementation within base class
# * Updated to force model-specific subclasses to implement their own extraction logic
# 2025-05-05T22:14:12Z : Added model-specific text extraction hook by CodeAssistant
# * Added _extract_text_from_chunk class method as a customization point for model-specific implementations
# * Updated astream, stream_text, and astream_text to use the new hook method
# * Preserved original extract_text_from_chunk static method for backwards compatibility
# * Improved separation of concerns for model-specific text extraction
# 2025-05-05T16:59:08Z : Simplified implementation with KISS principle by CodeAssistant
# * Applied direct retry logic in stream/astream methods for better readability
# * Removed complex wrappers and middleware functions
# * Improved extract_text_from_chunk to handle LangChain objects
# 2025-05-05T15:25:36Z : Added text extraction and streaming methods by CodeAssistant
# * Added extract_text_from_chunk method for clean text extraction from any model responses
# * Implemented stream_text and astream_text methods for text-only streaming
# * Made text extraction model-agnostic (works with any model, not just Claude)
###############################################################################

import asyncio
import abc
import logging
import random
import time
from typing import Any, Dict, List, Iterator, AsyncIterator, ClassVar

import botocore.exceptions
import orjson
from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
from langchain_core.language_models.chat_models import BaseMessage
from langchain_core.messages import AIMessageChunk

from ..common.exceptions import ClientError, InvocationError, LLMError, ModelNotAvailableError, StreamingError


class EnhancedChatBedrockConverse(ChatBedrockConverse, abc.ABC):
    """
    [Class intent]
    Extends ChatBedrockConverse to provide enhanced error handling, automatic retries,
    and clean text extraction for AWS Bedrock models across all provider types.
    
    [Design principles]
    - KISS: Keep It Simple & Stupid - simple, maintainable implementation
    - Direct method overrides with clear retry logic
    - Unified error classification for consistency
    - Model-agnostic text extraction
    
    [Implementation details]
    - Directly overrides key methods with retry logic
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
        max_retries = kwargs.pop('max_retries', self.DEFAULT_MAX_RETRIES)
        base_delay = kwargs.pop('base_delay', self.DEFAULT_BASE_DELAY)
        max_delay = kwargs.pop('max_delay', self.DEFAULT_MAX_DELAY)
        logger = kwargs.pop('logger', logging.getLogger(__name__))
                
        # Initialize the parent class with cleaned kwargs
        super().__init__(**kwargs)
        
        # Ensure the logger level is at least WARNING
        if logger.level < logging.WARNING or logger.level == 0:
            logger.setLevel(logging.WARNING)
        
        # Set retry configuration directly as instance attributes using model_extra to avoid Pydantic validation
        # These attributes are not part of the model schema
        object.__setattr__(self, "max_retries", max_retries)
        object.__setattr__(self, "base_delay", base_delay)
        object.__setattr__(self, "max_delay", max_delay)
        object.__setattr__(self, "logger", logger)
                    
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
   
    def stream(self, messages, **kwargs):
        """
        [Method intent]
        Override LangChain's stream method with built-in throttling retry logic.
        
        [Design principles]
        - Direct implementation of retry logic
        - Simple exponential backoff with jitter
        - Clear error handling and classification
        
        [Implementation details]
        - Sets boto3 retry count to 3
        - Implements retry logic for throttling exceptions
        - Handles all Bedrock errors with appropriate classification
        - Properly delegates to parent implementation
        
        Args:
            messages: List of chat messages
            **kwargs: Keyword arguments for the model
            
        Returns:
            Iterator yielding model responses
            
        Raises:
            Various exception types based on the specific error encountered
        """
        
        retry_count = 0
        
        while True:
            try:
                # Call parent implementation
                return super().stream(messages, **kwargs)
                
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code == "ThrottlingException" and "Too many requests" in error_message:
                    retry_count += 1
                    
                    if retry_count <= self.max_retries:
                        # Calculate backoff with jitter
                        delay = min(self.max_delay, self.base_delay * (2 ** (retry_count - 1)))
                        jitter = random.uniform(0.8, 1.0)
                        delay_with_jitter = delay * jitter
                        
                        # Log retry attempt
                        warning_msg = f"Request throttled: {error_message}. Retry {retry_count}/{self.max_retries} in {delay_with_jitter:.2f}s"
                        self.logger.warning(warning_msg)
                        
                        # Wait before retry
                        time.sleep(delay_with_jitter)
                        continue
                
                # For non-throttling or max-retries-exceeded cases, classify and raise
                if error_code == "ThrottlingException" and retry_count > self.max_retries:
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

    async def astream(self, messages, **kwargs):
        """
        [Method intent]
        Override LangChain's astream method with built-in throttling retry logic.
        
        [Design principles]
        - Direct implementation of retry logic for async operations
        - Simple exponential backoff with jitter
        - Clear error handling and classification
        
        [Implementation details]
        - Sets boto3 retry count to 3
        - Implements retry logic for throttling exceptions
        - Uses async sleep for waiting between retries
        - Properly delegates to parent implementation as an async generator
        
        Args:
            messages: List of chat messages
            **kwargs: Keyword arguments for the model
            
        Returns:
            AsyncIterator yielding model responses
            
        Raises:
            Various exception types based on the specific error encountered
        """
        
        retry_count = 0
        
        while True:
            try:
                # Get parent's async generator - don't await it directly
                parent_generator = super()._astream(
                    messages=messages,
                    stop=kwargs.get("stop"),
                    run_manager=kwargs.get("run_manager"),
                    **kwargs
                )
                
                # Process each chunk as they come through the generator
                async for chunk in parent_generator:
                    # Extract text using model-specific implementation
                    text_content = self._extract_text_from_chunk(chunk)
                    yield AIMessageChunk(content=text_content)
                
                # Exit the retry loop once complete
                return
                
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code == "ThrottlingException" and "Too many requests" in error_message:
                    retry_count += 1
                    
                    if retry_count <= self.max_retries:
                        # Calculate backoff with jitter
                        delay = min(self.max_delay, self.base_delay * (2 ** (retry_count - 1)))
                        jitter = random.uniform(0.8, 1.0)
                        delay_with_jitter = delay * jitter
                        
                        # Log retry attempt
                        warning_msg = f"Request throttled: {error_message}. Retry {retry_count}/{self.max_retries} in {delay_with_jitter:.2f}s"
                        self.logger.warning(warning_msg)
                        
                        # Wait before retry (async)
                        await asyncio.sleep(delay_with_jitter)
                        continue
                
                # For non-throttling or max-retries-exceeded cases, classify and raise
                if error_code == "ThrottlingException" and retry_count > self.max_retries:
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
                
                # Wrap other exceptions with StreamingError for async methods
                raise StreamingError(f"Bedrock streaming error: {str(e)}", e)
        
    @abc.abstractmethod
    def _extract_text_from_chunk(self, content):
        """
        [Method intent]
        Model-specific text extraction hook. This abstract method must be implemented
        by model-specific subclasses to provide specialized text extraction.
        
        [Design principles]
        - Model-specific implementation hook
        - Clean separation of concerns
        - Each model family implements its own extraction logic
        
        [Implementation details]
        - Must be implemented by each subclass
        - Should follow model-specific response format documentation
        - Should extract only the text content without metadata
        
        Args:
            content: Content from model in any format
            
        Returns:
            str: Clean text content without structure
        """
        pass
        
    def stream_text(self, messages: List[BaseMessage], **kwargs) -> Iterator[str]:
        """
        [Method intent]
        Stream clean text responses from the model without additional metadata or structure.
        
        [Design principles]
        - Provide a simpler interface for text-only responses
        - Filter out non-text elements from responses
        - Maintain compatibility with LangChain's stream method
        
        [Implementation details]
        - Uses the enhanced stream method with retry logic
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
            clean_text = self._extract_text_from_chunk(content)
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
        - Uses the enhanced astream method with retry logic
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
            clean_text = self._extract_text_from_chunk(content)
            if clean_text:
                yield clean_text
