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
# Provides foundational Amazon Bedrock integration focusing exclusively on 
# the Converse API. This base class serves as the foundation for all 
# Bedrock model clients, handling authentication, streaming API interactions, 
# and comprehensive error management.
###############################################################################
# [Source file design principles]
# - Exclusive use of Converse API for all interactions 
# - Streaming as the primary interaction pattern
# - Asynchronous interface for non-blocking operations
# - Comprehensive error handling and reporting
# - Clean separation of common Bedrock functionality from model specifics
# - Thread-safe AWS client management
# - Support for both chat and completion formats
###############################################################################
# [Source file constraints]
# - Must not contain model-specific parameters or logic
# - Must handle AWS credentials and region configuration properly
# - Must provide structured logging for all operations
# - Must be compatible with all Bedrock foundation models
# - Must use only the Converse API for all interactions
# - Must implement full asynchronous interface
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/llm/common/streaming.py
# codebase:doc/DESIGN.md
# codebase:doc/design/LLM_COORDINATION.md
# system:boto3
# system:botocore
# system:asyncio
###############################################################################
# [GenAI tool change history]
# 2025-05-03T08:53:00Z : Refactored _converse_stream for DRY principles by CodeAssistant
# * Eliminated code duplication between _converse_stream and _process_converse_stream
# * Modified _converse_stream to leverage _process_converse_stream method
# * Improved maintainability by centralizing stream event processing logic
# 2025-05-03T08:50:00Z : Moved _process_converse_stream from EnhancedBedrockBase by CodeAssistant
# * Moved method to base class to make it available to all Bedrock clients
# * Maintained method signature and functionality
# * Enhanced documentation to reflect method purpose
# 2025-05-02T22:19:00Z : Fixed EventStream streaming issue by CodeAssistant
# * Fixed EventStream iteration by creating explicit iterator from stream
# * Updated documentation to reflect EventStream handling
# * Enhanced error handling specificity for streaming operations
# 2025-05-02T11:13:00Z : Enhanced for LangChain/LangGraph integration by CodeAssistant
# * Updated to use Converse API exclusively
# * Implemented fully async interface for all operations
# * Added streaming support with AsyncIO generators
# * Enhanced error handling and classification
###############################################################################

import os
import logging
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Tuple, cast

import boto3
import botocore.exceptions
from botocore.config import Config

from .discovery.models import BedrockModelDiscovery
from .discovery.profiles import BedrockProfileDiscovery

from ..common.base import ModelClientBase
from ..common.exceptions import (
    LLMError, ClientError, ModelNotAvailableError, InvocationError, StreamingError
)
from ..common.streaming import (
    StreamingResponse, TextStreamingResponse, IStreamable, AsyncTextStreamProvider
)


