# Phase 2: Base Interfaces

This phase establishes the core interfaces, abstract base classes, and exception types that will be used throughout the LangChain/LangGraph integration. These foundations ensure consistent patterns across the implementation.

## Objectives

1. Define core exception types with a clear hierarchy
2. Create abstract base classes for LLM clients
3. Establish interface contracts for streaming, tools, and configuration

## Exception Hierarchy

Create a comprehensive exception hierarchy in `src/dbp/llm/common/exceptions.py`:

```python
class LLMError(Exception):
    """
    [Class intent]
    Base exception for all LLM-related errors, providing a common type for
    catching any error from the LLM module.
    
    [Design principles]
    - Serves as the root exception for the LLM module
    - Contains essential error information for logging and debugging
    - Allows for categorization of errors by type
    
    [Implementation details]
    - Stores error message and optional cause
    - Provides standardized string representation
    """
    
    def __init__(self, message: str, cause: Exception = None):
        self.message = message
        self.cause = cause
        super().__init__(message)


class ClientError(LLMError):
    """Base exception for client-related errors."""
    pass


class ModelNotAvailableError(ClientError):
    """Raised when a requested model is not available."""
    pass


class InvocationError(ClientError):
    """Raised when model invocation fails."""
    pass


class StreamingError(ClientError):
    """Raised when streaming operations fail."""
    pass


class PromptError(LLMError):
    """Base exception for prompt-related errors."""
    pass


class PromptNotFoundError(PromptError):
    """Raised when a requested prompt template is not found."""
    pass


class PromptRenderingError(PromptError):
    """Raised when prompt template rendering fails."""
    pass


class ConfigurationError(LLMError):
    """Base exception for configuration-related errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid."""
    pass


class ToolError(LLMError):
    """Base exception for tool-related errors."""
    pass


class ToolRegistrationError(ToolError):
    """Raised when tool registration fails."""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""
    pass


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""
    pass
```

This hierarchy follows the project's "throw on error" approach with no fallbacks, providing specific error types for each category of failure.

## Abstract Base Classes

### ModelClientBase

Define the abstract base class for all model clients in `src/dbp/llm/common/base.py`:

```python
import abc
import logging
from typing import Dict, Any, AsyncIterator, List, Optional, Union

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
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize a new model client with common parameters.
        
        [Design principles]
        - Standardize initialization parameters across providers
        - Support configurable logging
        
        [Implementation details]
        - Sets common properties used by all model clients
        - Configures appropriate logger instance
        
        Args:
            model_id: Identifier for the specific model
            logger: Optional custom logger instance
        """
        self.model_id = model_id
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._initialized = False
    
    @abc.abstractmethod
    async def initialize(self) -> None:
        """
        [Method intent]
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
        [Method intent]
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
        [Method intent]
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
        [Method intent]
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
        [Method intent]
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
```

### Message Interface

Define a standard message class for chat interactions:

```python
class Message:
    """
    [Class intent]
    Represents a message in a conversation with standard roles and content.
    
    [Design principles]
    - Provide a standard format for messages across providers
    - Support different message roles (system, user, assistant)
    
    [Implementation details]
    - Contains role, content, and optional metadata
    - Supports conversion between different formats
    """
    
    # Standard roles
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    
    def __init__(
        self,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new message.
        
        Args:
            role: The role of the message sender (system, user, assistant)
            content: The message text
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
        return cls(
            role=data["role"],
            content=data["content"],
            message_id=data.get("message_id"),
            metadata=data.get("metadata")
        )
    
    @classmethod
    def system(cls, content: str) -> 'Message':
        """Create a system message."""
        return cls(cls.ROLE_SYSTEM, content)
    
    @classmethod
    def user(cls, content: str) -> 'Message':
        """Create a user message."""
        return cls(cls.ROLE_USER, content)
    
    @classmethod
    def assistant(cls, content: str) -> 'Message':
        """Create an assistant message."""
        return cls(cls.ROLE_ASSISTANT, content)
```

### IStreamable Interface

Define an interface for streaming objects in `src/dbp/llm/common/streaming.py`:

```python
import abc
from typing import AsyncIterator, Dict, Any

class IStreamable(abc.ABC):
    """
    [Class intent]
    Interface for objects that support streaming response generation.
    
    [Design principles]
    - Establish a common interface for all streaming operations
    - Allow unified handling of different streaming sources
    
    [Implementation details]
    - Abstract base class with a single required method
    - Simple interface that can be implemented by various components
    """
    
    @abc.abstractmethod
    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Stream responses from this object.
        
        [Design principles]
        - Universal streaming interface
        - AsyncIO-based for non-blocking operation
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should yield dictionary chunks
        
        Yields:
            Response chunks
            
        Raises:
            StreamingError: If streaming fails
        """
        pass
```

### IToolRegistry Interface

Define an interface for the tool registry in `src/dbp/llm/common/tool_registry.py`:

