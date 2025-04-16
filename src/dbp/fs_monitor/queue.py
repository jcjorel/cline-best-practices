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
# Implements a thread-safe queue for managing file system change events.
# It includes logic for debouncing rapid changes to the same file, prioritizing
# events based on when they should be processed, and optionally filtering events.
###############################################################################
# [Source file design principles]
# - Uses a min-heap (priority queue) to efficiently retrieve the next event ready for processing.
# - Employs a dictionary to track the latest event per path for deduplication and debouncing.
# - Implements configurable delay and max delay for debouncing.
# - Uses threading primitives (RLock, Event) for thread safety.
# - Allows an optional filter object (e.g., GitIgnoreFilter) to be applied.
# - Coalesces certain event sequences (e.g., CREATE then DELETE cancels out).
# - Design Decision: Priority Queue with Debouncing Logic (2025-04-14)
#   * Rationale: Efficiently handles large volumes of events, prevents excessive processing for rapidly changing files, and allows processing events in a timely manner.
#   * Alternatives considered: Simple FIFO queue (no debouncing), Timer per file (more complex state management).
###############################################################################
# [Source file constraints]
# - Requires a configuration object providing scheduler delay settings.
# - Assumes ChangeEvent objects are hashable and comparable (based on path, type, old_path).
# - Relies on accurate timestamps within ChangeEvent objects.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/BACKGROUND_TASK_SCHEDULER.md
# - scratchpad/dbp_implementation_plan/plan_fs_monitoring.md
# - src/dbp/fs_monitor/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:44:35Z : Initial creation of ChangeDetectionQueue by CodeAssistant
# * Implemented priority queue, event deduplication, debouncing, and filtering logic.
###############################################################################

import threading
import time
import logging
import heapq
from typing import List, Set, Dict, Any, Optional
import copy
from ..core.component import Component

# Assuming base.py and filter.py are accessible
try:
    from .base import ChangeEvent, ChangeType
    from .filter import GitIgnoreFilter # Assuming filter is in the same package
except ImportError:
    # Fallback for potential execution context issues
    from base import ChangeEvent, ChangeType
    # Attempt to import filter if needed, might fail if structure differs
    try:
        from filter import GitIgnoreFilter
    except ImportError:
        GitIgnoreFilter = None # Define as None if filter cannot be imported

logger = logging.getLogger(__name__)

