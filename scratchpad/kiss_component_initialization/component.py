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
# 2025-04-16T15:29:45Z : Initial creation of simplified Component class by CodeAssistant
# * Implemented minimal Component interface with simplified lifecycle methods
###############################################################################

import logging
from typing import Any, List, TypeVar, TYPE_CHECKING

# Type definitions
if TYPE_CHECKING:
    from .system import ComponentSystem  # Forward reference

# Type variable for the concrete component type
T = TypeVar('T', bound='Component')

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
    
    [Design principles]
    Single responsibility for component lifecycle management.
    Simple dependency declaration with explicit dependencies list.
    Clear initialization status tracking with _initialized flag.
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
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the component with configuration and prepares it for use.
        
        [Implementation details]
        Must be implemented by concrete component classes.
        MUST set self._initialized = True when initialization succeeds.
        
        [Design principles]
        Explicit initialization with clear success/failure indication.
        
        Args:
            config: Configuration object with application settings
            
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
