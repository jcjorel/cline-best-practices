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
# This file implements the main component class for the file system monitor.
# It coordinates the various subcomponents (watch manager, event dispatcher,
# and platform monitor) and provides a simplified interface for other components
# to register listeners for file system events.
###############################################################################
# [Source file design principles]
# - Centralized coordination of fs_monitor subcomponents
# - Simplified interface for other components
# - Configuration-driven behavior
# - Clean lifecycle management
# - Thread-safe operations
###############################################################################
# [Source file constraints]
# - Must properly initialize and manage subcomponents 
# - Must maintain thread safety for concurrent operations
# - Must handle configuration changes gracefully
# - Must provide a clean API for other components
# - Must ensure proper resource cleanup during shutdown
###############################################################################
# [Dependencies]
# system:logging
# system:os
# system:threading
# system:typing
# codebase:src/dbp/core/component.py
# codebase:src/dbp/config/config_manager.py
# codebase:src/dbp/fs_monitor/watch_manager.py
# codebase:src/dbp/fs_monitor/dispatch/event_dispatcher.py
# codebase:src/dbp/fs_monitor/platforms/factory.py 
# codebase:src/dbp/fs_monitor/core/listener.py
# codebase:src/dbp/fs_monitor/dispatch/thread_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T01:04:00Z : Updated import paths for module reorganization by CodeAssistant
# * Updated imports to use core/, dispatch/, and platforms/ submodules  
# * Updated dependencies section to reflect the new file locations
# 2025-04-29T00:28:00Z : Initial implementation of FSMonitorComponent for fs_monitor redesign by CodeAssistant
# * Created FSMonitorComponent class with lifecycle management
# * Implemented configuration handling
# * Added listener registration methods
###############################################################################

import logging
import os
import threading
from typing import Dict, List, Optional, Set, Any

from ..core.component import Component
from ..config.config_manager import ConfigManager
from .watch_manager import WatchManager
from .dispatch.event_dispatcher import EventDispatcher
from .dispatch.thread_manager import ThreadPriority
from .platforms.factory import create_platform_monitor
from .core.listener import FileSystemEventListener

logger = logging.getLogger(__name__)