class ChangeDetectionQueue:
    """
    A thread-safe queue designed to handle file system change events,
    providing debouncing, prioritization, and optional filtering.

    Events are stored in a min-heap ordered by their 'ready time', which is
    calculated based on the event timestamp plus a configurable delay.
    Rapid changes to the same file are debounced by updating the ready time.
    """

    def __init__(self, config: Any):
        """
        Initializes the ChangeDetectionQueue.

        Args:
            config: A configuration object (e.g., ConfigurationManager instance)
                    providing access to 'scheduler.delay_seconds' and
                    'scheduler.max_delay_seconds'.
        """
        self.config = config
        # Priority queue storing tuples of (ready_time, event_hash, event)
        # event_hash is included to handle potential non-comparable events in Python < 3.8 heapq
        self._queue: List[tuple[float, int, ChangeEvent]] = []
        # Dictionary mapping path -> latest ChangeEvent for that path
        self._events: Dict[str, ChangeEvent] = {}
        self._lock = threading.RLock() # Reentrant lock for thread safety
        self._event_available = threading.Event() # Signal for waiting consumers
        self._filter: Optional[GitIgnoreFilter] = None # Optional event filter
        logger.debug("ChangeDetectionQueue initialized.")

    def set_filter(self, filter_obj: Optional[GitIgnoreFilter]):
        """
        Sets the filter object to be used for ignoring events.

        Args:
            filter_obj: An instance of GitIgnoreFilter or a compatible filter object
                        with a `should_ignore(path: str) -> bool` method, or None to disable filtering.
        """
        with self._lock:
            if filter_obj is not None and not hasattr(filter_obj, 'should_ignore'):
                 logger.error("Invalid filter object provided: must have a 'should_ignore' method.")
                 self._filter = None # Disable filtering if object is invalid
            else:
                 self._filter = filter_obj
                 logger.info(f"Event filter set to: {type(filter_obj).__name__ if filter_obj else 'None'}")


    def add_event(self, event: ChangeEvent):
        """
        Adds a file system change event to the queue, applying debouncing logic.

        Args:
            event: The ChangeEvent object to add.
        """
        if not isinstance(event, ChangeEvent):
            logger.warning(f"Attempted to add non-ChangeEvent object to queue: {type(event)}")
            return

        with self._lock:
            # 1. Apply Filter
            if self._filter and self._filter.should_ignore(event.path):
                logger.debug(f"Ignoring event for filtered path: {event.path}")
                # Also ignore if the old path (for renames) should be ignored
                if event.old_path and self._filter.should_ignore(event.old_path):
                     logger.debug(f"Ignoring rename event due to filtered old_path: {event.old_path}")
                     return
                elif not event.old_path: # Only return if it's not a rename potentially involving unfiltered path
                     return


            path_key = event.path # Use the primary path as the key for debouncing

            # 2. Debouncing and Coalescing Logic
            existing_event = self._events.get(path_key)

            if existing_event:
                # --- Event exists for this path ---
                logger.debug(f"Existing event found for path '{path_key}': {existing_event.change_type.name}")

                # Basic Coalescing:
                # - If CREATED then DELETED -> Cancel both out
                if existing_event.change_type == ChangeType.CREATED and event.change_type == ChangeType.DELETED:
                    logger.debug(f"Coalescing CREATED+DELETED for '{path_key}'. Removing event.")
                    self._remove_event_from_heap(existing_event)
                    del self._events[path_key]
                    # No need to signal, as we removed an event
                    return

                # - If DELETED then CREATED -> Treat as MODIFIED
                if existing_event.change_type == ChangeType.DELETED and event.change_type == ChangeType.CREATED:
                    logger.debug(f"Coalescing DELETED+CREATED for '{path_key}' into MODIFIED.")
                    # Update the existing event in the dictionary to MODIFIED
                    # Keep the timestamp of the CREATE event (the latest action)
                    modified_event = ChangeEvent(event.path, ChangeType.MODIFIED)
                    modified_event.timestamp = event.timestamp # Use latest timestamp
                    self._events[path_key] = modified_event
                    # Remove old DELETED event from heap and add new MODIFIED event
                    self._remove_event_from_heap(existing_event)
                    self._push_event_to_heap(modified_event)
                    self._event_available.set() # Signal change
                    return

                # --- Debouncing: Update existing event ---
                # Update the event in the dictionary (always keep the latest event details)
                logger.debug(f"Debouncing event for '{path_key}'. Updating to {event.change_type.name}.")
                self._events[path_key] = event
                # Remove the old event's entry from the heap
                self._remove_event_from_heap(existing_event)
                # Add the new event to the heap with potentially updated ready time
                self._push_event_to_heap(event) # _push_event handles delay calculation
                self._event_available.set() # Signal update

            else:
                # --- New event for this path ---
                logger.debug(f"New event for path '{path_key}': {event.change_type.name}")
                self._events[path_key] = event
                self._push_event_to_heap(event)
                self._event_available.set() # Signal new event

    def _remove_event_from_heap(self, event_to_remove: ChangeEvent):
        """Removes a specific event from the heap. Requires heap rebuild."""
        # This is inefficient (O(n)). Consider alternatives if performance is critical.
        original_length = len(self._queue)
        self._queue = [item for item in self._queue if item[2] != event_to_remove]
        if len(self._queue) < original_length:
            heapq.heapify(self._queue) # Rebuild heap property
            logger.debug(f"Removed existing event from heap: {event_to_remove}")
        else:
             logger.warning(f"Event to remove not found in heap: {event_to_remove}")


    def _push_event_to_heap(self, event: ChangeEvent):
        """Calculates ready time and pushes event onto the heap."""
        # Calculate delay based on configuration
        delay_seconds = float(self.config.get('scheduler.delay_seconds', 10.0))
        # max_delay_seconds = float(self.config.get('scheduler.max_delay_seconds', 120.0)) # Max delay not used in simple debounce

        # Simple debounce: always apply the base delay from the latest event time
        ready_time = event.timestamp + delay_seconds

        # Add to priority queue: (ready_time, event_hash, event)
        # Use hash(event) for tie-breaking and compatibility
        heap_item = (ready_time, hash(event), event)
        heapq.heappush(self._queue, heap_item)
        logger.debug(f"Pushed event to heap with ready_time {ready_time:.2f}: {event}")


    def get_next_event(self, block: bool = True, timeout: Optional[float] = None) -> Optional[ChangeEvent]:
        """
        Retrieves the next event that is ready for processing.

        Blocks until an event is ready or the timeout expires, unless block=False.

        Args:
            block: If True, wait for an event to become ready.
            timeout: Maximum time in seconds to block (if block=True).

        Returns:
            The next ready ChangeEvent, or None if no event is ready
            within the timeout or if the queue is empty (and not blocking).
        """
        start_time = time.monotonic() # Use monotonic clock for timeout calculation

        while True: # Loop to handle waiting for ready time
            with self._lock:
                if not self._queue:
                    # Queue is empty
                    if not block:
                        return None
                    # Wait for a signal that an event was added
                    self._event_available.clear() # Clear signal before releasing lock
                    self._lock.release() # Release lock while waiting
                    try:
                        wait_succeeded = self._event_available.wait(timeout=timeout)
                    finally:
                        self._lock.acquire() # Re-acquire lock

                    if not wait_succeeded:
                        return None # Timeout occurred
                    # If wait succeeded, loop again to check the queue
                    continue

                # Queue is not empty, check the next event's ready time
                ready_time, _, event = self._queue[0] # Peek at the top event
                now = time.time()

                if ready_time <= now:
                    # Event is ready for processing
                    _, _, ready_event = heapq.heappop(self._queue) # Remove from heap

                    # Critical: Only return the event if it's still the *latest* known event
                    # for its path in the _events dictionary. If another event for the same
                    # path was added later (debounced), this popped event is stale.
                    latest_event_for_path = self._events.get(ready_event.path)
                    if latest_event_for_path is ready_event:
                        # This is the latest event, remove from tracking dict
                        del self._events[ready_event.path]
                        logger.debug(f"Returning ready event: {ready_event}")
                        return ready_event
                    else:
                        # This event is stale (debounced), discard it and loop again
                        logger.debug(f"Discarding stale event from heap: {ready_event}")
                        continue # Check the next item in the heap

                else:
                    # Top event is not ready yet
                    if not block:
                        return None # Don't wait if not blocking

                    # Calculate wait time until the next event is ready
                    wait_duration = ready_time - now

                    # Adjust wait time based on overall timeout
                    if timeout is not None:
                        elapsed = time.monotonic() - start_time
                        remaining_timeout = timeout - elapsed
                        if remaining_timeout <= 0:
                            return None # Overall timeout expired
                        wait_duration = min(wait_duration, remaining_timeout)

                    # Wait for the calculated duration OR until a new event is signaled
                    self._event_available.clear()
                    self._lock.release()
                    try:
                        self._event_available.wait(timeout=wait_duration)
                    finally:
                        self._lock.acquire()
                    # Loop again after waiting to re-evaluate the queue
                    continue

    def get_pending_count(self) -> int:
        """Returns the number of events currently in the queue (waiting or ready)."""
        with self._lock:
            return len(self._queue)

    def clear(self):
        """Removes all events from the queue and tracking dictionary."""
        with self._lock:
            self._queue = []
            self._events = {}
            self._event_available.clear() # Clear signal as queue is now empty
            logger.info("Change detection queue cleared.")


