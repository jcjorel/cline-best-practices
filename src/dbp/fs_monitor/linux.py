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
# Implements the Linux-specific file system monitor using the 'inotify' kernel
# subsystem via the 'inotify' Python library. This provides an efficient,
# event-driven mechanism for detecting file changes on Linux systems.
###############################################################################
# [Source file design principles]
# - Inherits from the FileSystemMonitor base class.
# - Uses the 'inotify' library for interacting with the kernel API.
# - Runs the monitoring logic in a separate background thread.
# - Maps inotify events to the standardized ChangeEvent structure.
# - Handles adding and removing watches dynamically.
# - Supports recursive monitoring by watching subdirectories.
# - Includes error handling for inotify operations.
# - Design Decision: Use 'inotify' library (2025-04-14)
#   * Rationale: Provides a direct and efficient interface to the Linux kernel's file system event notification system.
#   * Alternatives considered: Polling (inefficient), other libraries (less common or direct).
###############################################################################
# [Source file constraints]
# - Requires the 'inotify' Python library to be installed (`pip install inotify`).
# - Only functional on Linux-based operating systems (including WSL).
# - Relies on the availability and proper functioning of the inotify kernel subsystem.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/fs_monitor/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-18T17:12:00Z : Fixed LinuxFileSystemMonitor thread exit issue by CodeAssistant
# * Modified _monitor_loop to use timeout_s=1.0 and yield_nones=True for proper thread termination
# * Ensures monitor thread can properly shut down when stop() is called
# 2025-04-15T09:41:20Z : Initial creation of LinuxFileSystemMonitor by CodeAssistant
# * Implemented start, stop, add/remove directory, and event handling loop using inotify.
###############################################################################

import os
import select
import struct
import threading
import logging
import time
from pathlib import Path
from typing import Dict, Set, Optional

# Try to import inotify library
try:
    import inotify.adapters
    import inotify.constants
    HAS_INOTIFY = True
except ImportError:
    HAS_INOTIFY = False
    # Log error if library is missing
    logging.getLogger(__name__).error("The 'inotify' library is required for LinuxFileSystemMonitor but was not found. Install it using 'pip install inotify'.")
    # We're still loading the module, but will raise an error when instantiated


# Assuming base.py is accessible
try:
    from .base import FileSystemMonitor, ChangeEvent, ChangeType
