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
# - Support for multimodal capabilities
# - Clean extension of BedrockBase
# - Direct access to model details for capability checking
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
# codebase:src/dbp/llm/bedrock/discovery/models.py
# system:typing
# system:asyncio
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-05T01:05:00Z : Fixed region handling with inference profiles by CodeAssistant
# * Fixed bug in EnhancedBedrockBase.__init__ to use self.region_name rather than original region_name
# * Ensures region from inference profile ARN is used consistently when fetching model details
# * Prevents unnecessary region scanning in wrong region when using inference profiles
# 2025-05-05T00:33:00Z : Refactored EnhancedBedrockBase to improve DRY principles by CodeAssistant
# * Removed duplicated internal formatting methods and template methods
# * Simplified stream_chat to delegate to parent implementation
# * Made EnhancedBedrockBase abstract class to enforce contract
# * Maintained specialized capabilities like prompt caching
# 2025-05-04T23:45:00Z : Implemented Template Method pattern for request preparation by CodeAssistant
# * Added internal formatting methods for model-specific customization
# * Added _prepare_request template method for unified request creation
# * Refactored stream_chat to use template methods for consistency
# * Eliminated duplication of stream_chat in model-specific clients
# 2025-05-04T23:05:00Z : Refactored capability management to use raw model details by CodeAssistant
# * Removed ModelCapability enum and CapabilityRegistry class
# * Added direct model details access methods
# * Added capability check methods that use model details directly
# * Simplified handler management with string-based registration
# 2025-05-04T11:22:00Z : Implemented prompt caching API methods by CodeAssistant
# * Added enable_prompt_caching method to toggle caching
# * Added is_prompt_caching_enabled method to check caching status
# * Added mark_cache_point method to mark caching points in conversations
# * Enhanced stream_chat method to use caching configuration
###############################################################################

import logging
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable, Tuple

from .base import BedrockBase
from ..common.streaming import StreamingResponse, TextStreamingResponse, IStreamable
from ..common.exceptions import LLMError, InvocationError, UnsupportedFeatureError


