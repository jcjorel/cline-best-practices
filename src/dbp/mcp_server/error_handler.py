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
# Implements the ErrorHandler class for the MCP Server. This class catches
# exceptions raised during request processing (authentication, authorization,
# tool execution, resource access) and translates them into standardized
# MCPError objects suitable for inclusion in an MCPResponse.
###############################################################################
# [Source file design principles]
# - Centralizes error handling logic for MCP requests.
# - Maps specific Python exceptions (e.g., ComponentNotFoundError, Auth errors)
#   to predefined MCP error codes and messages.
# - Provides a default handler for unexpected exceptions.
# - Logs errors appropriately.
# - Design Decision: Centralized Error Handler (2025-04-15)
#   * Rationale: Ensures consistent error reporting format across all MCP tools and resources. Simplifies error handling in individual tool/resource implementations.
#   * Alternatives considered: Handling errors within each tool/resource (inconsistent, boilerplate).
###############################################################################
# [Source file constraints]
# - Depends on `MCPError` and `MCPRequest` data models.
# - Depends on custom exception types defined elsewhere (e.g., `ComponentNotFoundError`, `AuthenticationError`).
# - The mapping between Python exceptions and MCP error codes needs to be maintained.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# other:- src/dbp/mcp_server/data_models.py
# other:- src/dbp/mcp_server/auth.py (Defines Auth exceptions)
# other:- src/dbp/mcp_server/adapter.py (Defines ComponentNotFoundError)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T16:36:30Z : Updated error handler to use centralized exceptions by CodeAssistant
# * Modified imports to use exceptions from centralized exceptions module
# * Added additional error mappings for new exception types
# 2025-04-15T10:50:15Z : Initial creation of ErrorHandler class by CodeAssistant
# * Implemented mapping from Python exceptions to MCPError objects.
###############################################################################

import logging
from typing import Optional, Dict, Any

# Assuming necessary imports
try:
    from .data_models import MCPError, MCPRequest
    # Import custom exceptions from the centralized exceptions module
    from .exceptions import (
        AuthenticationError, AuthorizationError, ComponentNotFoundError,
        ToolNotFoundError, ResourceNotFoundError, MalformedRequestError,
        ExecutionError, ConfigurationError, MissingDependencyError
    )
except ImportError as e:
    logging.getLogger(__name__).error(f"ErrorHandler ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    MCPError = object
    MCPRequest = object
    AuthenticationError = Exception
    AuthorizationError = Exception
    ComponentNotFoundError = Exception
    ToolNotFoundError = Exception
    ResourceNotFoundError = Exception
    MalformedRequestError = Exception
    ExecutionError = Exception
    ConfigurationError = Exception
    MissingDependencyError = Exception


logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    Handles exceptions raised during MCP request processing and converts them
    into standardized MCPError objects.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ErrorHandler.

        Args:
            logger_override: Optional logger instance.
        """
        self.logger = logger_override or logger
        self.logger.debug("ErrorHandler initialized.")

    def handle_error(self, error: Exception, request: Optional[MCPRequest] = None) -> MCPError:
        """
        Processes an exception and returns a corresponding MCPError object.

        Args:
            error: The exception that was raised.
            request: The original MCPRequest that caused the error (optional, for context).

        Returns:
            An MCPError object representing the error.
        """
        request_id = getattr(request, 'id', 'unknown')
        error_type = type(error).__name__
        self.logger.error(f"Handling error ({error_type}) for request ID '{request_id}': {error}", exc_info=True)

        # --- Map specific known exceptions to MCP error codes ---

        if isinstance(error, AuthenticationError):
            return MCPError(
                code="AUTHENTICATION_FAILED",
                message=str(error) or "Authentication failed.",
                data=None
            )
        elif isinstance(error, AuthorizationError):
            return MCPError(
                code="AUTHORIZATION_FAILED",
                message=str(error) or "Authorization failed.",
                data={"required_permission": getattr(error, 'required_permission', None)}
            )
        elif isinstance(error, ComponentNotFoundError):
            return MCPError(
                code="DEPENDENCY_ERROR",
                message=f"Required system component '{error.component_name}' not found or not ready.",
                data={"component_name": error.component_name}
            )
        elif isinstance(error, FileNotFoundError): # Handle standard Python errors
             return MCPError(
                  code="RESOURCE_NOT_FOUND",
                  message=f"File or resource not found: {error}",
                  data={"filename": getattr(error, 'filename', None)}
             )
        elif isinstance(error, PermissionError):
             return MCPError(
                  code="PERMISSION_DENIED",
                  message=f"Permission denied: {error}",
                  data={"filename": getattr(error, 'filename', None)}
             )
        elif isinstance(error, ValueError): # E.g., invalid parameters for a tool
             return MCPError(
                  code="INVALID_PARAMETERS",
                  message=f"Invalid value or parameter provided: {error}",
                  data=None
             )
        elif isinstance(error, NotImplementedError):
             return MCPError(
                  code="NOT_IMPLEMENTED",
                  message=f"Functionality not implemented: {error}",
                  data=None
             )
        elif isinstance(error, ToolNotFoundError):
             return MCPError(
                  code="TOOL_NOT_FOUND",
                  message=str(error),
                  data=None
             )
        elif isinstance(error, ResourceNotFoundError):
             return MCPError(
                  code="RESOURCE_NOT_FOUND",
                  message=str(error),
                  data=None
             )
        elif isinstance(error, MalformedRequestError):
             return MCPError(
                  code="MALFORMED_REQUEST",
                  message=str(error),
                  data=getattr(error, 'details', None)
             )
        elif isinstance(error, ExecutionError):
             return MCPError(
                  code="EXECUTION_ERROR",
                  message=str(error),
                  data={
                       "tool_name": getattr(error, 'tool_name', None),
                       "details": getattr(error, 'details', None)
                  }
             )
        elif isinstance(error, ConfigurationError):
             return MCPError(
                  code="CONFIGURATION_ERROR",
                  message=str(error),
                  data={"config_key": getattr(error, 'config_key', None)}
             )
        elif isinstance(error, MissingDependencyError):
             return MCPError(
                  code="MISSING_DEPENDENCY",
                  message=str(error),
                  data={"dependency_name": getattr(error, 'dependency_name', None)}
             )
        # Add mappings for other specific custom exceptions from your components
        # elif isinstance(error, SpecificToolError):
        #     return MCPError(code="TOOL_EXECUTION_ERROR", message=str(error), data=error.details)

        # --- Default handler for unexpected exceptions ---
        else:
            return MCPError(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal error occurred.",
                # Include error type and message in data for debugging, but be cautious
                # about exposing sensitive details to the client.
                data={"error_type": error_type, "detail": str(error)}
            )
