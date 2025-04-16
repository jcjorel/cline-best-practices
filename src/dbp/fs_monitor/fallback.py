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
# Implements a fallback file system monitor that uses periodic polling (stat)
# to detect changes. This serves as a cross-platform compatible monitor when
# native OS-specific mechanisms (inotify, FSEvents, ReadDirectoryChangesW)
# are unavailable or fail.
###############################################################################
# [Source file design principles]
# - Inherits from the FileSystemMonitor base class.
# - Periodically scans watched directories and compares file states (mtime, size).
# - Runs the polling logic in a separate background thread.
# - Detects CREATED, MODIFIED, and DELETED events based on state changes.
# - Rename detection is inherently difficult and less reliable with polling.
# - Design Decision: Polling as Fallback (2025-04-14)
#   * Rationale: Provides a universally compatible monitoring mechanism, ensuring basic functionality on any platform, albeit less efficiently.
#   * Alternatives considered: No fallback (limits platform support).
###############################################################################
# [Source file constraints]
# - Less efficient than native event-based monitors, especially for large numbers of files.
# - Higher potential latency in detecting changes (dependent on polling interval).
# - Less reliable rename detection (often seen as DELETE + CREATE).
# - Resource usage (CPU, I/O) increases with the number of files and polling frequency.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/fs_monitor/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:43:55Z : Initial creation of FallbackFileSystemMonitor by CodeAssistant
# * Implemented polling loop, state tracking, and change detection logic.
###############################################################################

import os
import threading
import logging
import time
from typing import Dict, Any, Set, Optional
from pathlib import Path

# Assuming base.py is accessible
try:
    from .base import FileSystemMonitor, ChangeEvent, ChangeType
except ImportError:
    from base import FileSystemMonitor, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)

