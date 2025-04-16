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
# Implements the ChangeDetectionQueue for the Background Task Scheduler. This queue
# receives file change events, applies debouncing logic based on configured delays,
# and provides batches of changes ready for processing by worker threads.
# Also defines the data structures for representing file changes within the scheduler.
###############################################################################
# [Source file design principles]
# - Defines `ChangeType` enum and `FileChange` dataclass for clear event representation.
# - Uses a dictionary combined with threading.Timer for debouncing file changes.
# - Provides a thread-safe mechanism for adding changes and retrieving batches.
# - Uses a threading.Event to signal availability of changes for processing.
# - Handles maximum delay constraints to ensure changes are eventually processed.
# - Design Decision: Timer-Based Debouncing (2025-04-15)
#   * Rationale: Allows changes to be queued only after a specified quiet period for a given file, reducing redundant processing for rapid saves.
#   * Alternatives considered: Heap-based queue (used in fs_monitor, different debounce logic), Simple time check on retrieval (less precise debounce).
###############################################################################
# [Source file constraints]
# - Requires configuration for debounce delays (`scheduler.delay_seconds`, `scheduler.max_delay_seconds`).
# - Relies on accurate timestamps in `FileChange` objects.
# - Performance of adding changes depends on timer management overhead.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/BACKGROUND_TASK_SCHEDULER.md
# - src/dbp/fs_monitor/base.py (Similar ChangeEvent structure)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:02:15Z : Initial creation of scheduler queue by CodeAssistant
# * Implemented ChangeType, FileChange, and ChangeDetectionQueue with timer-based debouncing.
###############################################################################

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from threading import Timer, RLock, Event

logger = logging.getLogger(__name__)

