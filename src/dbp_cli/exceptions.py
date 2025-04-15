###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Defines custom exception classes used throughout the DBP CLI application
# for specific error handling scenarios like configuration issues, authentication
# failures, API errors, etc.
###############################################################################
# [Source file design principles]
# - Provides specific exception types inheriting from a base CLIError.
# - Allows for more granular error catching and reporting.
###############################################################################
# [Source file constraints]
# - None beyond standard Python exception handling.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:56:30Z : Initial creation of CLI exception classes by CodeAssistant
# * Defined base CLIError and specific error types.
###############################################################################

class CLIError(Exception):
    """Base exception class for all DBP CLI errors."""
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code

class ConfigurationError(CLIError):
    """Raised for errors related to loading or accessing configuration."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=2)

class AuthenticationError(CLIError):
    """Raised for authentication failures with the MCP server."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=3)

class AuthorizationError(CLIError):
    """Raised for authorization failures (insufficient permissions)."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=4)

class ConnectionError(CLIError):
    """Raised for network connection errors when contacting the MCP server."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=5)

class APIError(CLIError):
    """Raised for general errors returned by the MCP server API."""
    def __init__(self, message: str, code: str = "API_ERROR"):
        super().__init__(f"API Error [{code}]: {message}", exit_code=6)
        self.code = code

class ClientError(CLIError):
    """Raised for general client-side errors not covered by other exceptions."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=10)

class CommandError(CLIError):
    """Raised for errors specific to command execution logic."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=11)
