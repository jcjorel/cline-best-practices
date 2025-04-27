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
# Implements the FileAccessComponent class which provides file access services
# to the application. This component manages the DBPFile cache and makes file
# access utilities available to other components through the component system.
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
# system:pathlib
###############################################################################
# [GenAI tool change history]
# 2025-04-27T23:24:00Z : Updated to use DBPFile instead of FileAccessService by CodeAssistant
# * Removed FileAccessService dependency
# * Added methods to work with DBPFile instances
# * Added LRU cache configuration from component config
# 2025-04-19T23:46:00Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter
# * Enhanced documentation for dependency injection pattern
# 2025-04-18T15:41:30Z : Initial creation of FileAccessComponent by CodeAssistant
# * Implemented Component protocol methods and FileAccessService integration
###############################################################################

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from .component import Component, InitializationContext
from .file_access import get_dbp_file, configure_dbp_file_cache, clear_dbp_file_cache, remove_from_cache, DBPFile

logger = logging.getLogger(__name__)

class FileAccessComponent(Component):
    """
    [Class intent]
    Component wrapper for file access operations that provides standardized
    file access utilities to other components in the DBP system.
    
    [Implementation details]
    Manages the DBPFile cache and provides methods to access file metadata and content.
    
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
        Minimal initialization with deferred configuration.
        """
        self._initialized: bool = False
        self._cache_size: int = 100  # Default cache size
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
        Configures the DBPFile cache with the provided configuration.
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
            
            # Configure the DBPFile cache size from config
            self._cache_size = config.file_access.cache_size
            
            # Configure the DBPFile cache
            configure_dbp_file_cache(maxsize=self._cache_size)
            self.logger.info(f"DBPFile cache configured with size {self._cache_size}")
            
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
        Clears the DBPFile cache.
        
        [Design principles]
        Clean resource management and shutdown.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        try:
            clear_dbp_file_cache()
            self.logger.info("DBPFile cache cleared")
        except Exception as e:
            self.logger.error(f"Error clearing DBPFile cache: {e}", exc_info=True)
        
        self._initialized = False
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
    
    def get_file(self, file_path: Union[str, Path]) -> DBPFile:
        """
        [Function intent]
        Returns a DBPFile instance for the specified file path.
        
        [Implementation details]
        Uses the get_dbp_file function to retrieve a cached DBPFile instance.
        
        [Design principles]
        Efficient file access through caching.
        
        Args:
            file_path: Path to the file
            
        Returns:
            DBPFile: A DBPFile instance for the specified path
            
        Raises:
            RuntimeError: If the component is not initialized
        """
        if not self._initialized:
            raise RuntimeError("FileAccessComponent not initialized")
        
        return get_dbp_file(file_path)
    
    def remove_from_cache(self, file_path: Union[str, Path]) -> bool:
        """
        [Function intent]
        Removes a specific file from the DBPFile cache.
        
        [Implementation details]
        Uses the remove_from_cache function to remove a file from the cache.
        
        [Design principles]
        Targeted cache invalidation for specific files.
        
        Args:
            file_path: Path to the file to remove from cache
            
        Returns:
            bool: True if the file was in the cache and removed, False otherwise
            
        Raises:
            RuntimeError: If the component is not initialized
        """
        if not self._initialized:
            raise RuntimeError("FileAccessComponent not initialized")
        
        return remove_from_cache(file_path)
    
    def clear_cache(self) -> None:
        """
        [Function intent]
        Clears the entire DBPFile cache.
        
        [Implementation details]
        Uses the clear_dbp_file_cache function to clear the cache.
        
        [Design principles]
        Complete cache invalidation for memory management.
        
        Raises:
            RuntimeError: If the component is not initialized
        """
        if not self._initialized:
            raise RuntimeError("FileAccessComponent not initialized")
        
        clear_dbp_file_cache()
        self.logger.info("DBPFile cache cleared")
    
    def reconfigure_cache(self, cache_size: int) -> None:
        """
        [Function intent]
        Reconfigures the DBPFile cache with a new size.
        
        [Implementation details]
        Uses the configure_dbp_file_cache function to update the cache size.
        
        [Design principles]
        Runtime configuration of caching behavior.
        
        Args:
            cache_size: New maximum number of entries in the cache
            
        Raises:
            RuntimeError: If the component is not initialized
            ValueError: If cache_size is not positive
        """
        if not self._initialized:
            raise RuntimeError("FileAccessComponent not initialized")
        
        if cache_size <= 0:
            raise ValueError("Cache size must be positive")
        
        self._cache_size = cache_size
        configure_dbp_file_cache(maxsize=cache_size)
        self.logger.info(f"DBPFile cache reconfigured with size {cache_size}")