class FSMonitorComponent(Component):
    """
    [Class intent]
    Main component class for the file system monitor.
    
    [Design principles]
    - Centralized coordination of fs_monitor subcomponents
    - Simplified interface for other components
    - Configuration-driven behavior
    - Clean lifecycle management
    
    [Implementation details]
    - Manages watch_manager, event_dispatcher, and platform_monitor
    - Handles component configuration
    - Provides registration methods for other components
    """
    
    def __init__(self, config_manager: ConfigManager) -> None:
        """
        [Function intent]
        Initialize the FSMonitorComponent.
        
        [Design principles]
        - Component-based architecture
        - Dependency injection
        
        [Implementation details]
        - Stores reference to config_manager
        - Initializes internal state
        
        Args:
            config_manager: Reference to the application's configuration manager
        """
        super().__init__(name="fs_monitor", dependencies=["config"])
        self._config_manager = config_manager
        self._watch_manager = None
        self._event_dispatcher = None
        self._platform_monitor = None
        self._lock = threading.RLock()
        self._started = False
    
    def initialize(self) -> None:
        """
        [Function intent]
        Initialize the component.
        
        [Design principles]
        - Clean initialization sequence
        - Order-dependent initialization
        
        [Implementation details]
        - Creates watch_manager, event_dispatcher, and platform_monitor
        - Does not start monitoring (start() must be called separately)
        """
        with self._lock:
            logger.info("Initializing FSMonitorComponent")
            
            # Create watch manager
            self._watch_manager = WatchManager()
            
            # Get configuration
            config = self._config_manager.get_config()
            fs_monitor_config = config.fs_monitor
            
            # Thread priority mapping
            thread_priority = ThreadPriority.NORMAL
            if fs_monitor_config.thread_priority.lower() == "low":
                thread_priority = ThreadPriority.LOW
            elif fs_monitor_config.thread_priority.lower() == "high":
                thread_priority = ThreadPriority.HIGH
            
            # Create event dispatcher
            self._event_dispatcher = EventDispatcher(self._watch_manager)
            self._event_dispatcher.configure(
                thread_count=fs_monitor_config.thread_count,
                thread_priority=thread_priority,
                default_debounce_ms=fs_monitor_config.default_debounce_ms
            )
            
            # Create platform-specific monitor
            self._platform_monitor = create_platform_monitor(
                self._watch_manager, 
                self._event_dispatcher,
                polling_fallback_enabled=fs_monitor_config.polling_fallback.enabled,
                polling_interval=fs_monitor_config.polling_fallback.poll_interval,
                hash_size=fs_monitor_config.polling_fallback.hash_size
            )
            
            logger.info("FSMonitorComponent initialized")
    
    def start(self) -> None:
        """
        [Function intent]
        Start the component.
        
        [Design principles]
        - Clean startup sequence
        
        [Implementation details]
        - Starts event dispatcher and platform monitor
        - Sets started flag
        """
        with self._lock:
            if self._started:
                logger.warning("FSMonitorComponent already started")
                return
            
            if not self._platform_monitor or not self._event_dispatcher:
                raise RuntimeError("FSMonitorComponent not initialized")
            
            # Check if component is enabled in configuration
            config = self._config_manager.get_config()
            if not config.fs_monitor.enabled:
                logger.info("FSMonitorComponent is disabled in configuration, not starting")
                return
                
            logger.info("Starting FSMonitorComponent")
            
            # Start event dispatcher
            self._event_dispatcher.start()
            
            # Start platform monitor
            self._platform_monitor.start()
            
            self._started = True
            
            logger.info("FSMonitorComponent started")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the component.
        
        [Design principles]
        - Clean shutdown sequence
        - Resource cleanup
        
        [Implementation details]
        - Stops platform monitor and event dispatcher
        - Clears started flag
        """
        with self._lock:
            if not self._started:
                logger.debug("FSMonitorComponent already stopped")
                return
            
            logger.info("Stopping FSMonitorComponent")
            
            # Stop platform monitor (this will stop watching all directories)
            if self._platform_monitor:
                self._platform_monitor.stop()
            
            # Stop event dispatcher
            if self._event_dispatcher:
                self._event_dispatcher.stop()
            
            self._started = False
            
            logger.info("FSMonitorComponent stopped")
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shut down the component.
        
        [Design principles]
        - Clean shutdown sequence
        - Complete resource cleanup
        
        [Implementation details]
        - Ensures component is stopped
        - Releases all resources
        """
        with self._lock:
            logger.info("Shutting down FSMonitorComponent")
            
            # Make sure we're stopped
            self.stop()
            
            # Clear references
            self._watch_manager = None
            self._event_dispatcher = None
            self._platform_monitor = None
            
            logger.info("FSMonitorComponent shut down")
    
    def register_listener(self, listener: FileSystemEventListener, patterns: List[str] = None) -> int:
        """
        [Function intent]
        Register a file system event listener.
        
        [Design principles]
        - Simple public API
        - Delegation to specialized components
        
        [Implementation details]
        - Delegates to watch_manager for listener registration
        - Returns listener ID for future reference
        
        Args:
            listener: The listener to register
            patterns: List of path patterns to watch
            
        Returns:
            Listener ID
            
        Raises:
            RuntimeError: If the component is not initialized
        """
        with self._lock:
            if not self._watch_manager:
                raise RuntimeError("FSMonitorComponent not initialized")
            
            return self._watch_manager.register_listener(listener, patterns)
    
    def unregister_listener(self, listener_id: int) -> None:
        """
        [Function intent]
        Unregister a file system event listener.
        
        [Design principles]
        - Simple public API
        - Resource cleanup
        
        [Implementation details]
        - Delegates to watch_manager for listener unregistration
        
        Args:
            listener_id: ID of the listener to unregister
            
        Raises:
            RuntimeError: If the component is not initialized
        """
        with self._lock:
            if not self._watch_manager:
                raise RuntimeError("FSMonitorComponent not initialized")
            
            self._watch_manager.unregister_listener(listener_id)
    
    def update_listener_patterns(self, listener_id: int, patterns: List[str]) -> None:
        """
        [Function intent]
        Update the patterns for a registered listener.
        
        [Design principles]
        - Dynamic configuration
        - Simple public API
        
        [Implementation details]
        - Delegates to watch_manager for pattern update
        
        Args:
            listener_id: ID of the listener
            patterns: New list of path patterns
            
        Raises:
            RuntimeError: If the component is not initialized
        """
        with self._lock:
            if not self._watch_manager:
                raise RuntimeError("FSMonitorComponent not initialized")
            
            self._watch_manager.update_listener_patterns(listener_id, patterns)
    
    def configure(self) -> None:
        """
        [Function intent]
        Handle configuration changes.
        
        [Design principles]
        - Dynamic configuration
        - Configuration-driven behavior
        
        [Implementation details]
        - Reinitializes component with new configuration if needed
        - Otherwise updates subcomponent configurations
        """
        with self._lock:
            if not self._started:
                # If not started, just reinitialize
                self.initialize()
                return
                
            # If already started, update configurations dynamically
            config = self._config_manager.get_config()
            fs_monitor_config = config.fs_monitor
            
            # Thread priority mapping
            thread_priority = ThreadPriority.NORMAL
            if fs_monitor_config.thread_priority.lower() == "low":
                thread_priority = ThreadPriority.LOW
            elif fs_monitor_config.thread_priority.lower() == "high":
                thread_priority = ThreadPriority.HIGH
            
            # Update event dispatcher configuration
            if self._event_dispatcher:
                self._event_dispatcher.configure(
                    thread_count=fs_monitor_config.thread_count,
                    thread_priority=thread_priority,
                    default_debounce_ms=fs_monitor_config.default_debounce_ms
                )
            
            # Update platform monitor configuration (if applicable)
            if self._platform_monitor and hasattr(self._platform_monitor, "set_poll_interval"):
                # This is likely the fallback monitor
                self._platform_monitor.set_poll_interval(fs_monitor_config.polling_fallback.poll_interval)
            
            logger.debug("FSMonitorComponent configuration updated")
