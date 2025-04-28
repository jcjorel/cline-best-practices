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
# This file implements the event dispatcher for the file system monitor component.
# It coordinates event processing by receiving events from platform-specific monitors,
# debouncing them to prevent notification storms, and dispatching them to interested
# listeners using a thread pool.
###############################################################################
# [Source file design principles]
# - Central hub for event processing
# - Thread-safe operations for concurrent access
# - Efficient event routing to interested listeners
# - Support for debounced event delivery to prevent notification storms
# - Clean integration with watch manager and listener components
###############################################################################
# [Source file constraints]
# - Must handle concurrent event submissions from multiple sources
# - Must ensure proper event routing based on path patterns
# - Must properly manage thread resources and lifecycle
# - Must prevent endless notification cycles
# - Must avoid circular dependencies with other components
###############################################################################
# [Dependencies]
# system:threading
# system:logging
# system:typing
# codebase:src/dbp/fs_monitor/event_types.py
# codebase:src/dbp/fs_monitor/listener.py
# codebase:src/dbp/fs_monitor/debouncer.py
# codebase:src/dbp/fs_monitor/thread_manager.py
# codebase:src/dbp/fs_monitor/watch_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T00:12:00Z : Initial implementation of event dispatcher for fs_monitor redesign by CodeAssistant
# * Created EventDispatcher class for event routing and coordination
# * Implemented integration with WatchManager, Debouncer, and ThreadManager
# * Added configuration options for event processing behavior
###############################################################################

import threading
import logging
from typing import Dict, List, Optional, Any, Set, Callable

from .event_types import EventType, FileSystemEvent
from .listener import FileSystemEventListener
from .debouncer import Debouncer
from .thread_manager import ThreadManager, ThreadPriority

logger = logging.getLogger(__name__)