class FallbackFileSystemMonitor(FileSystemMonitor):
    """
    Fallback file system monitor implementation using periodic directory polling (os.stat).
    Used when platform-specific native monitors are unavailable. Less efficient.
    """

    def __init__(self, config, change_queue):
        """Initializes the fallback polling file system monitor."""
        super().__init__(config, change_queue)
        # Store file states: path -> {'mtime': float, 'size': int, 'is_dir': bool}
        self._file_states: Dict[str, Dict[str, Any]] = {}
        self._polling_interval: float = float(self.config.get('monitor.polling_interval', 2.0))
        if self._polling_interval <= 0:
             logger.warning(f"Polling interval must be positive, defaulting to 2.0 seconds.")
             self._polling_interval = 2.0
        logger.info(f"Fallback monitor initialized with polling interval: {self._polling_interval}s")

    def start(self):
        """Starts the polling monitor thread."""
        with self._lock:
            if self.running:
                logger.warning("FallbackFileSystemMonitor is already running.")
                return
            super().start() # Sets self._running = True

            try:
                # Initialize file states for currently watched directories
                logger.debug("Initializing file states for fallback monitor...")
                initial_dirs = self.get_watched_directories() # Get a copy
                self._file_states = self._scan_all_watched_dirs(initial_dirs)
                logger.info(f"Initial scan complete. Found {len(self._file_states)} items.")

                # Start the polling thread
                self.monitor_thread = threading.Thread(
                    target=self._polling_loop,
                    daemon=True,
                    name="FallbackFSMonitorThread"
                )
                self.monitor_thread.start()
                logger.info("Fallback file system monitor started successfully.")

            except Exception as e:
                logger.error(f"Failed to start FallbackFileSystemMonitor: {e}", exc_info=True)
                self._running = False # Reset running state
                self._file_states = {} # Clear state
                raise

    def stop(self):
        """Stops the polling monitor thread."""
        super().stop() # Sets self._running = False and joins thread
        # Clear file states after thread has stopped
        self._file_states = {}
        logger.info("Fallback file system monitor stopped.")

    def add_directory(self, directory: str):
        """Adds a directory to monitor and scans its initial state."""
        # Base class handles adding to self._watched_directories and path normalization
        super().add_directory(directory)
        abs_path = str(Path(directory).resolve())

        # If monitor is running, scan the new directory immediately
        if self.running:
            with self._lock: # Protect access to _file_states
                 if abs_path in self._watched_directories: # Check if successfully added by super()
                     logger.debug(f"Scanning newly added directory for initial state: {abs_path}")
                     new_states = self._scan_directory_recursive(abs_path)
                     self._file_states.update(new_states)
                     logger.info(f"Added {len(new_states)} items from new directory {abs_path} to state.")

    def remove_directory(self, directory: str):
        """Removes a directory and its tracked file states."""
        # Base class handles removing from self._watched_directories and path normalization
        super().remove_directory(directory)
        abs_path = str(Path(directory).resolve())

        # Remove file states associated with this directory
        if self.running:
            with self._lock: # Protect access to _file_states
                paths_to_remove = {p for p in self._file_states if p == abs_path or p.startswith(abs_path + os.sep)}
                if paths_to_remove:
                    logger.debug(f"Removing {len(paths_to_remove)} state entries for removed directory: {abs_path}")
                    for p in paths_to_remove:
                        self._file_states.pop(p, None)
                else:
                     logger.debug(f"No state entries found to remove for directory: {abs_path}")


    def _scan_all_watched_dirs(self, dir_list: list[str]) -> Dict[str, Dict[str, Any]]:
        """Scans all watched directories and returns the collective file states."""
        all_states = {}
        for directory in dir_list:
             all_states.update(self._scan_directory_recursive(directory))
        return all_states

    def _scan_directory_recursive(self, directory: str) -> Dict[str, Dict[str, Any]]:
        """Recursively scans a directory and returns states of files/subdirs."""
        states = {}
        try:
            # Add the directory itself
            dir_state = self._get_file_state(directory)
            if dir_state['exists']:
                 states[directory] = dir_state
            else:
                 logger.warning(f"Directory to scan does not exist: {directory}")
                 return states # Don't scan if dir doesn't exist

            # Scan contents
            for entry in os.scandir(directory):
                try:
                    path = entry.path
                    states[path] = self._get_file_state(path)
                    if entry.is_dir(follow_symlinks=False) and self.config.get('monitor.recursive', True):
                        states.update(self._scan_directory_recursive(path))
                except OSError as e:
                    logger.warning(f"Could not access item {entry.path} during scan: {e}")
        except OSError as e:
            logger.warning(f"Could not scan directory {directory}: {e}")
        return states

    def _get_file_state(self, path: str) -> Dict[str, Any]:
        """Gets the state (mtime, size, is_dir, exists) of a file/directory."""
        try:
            stat_result = os.stat(path)
            is_dir = Path(path).is_dir() # Use Path.is_dir() for better symlink handling? os.stat follows symlinks.
            return {
                'mtime': stat_result.st_mtime,
                'size': stat_result.st_size,
                'is_dir': is_dir,
                'exists': True
            }
        except FileNotFoundError:
            return {'mtime': 0, 'size': 0, 'is_dir': False, 'exists': False}
        except OSError as e: # Catch permission errors etc.
            logger.warning(f"Could not stat path {path}: {e}")
            return {'mtime': 0, 'size': 0, 'is_dir': False, 'exists': False} # Treat as non-existent on error

    def _polling_loop(self):
        """The main polling loop that periodically checks for changes."""
        logger.debug("Starting fallback polling loop...")
        while self.running:
            start_time = time.monotonic()
            try:
                # Get a snapshot of watched directories at the start of the poll
                current_watched_dirs = self.get_watched_directories()
                if not current_watched_dirs:
                     logger.debug("No directories currently watched, skipping poll.")
                     time.sleep(self._polling_interval)
                     continue

                logger.debug(f"Polling cycle started for {len(current_watched_dirs)} watched directories...")
                # Scan current state of all watched directories
                current_states = self._scan_all_watched_dirs(current_watched_dirs)

                with self._lock: # Lock when comparing and modifying self._file_states
                    previous_states = self._file_states.copy() # Work with a copy

                    # --- Detect changes by comparing states ---

                    # 1. Check for DELETED files/dirs
                    deleted_paths = previous_states.keys() - current_states.keys()
                    for path in deleted_paths:
                        if path in previous_states: # Ensure it was actually tracked
                             logger.debug(f"Detected DELETION: {path}")
                             change_event = ChangeEvent(path, ChangeType.DELETED)
                             self.change_queue.add_event(change_event)
                             # Remove from internal state immediately after processing deletion
                             self._file_states.pop(path, None)


                    # 2. Check for CREATED or MODIFIED files/dirs
                    for path, current_state in current_states.items():
                        if not current_state['exists']: continue # Skip if scan failed

                        if path not in previous_states:
                            # CREATED
                            logger.debug(f"Detected CREATION: {path}")
                            change_event = ChangeEvent(path, ChangeType.CREATED)
                            self.change_queue.add_event(change_event)
                            # Add to internal state immediately
                            self._file_states[path] = current_state
                        else:
                            # Existed before, check for MODIFIED
                            prev_state = previous_states[path]
                            # Compare mtime and size for modification
                            # Note: mtime might not be precise on all filesystems/OS
                            if (current_state['mtime'] > prev_state['mtime'] or
                                (current_state['mtime'] == prev_state['mtime'] and current_state['size'] != prev_state['size'])):
                                # MODIFIED (ignore pure directory modifications unless size changes?)
                                if not current_state['is_dir'] or current_state['size'] != prev_state['size']:
                                     logger.debug(f"Detected MODIFICATION: {path} (mtime: {prev_state['mtime']}->{current_state['mtime']}, size: {prev_state['size']}->{current_state['size']})")
                                     change_event = ChangeEvent(path, ChangeType.MODIFIED)
                                     self.change_queue.add_event(change_event)
                                # Update internal state immediately
                                self._file_states[path] = current_state
                            elif current_state != prev_state:
                                 # State changed but not modification time/size (e.g., permissions?)
                                 # Update state but don't necessarily fire event unless configured to
                                 logger.debug(f"Detected non-content state change: {path}")
                                 self._file_states[path] = current_state


                    # 3. Update internal state for next cycle (already done above)
                    # self._file_states = current_states # Replace old state with new scan results

                poll_duration = time.monotonic() - start_time
                logger.debug(f"Polling cycle finished in {poll_duration:.3f} seconds.")

                # Wait for the next interval, accounting for poll duration
                wait_time = max(0, self._polling_interval - poll_duration)
                time.sleep(wait_time)

            except Exception as e:
                if self.running: # Log errors only if we are supposed to be running
                    logger.error(f"Error in polling loop: {e}", exc_info=True)
                    # Avoid tight loop on error
                    time.sleep(self._polling_interval)
                else:
                     logger.debug(f"Polling loop exiting due to stop signal or error during shutdown: {e}")
                     break # Exit loop if stopped or error during shutdown

        logger.info("Fallback polling loop finished.")