class EnhancedBedrockBase(BedrockBase, ABC):
    """
    [Class intent]
    Provides an enhanced base interface for all Bedrock models with unified
    capabilities for both common and specialized operations while maintaining
    model-specific optimizations.
    
    [Design principles]
    - Unified core API with model-agnostic interfaces
    - Direct model details access for capability checking
    - Consistent streaming pattern across all methods
    - Support for multimodal capabilities
    
    [Implementation details]
    - Extends BedrockBase with model details access
    - Uses direct model details for capability checking
    - Provides string-based handler registration system
    - Handles capability differences gracefully with clear error messages
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
        Initialize the enhanced Bedrock base with model details from discovery.
        
        [Design principles]
        - Clean delegation to parent class
        - Model details retrieval and storage
        - Consistent parameter handling
        - Errors are propagated, not caught
        
        [Implementation details]
        - Gets model details from discovery service
        - Stores model details for capability checks
        - Passes all parameters to parent class
        
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
            
        Raises:
            ModelNotAvailableError: If the model is not available or accessible
            AWSClientError: If there are AWS client issues
            LLMError: If there are other errors fetching model details
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
        
        # Get model discovery
        from .discovery.models import BedrockModelDiscovery
        self._model_discovery = BedrockModelDiscovery.get_instance()
        
        # Fetch model details - let errors propagate to caller
        self._model_details = self._model_discovery.get_model(
            model_id=model_id,
            region=self.region_name
        )
        self.logger.info(f"Loaded model details for {model_id}")
    
    def model(self) -> Dict[str, Any]:
        """
        [Method intent]
        Get the detailed model information for this client.
        
        [Design principles]
        - Direct model details access
        - Complete information retrieval
        - No data transformation
        
        [Implementation details]
        - Returns stored model details from discovery
        
        Returns:
            Dict[str, Any]: Complete model information from discovery
        """
        return self._model_details

    def has_input_modality(self, modality: str) -> bool:
        """
        [Method intent]
        Check if the model supports a specific input modality.
        
        [Design principles]
        - Simple capability checking
        - Direct model details access
        - Clean boolean interface
        
        [Implementation details]
        - Checks inputModalities field in model details
        
        Args:
            modality: The modality to check (e.g., "TEXT", "IMAGE")
            
        Returns:
            bool: True if the model supports the input modality
        """
        modalities = self._model_details.get("inputModalities", [])
        return modality in modalities

    def has_output_modality(self, modality: str) -> bool:
        """
        [Method intent]
        Check if the model supports a specific output modality.
        
        [Design principles]
        - Simple capability checking
        - Direct model details access
        - Clean boolean interface
        
        [Implementation details]
        - Checks outputModalities field in model details
        
        Args:
            modality: The modality to check (e.g., "TEXT", "IMAGE")
            
        Returns:
            bool: True if the model supports the output modality
        """
        modalities = self._model_details.get("outputModalities", [])
        return modality in modalities

    def supports_streaming(self) -> bool:
        """
        [Method intent]
        Check if the model supports streaming responses.
        
        [Design principles]
        - Simple capability checking
        - Direct model details access
        - Clean boolean interface
        
        [Implementation details]
        - Checks responseStreamingSupported field in model details
        
        Returns:
            bool: True if the model supports streaming
        """
        return self._model_details.get("responseStreamingSupported", True)

    def supports_prompt_caching(self) -> bool:
        """
        [Method intent]
        Check if the model supports prompt caching.
        
        [Design principles]
        - Simple capability checking
        - Delegation to model discovery
        - Clean boolean interface
        
        [Implementation details]
        - Uses model discovery's check which is based on model ID
        
        Returns:
            bool: True if prompt caching is supported
        """
        # Use model discovery's check which is based on model ID
        return self._model_discovery.supports_prompt_caching(
            self._model_details.get("modelId", "")
        )
    
    def enable_prompt_caching(self, enabled: bool = True) -> bool:
        """
        [Method intent]
        Enable or disable prompt caching for this model client if supported.
        
        [Design principles]
        - Simple interface to toggle caching
        - Clear error if not supported
        - Clear return value indicating actual state
        
        [Implementation details]
        - Stores desired state in instance variable
        - Checks model support via discovery
        - Throws error if enabling but not supported
        
        Args:
            enabled: Whether to enable prompt caching (default: True)
            
        Returns:
            bool: True if prompt caching is now enabled
            
        Raises:
            UnsupportedFeatureError: If enabling caching for a model that doesn't support it
        """
        # Check if model supports caching when enabling
        if enabled and not self.supports_prompt_caching():
            raise UnsupportedFeatureError(f"Model {self.model_id} does not support prompt caching")
        
        # Store state and return
        self._prompt_caching_enabled = enabled
        return enabled

    def is_prompt_caching_enabled(self) -> bool:
        """
        [Method intent]
        Check if prompt caching is currently enabled for this model client.
        
        [Design principles]
        - Simple status check
        - Clear boolean interface
        
        [Implementation details]
        - Checks stored state 
        - Returns boolean indicating if caching is active
        
        Returns:
            bool: True if prompt caching is enabled
        """
        return getattr(self, '_prompt_caching_enabled', False)
        
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
        caching_active = self.is_prompt_caching_enabled() and self.supports_prompt_caching()
        
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
    
    
    # The abstract methods from BedrockBase must be implemented by concrete model classes
    # We don't need to redefine them here as they are already defined in the parent class:
    # - _format_messages
    # - _format_model_kwargs
    # - _get_system_content
    # - _get_model_specific_params

    async def get_model_capabilities(self) -> Dict[str, bool]:
        """
        [Method intent]
        Get a dictionary of model capabilities based on model details.
        
        [Design principles]
        - Dynamic capability reporting
        - Serializable capability format
        - Based directly on model details
        
        [Implementation details]
        - Extracts capabilities from model details
        
        Returns:
            Dict[str, bool]: Dictionary of capability names to support status
        """
        capabilities = {
            "streaming": self.supports_streaming(),
            "text_input": self.has_input_modality("TEXT"),
            "text_output": self.has_output_modality("TEXT"),
            "image_input": self.has_input_modality("IMAGE"),
            "image_output": self.has_output_modality("IMAGE"),
            "video_input": self.has_input_modality("VIDEO"),
            "video_output": self.has_output_modality("VIDEO"),
            "prompt_caching": self.supports_prompt_caching()
        }
            
        return capabilities
        
    async def _process_stream_chunk(
        self, 
        chunk: Dict[str, Any],
        has_special_content_types: bool = False
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Process a streaming chunk before yielding it to client code.
        
        [Design principles]
        - Template method for subclass customization
        - Default pass-through behavior
        - Support for custom content processing
        
        [Implementation details]
        - Default implementation returns unchanged chunk
        - Subclasses can override to add processing
        - Designed for use by stream_chat
        
        Args:
            chunk: The raw chunk from the response stream
            has_special_content_types: Whether to expect special content types
            
        Returns:
            Dict[str, Any]: Processed chunk ready for client code
        """
        # Default implementation just passes through the chunk
        return chunk
        
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response from the model for a chat conversation using streaming.
        Enhanced version that supports prompt caching and special content types.
        
        [Design principles]
        - Streaming as the standard interaction pattern
        - Support for model-specific parameters and content processing
        - Template method pattern for specialized processing
        
        [Implementation details]
        - Enables prompt caching if configured
        - Processes chunks through template method hook
        - Handles special content types like reasoning
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Model-specific parameters
            
        Yields:
            Dict[str, Any]: Processed response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        # Check if caching should be enabled for this request
        if self.is_prompt_caching_enabled() and self.supports_prompt_caching():
            kwargs["enable_caching"] = True
            
        try:
            # Delegate to parent's stream_chat implementation
            async for chunk in super().stream_chat(messages, **kwargs):
                # Process the chunk through the hook
                processed_chunk = await self._process_stream_chunk(chunk, False)
                yield processed_chunk
                
        except Exception as e:
            # Add context about processing
            self.logger.error(f"Error processing stream: {str(e)}")
            raise LLMError(f"Error in stream processing: {str(e)}", e)
