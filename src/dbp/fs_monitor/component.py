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
# Implements the FileSystemMonitorComponent class which provides file system
# change detection functionality to the application. This component monitors
# the file system for changes and notifies interested components.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`)
# - Encapsulates platform-specific file system monitoring implementations
# - Provides cross-platform and fallback monitoring capabilities
# - Uses factory pattern to create appropriate monitor for the current platform
# - Operates with a change queue for efficient event processing
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and other system components
# - Platform-specific implementations may have their own dependencies
# - Expects configuration for monitoring settings via InitializationContext
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - src/dbp/core/component.py
# - src/dbp/fs_monitor/factory.py
###############################################################################
# [GenAI tool change history]
# 2025-04-20T01:41:39Z : Completed dependency injection refactoring by CodeAssistant
# * Removed dependencies property
# * Made dependencies parameter required in initialize method
# * Removed conditional logic for backwards compatibility
# 2025-04-19T23:56:00Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter
# * Modified initialization to use injected dependencies when available
# * Improved dependency resolution with explicit error handling
# 2025-04-17T23:22:30Z : Updated to use strongly-typed configuration by CodeAssistant
# * Refactored configuration access to use type-safe get_typed_config() method
# * Enhanced config access for both component configuration and project settings
# * Improved type safety with direct attribute access to configuration properties
# 2025-04-16T20:04:42Z : Initial creation of FileSystemMonitorComponent by CodeAssistant
# * Implemented Component protocol methods and integration with fs_monitor factory
# 2025-04-16T23:47:26Z : Fixed component dependencies by CodeAssistant
# * Added explicit dependency on "change_queue" component to fix initialization order
###############################################################################

import logging
from typing import List, Optional, Any, Dict

from ..core.component import Component, InitializationContext
from .factory import FileSystemMonitorFactory
from .base import FileSystemMonitor
from .queue import ChangeDetectionQueue

logger = logging.getLogger(__name__)

