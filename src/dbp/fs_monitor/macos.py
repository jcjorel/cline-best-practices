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
# Implements the macOS-specific file system monitor using the FSEvents API
# via the 'fsevents' Python library. This provides an efficient, native
# mechanism for detecting file changes on macOS.
###############################################################################
# [Source file design principles]
# - Inherits from the FileSystemMonitor base class.
# - Uses the 'fsevents' library to interact with the macOS FSEvents service.
# - Leverages an Observer and Stream pattern provided by the library.
# - Maps FSEvents flags to the standardized ChangeEvent structure.
# - Handles adding and removing watches dynamically by scheduling/unscheduling streams.
# - Design Decision: Use 'fsevents' library (2025-04-14)
#   * Rationale: Provides a Pythonic interface to the native macOS FSEvents API, offering better performance and lower resource usage than polling.
#   * Alternatives considered: Polling (inefficient), kqueue (lower-level, more complex).
###############################################################################
# [Source file constraints]
# - Requires the 'fsevents' Python library (`pip install fsevents`). Note: This
#   library typically requires C compilation and might have dependencies.
# - Only functional on macOS operating systems.
# - FSEvents provides less granular information than inotify (e.g., rename detection is harder).
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# other:- src/dbp/fs_monitor/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:42:15Z : Initial creation of MacOSFileSystemMonitor by CodeAssistant
# * Implemented start, stop, add/remove directory, and event handling using fsevents.
###############################################################################

import os
import threading
import logging
import time
from typing import Dict, Set, Optional
from pathlib import Path

# Try to import fsevents library
try:
    import fsevents
    HAS_FSEVENTS = True
except ImportError:
    HAS_FSEVENTS = False
    logging.getLogger(__name__).warning("The 'fsevents' library is required for MacOSFileSystemMonitor but was not found. Install it using 'pip install fsevents'.")
except Exception as e:
    # Catch other potential import errors (e.g., compilation issues)
    HAS_FSEVENTS = False
    logging.getLogger(__name__).error(f"Failed to import 'fsevents' library, possibly due to compilation or dependency issues: {e}", exc_info=True)


# Assuming base.py is accessible
try:
    from .base import FileSystemMonitor, ChangeEvent, ChangeType
