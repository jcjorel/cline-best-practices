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
# Implements an enhanced base interface for all Bedrock models that unifies 
# capabilities across different model families while preserving their specialized
# features. This interface enables consistent interaction with diverse models 
# like Claude and Nova through a common API layer.
###############################################################################
# [Source file design principles]
# - Unified core API with model-agnostic interfaces
# - Feature capability discovery and adaptation
# - Consistent streaming pattern across all methods
# - Support for multimodal and reasoning capabilities
# - Clean extension of BedrockBase
# - Backward compatibility with existing clients
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with all Bedrock model families
# - Must preserve specialized features of each model type
# - Must handle capability differences gracefully
# - Must be fully asynchronous
# - Must support streaming as the primary interface
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/base.py
# codebase:src/dbp/llm/common/streaming.py
# codebase:src/dbp/llm/common/exceptions.py
# system:typing
# system:asyncio
# system:json
# system:enum
###############################################################################
# [GenAI tool change history]
# 2025-05-04T11:22:00Z : Implemented prompt caching API methods by CodeAssistant
# * Added enable_prompt_caching method to toggle caching
# * Added is_prompt_caching_enabled method to check caching status
# * Added mark_cache_point method to mark caching points in conversations
# * Enhanced stream_chat method to use caching configuration
# 2025-05-04T10:34:00Z : Added prompt caching capability by CodeAssistant
# * Added PROMPT_CACHING to ModelCapability enum
# * Enables capability-based detection and registration for prompt caching
# * Part of implementation for Bedrock prompt caching support
# 2025-05-03T08:50:00Z : Moved _process_converse_stream to BedrockBase by CodeAssistant
# * Moved method to parent class to make it available to all Bedrock clients
# * Maintained consistent stream processing functionality
# * Ensures standardized handling of Bedrock streams across all implementations
# 2025-05-02T13:02:00Z : Created enhanced base interface for Bedrock models by CodeAssistant
# * Implemented unified API for different model capabilities
# * Added capability discovery and registration system
# * Created common interfaces for specialized features
# * Added backward compatibility adapters
###############################################################################

import logging
import json
import asyncio
import enum
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Set, Callable, Type, TypeVar

from .base import BedrockBase
from ..common.streaming import StreamingResponse, TextStreamingResponse, IStreamable
from ..common.exceptions import LLMError, InvocationError, UnsupportedFeatureError


class ModelCapability(str, enum.Enum):
    """
    [Class intent]
    Defines standard capability identifiers for model features to enable
    consistent capability checking across different model implementations.
    
    [Design principles]
    - Standardized capability naming
    - Enum-based for type safety
    - Comprehensive coverage of model features
    
    [Implementation details]
    - String enum for easy serialization
    - Structured by capability category
    """
    
    # Core capabilities
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    SYSTEM_PROMPT = "system_prompt"
    
    # Content handling capabilities
    TEXT_INPUT = "text_input"
    TEXT_OUTPUT = "text_output"
    IMAGE_INPUT = "image_input"
    IMAGE_OUTPUT = "image_output"
    VIDEO_INPUT = "video_input"
    VIDEO_OUTPUT = "video_output"
    
    # Processing capabilities
    REASONING = "reasoning"
    STRUCTURED_OUTPUT = "structured_output"
    KEYWORD_EXTRACTION = "keyword_extraction"
    SUMMARIZATION = "summarization"
    
    # Advanced features
    MULTIMODAL = "multimodal"
    VISION = "vision"
    RAG = "retrieval_augmented_generation"
    PROMPT_CACHING = "prompt_caching"  # New capability for prompt caching


# Type variable for callback function parameter types
T = TypeVar('T')


