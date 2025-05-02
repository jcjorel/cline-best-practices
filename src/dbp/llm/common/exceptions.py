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
# Defines all exceptions used across the LLM module. This centralizes error types
# to ensure consistent error handling and reporting throughout the codebase.
# Provides specific exception types for different failure scenarios.
###############################################################################
# [Source file design principles]
# - All exceptions derive from a common base class for unified handling
# - Exceptions include descriptive error messages and contextual information
# - Each exception type represents a distinct failure scenario
# - Error information is structured to support easy logging and debugging
# - No catch-all handlers or silent failure modes (follows "raise on error" principle)
###############################################################################
# [Source file constraints]
# - Must not suppress or transform exceptions from lower levels
# - Custom exceptions must provide enough context for troubleshooting
# - Exceptions should be fine-grained to support specific error handling
###############################################################################
# [Dependencies]
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-02T13:04:00Z : Added UnsupportedFeatureError for capability checking by CodeAssistant
# * Added exception for feature capability checks
# * Used by EnhancedBedrockBase for model capability validation
# 2025-05-02T10:32:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created exception hierarchy for LLM module
###############################################################################

"""
Exceptions for the LLM module.
"""

from typing import Any, Dict, Optional


class UnsupportedFeatureError(Exception):
    """
    [Class intent]
    Exception raised when a requested feature is not supported by a model.
    
    [Design principles]
    Clear indication of capability mismatches between request and model support.
    
    [Implementation details]
    Simple exception for feature capability checking.
    """
    pass


class LLMError(Exception):
    """
    [Class intent]
    Base exception for all LLM-related errors. All other custom exceptions
    in this module inherit from this class.
    
    [Design principles]
    Provides a common parent class for consistent error handling.
    
    [Implementation details]
    Extends Python's Exception class with additional context information.
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        [Class method intent]
        Initializes an LLM error with a message and optional context.
        
        [Design principles]
        Allows capturing of contextual information to aid in debugging.
        
        [Implementation details]
        Stores both the error message and context dictionary.
        """
        super().__init__(message)
        self.context = context or {}


class StreamingError(LLMError):
    """
    [Class intent]
    Exception raised when streaming LLM responses fail.
    
    [Design principles]
    Indicates failures in the streaming process.
    
    [Implementation details]
    Extends LLMError with stream-specific context information.
    """
    pass


class StreamingTimeoutError(StreamingError):
    """
    [Class intent]
    Exception raised when streaming exceeds the allowed time.
    
    [Design principles]
    Signals that a streaming operation did not complete within
    the specified time constraints.
    
    [Implementation details]
    Extends StreamingError with timeout-specific information.
    """
    pass


class ModelError(LLMError):
    """
    [Class intent]
    Exception raised when an LLM model returns an error.
    
    [Design principles]
    Indicates an error produced directly by the model rather
    than the surrounding infrastructure.
    
    [Implementation details]
    Extends LLMError with model-specific context.
    """
    
    def __init__(
        self,
        message: str,
        model_name: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        [Class method intent]
        Initializes a model error with message, model name and context.
        
        [Design principles]
        Captures the specific model that caused the error.
        
        [Implementation details]
        Adds model_name as a required parameter and extends context.
        """
        context = context or {}
        context["model_name"] = model_name
        super().__init__(message, context)
        self.model_name = model_name


class ConfigurationError(LLMError):
    """
    [Class intent]
    Exception raised when there are issues with LLM configuration.
    
    [Design principles]
    Indicates configuration errors before model invocation.
    
    [Implementation details]
    Extends LLMError with configuration-specific context.
    """
    pass


class AuthenticationError(LLMError):
    """
    [Class intent]
    Exception raised when authentication fails for LLM services.
    
    [Design principles]
    Specifically identifies credential and access issues.
    
    [Implementation details]
    Extends LLMError with authentication context.
    """
    pass


class RateLimitError(LLMError):
    """
    [Class intent]
    Exception raised when rate limits are exceeded.
    
    [Design principles]
    Identifies when API quotas or rate limits are hit.
    
    [Implementation details]
    Extends LLMError with quota/limit information.
    """
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        [Class method intent]
        Initializes a rate limit error with retry information.
        
        [Design principles]
        Provides retry timing information when available.
        
        [Implementation details]
        Adds retry_after as an optional parameter for backoff information.
        """
        context = context or {}
        if retry_after is not None:
            context["retry_after"] = retry_after
        super().__init__(message, context)
        self.retry_after = retry_after


class PromptError(LLMError):
    """
    [Class intent]
    Exception raised when there are issues with prompts or templates.
    
    [Design principles]
    Identifies errors in prompt construction or rendering.
    
    [Implementation details]
    Extends LLMError with prompt-specific context.
    """
    pass


class ToolError(LLMError):
    """
    [Class intent]
    Exception raised when LLM tools fail.
    
    [Design principles]
    Indicates errors in tool execution or validation.
    
    [Implementation details]
    Extends LLMError with tool-specific context.
    """
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        [Class method intent]
        Initializes a tool error with the tool name and context.
        
        [Design principles]
        Captures the specific tool that caused the error.
        
        [Implementation details]
        Adds tool_name as a required parameter and extends context.
        """
        context = context or {}
        context["tool_name"] = tool_name
        super().__init__(message, context)
        self.tool_name = tool_name


class ConnectionError(LLMError):
    """
    [Class intent]
    Exception raised when network connections to LLM services fail.
    
    [Design principles]
    Distinguishes network/connection issues from other error types.
    
    [Implementation details]
    Extends LLMError with connection-specific information.
    """
    pass


class ServiceError(LLMError):
    """
    [Class intent]
    Exception raised when LLM service returns an error.
    
    [Design principles]
    Indicates errors from the LLM service infrastructure.
    
    [Implementation details]
    Extends LLMError with service-specific context.
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        service_name: str = "LLM Service",
        context: Optional[Dict[str, Any]] = None
    ):
        """
        [Class method intent]
        Initializes a service error with service details.
        
        [Design principles]
        Captures HTTP status codes and service identification.
        
        [Implementation details]
        Adds status_code and service_name parameters and extends context.
        """
        context = context or {}
        context["service_name"] = service_name
        if status_code is not None:
            context["status_code"] = status_code
        super().__init__(message, context)
        self.status_code = status_code
        self.service_name = service_name
