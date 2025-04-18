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
# Defines the simplified Component base class that all system components must
# extend. Provides a clean and minimal interface for component lifecycle management
# and dependency declaration following KISS principles.
###############################################################################
# [Source file design principles]
# - Ultra-simple interface for component lifecycle management
# - Explicit dependency declaration via simple properties
# - Clear initialization status tracking
# - Minimal required methods (initialize, shutdown)
# - Single responsibility for lifecycle management
###############################################################################
# [Source file constraints]
# - Must be straightforward enough for all components to implement correctly
# - Must provide clear indication of initialization status
# - Must not introduce complexity in dependency declaration
# - Requires components to set _initialized flag properly
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-17T23:18:30Z : Added strong typing to Component.initialize() method by CodeAssistant
# * Updated initialize() method signature to use typed InitializationContext parameter
# * Enhanced Component documentation to reflect strong typing support
# * Improved method signature for better IDE support and type checking
# 2025-04-17T23:10:30Z : Enhanced InitializationContext with typed configuration by CodeAssistant
# * Added typed_config field to provide access to strongly-typed configuration
# * Added get_typed_config() method for type-safe configuration access
# * Improved documentation with more detailed function intent and design principles
# * Added forward references for proper type annotations
# 2025-04-17T08:54:49Z : Added get_debug_info method for better diagnostics by CodeAssistant
# * Implemented debug information gathering for component failure analysis
# * Enhanced Component base class with diagnostic capabilities
# * Added documentation for new debugging methods
# 2025-04-16T15:45:16Z : Replaced with simplified Component implementation by CodeAssistant
# * Implemented minimal Component interface with simplified lifecycle methods
###############################################################################

import logging
import inspect
import sys
import traceback
from typing import Any, Dict, List, TypeVar, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass, field

# Type definitions
if TYPE_CHECKING:
    from .system import ComponentSystem  # Forward reference
    from ..config.config_schema import AppConfig  # Forward reference for type annotations

# Type variable for the concrete component type
T = TypeVar('T', bound='Component')

@dataclass
class InitializationContext:
    """
    [Class intent]
    Context object passed to components during initialization that provides
    access to necessary resources and configuration.
    
    [Implementation details]
    Contains the configuration manager reference, logger instance, and typed configuration object.
    Provides methods to access other components and retrieve strongly-typed configuration.
    
    [Design principles]
    Dependency injection for component initialization.
    Strong typing for configuration access.
    """
    config: Any  # For backward compatibility
    logger: logging.Logger
    typed_config: Optional['AppConfig'] = None  # New field for strongly-typed configuration
    
    def get_component(self, name: str) -> Any:
        """
        [Function intent]
        Provides access to other initialized components by name.
        
        [Implementation details]
        Retrieves components from the ComponentSystem singleton.
        
        [Design principles]
        Component dependency resolution without direct coupling.
        
        Args:
            name: Name of the component to retrieve
            
        Returns:
            The requested component instance or None if not found
        """
        from .system import ComponentSystem
        system = ComponentSystem.get_instance()
        return system.get_component(name) if system else None
    
    def get_typed_config(self) -> 'AppConfig':
        """
        [Function intent]
        Provides access to the strongly-typed configuration model.
        
        [Implementation details]
        Returns the stored typed_config if available, otherwise returns
        a default AppConfig instance.
        
        [Design principles]
        Type safety for configuration access.
        
        Returns:
            AppConfig: The strongly-typed configuration model
        """
        if self.typed_config is None:
            # This should not happen if the context is properly initialized,
            # but we provide a fallback for robustness
            from ..config.config_schema import AppConfig
            return AppConfig()
        
        return self.typed_config

