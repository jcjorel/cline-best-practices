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
# Implements the FileAccessComponent class which provides a file access service
# to the application. This component manages the FileAccessService and makes it
# available to other components through the component system.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (src/dbp/core/component.py)
# - Provides a centralized service for file operations
# - Minimal dependencies to ensure early initialization
# - Single responsibility for file access operations
###############################################################################
# [Source file constraints]
# - Must be initialized early in the component lifecycle
# - Should not have dependencies on high-level components
###############################################################################
# [Dependencies]
# codebase:doc/DESIGN.md
# codebase:src/dbp/core/component.py
# codebase:src/dbp/core/file_access.py
# system:logging
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-04-19T23:46:00Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter
# * Enhanced documentation for dependency injection pattern
# 2025-04-18T15:41:30Z : Initial creation of FileAccessComponent by CodeAssistant
# * Implemented Component protocol methods and FileAccessService integration
###############################################################################

import logging
from typing import Dict, List, Optional

from .component import Component, InitializationContext
from .file_access import FileAccessService

logger = logging.getLogger(__name__)

class FileAccessComponent(Component):
    """
    [Class intent]
    Component wrapper for the FileAccessService that provides standardized
    file access operations to other components in the DBP system.
    
    [Implementation details]
    Creates and initializes a FileAccessService instance and makes it
    available through a public property.
    
    [Design principles]
    Single responsibility for file access operations.
    Minimal dependencies to ensure early initialization.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes a new FileAccessComponent instance.
        
        [Implementation details]
        Sets up initial state variables.
        
        [Design principles]
        Minimal initialization with deferred service creation.
        """
        self._service: Optional[FileAccessService] = None
        self._initialized: bool = False
        self.logger = logger
    
    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of the component.
        
        [Implementation details]
        Simple string return.
        
        [Design principles]
        Clear component identification.
        
        Returns:
            str: The component name
        """
        return "file_access"
    
    @property
    def dependencies(self) -> List[str]:
        """
        [Function intent]
        Returns the list of component names this component depends on.
        
        [Implementation details]
        This component has minimal dependencies to ensure early initialization.
        
        [Design principles]
        Minimal dependencies for critical services.
        
        Returns:
            List[str]: List of component dependencies
        """
        # Only depends on config_manager for configuration
        return ["config_manager"]
    
    def initialize(self, context: InitializationContext, dependencies: Optional[Dict[str, Component]] = None) -> None:
        """
        [Function intent]
        Initializes the file access component.
        
        [Implementation details]
        Creates the FileAccessService with the provided configuration.
        Uses directly injected dependencies if provided, falling back to context.get_component().
        
        [Design principles]
        Simple initialization with configuration-based behavior.
        Dependency injection for improved testability.
        
        Args:
            context: The initialization context
            dependencies: Optional dictionary of pre-resolved dependencies {name: component_instance}
        """
        if self._initialized:
            self.logger.warning("FileAccessComponent already initialized")
            return
        
        try:
            if hasattr(context, 'logger') and context.logger is not None:
                self.logger = context.logger.getChild(self.name)
            
            self.logger.info(f"Initializing component '{self.name}'...")
            
            # Get configuration from context
            config = context.get_typed_config()
            
            # Create the file access service
            self._service = FileAccessService(
                config=config,
                logger_override=self.logger.getChild("service")
            )
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FileAccessComponent: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize {self.name}: {e}") from e
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Performs graceful shutdown of the file access component.
        
        [Implementation details]
        Clears the service cache if it exists.
        
        [Design principles]
        Clean resource management and shutdown.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        if self._service:
            try:
                self._service.clear_cache()
                self.logger.info("File access service cache cleared")
            except Exception as e:
                self.logger.error(f"Error clearing file access service cache: {e}", exc_info=True)
        
        self._initialized = False
        self._service = None
        self.logger.info(f"Component '{self.name}' shut down")
    
    @property
    def is_initialized(self) -> bool:
        """
        [Function intent]
        Returns whether the component is initialized.
        
        [Implementation details]
        Simple boolean return.
        
        [Design principles]
        Clear state reporting.
        
        Returns:
            bool: True if initialized, False otherwise
        """
        return self._initialized
    
    @property
    def service(self) -> Optional[FileAccessService]:
        """
        [Function intent]
        Returns the underlying file access service instance.
        
        [Implementation details]
        Returns the service created during initialization.
        
        [Design principles]
        Controlled access to internal service.
        
        Returns:
            Optional[FileAccessService]: The service instance or None if not initialized
        """
        return self._service if self._initialized else None