except ImportError:
    # Fallback for potential execution context issues
    from base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class LinuxFileSystemMonitor(FileSystemMonitor):
    """
    Linux-specific file system monitor implementation using the inotify kernel API.
    Requires the 'inotify' Python library.
    """

    # Define the mask for events we care about
    _WATCH_MASK = (
        inotify.constants.IN_CREATE |
        inotify.constants.IN_DELETE |
        inotify.constants.IN_MODIFY |
        inotify.constants.IN_MOVED_FROM |
        inotify.constants.IN_MOVED_TO |
        inotify.constants.IN_DELETE_SELF | # Watch for directory deletion
        inotify.constants.IN_MOVE_SELF    # Watch for directory move
    )

    def __init__(self, config, change_queue):
        """
        Initializes the LinuxFileSystemMonitor.

        Raises:
            ImportError: If the 'inotify' library is not installed.
        """
        super().__init__(config, change_queue)

        if not HAS_INOTIFY:
            error_msg = "The 'inotify' library is required to use LinuxFileSystemMonitor on Linux. Install it using 'pip install inotify'."
            logger.critical(error_msg)
            raise ImportError(error_msg)

        self._inotify = None
        self._watch_descriptors: Dict[int, str] = {}  # Maps watch descriptors (wd) to paths
        self._path_to_wd: Dict[str, int] = {}         # Maps paths to watch descriptors (wd)
        self._moved_from_cookie: Optional[int] = None # Track cookie for rename events
        self._moved_from_path: Optional[str] = None   # Track path for rename events

    def start(self):
        """Starts the inotify monitoring thread."""
        with self._lock:
            if self.running:
                logger.warning("LinuxFileSystemMonitor is already running.")
                return
            super().start() # Sets self._running = True

            try:
                # Initialize inotify adapter instance
                # Use NonBlocking=True if event_gen timeout is used, otherwise blocking is fine
                self._inotify = inotify.adapters.Inotify(block_duration_s=None) # Blocking call
                logger.debug("Inotify instance created.")

                # Add watches for initially configured directories
                initial_dirs = self.get_watched_directories() # Get a copy
                for directory in initial_dirs:
                    self._add_watch_recursive(directory)

                # Start the monitoring thread
                self.monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    daemon=True, # Ensure thread exits when main program exits
                    name="LinuxFSMonitorThread"
                )
                self.monitor_thread.start()
                logger.info("Linux file system monitor started successfully.")

            except Exception as e:
                logger.error(f"Failed to start LinuxFileSystemMonitor: {e}", exc_info=True)
                self._running = False # Reset running state on failure
                if self._inotify:
                    # Clean up watches if partially added
                    self._cleanup_watches()
                    self._inotify = None
                raise # Re-raise the exception

    def stop(self):
        """Stops the inotify monitoring thread and cleans up watches."""
        super().stop() # Sets self._running = False, joins thread
        # Cleanup happens after thread join in super().stop()
        self._cleanup_watches()
        self._inotify = None # Release inotify instance
        logger.info("Linux file system monitor stopped.")

    def _cleanup_watches(self):
        """Removes all active inotify watches."""
        if not self._inotify:
            return
        logger.debug("Cleaning up inotify watches...")
        # Iterate over a copy of keys as we modify the dict
        paths_to_remove = list(self._path_to_wd.keys())
        for path in paths_to_remove:
            self._remove_watch(path)
        logger.debug("Inotify watch cleanup complete.")


    def add_directory(self, directory: str):
        """Adds a directory and potentially its subdirectories to be monitored."""
        # Base class handles adding to self._watched_directories and path normalization
        super().add_directory(directory)
        abs_path = str(Path(directory).resolve()) # Get the normalized path used by base class

        # If monitor is running, add the actual watch
        if self.running and self._inotify:
             with self._lock: # Protect access to watch dictionaries
                 if abs_path in self._watched_directories: # Check if it was successfully added by super()
                     self._add_watch_recursive(abs_path)


    def remove_directory(self, directory: str):
        """Removes a directory and potentially its subdirectories from monitoring."""
        # Base class handles removing from self._watched_directories and path normalization
        super().remove_directory(directory)
        abs_path = str(Path(directory).resolve()) # Get the normalized path used by base class

        # If monitor is running, remove the actual watches
        if self.running and self._inotify:
            with self._lock:
                # Remove watch for the directory itself
                self._remove_watch(abs_path)
                # Remove watches for subdirectories if they were added due to this parent
                # Iterate over a copy of keys as _remove_watch modifies the dict
                subdirs_to_remove = [p for p in list(self._path_to_wd.keys()) if p.startswith(abs_path + os.sep)]
                for subdir_path in subdirs_to_remove:
                    self._remove_watch(subdir_path)


    def _add_watch_recursive(self, path: str):
        """Adds an inotify watch to a directory and optionally its subdirectories."""
        if not self.running or not self._inotify:
            return # Don't add watches if not running

        if not Path(path).is_dir():
            logger.warning(f"Attempted to watch non-directory: {path}")
            return

        # Add watch for the directory itself
        self._add_single_watch(path)

        # Add watches for subdirectories if recursive monitoring is enabled
        if self.config.get('monitor.recursive', True):
            try:
                for item in os.scandir(path):
                    if item.is_dir(follow_symlinks=False): # Avoid following symlinks recursively
                        self._add_watch_recursive(item.path)
            except OSError as e:
                logger.warning(f"Could not scan directory {path} for recursive watch: {e}")


    def _add_single_watch(self, path: str):
        """Adds an inotify watch to a single directory path."""
        if path in self._path_to_wd:
            # logger.debug(f"Watch already exists for: {path}")
            return # Already watching

        try:
            wd = self._inotify.add_watch(path, self._WATCH_MASK)
            self._watch_descriptors[wd] = path
            self._path_to_wd[path] = wd
            logger.debug(f"Added inotify watch (wd={wd}) for: {path}")
        except FileNotFoundError:
             logger.warning(f"Directory not found when adding watch: {path}")
        except PermissionError:
             logger.warning(f"Permission denied when adding watch: {path}")
        except OSError as e:
            logger.error(f"Failed to add inotify watch for {path}: {e}", exc_info=True)
        except Exception as e:
            # Catch potential issues with the inotify library itself
            logger.error(f"Unexpected error adding inotify watch for {path}: {e}", exc_info=True)


    def _remove_watch(self, path: str):
        """Removes an inotify watch from a single directory path."""
        if path not in self._path_to_wd:
            # logger.debug(f"No watch exists to remove for: {path}")
            return # Not watching

        wd = self._path_to_wd[path]
        try:
            self._inotify.remove_watch(wd) # Use wd for removal
            logger.debug(f"Removed inotify watch (wd={wd}) for: {path}")
        except OSError as e:
            # Ignore errors like "invalid argument" if watch was already removed somehow
            if e.errno != 22: # errno 22 is EINVAL
                 logger.error(f"Failed to remove inotify watch (wd={wd}) for {path}: {e}", exc_info=True)
        except Exception as e:
             logger.error(f"Unexpected error removing inotify watch (wd={wd}) for {path}: {e}", exc_info=True)
        finally:
            # Clean up mappings regardless of removal success
            if wd in self._watch_descriptors:
                del self._watch_descriptors[wd]
            if path in self._path_to_wd:
                del self._path_to_wd[path]


    def _monitor_loop(self):
        """The main loop that reads and processes inotify events."""
        logger.debug("Starting inotify event loop...")
        while self.running:
            try:
                # Read events from inotify. event_gen WITH timeout so it can check self.running periodically
                # Using yield_nones=True and a timeout allows checking self.running flag regularly
                for event in self._inotify.event_gen(yield_nones=True, timeout_s=1.0):
                    if not self.running: # Check running flag after potentially blocking
                        break
                    if event is None: # Skip None events (timeouts)
                        continue

                    # event is a tuple: (header, type_names, watch_path, filename)
                    header, type_names, watch_path, filename = event
                    wd = header.wd
                    cookie = header.cookie # Used to correlate MOVED_FROM and MOVED_TO

                    # Get the path associated with the watch descriptor
                    # watch_path provided by event_gen is usually correct, but double-check
                    base_path = self._watch_descriptors.get(wd)
                    if not base_path:
                        logger.warning(f"Received event for unknown watch descriptor: {wd}. Ignoring.")
                        continue

                    # Construct full path if filename is present
                    full_path = os.path.join(base_path, filename) if filename else base_path

                    logger.debug(f"Inotify Event: wd={wd}, cookie={cookie}, types={type_names}, path='{base_path}', file='{filename}' -> full_path='{full_path}'")

                    # --- Event Processing Logic ---

                    if 'IN_IGNORED' in type_names:
                        logger.debug(f"Watch for wd={wd} path='{base_path}' was removed by kernel. Cleaning up.")
                        # Watch was removed (e.g., directory deleted), clean up our state
                        if wd in self._watch_descriptors:
                             del self._watch_descriptors[wd]
                        if base_path in self._path_to_wd:
                             del self._path_to_wd[base_path]
                        continue # Don't process this event further

                    # Handle directory being deleted or moved itself
                    if 'IN_DELETE_SELF' in type_names or 'IN_MOVE_SELF' in type_names:
                         logger.info(f"Monitored directory itself deleted or moved: {base_path}")
                         # The watch is automatically removed by the kernel (IN_IGNORED follows)
                         # We should signal deletion for the base path
                         change_event = ChangeEvent(base_path, ChangeType.DELETED)
                         self.change_queue.add_event(change_event)
                         # Clean up internal state immediately
                         if wd in self._watch_descriptors:
                             del self._watch_descriptors[wd]
                         if base_path in self._path_to_wd:
                             del self._path_to_wd[base_path]
                         continue


                    # Handle MOVED_FROM - start of a rename/move
                    if 'IN_MOVED_FROM' in type_names:
                        self._moved_from_cookie = cookie
                        self._moved_from_path = full_path
                        logger.debug(f"Rename started: cookie={cookie}, old_path='{full_path}'")
                        # If it's a directory we were watching, remove the watch
                        if full_path in self._path_to_wd:
                             self._remove_watch(full_path)
                        continue # Wait for the corresponding MOVED_TO

                    # Handle MOVED_TO - end of a rename/move or move into monitored dir
                    if 'IN_MOVED_TO' in type_names:
                        if self._moved_from_cookie == cookie and self._moved_from_path:
                            # This is the second part of a rename within the monitored scope
                            old_path = self._moved_from_path
                            new_path = full_path
                            logger.debug(f"Rename completed: cookie={cookie}, old='{old_path}', new='{new_path}'")
                            change_event = ChangeEvent(new_path, ChangeType.RENAMED, old_path=old_path)
                            self.change_queue.add_event(change_event)
                            # If the renamed item is a directory, add a watch for the new path
                            if Path(new_path).is_dir() and self.config.get('monitor.recursive', True):
                                 self._add_watch_recursive(new_path) # Watch the new directory location
                            # Reset rename tracking state
                            self._moved_from_cookie = None
                            self._moved_from_path = None
                        else:
                            # Item moved *into* the monitored directory from outside
                            logger.debug(f"Item moved into directory: path='{full_path}'")
                            change_event = ChangeEvent(full_path, ChangeType.CREATED)
                            self.change_queue.add_event(change_event)
                            # If it's a directory, watch it recursively
                            if Path(full_path).is_dir() and self.config.get('monitor.recursive', True):
                                 self._add_watch_recursive(full_path)
                        # Reset rename state just in case
                        self._moved_from_cookie = None
                        self._moved_from_path = None
                        continue # Processed move event

                    # Handle CREATE
                    if 'IN_CREATE' in type_names:
                        logger.debug(f"Item created: path='{full_path}'")
                        change_event = ChangeEvent(full_path, ChangeType.CREATED)
                        self.change_queue.add_event(change_event)
                        # If a directory was created, watch it recursively
                        if Path(full_path).is_dir() and self.config.get('monitor.recursive', True):
                             self._add_watch_recursive(full_path)
                        continue # Processed create event

                    # Handle DELETE
                    if 'IN_DELETE' in type_names:
                        logger.debug(f"Item deleted: path='{full_path}'")
                        change_event = ChangeEvent(full_path, ChangeType.DELETED)
                        self.change_queue.add_event(change_event)
                        # If a directory we were watching is deleted, remove watch state
                        if full_path in self._path_to_wd:
                             self._remove_watch(full_path) # Should already be handled by IN_IGNORED? Maybe not always.
                        continue # Processed delete event

                    # Handle MODIFY
                    if 'IN_MODIFY' in type_names:
                        # Ignore modification events for directories themselves
                        if not Path(full_path).is_dir():
                             logger.debug(f"Item modified: path='{full_path}'")
                             change_event = ChangeEvent(full_path, ChangeType.MODIFIED)
                             self.change_queue.add_event(change_event)
                        else:
                             logger.debug(f"Ignoring directory modification event for: {full_path}")
                        continue # Processed modify event

                    # If we reach here, it might be an event type we don't explicitly handle
                    # or a combination. Log it for debugging.
                    logger.debug(f"Unhandled or combined event type: {type_names} for path '{full_path}'")


            except InterruptedError:
                 logger.info("Inotify monitor loop interrupted.")
                 break # Exit loop if interrupted
            except Exception as e:
                if self.running: # Only log errors if we are supposed to be running
                    logger.error(f"Error in inotify event loop: {e}", exc_info=True)
                    # Avoid tight loop on persistent errors
                    time.sleep(1)
                else:
                     # If not running, error might be due to shutdown, log as debug
                     logger.debug(f"Exception during shutdown in event loop: {e}")
                     break

        logger.info("Inotify event loop finished.")