class Component:
    """
    [Class intent]
    Base class for all system components with simplified initialization approach.
    All DBP components must inherit from this class and implement the required
    methods to participate in the component lifecycle.
    
    [Implementation details]
    Provides simple lifecycle methods (initialize, shutdown) and dependency
    declaration properties. Initialization status is tracked via a simple boolean
    flag that component implementations must set.
    
    Components receive a strongly-typed InitializationContext object during initialization
    that provides access to configuration, logger, and other system resources.
    
    [Design principles]
    Single responsibility for component lifecycle management.
    Simple dependency declaration with explicit dependencies list.
    Clear initialization status tracking with _initialized flag.
    Strong typing for component initialization.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes the component instance with basic setup.
        
        [Implementation details]
        Sets the _initialized flag to False by default.
        
        [Design principles]
        Minimal initialization - concrete setup happens in initialize() method.
        """
        self._initialized = False
        self.logger = None  # Will be set during initialize()
        self._initialization_error = None  # Track last initialization error
        
    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of this component, used for registration and dependency references.
        
        [Implementation details]
        Must be implemented by concrete component classes.
        
        [Design principles]
        Explicit naming for clear component identification.
        
        Returns:
            str: Unique component name
        
        Raises:
            NotImplementedError: If not implemented by concrete component
        """
        raise NotImplementedError("Component must implement name property")
    
    @property
    def dependencies(self) -> List[str]:
        """
        [Function intent]
        Returns a list of component names that this component depends on.
        
        [Implementation details]
        Default implementation returns an empty list (no dependencies).
        Override in concrete components to declare dependencies.
        
        [Design principles]
        Explicit dependency declaration for clear initialization order.
        
        Returns:
            List[str]: List of component names this component depends on
        """
        return []
    
    @property
    def is_initialized(self) -> bool:
        """
        [Function intent]
        Indicates whether this component has been successfully initialized.
        
        [Implementation details]
        Returns the value of the _initialized flag which components must set.
        
        [Design principles]
        Simple boolean flag for clear initialization status.
        
        Returns:
            bool: True if component is initialized, False otherwise
        """
        return self._initialized
    
    def initialize(self, context: 'InitializationContext') -> None:
        """
        [Function intent]
        Initializes the component with context information and prepares it for use.
        
        [Implementation details]
        Must be implemented by concrete component classes.
        MUST set self._initialized = True when initialization succeeds.
        
        [Design principles]
        Explicit initialization with clear success/failure indication.
        Strong typing for context parameter.
        
        Args:
            context: Initialization context with configuration and resources
            
        Raises:
            NotImplementedError: If not implemented by concrete component
        """
        raise NotImplementedError("Component must implement initialize method")
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Gracefully shuts down the component and releases all resources.
        
        [Implementation details]
        Must be implemented by concrete component classes.
        MUST set self._initialized = False when shutdown completes.
        
        [Design principles]
        Clean resource release with clear status indication.
        
        Raises:
            NotImplementedError: If not implemented by concrete component
        """
        raise NotImplementedError("Component must implement shutdown method")
        
    def get_debug_info(self) -> Dict[str, Any]:
        """
        [Function intent]
        Provides diagnostic information about the component state for debugging.
        
        [Implementation details]
        Gathers key component details including class details, initialization status,
        and any instance attributes that might be useful for diagnosing issues.
        Components may override to add component-specific diagnostic information.
        
        [Design principles]
        Provides actionable debug information when component initialization fails.
        Non-intrusive collection of state data with safe defaults.
        
        Returns:
            Dict[str, Any]: Dictionary containing component debug information
        """
        # Basic component information
        debug_info = {
            "class_name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "initialized": self._initialized,
            "dependencies": self.dependencies,
            "has_logger": self.logger is not None
        }
        
        # Collect initialization error if present
        if hasattr(self, '_initialization_error') and self._initialization_error:
            error_info = {
                "error_type": type(self._initialization_error).__name__,
                "error_message": str(self._initialization_error),
            }
            debug_info["initialization_error"] = error_info
        
        # Add component-specific attributes that might help with diagnosis
        # (but avoid large objects, sensitive data, or complex structures)
        for attr_name, attr_value in self.__dict__.items():
            # Skip internal attributes, logger, large objects
            if attr_name.startswith('_') or attr_name == 'logger':
                continue
                
            # For simple types that are useful for diagnosis
            if isinstance(attr_value, (bool, int, str, float)) or attr_value is None:
                debug_info[f"attr_{attr_name}"] = attr_value
            else:
                # Just note the type for complex objects
                debug_info[f"attr_{attr_name}_type"] = type(attr_value).__name__
        
        return debug_info
        
    def set_initialization_error(self, error: Exception) -> None:
        """
        [Function intent]
        Records an initialization error for improved diagnostics.
        
        [Implementation details]
        Stores the exception that caused initialization failure.
        
        [Design principles]
        Preserves error context for later diagnostic reporting.
        
        Args:
            error: The exception that caused initialization to fail
        """
        self._initialization_error = error
        
        # Also log the current traceback if a logger is available
        if self.logger:
            self.logger.debug(f"Component '{self.name}' initialization error recorded: {error}")
            
    def get_error_details(self) -> Dict[str, Any]:
        """
        [Function intent]
        Provides detailed information about initialization failures.
        
        [Implementation details]
        Returns comprehensive exception information including traceback
        if available from the most recent initialization failure.
        
        [Design principles]
        Preserves complete error context for diagnosis of initialization failures.
        
        Returns:
            Dict[str, Any]: Dictionary containing detailed error information or empty dict if no error
        """
        if not hasattr(self, '_initialization_error') or not self._initialization_error:
            return {}
            
        error = self._initialization_error
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_module": type(error).__module__
        }
        
        # Try to get traceback if available
        if hasattr(error, '__traceback__') and error.__traceback__:
            # Format the traceback as text
            tb_lines = traceback.format_exception(
                type(error), error, error.__traceback__
            )
            error_details["traceback"] = ''.join(tb_lines)
            
            # Get the frame where the exception occurred
            frame_info = traceback.extract_tb(error.__traceback__)
            if frame_info:
                last_frame = frame_info[-1]
                error_details["file"] = last_frame.filename
                error_details["line"] = last_frame.lineno
                error_details["function"] = last_frame.name
                error_details["line_context"] = last_frame.line
                
        return error_details