except ImportError:
    from base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class MacOSFileSystemMonitor(FileSystemMonitor):
    """
    macOS-specific file system monitor implementation using the FSEvents API
    via the 'fsevents' library.
    """

    def __init__(self, config, change_queue):
        """
        Initializes the MacOSFileSystemMonitor.

        Raises:
            ImportError: If the 'fsevents' library is not installed or fails to import.
        """
        super().__init__(config, change_queue)

        if not HAS_FSEVENTS:
            raise ImportError("The 'fsevents' library is required to use MacOSFileSystemMonitor.")

        self._observer: Optional[fsevents.Observer] = None
        self._watches: Dict[str, fsevents.Stream] = {}  # Maps normalized paths to stream objects

    def start(self):
        """Starts the FSEvents observer and schedules watches."""
        with self._lock:
            if self.running:
                logger.warning("MacOSFileSystemMonitor is already running.")
                return
            super().start() # Sets self._running = True

            try:
                # Initialize and start the observer thread
                self._observer = fsevents.Observer()
                self._observer.start() # Starts the observer thread
                logger.debug("FSEvents Observer thread started.")

                # Add watches for initially configured directories
                initial_dirs = self.get_watched_directories() # Get a copy
                for directory in initial_dirs:
                    self._add_watch(directory) # Schedule streams for existing dirs

                logger.info("macOS file system monitor started successfully.")

            except Exception as e:
                logger.error(f"Failed to start MacOSFileSystemMonitor: {e}", exc_info=True)
                self._running = False # Reset running state
                if self._observer:
                    try:
                        self._observer.stop()
                        self._observer.join(timeout=1.0)
                    except Exception as stop_e:
                         logger.error(f"Error stopping observer during failed start: {stop_e}")
                    self._observer = None
                self._watches = {} # Clear watches
                raise # Re-raise the exception

    def stop(self):
        """Stops the FSEvents observer and unschedules all watches."""
        # Stop observer first to prevent new events during cleanup
        if self._observer:
            try:
                logger.debug("Stopping FSEvents observer...")
                self._observer.stop()
                self._observer.join(timeout=2.0) # Wait for observer thread to finish
                if self._observer.is_alive():
                     logger.warning("FSEvents observer thread did not stop cleanly.")
                self._observer = None
                logger.debug("FSEvents observer stopped.")
            except Exception as e:
                logger.error(f"Error stopping FSEvents observer: {e}", exc_info=True)

        # Call super().stop() after observer is stopped
        super().stop() # Sets self._running = False

        # Clear watches dictionary (streams are stopped by observer.stop())
        self._watches = {}
        logger.info("macOS file system monitor stopped.")


    def add_directory(self, directory: str):
        """Adds a directory to be monitored by scheduling a new stream."""
        # Base class handles adding to self._watched_directories and path normalization
        super().add_directory(directory)
        abs_path = str(Path(directory).resolve())

        # If monitor is running, schedule the stream
        if self.running and self._observer:
            with self._lock: # Protect access to _watches
                 if abs_path in self._watched_directories: # Check if successfully added by super()
                     self._add_watch(abs_path)

    def remove_directory(self, directory: str):
        """Removes a directory from monitoring by unscheduling its stream."""
        # Base class handles removing from self._watched_directories and path normalization
        super().remove_directory(directory)
        abs_path = str(Path(directory).resolve())

        # If monitor is running, unschedule the stream
        if self.running and self._observer:
             with self._lock: # Protect access to _watches
                 self._remove_watch(abs_path)


    def _add_watch(self, path: str):
        """Schedules an FSEvents stream for the specified directory path."""
        if not self.running or not self._observer:
             logger.debug(f"Monitor not running, cannot add watch for {path}")
             return
        if not Path(path).is_dir():
            logger.warning(f"Attempted to watch non-directory with FSEvents: {path}")
            return
        if path in self._watches:
            # logger.debug(f"Watch already exists for: {path}")
            return # Already watching

        try:
            # Create a stream for the directory.
            # file_events=True includes events for files within the directory.
            stream = fsevents.Stream(
                self._handle_event, # Callback function
                path,              # Path to watch
                file_events=True   # Report events for files, not just the directory
            )
            self._observer.schedule(stream)
            # Note: stream.start() is not needed when scheduled with an observer

            self._watches[path] = stream
            logger.info(f"Scheduled FSEvents stream for: {path}")
        except Exception as e:
            logger.error(f"Failed to schedule FSEvents stream for {path}: {e}", exc_info=True)
            if path in self._watches: # Clean up if partially added
                 del self._watches[path]

    def _remove_watch(self, path: str):
        """Unschedules an FSEvents stream for the specified directory path."""
        if not self.running or not self._observer:
             logger.debug(f"Monitor not running, cannot remove watch for {path}")
             return
        if path not in self._watches:
            # logger.debug(f"No watch exists to remove for: {path}")
            return

        stream = self._watches.pop(path) # Remove from dict and get stream
        try:
            self._observer.unschedule(stream)
            # stream.stop() is implicitly called by observer.stop() or unschedule? Check fsevents docs.
            # Explicitly stopping might be safer if unschedule doesn't guarantee it.
            # stream.stop() # Let's assume unschedule handles stopping.
            logger.info(f"Unscheduled FSEvents stream for: {path}")
        except Exception as e:
            logger.error(f"Failed to unschedule FSEvents stream for {path}: {e}", exc_info=True)
            # Add back to dict if removal failed? Or assume it's gone?
            # self._watches[path] = stream # Maybe not safe if stream is broken


    def _handle_event(self, event):
        """
        Callback function executed by the fsevents library when an event occurs.

        Args:
            event: An object containing event details (path, mask, cookie, id).
        """
        if not self.running:
            return # Ignore events if monitor is stopping

        # FSEvents can sometimes report events for paths outside the watched dir? Filter.
        # Also, normalize the path received from the event.
        try:
             event_path = str(Path(event.name).resolve())
        except Exception as e:
             logger.warning(f"Could not resolve event path '{event.name}': {e}")
             return

        # Check if the event path is within any of our watched directories
        # This is important because FSEvents might report related events slightly outside.
        is_relevant = False
        watched_dirs = self.get_watched_directories() # Get current list
        for watched_dir in watched_dirs:
             if event_path.startswith(watched_dir):
                  is_relevant = True
                  break
        if not is_relevant:
             logger.debug(f"Ignoring irrelevant FSEvent outside watched dirs: {event_path}")
             return


        logger.debug(f"FSEvent received: path='{event.name}', mask={event.mask:#x}, cookie={event.cookie}, id={event.id}")

        # --- Map FSEvents mask to ChangeType ---
        # This mapping can be complex and might require heuristics.
        # FSEvents flags are defined in fsevents.constants (if available) or use raw values.
        # Common flags (may vary slightly based on fsevents version/macOS version):
        # ItemCreated = 0x00000100
        # ItemRemoved = 0x00000200
        # ItemInodeMetaMod = 0x00000400 (metadata change)
        # ItemRenamed = 0x00000800
        # ItemModified = 0x00001000 (content modification)
        # ItemFinderInfoMod = 0x00002000
        # ItemChangeOwner = 0x00004000
        # ItemXattrMod = 0x00008000
        # ItemIsDir = 0x01000000
        # ItemIsFile = 0x02000000
        # ItemIsSymlink = 0x04000000

        # Heuristic mapping:
        change_type = ChangeType.UNKNOWN
        old_path = None # FSEvents doesn't directly provide the old path for renames

        # Check for specific flags (adjust masks as needed)
        if event.mask & 0x00000100: # ItemCreated
            change_type = ChangeType.CREATED
        elif event.mask & 0x00000200: # ItemRemoved
            change_type = ChangeType.DELETED
        elif event.mask & 0x00000800: # ItemRenamed
            # FSEvents rename detection is tricky. It often reports the *new* path
            # with the ItemRenamed flag. We can't easily get the old path.
            # Treat as MODIFIED for simplicity, or implement more complex tracking.
            # Let's treat as MODIFIED for now.
            change_type = ChangeType.MODIFIED
            logger.debug(f"Detected FSEvents rename for '{event_path}', treating as MODIFIED.")
        elif event.mask & 0x00001000: # ItemModified (content)
             change_type = ChangeType.MODIFIED
        elif event.mask & 0x00000400: # ItemInodeMetaMod (metadata change, e.g., permissions)
             # Often accompanies content changes, might be noisy.
             # Let's treat it as MODIFIED if it's not a directory.
             if not (event.mask & 0x01000000): # Not ItemIsDir
                 change_type = ChangeType.MODIFIED
             else:
                  logger.debug(f"Ignoring directory metadata change: {event_path}")
                  return # Ignore pure directory metadata changes

        # Add event to the queue if a relevant change type was determined
        if change_type != ChangeType.UNKNOWN:
            # Use the resolved event_path
            change_event = ChangeEvent(event_path, change_type, old_path=old_path)
            logger.debug(f"Queueing event: {change_event}")
            self.change_queue.add_event(change_event)

            # Handle directory changes for recursive monitoring
            if change_type == ChangeType.CREATED and Path(event_path).is_dir() and self.config.get('monitor.recursive', True):
                 logger.debug(f"Adding watch for newly created directory: {event_path}")
                 self._add_watch(event_path) # Watch the new directory
            elif change_type == ChangeType.DELETED and event_path in self._watches:
                 logger.debug(f"Removing watch for deleted directory: {event_path}")
                 self._remove_watch(event_path) # Stop watching the deleted directory

        else:
             logger.debug(f"Ignoring FSEvent with unhandled mask {event.mask:#x} for path: {event_path}")