class FileSystemMonitorComponent(Component):
    """
    [Class intent]
    Component wrapper for the file system monitoring functionality that detects
    file system changes and provides them to interested components.
    
    [Implementation details]
    Uses a factory to create the appropriate platform-specific monitor implementation
    and integrates with the change queue for efficient event processing.
    
    [Design principles]
    Single responsibility for file system change detection.
    Platform independence through factory-created implementations.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes a new FileSystemMonitorComponent instance.
        
        [Implementation details]
        Sets up initial state variables.
        
        [Design principles]
        Minimal initialization with deferred monitor creation.
        """
        self._monitor: Optional[FileSystemMonitor] = None
        self._initialized: bool = False
        self._change_queue: Optional[ChangeDetectionQueue] = None
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
        return "fs_monitor"
    
    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
        """
        [Function intent]
        Initializes the file system monitor component.
        
        [Implementation details]
        Uses the factory to create the appropriate platform-specific monitor
        and starts monitoring based on configuration.
        
        [Design principles]
        Platform-independent initialization with configuration-based behavior.
        For Linux systems, strictly enforces the requirement for inotify.
        
        Args:
            context: The initialization context
            dependencies: Dictionary of pre-resolved dependencies {name: component_instance}
        """
        if self._initialized:
            self.logger.warning("FileSystemMonitorComponent already initialized")
            return
        
        # Add robust logger initialization with detailed error handling
        try:
            # First try to get logger from context as per API expectation
            if hasattr(context, 'logger') and context.logger is not None:
                self.logger = context.logger.getChild(self.name)
                self.logger.debug(f"Logger obtained from context.logger: {type(context.logger)}")
            # Fall back to direct access if context doesn't have logger attribute
            else:
                self.logger.debug(f"Context doesn't have logger attribute or it's None: {type(context)}")
                self.logger.debug(f"Context attributes: {dir(context)}")
                # Keep existing logger initialized in __init__
        except Exception as e:
            # Catch any logger initialization issues and log details
            logger.error(f"Logger initialization failed: {e}, context type: {type(context)}")
            logger.error(f"Available context attributes: {dir(context)}")
            # Continue with the existing logger
            
        self.logger.info(f"Initializing component '{self.name}'...")
        
        try:
            # Get configuration and dependencies
            self.logger.debug("Using injected dependencies")
            # Get config from the config_manager component in dependencies
            config_manager = self.get_dependency(dependencies, "config_manager")
            typed_config = config_manager.get_typed_config()
            
            # Get change queue component from dependencies
            queue_component = self.get_dependency(dependencies, "change_queue")
            
            # Validate configuration
            config = typed_config.fs_monitor
            if not config:
                error_msg = f"Missing configuration section for '{self.name}'"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Validate change queue component
            if not hasattr(queue_component, 'get_queue'):
                error_msg = "Queue component missing get_queue method"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            self._change_queue = queue_component.get_queue()
            self.logger.info("Change queue component successfully initialized")
            
            # Get project root from typed configuration
            project_root = typed_config.project.root_path
            if project_root is None:
                error_msg = "Project root path not found in configuration"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Create filesystem monitor using factory
            self.logger.info(f"Creating monitor for platform with project root: {project_root}")
            self._monitor = FileSystemMonitorFactory.create_monitor(
                config=config,
                project_root=project_root
            )
            
            # Start monitoring - strict approach with no conditional checks
            # We assume monitoring should always be enabled
            self._monitor.start()
            self.logger.info("File system monitoring started")
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FileSystemMonitorComponent: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize {self.name}: {e}") from e
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Performs graceful shutdown of the file system monitor component.
        
        [Implementation details]
        Stops the monitor if it's running.
        
        [Design principles]
        Clean resource management and shutdown.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        if self._monitor:
            try:
                self._monitor.stop()
                self.logger.info("File system monitor stopped")
            except Exception as e:
                self.logger.error(f"Error stopping file system monitor: {e}", exc_info=True)
        
        self._initialized = False
        self._monitor = None
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
    
    def get_monitor(self) -> Optional[FileSystemMonitor]:
        """
        [Function intent]
        Returns the underlying file system monitor instance.
        
        [Implementation details]
        Returns the monitor created during initialization.
        
        [Design principles]
        Controlled access to internal implementation.
        
        Returns:
            Optional[FileSystemMonitor]: The monitor instance or None if not initialized
        """
        return self._monitor if self._initialized else None
    
    def register_change_listener(self, listener):
        """
        [Function intent]
        Registers a change listener to receive file system change notifications.
        
        [Implementation details]
        Delegates to the change queue if available.
        
        [Design principles]
        Observer pattern for change notifications.
        
        Args:
            listener: Callable that accepts FileChange objects
            
        Returns:
            bool: True if registered successfully, False otherwise
        """
        if not self._initialized or not self._change_queue:
            self.logger.warning("Cannot register listener, component not fully initialized")
            return False
            
        try:
            # Check if change_queue has register_listener method, add it if not
            if not hasattr(self._change_queue, 'register_listener'):
                self.logger.info("Adding listener support to change queue")
                # The queue doesn't have a register_listener method, so we need to add it directly
                if not hasattr(self._change_queue, '_listeners'):
                    self._change_queue._listeners = []
                
                # Add the listener directly to the queue's internal list
                self._change_queue._listeners.append(listener)
                
                # Monkey patch the add_change method if needed to notify listeners
                if not hasattr(self._change_queue, '_original_add_change'):
                    self._change_queue._original_add_change = self._change_queue.add_event
                    
                    def enhanced_add_event(event):
                        # Call the original method first
                        self._change_queue._original_add_change(event)
                        # Then notify all listeners
                        for l in self._change_queue._listeners:
                            try:
                                l(event)
                            except Exception as e:
                                self.logger.error(f"Error notifying listener about change: {e}")
                    
                    # Replace the method
                    self._change_queue.add_event = enhanced_add_event
                
                self.logger.info("Successfully added listener support to change queue")
                return True
            else:
                # The queue has a register_listener method, use it
                self._change_queue.register_listener(listener)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register change listener: {e}")
            return False
