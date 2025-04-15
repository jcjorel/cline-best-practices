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
# Defines all exception classes used throughout the MCP server implementation.
# Centralizes exception definitions to avoid circular imports and ensure a
# consistent error handling approach across the MCP server codebase.
###############################################################################
# [Source file design principles]
# - Defines custom exceptions for the MCP server component.
# - Uses descriptive class names that indicate the error type.
# - Includes docstrings for all exceptions with clear error descriptions.
# - Inherits appropriately from standard exception types.
# - Allows for additional context in exception instances via attributes.
###############################################################################
# [Source file constraints]
# - Must only use standard library imports to avoid circular dependencies.
# - Must be importable by all other MCP server modules.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T16:31:15Z : Created exceptions.py file by CodeAssistant
# * Implemented central exception definitions for MCP server
###############################################################################

class ToolNotFoundError(ValueError):
    """Exception raised when a requested MCP tool is not found in the registry."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ResourceNotFoundError(ValueError):
    """Exception raised when a requested MCP resource is not found in the registry."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ComponentNotInitializedError(RuntimeError):
    """Exception raised when a component method is called before initialization."""
    def __init__(self, component_name: str):
        self.component_name = component_name
        message = f"Component '{component_name}' not initialized"
        super().__init__(message)

class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class AuthorizationError(Exception):
    """Exception raised when authorization fails."""
    def __init__(self, message: str, required_permission: str = None):
        self.message = message
        self.required_permission = required_permission
        super().__init__(message)

class ComponentNotFoundError(Exception):
    """Exception raised when a required component is not found."""
    def __init__(self, component_name: str):
        self.component_name = component_name
        message = f"Required component '{component_name}' not found"
        super().__init__(message)

class MalformedRequestError(ValueError):
    """Exception raised when an MCP request is malformed."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details
        super().__init__(message)

class ExecutionError(RuntimeError):
    """Exception raised when an MCP tool execution fails."""
    def __init__(self, message: str, tool_name: str, details: dict = None):
        self.message = message
        self.tool_name = tool_name
        self.details = details
        super().__init__(f"Error executing tool '{tool_name}': {message}")

class MissingDependencyError(ImportError):
    """Exception raised when a required dependency is not available."""
    def __init__(self, dependency_name: str):
        self.dependency_name = dependency_name
        message = f"Required dependency '{dependency_name}' not found"
        super().__init__(message)

class ConfigurationError(ValueError):
    """Exception raised when there is an issue with server configuration."""
    def __init__(self, message: str, config_key: str = None):
        self.message = message
        self.config_key = config_key
        super().__init__(message)
