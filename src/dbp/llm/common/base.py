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
# Defines the abstract base classes and interfaces for all LLM model clients,
# regardless of provider. This establishes a common streaming-only interface that 
# all model clients must implement, enabling consistent interaction patterns across
# different LLM providers for both single-shot and conversational scenarios.
###############################################################################
# [Source file design principles]
# - Provide a provider-agnostic interface for LLM clients
# - Use streaming as the universal interaction pattern, including for models without native streaming
# - Support both single-shot and conversational interactions consistently
# - Define clear abstract methods that all implementations must support
# - Separate common functionality from provider-specific implementations
# - Enable seamless swapping between different LLM providers
# - Follow the abstract base class pattern for client implementation
###############################################################################
# [Source file constraints]
# - Must not contain provider-specific parameters or logic
# - Must define a broad interface that works for various LLM providers
# - Must provide structured logging for all operations
# - Must be compatible with diverse model response formats
# - Must not introduce dependencies on specific cloud providers
# - Must only expose streaming interfaces, even for non-streaming models
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-05-02T07:08:00Z : Created provider-agnostic base interface by Cline
# * Implemented streaming-only interface as per requirements
# * Added support for both single-shot and conversational patterns
# * Created ModelClientBase abstract base class for all providers
# * Added common exception types for LLM operations
###############################################################################

import abc
import logging
from typing import Dict, Optional, Any, AsyncIterator, Union, List

from .exceptions import LLMError, ModelError, ClientError, ModelClientError

class Message:
    """
    [Class intent]
    Represents a message in a conversation with an LLM model.
    
    [Design principles]
    - Provides a standard format for messages across providers
    - Supports different message roles (system, user, assistant)
    
    [Implementation details]
    - Contains role, content, and optional metadata for a message
    """
    
    # Standard message roles
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    
    def __init__(self, role: str, content: str, message_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a new message.
        
        Args:
            role: The role of the message sender (system, user, assistant)
            content: The message content
            message_id: Optional unique identifier for the message
            metadata: Optional additional metadata
        """
        self.role = role
        self.content = content
        self.message_id = message_id
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary representation."""
        result = {
            "role": self.role,
            "content": self.content
        }
        if self.message_id:
            result["message_id"] = self.message_id
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a message from a dictionary representation."""
        message_id = data.get("message_id")
        metadata = data.get("metadata")
        return cls(
            role=data["role"],
            content=data["content"],
            message_id=message_id,
            metadata=metadata
        )


class ModelClientBase(abc.ABC):
    """
    [Class intent]
    Abstract base class defining the common interface for all LLM model clients.
    This ensures consistent patterns across different LLM providers by mandating
    a streaming-only approach for all interactions.
    
    [Design principles]
    - Provider-agnostic design for consistent interface
    - Streaming-only interface for all models
    - Support for both single-shot and conversational interactions
    - Clear contract for all derived client implementations
    - Common lifecycle management (initialization, shutdown)
    
    [Implementation details]
    - Uses abstract methods to define required functionality
    - Provides base initialization for common properties
    - Implements consistent logging patterns
    """
    
    def __init__(
        self,
        model_id: str,
        max_retries: int = 3,
        connect_timeout_seconds: int = 10,
        read_timeout_seconds: int = 30,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Class method intent]
        Initialize a new model client with common parameters.
        
        [Design principles]
        - Standardize initialization parameters across providers
        - Support configurable retry and timeout behavior
        - Support configurable logging
        
        [Implementation details]
        - Sets common properties used by all model clients
        - Configures appropriate logger instance
        
        Args:
            model_id: Identifier for the specific model
            max_retries: Maximum number of retry attempts for API calls
            connect_timeout_seconds: Connection timeout in seconds
            read_timeout_seconds: Read timeout in seconds
            logger: Optional custom logger instance
        """
        self.model_id = model_id
        self.max_retries = max_retries
        self.connect_timeout = connect_timeout_seconds
        self.read_timeout = read_timeout_seconds
        
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._initialized = False
        
        self.logger.debug(f"Created model client for {self.model_id}")
    
    @abc.abstractmethod
    async def initialize(self) -> None:
        """
        [Class method intent]
        Initialize the client for use.
        
        [Design principles]
        - Ensure client is properly prepared before first use
        - Validate model availability and access
        - Clear lifecycle management
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should set self._initialized to True when successful
        - Should handle provider-specific setup
        
        Raises:
            LLMError: If initialization fails
        """
        pass
    
    @abc.abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Class method intent]
        Generate a response from the model for a single-shot prompt using streaming.
        
        [Design principles]
        - Universal streaming interface for single prompts
        - Support for model-specific parameters via kwargs
        - Consistent response structure
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should convert provider-specific responses to a standard format
        - Should handle provider-specific streaming
        
        Args:
            prompt: The text prompt to send to the model
            **kwargs: Model-specific parameters
            
        Yields:
            Response chunks from the model
            
        Raises:
            LLMError: If generation fails
        """
        pass
    
    @abc.abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Class method intent]
        Generate a response from the model for a chat conversation using streaming.
        
        [Design principles]
        - Universal streaming interface for chat conversations
        - Support for model-specific parameters via kwargs
        - Consistent response structure
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should convert provider-specific responses to a standard format
        - Should handle provider-specific streaming
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Model-specific parameters
            
        Yields:
            Response chunks from the model
            
        Raises:
            LLMError: If chat generation fails
        """
        pass
    
    def is_initialized(self) -> bool:
        """
        [Class method intent]
        Check if the client has been initialized.
        
        [Design principles]
        - Provide clear indication of initialization state
        - Enable safe usage checks
        
        [Implementation details]
        - Returns the internal initialization flag
        
        Returns:
            bool: True if initialized, False otherwise
        """
        return self._initialized
    
    async def shutdown(self) -> None:
        """
        [Class method intent]
        Clean up resources and prepare for shutdown.
        
        [Design principles]
        - Ensure proper resource cleanup
        - Support clean application shutdown
        
        [Implementation details]
        - Base implementation resets initialization state
        - Derived classes should override to add provider-specific cleanup
        
        Note: This implementation can be overridden by derived classes
        to add provider-specific cleanup logic.
        """
        self.logger.info(f"Shutting down model client for {self.model_id}")
        self._initialized = False