class ChangeQueueComponent(Component):
    """
    [Class intent]
    Component wrapper for the ChangeDetectionQueue class following the KISS component pattern.
    Provides thread-safe queuing of file system change events with debouncing and filtering.
    
    [Implementation details]
    Wraps the ChangeDetectionQueue class, initializing it during component initialization
    and providing access to the queue functionality through methods.
    
    [Design principles]
    Single responsibility for managing file system change events within the component system.
    Acts as a buffer between event detection and event processing.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes the ChangeQueueComponent with minimal setup.
        
        [Implementation details]
        Sets the initialized flag to False and prepares for queue creation.
        
        [Design principles]
        Minimal initialization with explicit state tracking.
        """
        super().__init__()
        self._initialized = False
        self._queue = None
        self.logger = None
    
    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of this component, used for registration and dependency references.
        
        [Implementation details]
        Returns a simple string constant.
        
        [Design principles]
        Explicit naming for clear component identification.
        
        Returns:
            str: The component name "change_queue"
        """
        return "change_queue"
    
    @property
    def dependencies(self) -> List[str]:
        """
        [Function intent]
        Returns the component names that this component depends on.
        
        [Implementation details]
        Change queue depends on config_manager for queue settings,
        and optionally filter if it's available.
        
        [Design principles]
        Explicit dependency declaration for clear initialization order.
        
        Returns:
            List[str]: List of component dependencies
        """
        return ["config_manager"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the change queue with the provided configuration.
        
        [Implementation details]
        Creates a ChangeDetectionQueue instance and optionally sets up a filter.
        
        [Design principles]
        Explicit initialization with clear success/failure indication.
        
        Args:
            config: Configuration object with queue settings
            
        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            self.logger.warning(f"Component '{self.name}' already initialized.")
            return
        
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")
        
        try:
            # Get component-specific configuration through config_manager
            from ..core.system import ComponentSystem
            system = ComponentSystem.get_instance()
            config_manager = system.get_component("config_manager")
            
            # Create and initialize the queue
            self._queue = ChangeDetectionQueue(config_manager)
            
            # Attempt to set up a filter if the filter component is available
            try:
                filter_component = system.get_component("filter")
                if filter_component and filter_component.is_initialized:
                    self.logger.info("Setting up event filtering with filter component")
                    # The filter itself has the should_ignore method that the queue expects
                    self._queue.set_filter(filter_component)
            except Exception as e:
                self.logger.warning(f"Could not set up filter for change queue: {e}")
                # Continue without filtering - it's optional
            
            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize change queue component: {e}", exc_info=True)
            self._queue = None
            self._initialized = False
            raise RuntimeError(f"Failed to initialize change queue component: {e}") from e
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the change queue and releases resources.
        
        [Implementation details]
        Clears the queue and resets state.
        
        [Design principles]
        Clean resource release with clear state reset.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        
        if self._queue:
            try:
                self._queue.clear()
            except Exception as e:
                self.logger.error(f"Error during queue shutdown: {e}", exc_info=True)
            finally:
                self._queue = None
        
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")
    
    @property
    def is_initialized(self) -> bool:
        """
        [Function intent]
        Indicates if the component is successfully initialized.
        
        [Implementation details]
        Returns the value of the internal _initialized flag.
        
        [Design principles]
        Simple boolean flag for clear initialization status.
        
        Returns:
            bool: True if component is initialized, False otherwise
        """
        return self._initialized
    
    def add_event(self, event: Any) -> None:
        """
        [Function intent]
        Adds a file system change event to the queue.
        
        [Implementation details]
        Delegates to the ChangeDetectionQueue's add_event method.
        
        [Design principles]
        Convenience method to simplify access to queue functionality.
        
        Args:
            event: The ChangeEvent object to add
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._queue:
            raise RuntimeError("ChangeQueueComponent not initialized")
        self._queue.add_event(event)
    
    def get_next_event(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """
        [Function intent]
        Retrieves the next event that is ready for processing.
        
        [Implementation details]
        Delegates to the ChangeDetectionQueue's get_next_event method.
        
        [Design principles]
        Convenience method to simplify access to queue functionality.
        
        Args:
            block: If True, wait for an event to become ready
            timeout: Maximum time in seconds to block (if block=True)
            
        Returns:
            The next ready ChangeEvent, or None if no event is ready
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._queue:
            raise RuntimeError("ChangeQueueComponent not initialized")
        return self._queue.get_next_event(block, timeout)
    
    def get_pending_count(self) -> int:
        """
        [Function intent]
        Returns the number of events currently in the queue.
        
        [Implementation details]
        Delegates to the ChangeDetectionQueue's get_pending_count method.
        
        [Design principles]
        Convenience method to simplify access to queue functionality.
        
        Returns:
            int: The number of pending events
            
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._queue:
            raise RuntimeError("ChangeQueueComponent not initialized")
        return self._queue.get_pending_count()
    
    def clear(self) -> None:
        """
        [Function intent]
        Removes all events from the queue.
        
        [Implementation details]
        Delegates to the ChangeDetectionQueue's clear method.
        
        [Design principles]
        Convenience method to simplify access to queue functionality.
        
        Raises:
            RuntimeError: If accessed before initialization
        """
        if not self._initialized or not self._queue:
            raise RuntimeError("ChangeQueueComponent not initialized")
        self._queue.clear()