class EventDispatcher:
    """
    [Class intent]
    Dispatches file system events to registered listeners.
    
    [Design principles]
    - Central hub for event processing
    - Thread safety
    - Efficient event routing
    - Support for debounced events
    
    [Implementation details]
    - Uses Debouncer for event throttling
    - Uses ThreadManager for dispatching events
    - Maintains a connection to the WatchManager
    """
    
    def __init__(self, watch_manager) -> None:
        """
        [Function intent]
        Initialize a new event dispatcher.
        
        [Design principles]
        - Clean initialization
        - Component linking
        
        [Implementation details]
        - Stores reference to watch manager
        - Creates debouncer and thread manager
        
        Args:
            watch_manager: Reference to the watch manager
        """
        self._watch_manager = watch_manager
        self._lock = threading.RLock()
        self._debouncer = Debouncer(self._dispatch_debounced_event)
        self._thread_manager = ThreadManager(num_threads=1, priority=ThreadPriority.NORMAL)
        self._started = False
    
    def start(self) -> None:
        """
        [Function intent]
        Start the event dispatcher.
        
        [Design principles]
        - Clean startup sequence
        
        [Implementation details]
        - Starts the debouncer and thread manager
        - Sets started flag
        """
        with self._lock:
            if self._started:
                logger.warning("EventDispatcher already started")
                return
            
            self._debouncer.start()
            self._thread_manager.start()
            self._started = True
            
            logger.debug("Started event dispatcher")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the event dispatcher.
        
        [Design principles]
        - Clean shutdown sequence
        
        [Implementation details]
        - Stops the debouncer and thread manager
        - Clears started flag
        """
        with self._lock:
            if not self._started:
                logger.debug("EventDispatcher already stopped")
                return
            
            self._debouncer.stop()
            self._thread_manager.stop()
            self._started = False
            
            logger.debug("Stopped event dispatcher")
    
    def dispatch_event(self, event: FileSystemEvent) -> None:
        """
        [Function intent]
        Dispatch a file system event to interested listeners.
        
        [Design principles]
        - Event routing based on path patterns
        - Support for debouncing
        
        [Implementation details]
        - Gets matching listeners from watch manager
        - Adds event to debouncer
        
        Args:
            event: The file system event to dispatch
        """
        if not self._started:
            logger.warning("EventDispatcher not started, event will not be dispatched")
            return
        
        # Get matching listeners from watch manager
        listener_ids = self._watch_manager.get_matching_listeners(event.path)
        
        if not listener_ids:
            logger.debug(f"No listeners found for path {event.path}, event will not be dispatched")
            return
        
        # Collect debounce delays for each listener
        listener_debounce_delays = {}
        for listener_id in listener_ids:
            listener = self._watch_manager.get_listener(listener_id)
            if listener:
                listener_debounce_delays[listener_id] = listener.debounce_delay_ms
        
        # Add event to debouncer
        self._debouncer.add_event(event, listener_ids, listener_debounce_delays)
    
    def _dispatch_debounced_event(self, event: FileSystemEvent, listener_ids: List[int]) -> None:
        """
        [Function intent]
        Dispatch a debounced event to interested listeners.
        
        [Design principles]
        - Thread safety
        - Error handling for individual listeners
        
        [Implementation details]
        - Retrieves listeners from watch manager
        - Submits dispatcher tasks to thread manager
        
        Args:
            event: The file system event to dispatch
            listener_ids: List of listener IDs to dispatch to
        """
        if not self._started:
            logger.warning("EventDispatcher not started, event will not be dispatched")
            return
        
        # For each listener, submit a task to the thread manager
        for listener_id in listener_ids:
            listener = self._watch_manager.get_listener(listener_id)
            if not listener:
                logger.warning(f"Listener {listener_id} not found, skipping event dispatch")
                continue
            
            # Submit task to thread manager
            self._thread_manager.submit_task(
                self._call_listener_method,
                listener,
                event
            )
    
    def _call_listener_method(self, listener: FileSystemEventListener, event: FileSystemEvent) -> None:
        """
        [Function intent]
        Call the appropriate method on a listener based on the event type.
        
        [Design principles]
        - Error handling
        - Event type routing
        
        [Implementation details]
        - Selects listener method based on event type
        - Handles exceptions from listener methods
        
        Args:
            listener: The listener to call
            event: The file system event
        """
        try:
            # Call the appropriate method based on the event type
            if event.event_type == EventType.FILE_CREATED:
                listener.on_file_created(event.path)
            elif event.event_type == EventType.FILE_MODIFIED:
                listener.on_file_modified(event.path)
            elif event.event_type == EventType.FILE_DELETED:
                listener.on_file_deleted(event.path)
            elif event.event_type == EventType.DIRECTORY_CREATED:
                listener.on_directory_created(event.path)
            elif event.event_type == EventType.DIRECTORY_DELETED:
                listener.on_directory_deleted(event.path)
            elif event.event_type == EventType.SYMLINK_CREATED:
                listener.on_symlink_created(event.path, event.new_target)
            elif event.event_type == EventType.SYMLINK_DELETED:
                listener.on_symlink_deleted(event.path)
            elif event.event_type == EventType.SYMLINK_TARGET_CHANGED:
                listener.on_symlink_target_changed(event.path, event.old_target, event.new_target)
            else:
                logger.warning(f"Unknown event type: {event.event_type}")
        except Exception as e:
            logger.error(f"Error calling listener method: {e}")
    
    def configure(self, thread_count: int, thread_priority: ThreadPriority, default_debounce_ms: int) -> None:
        """
        [Function intent]
        Configure the event dispatcher.
        
        [Design principles]
        - Runtime configuration
        
        [Implementation details]
        - Updates thread manager and debouncer configuration
        
        Args:
            thread_count: Number of worker threads
            thread_priority: Priority of worker threads
            default_debounce_ms: Default debounce delay in milliseconds
        """
        with self._lock:
            # Need to stop and restart components for configuration to take effect
            was_started = self._started
            
            if was_started:
                self.stop()
            
            # Update thread manager
            self._thread_manager = ThreadManager(num_threads=thread_count, priority=thread_priority)
            
            # Update debouncer
            self._debouncer.set_default_debounce_ms(default_debounce_ms)
            
            if was_started:
                self.start()
            
            logger.debug(f"EventDispatcher configured with {thread_count} threads, "
                         f"priority {thread_priority}, default debounce {default_debounce_ms}ms")
    
    @property
    def is_running(self) -> bool:
        """
        [Function intent]
        Check if the event dispatcher is running.
        
        [Design principles]
        - State verification
        
        [Implementation details]
        - Returns the current running state
        
        Returns:
            True if the event dispatcher is running, False otherwise
        """
        with self._lock:
            return self._started