class BedrockBase(ModelClientBase, AsyncTextStreamProvider):
    """
    [Class intent]
    Provides foundational Amazon Bedrock integration focusing exclusively on 
    the Converse API. This class serves as the base implementation for all 
    Bedrock model clients, handling authentication, API interactions, and error
    management.
    
    [Design principles]
    - Exclusive use of Converse API for all interactions
    - Comprehensive error handling and reporting
    - Clean separation of common Bedrock functionality from model specifics
    - Streaming as the primary interaction pattern
    - Asynchronous interface for non-blocking operations
    
    [Implementation details]
    - Uses boto3 for AWS API access
    - Implements retries with exponential backoff
    - Provides consistent error classification
    - Handles authentication through various methods
    - Abstracts Bedrock API details behind a simpler interface
    """
    
    # Default Bedrock API settings
    DEFAULT_REGION = "us-east-1"
    DEFAULT_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 0.5
    DEFAULT_TIMEOUT = 30
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = DEFAULT_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = False,
        preferred_regions: Optional[List[str]] = None,
        inference_profile_id: Optional[str] = None
    ):
        """
        [Method intent]
        Initialize the Bedrock base client with AWS configuration and credentials.
        
        [Design principles]
        - Flexible authentication options
        - Clear configuration parameters
        - Sensible defaults
        
        [Implementation details]
        - Supports multiple authentication methods (profile, explicit credentials, environment)
        - Configures retry behavior
        - Sets up logging
        - Prepares for client initialization
        
        Args:
            model_id: Bedrock model ID (e.g., "anthropic.claude-3-haiku-20240307-v1:0")
            region_name: AWS region name (default: value of DEFAULT_REGION)
            profile_name: AWS profile name for credentials (optional)
            credentials: Explicit AWS credentials (optional)
            max_retries: Maximum number of API retries (default: 3)
            timeout: API timeout in seconds (default: 30)
            logger: Optional custom logger instance
            use_model_discovery: Whether to use model discovery for region selection
            preferred_regions: List of preferred regions for model discovery
            inference_profile_id: Optional inference profile ID to use
        """
        # Initialize base class
        super().__init__(model_id, logger)
        
        # Store configuration
        self.region_name = region_name or self.DEFAULT_REGION
        self.profile_name = profile_name
        self.credentials = credentials
        self.max_retries = max_retries
        self.timeout = timeout
        self.use_model_discovery = use_model_discovery
        self.preferred_regions = preferred_regions or []
        self.inference_profile_id = inference_profile_id
        
        # Discovery components - will be initialized if enabled
        self._model_discovery = None
        self._profile_discovery = None
        
        if self.use_model_discovery:
            # Initialize discovery components
            self._model_discovery = BedrockModelDiscovery.get_instance()
            
            # Use model_discovery as owner for profile_discovery
            from .discovery.profiles import BedrockProfileDiscovery
            self._profile_discovery = BedrockProfileDiscovery(
                model_discovery=self._model_discovery,
                logger=self.logger
            )
        
        # Bedrock client - will be initialized later
        self._bedrock_runtime = None
        self._bedrock = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """
        [Method intent]
        Initialize the Bedrock client and validate access to the model.
        
        [Design principles]
        - Early validation of credentials and permissions
        - Comprehensive error handling
        - Clear error messages
        - Thread-safe initialization
        
        [Implementation details]
        - Creates boto3 clients for Bedrock and Bedrock Runtime
        - Validates that the model exists and is accessible
        - Sets initialization flag upon success
        - Uses locking to ensure thread safety
        
        Raises:
            LLMError: If initialization fails
            ModelNotAvailableError: If the model is not available
        """
        # Use a lock to prevent concurrent initialization
        async with self._lock:
            if self.is_initialized():
                return
                
            try:
                # Create boto3 config with retry settings
                boto_config = Config(
                    region_name=self.region_name,
                    retries={
                        "max_attempts": self.max_retries,
                        "mode": "standard"
                    },
                    connect_timeout=self.timeout,
                    read_timeout=self.timeout
                )
                
                # Create boto3 clients based on provided authentication
                session_kwargs = {}
                client_kwargs = {
                    "config": boto_config
                }
                
                if self.profile_name:
                    # Use named profile
                    session_kwargs["profile_name"] = self.profile_name
                    session = boto3.Session(**session_kwargs)
                    self._bedrock_runtime = session.client("bedrock-runtime", **client_kwargs)
                    self._bedrock = session.client("bedrock", **client_kwargs)
                elif self.credentials:
                    # Use explicit credentials
                    client_kwargs.update({
                        "aws_access_key_id": self.credentials.get("aws_access_key_id"),
                        "aws_secret_access_key": self.credentials.get("aws_secret_access_key"),
                        "aws_session_token": self.credentials.get("aws_session_token")
                    })
                    self._bedrock_runtime = boto3.client("bedrock-runtime", **client_kwargs)
                    self._bedrock = boto3.client("bedrock", **client_kwargs)
                else:
                    # Use default credentials from environment
                    self._bedrock_runtime = boto3.client("bedrock-runtime", **client_kwargs)
                    self._bedrock = boto3.client("bedrock", **client_kwargs)
                
                # Validate model access
                await self._validate_model_access()
                
                # Mark as initialized
                self._initialized = True
                self.logger.info(f"Initialized Bedrock client for model {self.model_id}")
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                if error_code == "AccessDeniedException":
                    raise LLMError(f"Access denied to Bedrock: {error_message}", e)
                elif error_code == "ValidationException":
                    raise ModelNotAvailableError(f"Invalid model ID: {self.model_id}", e)
                elif error_code == "ResourceNotFoundException":
                    raise ModelNotAvailableError(f"Model not found: {self.model_id}", e)
                else:
                    raise LLMError(f"Bedrock initialization error: {error_message}", e)
            except Exception as e:
                raise LLMError(f"Failed to initialize Bedrock client: {str(e)}", e)
    
    async def _validate_model_access(self) -> None:
        """
        [Method intent]
        Validate that the specified model exists and is accessible.
        
        [Design principles]
        - Early failure for invalid models
        - Separation of validation from initialization
        - Clear error messages
        - Model discovery support for region selection
        
        [Implementation details]
        - Uses Model Discovery if enabled
        - Falls back to ListFoundationModels API if discovery disabled
        - Checks model status for availability
        - Attempts region fallback if model not available in current region
        - Raises specific exceptions for different failure cases
        - Handles API access asynchronously
        
        Raises:
            ModelNotAvailableError: If the model is not available
        """
        # Extract base model ID (remove version)
        model_parts = self.model_id.split(":")
        base_model_id = model_parts[0]
        
        # If model discovery is enabled, use it to find the best region and check model requirements
        if self.use_model_discovery and self._model_discovery:
            try:
                # Check if the model is available in current region
                is_available = self._model_discovery.is_model_available_in_region(self.model_id, self.region_name)
                
                # Get model information to check if it requires an inference profile
                region_models = self._model_discovery.scan_all_regions([self.region_name])
                model_info = None
                
                # Find our model in the region data
                if self.region_name in region_models:
                    for model in region_models[self.region_name]:
                        if model["modelId"] == self.model_id:
                            model_info = model
                            break
                
                # Always check for inference profiles if none was explicitly provided
                if not self.inference_profile_id and self._profile_discovery:
                    # Try to get inference profiles for this model from the model data we already have
                    inference_profiles = self._profile_discovery.get_inference_profile_ids(self.model_id)
                    
                    if inference_profiles:
                        if len(inference_profiles) == 1:
                            # If exactly one profile is available, use it automatically
                            self.inference_profile_id = inference_profiles[0]
                            self.logger.info(f"Automatically using the only available inference profile: {self.inference_profile_id}")
                        else:
                            # If multiple profiles are available, require explicit selection
                            profile_list = ", ".join(inference_profiles[:5])
                            if len(inference_profiles) > 5:
                                profile_list += f" and {len(inference_profiles) - 5} more"
                            
                            raise ModelNotAvailableError(
                                f"Model {self.model_id} has multiple inference profiles available. "
                                f"Please specify one using the inference_profile_id parameter. "
                                f"Available profiles: {profile_list}"
                            )
                
                # If model explicitly requires a profile but we don't have one, raise error
                if model_info and model_info.get("requiresInferenceProfile", False) and not self.inference_profile_id:
                    raise ModelNotAvailableError(
                        f"Model {self.model_id} requires an inference profile. "
                        f"This model only supports provisioned throughput and cannot be used with on-demand invocations."
                    )
                
                if is_available:
                    self.logger.debug(f"Model {self.model_id} is available in region {self.region_name}")
                    return
                
                # If model not available in current region, look for alternative regions
                best_regions = self._model_discovery.get_best_regions_for_model(
                    self.model_id, 
                    preferred_regions=self.preferred_regions
                )
                
                if not best_regions:
                    raise ModelNotAvailableError(f"Model {self.model_id} is not available in any AWS region")
                
                # If current region is not in the best regions, switch to first available region
                if self.region_name not in best_regions:
                    new_region = best_regions[0]
                    self.logger.info(
                        f"Model {self.model_id} not available in {self.region_name}, "
                        f"switching to {new_region}"
                    )
                    self.region_name = new_region
                    return
                
            except Exception as e:
                self.logger.warning(f"Error using model discovery, falling back to direct validation: {str(e)}")
                # Fall through to traditional validation
        
        # Traditional validation using direct API call
        try:
            # Run a non-blocking task to get the model list
            loop = asyncio.get_event_loop()
            
            try:
                # Use direct API call instead of paginator
                response = await loop.run_in_executor(
                    None, 
                    lambda: self._bedrock.list_foundation_models()
                )
                
                found = False
                for model in response.get("modelSummaries", []):
                    if model["modelId"] == base_model_id:
                        found = True
                        # Check model status
                        if model.get("modelLifecycle", {}).get("status") != "ACTIVE":
                            raise ModelNotAvailableError(
                                f"Model {self.model_id} is not active: "
                                f"{model['modelLifecycle'].get('status', 'UNKNOWN')}"
                            )
                        break
                
                # If model was not found in the list
                if not found:
                    raise ModelNotAvailableError(f"Model {self.model_id} is not available in region {self.region_name}")
                
                self.logger.debug(f"Validated access to model {self.model_id}")
            except botocore.exceptions.ClientError as e:
                # If we can't list models, log a warning but continue
                # This allows the test command to work even without full permissions
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                self.logger.warning(f"Could not validate model access: {error_code} - {error_message}")
                self.logger.warning(f"Continuing without model validation - model {self.model_id} will be attempted")
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            if error_code == "AccessDeniedException":
                raise LLMError(f"Access denied to Bedrock ListFoundationModels: {error_message}", e)
            else:
                raise LLMError(f"Error validating model access: {error_message}", e)
        except ModelNotAvailableError:
            # Re-raise model-specific errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to validate model access: {str(e)}", e)
    
    def get_best_regions_for_model(self) -> List[str]:
        """
        [Method intent]
        Get the best regions for the current model based on availability and preferences.
        
        [Design principles]
        - Seamless integration with model discovery
        - Preference-based region selection
        - Efficient caching of results
        
        [Implementation details]
        - Uses model discovery if enabled
        - Returns empty list if discovery is disabled
        - Prioritizes regions based on user preferences
        - Caches results for efficiency
        
        Returns:
            List[str]: Ordered list of regions where the model is available
        """
        if not self.use_model_discovery or not self._model_discovery:
            return []
            
        try:
            return self._model_discovery.get_best_regions_for_model(
                self.model_id,
                preferred_regions=self.preferred_regions
            )
        except Exception as e:
            self.logger.warning(f"Error getting best regions for model: {str(e)}")
            return []
    
    async def _converse_stream(
        self, 
        messages: List[Dict[str, Any]], 
        model_kwargs: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Invokes the Bedrock Converse API with streaming (converse_stream).
        
        [Design principles]
        - Streaming as primary interaction method
        - Asynchronous yielding of chunks
        - Consistent error classification
        
        [Implementation details]
        - Validates client initialization
        - Handles API call with streaming
        - Processes and yields chunks
        - Classifies and raises appropriate exceptions
        
        Args:
            messages: List of message objects (role/content pairs)
            model_kwargs: Additional model parameters
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            ClientError: If invocation fails
            StreamingError: If streaming fails
        """
        if not self.is_initialized():
            raise ClientError("Bedrock client is not initialized")
        
        try:
            # Prepare request with appropriate identifier
            request = {"messages": messages}
            
            # If inference profile is available, use it as the identifier
            if hasattr(self, 'inference_profile_id') and self.inference_profile_id:
                request["modelId"] = self.inference_profile_id
                self.logger.info(f"Using inference profile as model ID: {self.inference_profile_id}")
            else:
                # Otherwise use the regular model ID
                request["modelId"] = self.model_id
            
            # Add inference parameters if provided
            if model_kwargs:
                request["inferenceConfig"] = model_kwargs
            
            # Make streaming API call - run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self._bedrock_runtime.converse_stream(**request)
            )
            
            # Use the process method to handle stream events
            complete_message = {"role": "", "content": ""}
            
            # Process each event
            async for chunk in self._process_converse_stream(response):
                # Track complete message for returning at the end
                if chunk["type"] == "message_start" and "message" in chunk:
                    complete_message["role"] = chunk["message"]["role"]
                elif chunk["type"] == "content_block_delta" and "delta" in chunk and "text" in chunk["delta"]:
                    complete_message["content"] += chunk["delta"]["text"]
                elif chunk["type"] == "message_stop":
                    # Add complete message to the stop event
                    yield {**chunk, "message": complete_message}
                    continue
                    
                # Yield the event unchanged
                yield chunk
            
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == "AccessDeniedException":
                raise ClientError(f"Access denied to Bedrock Converse Stream API: {error_message}", e)
            elif error_code == "ValidationException":
                raise InvocationError(f"Invalid request to Converse Stream API: {error_message}", e)
            elif error_code == "ThrottlingException":
                raise InvocationError(f"Request throttled by Bedrock: {error_message}", e)
            elif error_code == "ServiceQuotaExceededException":
                raise InvocationError(f"Service quota exceeded: {error_message}", e)
            elif error_code == "ModelTimeoutException":
                raise InvocationError(f"Model inference timeout: {error_message}", e)
            elif error_code == "ModelErrorException":
                raise InvocationError(f"Model error during inference: {error_message}", e)
            elif error_code == "ModelNotReadyException":
                raise ModelNotAvailableError(f"Model not ready: {error_message}", e)
            else:
                raise StreamingError(f"Bedrock API error: {error_code} - {error_message}", e)
        except Exception as e:
            raise StreamingError(f"Bedrock streaming error: {str(e)}", e)
    
    async def _iterate_stream_events(self, stream) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Process the raw Bedrock stream into asynchronously yielded events.
        
        [Design principles]
        - Clean conversion from boto3 stream to async generator
        - Proper error handling
        - Optimized for streaming performance
        
        [Implementation details]
        - Handles boto3's EventStream object properly
        - Creates an iterator from the EventStream
        - Yields individual events
        - Propagates errors appropriately
        - Allows asyncio cooperative multitasking
        
        Args:
            stream: Boto3 EventStream response
            
        Yields:
            Dict[str, Any]: Individual stream events
            
        Raises:
            StreamingError: If stream processing fails
        """
        try:
            # Process synchronous stream in a way that plays well with asyncio
            loop = asyncio.get_event_loop()
            
            # Create an iterator from the EventStream object
            stream_iterator = iter(stream)
            
            def get_next_event():
                try:
                    return next(stream_iterator)
                except StopIteration:
                    return None
                except Exception as e:
                    raise e
            
            # Get events one at a time to avoid blocking
            event = await loop.run_in_executor(None, get_next_event)
            while event is not None:
                # Let asyncio execute other tasks while processing
                yield event
                await asyncio.sleep(0)  # Cooperative multitasking yield point
                event = await loop.run_in_executor(None, get_next_event)
                
        except Exception as e:
            raise StreamingError(f"Error processing Bedrock stream: {str(e)}", e)
    
    async def _process_converse_stream(self, stream) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Process a raw Bedrock converse stream into standardized format chunks.
        
        [Design principles]
        - Common stream processing for all Bedrock models
        - Standardized chunk format for consumers
        - Clean event type handling
        
        [Implementation details]
        - Uses _iterate_stream_events for raw event processing
        - Converts events to standardized format
        - Handles all relevant event types (messageStart, contentBlockDelta, messageStop)
        
        Args:
            stream: Raw stream from Bedrock Converse API response
            
        Yields:
            Dict[str, Any]: Standardized event chunks with type information
        """
        # Handle case where stream is in a dictionary (common with boto3 responses)
        actual_stream = stream
        
        # If stream is a dict with a 'stream' key, extract the actual stream
        if isinstance(stream, dict) and "stream" in stream:
            actual_stream = stream["stream"]
            
        # Use the base class method to iterate over events with the actual stream
        async for event in self._iterate_stream_events(actual_stream):
            # Process events into the expected format
            if "messageStart" in event:
                message_start = event["messageStart"]
                yield {
                    "type": "message_start",
                    "message": {"role": message_start["role"]}
                }
            
            elif "contentBlockStart" in event:
                content_start = event["contentBlockStart"]
                block_type = content_start.get("contentType", "text/plain")
                
                yield {
                    "type": "content_block_start",
                    "content_type": block_type
                }
            
            elif "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]
                if "delta" in delta and "text" in delta["delta"]:
                    text_chunk = delta["delta"]["text"]
                    yield {
                        "type": "content_block_delta",
                        "delta": {"text": text_chunk}
                    }
            
            elif "contentBlockStop" in event:
                yield {
                    "type": "content_block_stop"
                }
            
            elif "messageStop" in event:
                stop_reason = event["messageStop"].get("stopReason")
                yield {
                    "type": "message_stop",
                    "stop_reason": stop_reason
                }
    
    async def stream_generate(
        self, 
        prompt: str, 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response from the model for a single-shot prompt using streaming.
        
        [Design principles]
        - Simple interface for single prompts
        - Streaming-only approach
        - User-friendly parameter handling
        
        [Implementation details]
        - Converts single prompt to messages format
        - Delegates to stream_chat
        - Maintains streaming semantics
        
        Args:
            prompt: The text prompt to send to the model
            **kwargs: Additional model parameters
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            LLMError: If generation fails
        """
        # Convert single prompt to messages format
        messages = [{"role": "user", "content": prompt}]
        
        # Delegate to stream_chat
        async for chunk in self.stream_chat(messages, **kwargs):
            yield chunk
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Generate a response from the model for a chat conversation using streaming.
        This is the primary method for interacting with Bedrock models.
        
        [Design principles]
        - Streaming as the standard interaction pattern
        - Support for model-specific parameters
        - Clean parameter passing
        
        [Implementation details]
        - Uses Converse Stream API exclusively
        - Formats messages for Bedrock
        - Allows model-specific parameter overrides
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Model-specific parameters
            
        Yields:
            Dict[str, Any]: Response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        # Validate initialization
        if not self.is_initialized():
            await self.initialize()
        
        # Format messages for Bedrock
        formatted_messages = self._format_messages(messages)
        
        # Format model kwargs
        model_kwargs = self._format_model_kwargs(kwargs)
        
        # Stream response
        try:
            async for chunk in self._converse_stream(formatted_messages, model_kwargs):
                yield chunk
        except Exception as e:
            if isinstance(e, LLMError):
                raise e
            raise LLMError(f"Failed to stream chat response: {str(e)}", e)
    
    def _format_messages(
        self, 
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages for the Bedrock Converse API.
        
        [Design principles]
        - Consistent message format conversion
        - Support for different content types
        - Clean separation from API logic
        
        [Implementation details]
        - Converts message content to Bedrock format
        - Handles role mapping
        - Ensures content is properly formatted
        
        Args:
            messages: List of message objects in standard format
            
        Returns:
            List[Dict[str, Any]]: Messages formatted for Bedrock API
        """
        # Basic implementation - override in model-specific clients
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
    
    def _format_model_kwargs(
        self, 
        kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Format model-specific parameters for the Bedrock Converse API.
        
        [Design principles]
        - Clean separation of parameter formatting
        - Support for model-specific overrides
        - Parameter validation
        
        [Implementation details]
        - Formats parameters for Bedrock API
        - Handles parameter naming conventions
        - Provides defaults for required parameters
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Bedrock API
        """
        # Basic implementation - override in model-specific clients
        return {
            "temperature": kwargs.get("temperature", 0.7),
            "maxTokens": kwargs.get("max_tokens", 1024),
            "topP": kwargs.get("top_p", 0.9),
            "stopSequences": kwargs.get("stop_sequences", [])
        }
    
    async def stream(self) -> AsyncIterator[str]:
        """
        [Method intent]
        Implementation of the AsyncTextStreamProvider interface for streaming text.
        
        [Design principles]
        - Conform to AsyncTextStreamProvider contract
        - Enable integration with common streaming interfaces
        - Simple conversion of raw model response to text chunks
        
        [Implementation details]
        - Uses a basic prompt to generate text
        - Extracts text chunks from streaming response
        - Yields plain text for ease of use
        
        Yields:
            str: Text chunks from the model response
            
        Raises:
            StreamingError: If streaming fails
        """
        if not hasattr(self, '_stream_prompt') or not self._stream_prompt:
            self._stream_prompt = "Hello, how can I assist you today?"
        
        try:
            async for chunk in self.stream_generate(self._stream_prompt):
                if chunk["type"] == "content_block_delta" and "delta" in chunk:
                    if "text" in chunk["delta"]:
                        yield chunk["delta"]["text"]
        except Exception as e:
            raise StreamingError(f"Error in stream provider: {str(e)}", e)
    
    @property
    def bedrock_runtime(self):
        """
        [Method intent]
        Property accessor for the Bedrock Runtime client used for model invocation.
        
        [Design principles]
        - Encapsulate internal client access
        - Provide controlled access to runtime client
        
        [Implementation details]
        - Returns the internal boto3 bedrock-runtime client
        
        Returns:
            The boto3 bedrock-runtime client for API calls
        
        Raises:
            ClientError: If client is not initialized
        """
        if not self.is_initialized():
            raise ClientError("Bedrock client is not initialized")
        return self._bedrock_runtime
    
    @property
    def bedrock(self):
        """
        [Method intent]
        Property accessor for the Bedrock client used for management operations.
        
        [Design principles]
        - Encapsulate internal client access
        - Provide controlled access to management client
        
        [Implementation details]
        - Returns the internal boto3 bedrock client
        
        Returns:
            The boto3 bedrock client for management API calls
            
        Raises:
            ClientError: If client is not initialized
        """
        if not self.is_initialized():
            raise ClientError("Bedrock client is not initialized")
        return self._bedrock
    
    async def shutdown(self) -> None:
        """
        [Method intent]
        Clean up resources and prepare for shutdown.
        
        [Design principles]
        - Proper resource cleanup
        - Clean shutdown process
        
        [Implementation details]
        - Releases AWS client resources
        - Resets initialization state
        
        Note: Boto3 clients don't require explicit cleanup, but this method
        still performs necessary state cleanup.
        """
        async with self._lock:
            if self.is_initialized():
                # Release references to boto3 clients
                self._bedrock_runtime = None
                self._bedrock = None
                
                # Reset initialization state
                self._initialized = False
                
                self.logger.info(f"Shutdown Bedrock client for model {self.model_id}")
