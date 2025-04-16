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
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/core/component.py
# - src/dbp/fs_monitor/factory.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T20:04:42Z : Initial creation of FileSystemMonitorComponent by CodeAssistant
# * Implemented Component protocol methods and integration with fs_monitor factory
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
    
    @property
    def dependencies(self) -> List[str]:
        """
        [Function intent]
        Returns the list of component names this component depends on.
        
        [Implementation details]
        Returns list of dependencies.
        
        [Design principles]
        Explicit dependency declaration.
        
        Returns:
            List[str]: List of component dependencies
        """
        # Depends on config for settings and queue for event delivery
        return ["config_manager"]
    
    def initialize(self, context: InitializationContext) -> None:
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
        """
        if self._initialized:
            self.logger.warning("FileSystemMonitorComponent already initialized")
            return
        
        self.logger = context.logger.getChild(self.name)
        self.logger.info(f"Initializing component '{self.name}'...")
        
        try:
            # Get monitor configuration
            config = context.config.get(self.name, {})
            
            # Get or create change queue
            try:
                queue_component = context.get_component("change_queue")
                if hasattr(queue_component, 'get_queue'):
                    self._change_queue = queue_component.get_queue()
                    self.logger.info("Using queue from change_queue component")
                else:
                    raise AttributeError("Queue component has no get_queue method")
            except (KeyError, AttributeError) as e:
                self.logger.warning(f"Could not get change_queue component: {e}, creating internal queue")
                from .queue import ChangeDetectionQueue
                self._change_queue = ChangeDetectionQueue(config)
            
            # Get project root from configuration
            project_root = config.get('project_root')
            if not project_root:
                # Try to determine from context if available
                try:
                    if hasattr(context, 'app_path'):
                        project_root = context.app_path
                    elif hasattr(context.config, 'get_app_path'):
                        project_root = context.config.get_app_path()
                except (AttributeError, Exception):
                    self.logger.warning("Could not determine project root path")
            
            # Create filesystem monitor using factory
            self.logger.info(f"Creating monitor for platform with project root: {project_root}")
            self._monitor = FileSystemMonitorFactory.create_monitor(
                config=config,
                project_root=project_root
            )
            
            # Start monitoring if enabled
            if config.get('enabled', True):
                self._monitor.start()
                self.logger.info(f"File system monitoring started")
            else:
                self.logger.info(f"File system monitoring disabled in configuration")
            
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
            self._change_queue.register_listener(listener)
            return True
        except Exception as e:
            self.logger.error(f"Failed to register change listener: {e}")
            return False
