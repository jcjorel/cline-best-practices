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
# Defines specific exceptions for the LLM Coordinator component. These exceptions
# provide clear error information for coordination-related issues, enabling proper
# error handling and debugging of LLM agent interactions.
###############################################################################
# [Source file design principles]
# - Clear exception hierarchy
# - Descriptive error messages
# - Contextual error information
# - Compatible with component exception handling
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with core exception handling
# - Must provide sufficient context for debugging
# - Must not expose sensitive information in error messages
###############################################################################
# [Dependencies]
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:38:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created CoordinationError for LLM coordinator exceptions
# * Added specialized exception types for different coordination failure modes
###############################################################################

"""
Exceptions for the LLM Coordinator component.
"""

from typing import Optional, Any, Dict, List


class CoordinationError(Exception):
    """Base exception for LLM coordination errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        [Method intent]
        Initialize a coordination error with message and optional details.
        
        [Design principles]
        - Informative error messages
        - Optional additional context
        
        [Implementation details]
        - Stores message and details
        - Allows for structured error information
        
        Args:
            message: Error message
            details: Optional additional context
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ModelNotAvailableError(CoordinationError):
    """Exception raised when a requested model is not available."""
    
    def __init__(self, model_name: str, available_models: Optional[List[str]] = None):
        """
        [Method intent]
        Initialize a model not available error.
        
        [Design principles]
        - Specific error for model availability issues
        - Informative context about available alternatives
        
        [Implementation details]
        - Includes model name that was requested
        - Optionally includes available models
        
        Args:
            model_name: Name of the unavailable model
            available_models: Optional list of available models
        """
        details = {
            "model_name": model_name,
            "available_models": available_models
        }
        message = f"Model '{model_name}' is not available"
        if available_models:
            models_str = "', '".join(available_models)
            message += f". Available models: '{models_str}'"
        
        super().__init__(message, details)


class WorkflowExecutionError(CoordinationError):
    """Exception raised when a workflow execution fails."""
    
    def __init__(self, workflow_name: str, reason: str, state: Optional[Dict[str, Any]] = None):
        """
        [Method intent]
        Initialize a workflow execution error.
        
        [Design principles]
        - Specific error for workflow failures
        - Contextual information about failure state
        
        [Implementation details]
        - Includes workflow name and reason
        - Optionally includes workflow state at failure
        
        Args:
            workflow_name: Name of the workflow that failed
            reason: Reason for the failure
            state: Optional workflow state at failure
        """
        details = {
            "workflow_name": workflow_name,
            "reason": reason,
            "state": state
        }
        message = f"Workflow '{workflow_name}' execution failed: {reason}"
        
        super().__init__(message, details)


class ToolExecutionError(CoordinationError):
    """Exception raised when a tool execution fails."""
    
    def __init__(self, tool_name: str, reason: str, parameters: Optional[Dict[str, Any]] = None):
        """
        [Method intent]
        Initialize a tool execution error.
        
        [Design principles]
        - Specific error for tool failures
        - Contextual information about failure parameters
        
        [Implementation details]
        - Includes tool name and reason
        - Optionally includes parameters used
        
        Args:
            tool_name: Name of the tool that failed
            reason: Reason for the failure
            parameters: Optional parameters used in the tool execution
        """
        details = {
            "tool_name": tool_name,
            "reason": reason
        }
        
        # Add parameters if available, filtering sensitive information
        if parameters:
            filtered_params = {}
            for k, v in parameters.items():
                # Filter sensitive keys
                if k.lower() not in ["password", "token", "api_key", "secret", "credential"]:
                    filtered_params[k] = v if not isinstance(v, str) else (v[:50] + "..." if len(v) > 50 else v)
                else:
                    filtered_params[k] = "[FILTERED]"
            details["parameters"] = filtered_params
        
        message = f"Tool '{tool_name}' execution failed: {reason}"
        
        super().__init__(message, details)


class AgentInitializationError(CoordinationError):
    """Exception raised when agent initialization fails."""
    
    def __init__(self, agent_type: str, reason: str):
        """
        [Method intent]
        Initialize an agent initialization error.
        
        [Design principles]
        - Specific error for agent setup failures
        - Clear distinction between agent types
        
        [Implementation details]
        - Includes agent type and reason
        
        Args:
            agent_type: Type of agent that failed to initialize
            reason: Reason for the failure
        """
        details = {
            "agent_type": agent_type,
            "reason": reason
        }
        message = f"Agent of type '{agent_type}' failed to initialize: {reason}"
        
        super().__init__(message, details)