class CapabilityRegistry:
    """
    [Class intent]
    Manages model capabilities and handles capability-based method dispatch,
    allowing models to register their supported features and providing a way 
    to access capability-specific methods.
    
    [Design principles]
    - Centralized capability management
    - Dynamic method registration and dispatch
    - Type-safe interface
    
    [Implementation details]
    - Maintains sets of capabilities per model
    - Maps capabilities to handler methods
    - Provides helper methods for capability checking
    """
    
    def __init__(self):
        """
        [Method intent]
        Initialize the capability registry with empty collections.
        
        [Design principles]
        - Clean initialization
        - Prepare data structures for capability registration
        
        [Implementation details]
        - Sets up capability set
        - Creates empty handler maps
        """
        self._capabilities: Set[ModelCapability] = set()
        self._handlers: Dict[ModelCapability, Callable] = {}
    
    def register_capability(self, capability: ModelCapability) -> None:
        """
        [Method intent]
        Register a capability as supported by the model.
        
        [Design principles]
        - Simple capability declaration
        - Idempotent registration
        
        [Implementation details]
        - Adds capability to the supported set
        - No effect if already registered
        
        Args:
            capability: The capability to register
        """
        self._capabilities.add(capability)
    
    def register_capabilities(self, capabilities: List[ModelCapability]) -> None:
        """
        [Method intent]
        Register multiple capabilities at once.
        
        [Design principles]
        - Batch capability registration
        - Convenience method
        
        [Implementation details]
        - Adds all capabilities to the supported set
        
        Args:
            capabilities: List of capabilities to register
        """
        for capability in capabilities:
            self.register_capability(capability)
    
    def register_handler(
        self, 
        capability: ModelCapability, 
        handler: Callable
    ) -> None:
        """
        [Method intent]
        Register a handler method for a specific capability.
        
        [Design principles]
        - Connect capabilities to implementation methods
        - Support polymorphic behavior
        
        [Implementation details]
        - Maps capability to handler function
        - Overwrites previous handler if exists
        
        Args:
            capability: The capability the handler implements
            handler: The method that implements the capability
        """
        self._handlers[capability] = handler
    
    def has_capability(self, capability: ModelCapability) -> bool:
        """
        [Method intent]
        Check if a capability is supported.
        
        [Design principles]
        - Simple capability checking
        - Clean boolean interface
        
        [Implementation details]
        - Checks presence in capability set
        
        Args:
            capability: The capability to check
            
        Returns:
            bool: True if the capability is supported
        """
        return capability in self._capabilities
    
    def require_capability(self, capability: ModelCapability) -> None:
        """
        [Method intent]
        Verify a capability is supported or raise an exception.
        
        [Design principles]
        - Fail-fast validation
        - Clear error messages
        
        [Implementation details]
        - Checks capability presence and raises if missing
        
        Args:
            capability: The capability that must be supported
            
        Raises:
            UnsupportedFeatureError: If the capability is not supported
        """
        if not self.has_capability(capability):
            raise UnsupportedFeatureError(f"Capability {capability.value} is not supported by this model")
    
    def get_handler(self, capability: ModelCapability) -> Optional[Callable]:
        """
        [Method intent]
        Get the handler method for a capability if registered.
        
        [Design principles]
        - Dynamic method lookup
        - Optional return for flexibility
        
        [Implementation details]
        - Returns registered handler or None
        
        Args:
            capability: The capability to get a handler for
            
        Returns:
            Optional[Callable]: The handler method if registered, None otherwise
        """
        return self._handlers.get(capability)
    
    def get_capabilities(self) -> Dict[str, bool]:
        """
        [Method intent]
        Get a dictionary of all supported capabilities.
        
        [Design principles]
        - Provide capability information in a serializable format
        - Convert internal representation to user-friendly format
        
        [Implementation details]
        - Converts set to dictionary mapping capability names to True
        
        Returns:
            Dict[str, bool]: Dictionary of capability names to support status
        """
        return {cap.value: True for cap in self._capabilities}