```python
import abc
from typing import Any, Callable, Dict, List, Optional, Type

class IToolRegistry(abc.ABC):
    """
    [Class intent]
    Interface for tool registry implementations.
    
    [Design principles]
    - Define a standard interface for tool registration
    - Support dynamic registration/unregistration
    - Enable tool discovery and lookup
    
    [Implementation details]
    - Abstract base class with required tool management methods
    - Provider-agnostic to work with different tool frameworks
    """
    
    @abc.abstractmethod
    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        [Method intent]
        Register a tool with the registry.
        
        [Design principles]
        - Support dynamic tool registration
        - Validate tool parameters
        - Prevent duplicate registrations
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should validate tool name uniqueness
        - Should store tool metadata
        
        Args:
            name: Unique name for the tool
            func: Function implementing the tool
            description: Human-readable tool description
            input_schema: JSON Schema for tool input validation
            output_schema: Optional JSON Schema for tool output validation
            **kwargs: Additional tool metadata
            
        Raises:
            ToolRegistrationError: If registration fails
        """
        pass
    
    @abc.abstractmethod
    def unregister_tool(self, name: str) -> None:
        """
        [Method intent]
        Unregister a tool from the registry.
        
        [Design principles]
        - Support dynamic tool removal
        - Validate tool existence
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should verify tool exists before removal
        
        Args:
            name: Name of the tool to unregister
            
        Raises:
            ToolNotFoundError: If tool does not exist
        """
        pass
    
    @abc.abstractmethod
    def get_tool(self, name: str) -> Dict[str, Any]:
        """
        [Method intent]
        Get a tool by name.
        
        [Design principles]
        - Enable tool lookup by name
        - Provide complete tool information
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should return tool function and metadata
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            Dictionary containing tool information
            
        Raises:
            ToolNotFoundError: If tool does not exist
        """
        pass
    
    @abc.abstractmethod
    def list_tools(self, tag: Optional[str] = None) -> List[str]:
        """
        [Method intent]
        List available tools, optionally filtered by tag.
        
        [Design principles]
        - Support tool discovery
        - Enable filtering for specific use cases
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should return a list of tool names
        
        Args:
            tag: Optional tag to filter tools
            
        Returns:
            List of tool names
        """
        pass
```

### IConfigRegistry Interface

Define an interface for the configuration registry in `src/dbp/llm/common/config_registry.py`:

```python
import abc
from typing import Any, Dict, List, Optional

class IConfigRegistry(abc.ABC):
    """
    [Class intent]
    Interface for LLM configuration registry implementations.
    
    [Design principles]
    - Define a standard interface for configuration management
    - Support named configurations
    - Enable configuration discovery and lookup
    
    [Implementation details]
    - Abstract base class with required configuration management methods
    - Provider-agnostic to work with different LLM backends
    """
    
    @abc.abstractmethod
    def register_config(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> None:
        """
        [Method intent]
        Register a configuration with the registry.
        
        [Design principles]
        - Support dynamic configuration registration
        - Validate configuration parameters
        - Prevent duplicate registrations
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should validate configuration name uniqueness
        - Should validate configuration parameters
        
        Args:
            name: Unique name for the configuration
            config: Configuration parameters
            
        Raises:
            ConfigurationError: If registration fails
        """
        pass
    
    @abc.abstractmethod
    def unregister_config(self, name: str) -> None:
        """
        [Method intent]
        Unregister a configuration from the registry.
        
        [Design principles]
        - Support dynamic configuration removal
        - Prevent removal of built-in configurations
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should verify configuration exists before removal
        - Should prevent removal of built-in configurations
        
        Args:
            name: Name of the configuration to unregister
            
        Raises:
            ConfigurationError: If unregistration fails
        """
        pass
    
    @abc.abstractmethod
    def get_config(self, name: str = "default") -> Dict[str, Any]:
        """
        [Method intent]
        Get a configuration by name.
        
        [Design principles]
        - Enable configuration lookup by name
        - Provide default configuration when name not specified
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should return a copy of the configuration to prevent modification
        
        Args:
            name: Name of the configuration to retrieve
            
        Returns:
            Configuration parameters
            
        Raises:
            ConfigurationError: If configuration does not exist
        """
        pass
    
    @abc.abstractmethod
    def list_configs(self) -> List[str]:
        """
        [Method intent]
        List available configurations.
        
        [Design principles]
        - Support configuration discovery
        
        [Implementation details]
        - Must be implemented by derived classes
        - Should return a list of configuration names
        
        Returns:
            List of configuration names
        """
        pass
```

## Implementation Steps

1. **Define Exception Hierarchy**
   - Create `src/dbp/llm/common/exceptions.py` with comprehensive exception hierarchy
   - Ensure each exception has a clear purpose and usage pattern
   - Document each exception with detailed docstrings

2. **Create Base Classes**
   - Implement `ModelClientBase` in `src/dbp/llm/common/base.py`
   - Create `Message` class in `src/dbp/llm/common/base.py`
   - Define streaming interfaces in `src/dbp/llm/common/streaming.py`

3. **Define Tool and Config Interfaces**
   - Create `IToolRegistry` in `src/dbp/llm/common/tool_registry.py`
   - Implement `IConfigRegistry` in `src/dbp/llm/common/config_registry.py`
   - Ensure all interfaces follow consistent patterns

## Notes

- All interfaces must follow the project's "throw on error" approach with no fallbacks
- Comprehensive documentation is essential for all interfaces and classes
- Abstract base classes ensure consistent implementation across providers
- The use of AsyncIO throughout supports the streaming-only approach
- Interfaces are designed to be provider-agnostic for maximum flexibility

## Next Steps

After completing this phase:
1. Proceed to Phase 3 (AsyncIO Streaming Foundation)
2. Implement concrete streaming components
3. Build stream handling utilities
