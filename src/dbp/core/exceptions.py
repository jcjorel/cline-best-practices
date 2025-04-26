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
# Defines core exceptions for the DBP system, specifically for component management.
# Provides standardized, specific exception types to enable precise error handling
# throughout the application rather than using generic exceptions.
###############################################################################
# [Source file design principles]
# - Clear, descriptive exception naming
# - Hierarchical exception structure with appropriate base classes
# - Consistent error message formatting
# - Specific exceptions for different error conditions
# - Design Decision: Component Exception Hierarchy (2025-04-25)
#   * Rationale: Enables targeted exception handling with specific error types
#   * Alternatives considered: Using generic RuntimeError (less precise)
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with existing code
# - Should provide informative error messages by default
# - Should support optional additional context in error messages
# - Should allow passing the causing exception when appropriate
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-26T01:45:00Z : Added DBPBaseException and updated inheritance hierarchy by CodeAssistant
# * Added DBPBaseException as the root exception class for all system exceptions
# * Updated ComponentError to inherit from DBPBaseException instead of Exception
# * Updated DeprecatedMethodError to inherit from DBPBaseException
# 2025-04-25T09:58:54Z : Added DeprecatedMethodError by CodeAssistant
# * Created a new exception class for deprecated method calls
# * Added descriptive error messaging with migration guidance
# * Included support for alternative method suggestion
# 2025-04-25T08:40:00Z : Created initial exceptions file by CodeAssistant
# * Added base ComponentError class
# * Added ComponentNotFoundError for missing components
# * Added ComponentNotInitializedError for uninitialized components
# * Added CircularDependencyError for dependency cycles
###############################################################################

"""
Core exceptions for the DBP system's component architecture.

This module defines the custom exceptions used throughout the component system
to provide specific, actionable error messages and enable targeted exception handling.
"""

class DBPBaseException(Exception):
    """
    [Class intent]
    Base exception class for all exceptions in the DBP system.
    
    [Design principles]
    Root exception class that all other system-specific exceptions should inherit from.
    Allows for catching all DBP-related exceptions with a single except clause.
    
    [Implementation details]
    Simple wrapper around the standard Exception class to establish inheritance hierarchy.
    """
    pass

class ComponentError(DBPBaseException):
    """
    [Class intent]
    Base exception class for all component-related errors in the DBP system.
    
    [Implementation details]
    Provides consistent error formatting and optional context for all derived exceptions.
    
    [Design principles]
    Base class for component exception hierarchy allowing for broad exception catching.
    """
    def __init__(self, message: str, component_name: str = None):
        """
        [Function intent]
        Initializes the ComponentError with a message and optional component name.
        
        [Implementation details]
        Formats the error message to include the component name if provided.
        
        [Design principles]
        Standardized error formatting with optional context.
        
        Args:
            message: The error message
            component_name: Optional name of the component related to the error
        """
        if component_name:
            formatted_message = f"Component '{component_name}': {message}"
        else:
            formatted_message = message
        super().__init__(formatted_message)
        self.component_name = component_name


class ComponentNotFoundError(ComponentError):
    """
    [Class intent]
    Exception raised when attempting to access a component that is not registered.
    
    [Implementation details]
    Provides a clear error message about the missing component.
    
    [Design principles]
    Specific exception type for targeted handling of non-existent components.
    """
    def __init__(self, component_name: str):
        """
        [Function intent]
        Initializes the ComponentNotFoundError with a component name.
        
        [Implementation details]
        Creates a standardized error message for missing components.
        
        [Design principles]
        Clear, descriptive error messaging with consistent format.
        
        Args:
            component_name: Name of the component that was not found
        """
        super().__init__("Component not found or not registered", component_name)


class ComponentNotInitializedError(ComponentError):
    """
    [Class intent]
    Exception raised when attempting to use a component that is registered but not initialized.
    
    [Implementation details]
    Provides a clear error message about the uninitialized component.
    
    [Design principles]
    Specific exception type for targeted handling of uninitialized components.
    """
    def __init__(self, component_name: str):
        """
        [Function intent]
        Initializes the ComponentNotInitializedError with a component name.
        
        [Implementation details]
        Creates a standardized error message for uninitialized components.
        
        [Design principles]
        Clear, descriptive error messaging with consistent format.
        
        Args:
            component_name: Name of the component that is not initialized
        """
        super().__init__("Component not initialized", component_name)


class CircularDependencyError(ComponentError):
    """
    [Class intent]
    Exception raised when a circular dependency is detected during component initialization.
    
    [Implementation details]
    Provides detailed information about the components involved in the circular dependency.
    
    [Design principles]
    Specific exception type for dependency resolution failures with detailed context.
    """
    def __init__(self, message: str):
        """
        [Function intent]
        Initializes the CircularDependencyError with a detailed message.
        
        [Implementation details]
        Uses the provided message which contains details about the circular dependency.
        
        [Design principles]
        Detailed error messaging for complex dependency issues.
        
        Args:
            message: Detailed message describing the circular dependency
        """
        super().__init__(message)


class DeprecatedMethodError(DBPBaseException):
    """
    [Class intent]
    Exception raised when a deprecated method is called.
    
    [Implementation details]
    Provides information about the deprecated method and its replacement.
    
    [Design principles]
    Clear indication of deprecated functionality with migration guidance.
    """
    def __init__(self, method_name: str, alternative: str = None):
        """
        [Function intent]
        Initializes the DeprecatedMethodError with method information.
        
        [Implementation details]
        Creates a standardized error message with migration guidance.
        
        [Design principles]
        Informative error messaging with clear migration path.
        
        Args:
            method_name: Name of the deprecated method
            alternative: Optional alternative method to use instead
        """
        if alternative:
            message = f"Method '{method_name}' is deprecated. Use '{alternative}' instead."
        else:
            message = f"Method '{method_name}' is deprecated and should not be used."
        super().__init__(message)
        self.method_name = method_name
        self.alternative = alternative