class ChangeType(Enum):
    """Enumeration of file change types relevant to the scheduler."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed" # May need special handling if old/new paths are needed

@dataclass
class FileChange:
    """Represents a detected file change event to be processed."""
    path: str
    change_type: ChangeType
    timestamp: float # Time the change was detected/added
    old_path: Optional[str] = None # For RENAMED changes

    # Allow hashing based on path for dictionary keys
    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if not isinstance(other, FileChange):
            return NotImplemented
        return self.path == other.path # Equality based on path for queue management

class ChangeDetectionQueue:
    """
    A thread-safe queue that receives file change events, debounces them,
    and makes them available in batches for processing.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ChangeDetectionQueue.

        Args:
            config: Configuration object providing 'scheduler.delay_seconds'
                    and 'scheduler.max_delay_seconds'. Defaults used if None.
            logger_override: Optional logger instance.
        """
        self.config = config or {} # Use empty dict if config is None
        self.logger = logger_override or logger
        # _queue stores changes ready for processing: path -> FileChange
        self._queue: Dict[str, FileChange] = {}
        # _pending_changes stores timers for debouncing: path -> Timer instance
        self._pending_changes: Dict[str, Timer] = {}
        # _first_pending_time stores when a path first entered pending state
        self._first_pending_time: Dict[str, float] = {}
        self._lock = RLock() # Lock for thread safety
        self._event_available = Event() # Signal when items are added to _queue

        # Get config values with defaults
        self._delay_seconds = float(self.config.get('scheduler.delay_seconds', 10.0))
        self._max_delay_seconds = float(self.config.get('scheduler.max_delay_seconds', 120.0))

        if self._delay_seconds <= 0:
             self.logger.warning("Scheduler delay_seconds must be positive. Using default 10.0.")
             self._delay_seconds = 10.0
        if self._max_delay_seconds <= self._delay_seconds:
             self.logger.warning("Scheduler max_delay_seconds should be greater than delay_seconds. Adjusting max delay.")
             self._max_delay_seconds = self._delay_seconds * 2 # Ensure max delay is larger

        self.logger.debug(f"ChangeDetectionQueue initialized (delay={self._delay_seconds}s, max_delay={self._max_delay_seconds}s).")


    def add_change(self, change: FileChange):
        """
        Adds a file change event. Debounces rapid changes to the same file path.

        Args:
            change: The FileChange event to add.
        """
        if not isinstance(change, FileChange):
            self.logger.warning(f"Invalid change object received: {type(change)}")
            return

        with self._lock:
            path = change.path
            now = time.time()
            self.logger.debug(f"Received change for '{path}': {change.change_type.name}")

            # Cancel any existing timer for this path (debouncing)
            self._cancel_pending_timer(path)

            # If change is DELETE and there was a pending CREATE/MODIFY, just remove pending
            # (This simple coalescing might need refinement based on exact needs)
            # A more robust approach might be needed in _add_change_to_queue
            # For now, let the latest change dictate the action after debounce.

            # Record the time this path first entered pending state if it wasn't already
            if path not in self._first_pending_time:
                 self._first_pending_time[path] = now

            # Check if max delay has been exceeded since first pending
            if self._should_process_immediately(path, now):
                self.logger.info(f"Max delay reached for '{path}'. Processing immediately.")
                self._add_change_to_queue(change)
            else:
                # Start a new timer to add the change after the debounce delay
                timer = Timer(
                    interval=self._delay_seconds,
                    function=self._add_change_to_queue,
                    args=(change,)
                )
                timer.daemon = True # Allow program to exit even if timers are pending
                self._pending_changes[path] = timer
                timer.start()
                self.logger.debug(f"Scheduled change for '{path}' in {self._delay_seconds}s.")

    def _add_change_to_queue(self, change: FileChange):
        """Internal method called by timer or immediately if max delay reached."""
        with self._lock:
            path = change.path
            self.logger.debug(f"Adding change to processing queue for '{path}': {change.change_type.name}")

            # Remove from pending state trackers
            self._pending_changes.pop(path, None) # Remove timer if it exists
            self._first_pending_time.pop(path, None) # Remove first pending time

            # Add or update the change in the actual processing queue
            # If a change for this path is already queued, the latest one replaces it.
            # Coalescing logic could be added here (e.g., CREATE+DELETE cancels out)
            # Simple approach: last write wins.
            self._queue[path] = change

            # Signal that an item is available in the queue
            self._event_available.set()

    def _cancel_pending_timer(self, path: str):
        """Cancels and removes a pending timer for a given path."""
        timer = self._pending_changes.pop(path, None)
        if timer:
            timer.cancel()
            self.logger.debug(f"Cancelled pending timer for path: {path}")
            # Keep _first_pending_time entry until change is actually queued or max delay hit

    def _should_process_immediately(self, path: str, current_time: float) -> bool:
        """Checks if the maximum debounce delay has been exceeded for a path."""
        first_time = self._first_pending_time.get(path)
        if first_time is None:
            return False # Not currently pending
        return (current_time - first_time) >= self._max_delay_seconds

    def get_next_batch(self, batch_size: int) -> List[FileChange]:
        """
        Retrieves a batch of file changes that are ready for processing.

        Args:
            batch_size: The maximum number of changes to retrieve.

        Returns:
            A list of FileChange objects, potentially empty if none are ready.
        """
        with self._lock:
            if not self._queue:
                self._event_available.clear() # Clear signal if queue is empty
                return []

            # Get up to batch_size items from the queue
            paths_to_process = list(self._queue.keys())[:batch_size]
            batch = [self._queue.pop(path) for path in paths_to_process]

            if not self._queue: # Check if queue became empty after batch retrieval
                self._event_available.clear()

            self.logger.debug(f"Retrieved batch of {len(batch)} changes.")
            return batch

    def wait_for_changes(self, timeout: Optional[float] = None) -> bool:
        """
        Waits until at least one change is available in the processing queue,
        or until the timeout expires.

        Args:
            timeout: Maximum time in seconds to wait. None waits indefinitely.

        Returns:
            True if changes became available, False if the timeout occurred.
        """
        return self._event_available.wait(timeout=timeout)

    def size(self) -> int:
        """Returns the number of changes currently waiting in the processing queue."""
        with self._lock:
            return len(self._queue)

    def pending_size(self) -> int:
         """Returns the number of changes currently waiting in the debounce timers."""
         with self._lock:
              return len(self._pending_changes)

    def clear(self):
        """Clears all pending timers and the processing queue."""
        with self._lock:
            self.logger.info("Clearing change detection queue...")
            # Cancel all pending timers
            for timer in self._pending_changes.values():
                timer.cancel()
            self._pending_changes.clear()
            self._first_pending_time.clear()
            # Clear the processing queue
            self._queue.clear()
            # Reset the event signal
            self._event_available.clear()
            self.logger.info("Change detection queue cleared.")