class EnhancedBedrockBase(BedrockBase):
    """
    [Class intent]
    Provides an enhanced base interface for all Bedrock models with unified
    capabilities for both common and specialized operations while maintaining
    model-specific optimizations.
    
    [Design principles]
    - Unified core API with model-agnostic interfaces
    - Feature capability discovery and adaptation
    - Consistent streaming pattern across all methods
    - Support for multimodal and reasoning across compatible models
    
    [Implementation details]
    - Extends BedrockBase with capability management
    - Implements common interface methods for all models
    - Provides capability-based dispatch system
    - Handles capability differences gracefully
    """
    
    # Class variable for model discovery
    SUPPORTED_MODELS = []
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """
        [Method intent]
        Get the list of model IDs supported by this model class.
        
        [Design principles]
        - Support dynamic model discovery
        - Clean class method interface
        - Consistent model identification
        
        [Implementation details]
        - Returns class-level SUPPORTED_MODELS list
        - Can be overridden by subclasses
        
        Returns:
            List[str]: List of supported model IDs
        """
        return cls.SUPPORTED_MODELS
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = BedrockBase.DEFAULT_RETRIES,
        timeout: int = BedrockBase.DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = False,
        preferred_regions: Optional[List[str]] = None,
        inference_profile_arn: Optional[str] = None
    ):
        """
        [Method intent]
        Initialize the enhanced Bedrock base with capability registry.
        
        [Design principles]
        - Clean delegation to parent class
        - Capability system initialization
        - Consistent parameter handling
        
        [Implementation details]
        - Sets up capability registry
        - Passes all parameters to parent
        
        Args:
            model_id: The Bedrock model ID
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            use_model_discovery: Whether to discover model availability
            preferred_regions: List of preferred regions for model discovery
            inference_profile_arn: Optional inference profile ARN to use
        """
        super().__init__(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            credentials=credentials,
            max_retries=max_retries,
            timeout=timeout,
            logger=logger or logging.getLogger("EnhancedBedrockBase"),
            use_model_discovery=use_model_discovery,
            preferred_regions=preferred_regions,
            inference_profile_arn=inference_profile_arn
        )
        
        # Initialize capability registry
        self._capability_registry = CapabilityRegistry()
        
        # Register core capabilities all models should have
        self._capability_registry.register_capabilities([
            ModelCapability.STREAMING,
            ModelCapability.TEXT_INPUT,
            ModelCapability.TEXT_OUTPUT
        ])
    
    def register_capability(self, capability: ModelCapability) -> None:
        """
        [Method intent]
        Register a capability as supported by this model.
        
        [Design principles]
        - Simple capability declaration
        - Public interface for capability registration
        
        [Implementation details]
        - Delegates to capability registry
        
        Args:
            capability: The capability to register
        """
        self._capability_registry.register_capability(capability)
    
    def register_capabilities(self, capabilities: List[ModelCapability]) -> None:
        """
        [Method intent]
        Register multiple capabilities at once.
        
        [Design principles]
        - Batch capability registration
        - Convenience method
        
        [Implementation details]
        - Delegates to capability registry
        
        Args:
            capabilities: List of capabilities to register
        """
        self._capability_registry.register_capabilities(capabilities)
    
    def register_handler(
        self, 
        capability: ModelCapability, 
        handler: Callable
    ) -> None:
        """
        [Method intent]
        Register a handler method for a specific capability.
        
        [Design principles]
        - Connect capabilities to implementation methods
        - Allow specialized implementations
        
        [Implementation details]
        - Delegates to capability registry
        
        Args:
            capability: The capability the handler implements
            handler: The method that implements the capability
        """
        self._capability_registry.register_handler(capability, handler)
    
    def has_capability(self, capability: ModelCapability) -> bool:
        """
        [Method intent]
        Check if a capability is supported by the model.
        
        [Design principles]
        - Simple capability checking
        - Public interface for capability queries
        
        [Implementation details]
        - Delegates to capability registry
        
        Args:
            capability: The capability to check
            
        Returns:
            bool: True if the capability is supported
        """
        return self._capability_registry.has_capability(capability)
    
    def require_capability(self, capability: ModelCapability) -> None:
        """
        [Method intent]
        Verify a capability is supported or raise an exception.
        
        [Design principles]
        - Fail-fast validation
        - Input validation helper
        
        [Implementation details]
        - Delegates to capability registry
        
        Args:
            capability: The capability that must be supported
            
        Raises:
            UnsupportedFeatureError: If the capability is not supported
        """
        self._capability_registry.require_capability(capability)
    
    async def get_model_capabilities(self) -> Dict[str, bool]:
        """
        [Method intent]
        Get a dictionary of all capabilities supported by this model.
        
        [Design principles]
        - Dynamic capability reporting
        - Serializable capability format
        
        [Implementation details]
        - Returns map of capability names to boolean support flags
        
        Returns:
            Dict[str, bool]: Dictionary of capability names to support status
        """
        return self._capability_registry.get_capabilities()
        
    def enable_prompt_caching(self, enabled: bool = True) -> bool:
        """
        [Method intent]
        Enable or disable prompt caching for this model client if supported.
        
        [Design principles]
        - Simple interface to toggle caching
        - No errors for unsupported models
        - Consistent with capability system
        - Clear return value indicating actual state
        
        [Implementation details]
        - Stores desired state in instance variable
        - Checks model support via capability system
        - Returns actual state (may be false if not supported)
        
        Args:
            enabled: Whether to enable prompt caching (default: True)
            
        Returns:
            bool: True if prompt caching is now enabled, False otherwise
        """
        # Store desired state
        self._prompt_caching_enabled = enabled
        
        # Check if model supports caching
        supports_caching = self.has_capability(ModelCapability.PROMPT_CACHING)
        
        # If enabling but model doesn't support it, log warning
        if enabled and not supports_caching:
            self.logger.warning(f"Model {self.model_id} does not support prompt caching")
            return False
            
        # Return actual state (enabled only if supported)
        return enabled and supports_caching

    def is_prompt_caching_enabled(self) -> bool:
        """
        [Method intent]
        Check if prompt caching is currently enabled for this model client.
        
        [Design principles]
        - Simple status check
        - Clear boolean interface
        
        [Implementation details]
        - Checks stored state and capability support
        - Returns boolean indicating if caching is active
        
        Returns:
            bool: True if prompt caching is enabled and supported
        """
        has_setting = hasattr(self, '_prompt_caching_enabled')
        is_enabled = getattr(self, '_prompt_caching_enabled', False)
        supports_caching = self.has_capability(ModelCapability.PROMPT_CACHING)
        
        return has_setting and is_enabled and supports_caching
        
    def mark_cache_point(
        self, 
        messages: List[Dict[str, Any]], 
        cache_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Mark a cache point in a conversation for prompt caching.
        
        [Design principles]
        - Non-destructive operation (creates copies)
        - No errors for unsupported models
        - Support for custom cache IDs
        
        [Implementation details]
        - Creates a copy of messages to avoid modifying originals
        - Adds cache point metadata to the last message
        - Generates a cache ID if not provided
        - Returns information about the cache point
        
        Args:
            messages: List of message objects to mark with cache point
            cache_id: Optional custom cache ID (generated if not provided)
            
        Returns:
            Dict[str, Any]: Cache point information including modified messages
        """
        import time
        import copy
        import uuid
        
        # Check if caching is enabled and supported
        caching_active = self.is_prompt_caching_enabled()
        
        # Generate or use provided cache ID
        cache_id = cache_id or f"cache-{uuid.uuid4()}"
        
        result = {
            "cache_id": cache_id,
            "cache_active": caching_active,
            "timestamp": time.time()
        }
        
        # If caching not active, return early with original messages
        if not caching_active:
            result["status"] = "ignored"
            result["messages"] = messages
            return result
        
        # Create a copy of messages to avoid modifying originals
        messages_copy = copy.deepcopy(messages)
        
        # Mark cache point in the last message
        if messages_copy:
            # If last message doesn't have metadata, add it
            if "metadata" not in messages_copy[-1]:
                messages_copy[-1]["metadata"] = {}
                
            # Add cache marker
            messages_copy[-1]["metadata"]["cache_point"] = {
                "id": result["cache_id"],
                "timestamp": result["timestamp"]
            }
        
        result["status"] = "marked"
        result["messages"] = messages_copy
        return result
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response from the model for a chat conversation using streaming.
        
        [Design principles]
        - Streaming as the standard interaction pattern
        - Support for model-specific parameters and caching
        - Clean parameter passing
        
        [Implementation details]
        - Checks for cache point metadata
        - Forwards caching settings to parent method
        - Handles streaming response
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Model-specific parameters
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        # Check if caching should be enabled for this request
        if self.is_prompt_caching_enabled():
            kwargs["enable_caching"] = True
        
        # Delegate to parent implementation
        async for chunk in super().stream_chat(messages, **kwargs):
            yield chunk
            
    async def stream_enhanced_generation(
        self,
        prompt: str,
        enhancement_type: Optional[str] = None,
        enhancement_options: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response with model-specific enhancements.
        This provides a unified interface to access model-specific features.
        
        [Design principles]
        - Unified interface for enhanced generation
        - Support for model-specific features
        - Consistent streaming pattern
        
        [Implementation details]
        - Maps enhancement_type to capabilities
        - Uses capability-specific handlers when available
        - Falls back to standard streaming for unknown enhancements
        
        Args:
            prompt: The text prompt
            enhancement_type: Type of enhancement ("reasoning", "multimodal", etc.)
            enhancement_options: Enhancement-specific options
            **kwargs: Standard model parameters
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            UnsupportedFeatureError: If the enhancement is not supported
            LLMError: If generation fails
        """
        # Convert enhancement type to capability if specified
        if enhancement_type:
            try:
                capability = ModelCapability(enhancement_type)
                self.require_capability(capability)
                
                # Get the specialized handler if registered
                handler = self._capability_registry.get_handler(capability)
                if handler:
                    # Use the specialized handler
                    options = enhancement_options or {}
                    async for chunk in handler(prompt, **options, **kwargs):
                        yield chunk
                    return
            except (ValueError, UnsupportedFeatureError) as e:
                # Either invalid enhancement type or unsupported capability
                raise UnsupportedFeatureError(
                    f"Enhancement '{enhancement_type}' is not supported by this model"
                ) from e
        
        # Default implementation uses standard stream_chat
        messages = [{"role": "user", "content": prompt}]
        async for chunk in self.stream_chat(messages, **kwargs):
            yield chunk
    
    async def process_content(
        self,
        content: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        content_type: str = "text",
        processing_type: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """
        [Method intent]
        Process content using the model's capabilities with a unified interface.
        This method handles different content types and processing operations.
        
        [Design principles]
        - Unified interface for content processing
        - Support for different content types
        - Dynamic dispatch based on content and processing type
        
        [Implementation details]
        - Maps content_type and processing_type to capabilities
        - Validates capability support
        - Uses specialized handlers when available
        - Handles multimodal content
        
        Args:
            content: Input content (text, image bytes, etc.)
            content_type: Type of input content ("text", "image", "video", "mixed")
            processing_type: Type of processing ("summarize", "extract_keywords",
                            "reasoning", "structured_output")
            options: Processing-specific options
            **kwargs: Standard model parameters
            
        Returns:
            Union[str, Dict[str, Any], AsyncIterator[Dict[str, Any]]]: 
                Processing result based on the operation
                
        Raises:
            UnsupportedFeatureError: If the content type or processing is not supported
            LLMError: If processing fails
        """
        # Validate content type capability
        content_capability_map = {
            "text": ModelCapability.TEXT_INPUT,
            "image": ModelCapability.IMAGE_INPUT,
            "video": ModelCapability.VIDEO_INPUT,
            "mixed": ModelCapability.MULTIMODAL
        }
        
        if content_type in content_capability_map:
            capability = content_capability_map[content_type]
            if not self.has_capability(capability):
                raise UnsupportedFeatureError(
                    f"Content type '{content_type}' is not supported by this model"
                )
        else:
            raise ValueError(f"Unknown content type: {content_type}")
        
        # Handle processing type if specified
        if processing_type:
            processing_capability_map = {
                "summarize": ModelCapability.SUMMARIZATION,
                "extract_keywords": ModelCapability.KEYWORD_EXTRACTION,
                "reasoning": ModelCapability.REASONING,
                "structured_output": ModelCapability.STRUCTURED_OUTPUT
            }
            
            if processing_type in processing_capability_map:
                capability = processing_capability_map[processing_type]
                if not self.has_capability(capability):
                    raise UnsupportedFeatureError(
                        f"Processing type '{processing_type}' is not supported by this model"
                    )
                
                # Get the specialized handler if registered
                handler = self._capability_registry.get_handler(capability)
                if handler:
                    # Use the specialized handler
                    opts = options or {}
                    return await handler(content, **opts, **kwargs)
            else:
                # Unknown processing type
                raise ValueError(f"Unknown processing type: {processing_type}")
        
        # Default implementation processes as text prompt
        if content_type == "text" and isinstance(content, str):
            # Simple text processing
            messages = [{"role": "user", "content": content}]
            result = ""
            async for chunk in self.stream_chat(messages, **kwargs):
                if "delta" in chunk and "text" in chunk["delta"]:
                    result += chunk["delta"]["text"]
            return result
        elif content_type == "mixed":
            # For multimodal content, look for a multimodal handler
            if self.has_capability(ModelCapability.MULTIMODAL):
                handler = self._capability_registry.get_handler(ModelCapability.MULTIMODAL)
                if handler:
                    opts = options or {}
                    return await handler(content, **opts, **kwargs)
            
            # No handler or capability for multimodal
            raise UnsupportedFeatureError(
                "This model does not support processing mixed content types"
            )
        else:
            # Other content types need specialized handling
            raise UnsupportedFeatureError(
                f"Default processing for content type '{content_type}' is not implemented"
            )
