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
# This file implements a fallback file system monitor using periodic directory polling.
# It is used when platform-specific APIs are unavailable or when they fail to work.
# The monitor periodically scans watched directories and compares their contents to
# detect file system changes.
###############################################################################
# [Source file design principles]
# - Cross-platform compatibility (no OS-specific APIs)
# - Minimal resource usage through efficient polling algorithms
# - Scalable tracking of many watched paths
# - Accurate detection of created, modified, deleted, and renamed files/directories
# - Smart handling of temporary files and false positives
###############################################################################
# [Source file constraints]
# - Must handle potentially large directory structures efficiently
# - Must minimize CPU and I/O usage during polling operations
# - Must properly detect all types of file system changes
# - Must work reliably on all platforms (Linux, Windows, macOS, etc.)
# - Must scale to many watched directories without performance degradation
###############################################################################
# [Dependencies]
# system:os
# system:time
# system:threading
# system:logging
# system:typing
# system:stat
# system:pathlib
# codebase:src/dbp/fs_monitor/monitor_base.py
# codebase:src/dbp/fs_monitor/event_types.py
# codebase:src/dbp/fs_monitor/exceptions.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T00:24:00Z : Initial implementation of fallback monitor for fs_monitor redesign by CodeAssistant
# * Created FallbackMonitor class with polling-based implementation
# * Implemented snapshot-based comparison for detecting changes
# * Added optimizations to reduce CPU and I/O usage
###############################################################################

import os
import time
import threading
import logging
import stat
from pathlib import Path
from typing import Dict, Set, List, Optional, Callable, Any, Tuple

from .monitor_base import MonitorBase
from .event_types import EventType, FileSystemEvent
from .exceptions import WatchCreationError
from .watch_manager import WatchManager
from .event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)


class FileInfo:
    """
    [Class intent]
    Store information about a file or directory for change detection.
    
    [Design principles]
    - Efficient storage of file metadata
    - Simple comparison of file states
    
    [Implementation details]
    - Stores modification time, size, and type information
    - Provides methods for comparing file states
    """
    
    def __init__(self, path: str, is_dir: bool = False, is_symlink: bool = False,
                 mtime: float = 0.0, size: int = 0, symlink_target: Optional[str] = None) -> None:
        """
        [Function intent]
        Initialize file information.
        
        [Design principles]
        - Capture essential file metadata
        
        [Implementation details]
        - Stores path, type, modification time, size, and symlink target
        
        Args:
            path: File or directory path
            is_dir: Whether the path is a directory
            is_symlink: Whether the path is a symbolic link
            mtime: Modification time
            size: File size in bytes
            symlink_target: Target path for symbolic links
        """
        self.path = path
        self.is_dir = is_dir
        self.is_symlink = is_symlink
        self.mtime = mtime
        self.size = size
        self.symlink_target = symlink_target
    
    @classmethod
    def from_path(cls, path: str) -> Optional['FileInfo']:
        """
        [Function intent]
        Create a FileInfo object from a path.
        
        [Design principles]
        - Error-resistant path inspection
        
        [Implementation details]
        - Uses os.stat to get file information
        - Handles different file types (files, directories, symlinks)
        
        Args:
            path: Path to get information for
            
        Returns:
            FileInfo object or None if the path does not exist or is inaccessible
        """
        try:
            # Use lstat to get information about the link itself, not its target
            stat_result = os.lstat(path)
            
            is_dir = stat.S_ISDIR(stat_result.st_mode)
            is_symlink = stat.S_ISLNK(stat_result.st_mode)
            mtime = stat_result.st_mtime
            size = stat_result.st_size if not is_dir else 0
            
            symlink_target = None
            if is_symlink:
                try:
                    symlink_target = os.readlink(path)
                except (OSError, AttributeError):
                    # readlink not available or other error
                    pass
            
            return cls(path, is_dir, is_symlink, mtime, size, symlink_target)
        except (FileNotFoundError, PermissionError):
            return None


class DirectorySnapshot:
    """
    [Class intent]
    Captures the state of a directory for change detection.
    
    [Design principles]
    - Efficient tracking of directory contents
    - Simple comparison of directory snapshots
    
    [Implementation details]
    - Stores file information for all entries in a directory
    - Provides methods for comparing snapshots
    """
    
    def __init__(self, path: str, recursive: bool = True) -> None:
        """
        [Function intent]
        Initialize a directory snapshot.
        
        [Design principles]
        - Efficient directory traversal
        - Error handling for inaccessible paths
        
        [Implementation details]
        - Captures file information for all entries in the directory
        - Optionally traverses subdirectories recursively
        
        Args:
            path: Directory path to snapshot
            recursive: Whether to recursively snapshot subdirectories
        """
        self.path = path
        self.recursive = recursive
        self.entries: Dict[str, FileInfo] = {}
        self.snapshot_time = time.time()
        self._capture_snapshot(path, recursive)
    
    def _capture_snapshot(self, path: str, recursive: bool) -> None:
        """
        [Function intent]
        Capture the current state of the directory.
        
        [Design principles]
        - Efficient directory traversal
        - Error handling
        
        [Implementation details]
        - Uses os.scandir for efficient directory listing
        - Recursively traverses subdirectories if requested
        
        Args:
            path: Directory path to snapshot
            recursive: Whether to recursively snapshot subdirectories
        """
        try:
            # Capture information about the directory itself
            dir_info = FileInfo.from_path(path)
            if dir_info:
                self.entries[path] = dir_info
            
            # Iterate through directory contents
            with os.scandir(path) as scan_iter:
                for entry in scan_iter:
                    try:
                        entry_path = entry.path
                        
                        # Add entry to snapshot
                        is_dir = entry.is_dir(follow_symlinks=False)
                        is_symlink = entry.is_symlink()
                        
                        symlink_target = None
                        if is_symlink:
                            try:
                                symlink_target = os.readlink(entry_path)
                            except (OSError, AttributeError):
                                pass
                        
                        # Get file stats
                        stat_result = entry.stat(follow_symlinks=False)
                        mtime = stat_result.st_mtime
                        size = stat_result.st_size if not is_dir else 0
                        
                        # Store file information
                        self.entries[entry_path] = FileInfo(
                            entry_path, is_dir, is_symlink, mtime, size, symlink_target
                        )
                        
                        # Recursively process subdirectories
                        if recursive and is_dir and not is_symlink:
                            self._capture_snapshot(entry_path, recursive)
                    
                    except (PermissionError, FileNotFoundError) as e:
                        logger.debug(f"Error capturing snapshot entry {entry.path}: {e}")
        
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Error capturing snapshot for {path}: {e}")
    
    def compare(self, other: 'DirectorySnapshot') -> Tuple[List[str], List[str], List[str], List[Tuple[str, str]]]:
        """
        [Function intent]
        Compare this snapshot with another snapshot to detect changes.
        
        [Design principles]
        - Comprehensive change detection
        - Clear classification of changes
        
        [Implementation details]
        - Detects created, deleted, modified, and renamed files/directories
        - Returns lists of paths for each change type
        
        Args:
            other: Another snapshot to compare with
            
        Returns:
            Tuple containing lists of (created, deleted, modified, renamed) paths
        """
        created = []
        deleted = []
        modified = []
        renamed = []
        
        # Find created and modified files
        for path, info in self.entries.items():
            if path not in other.entries:
                created.append(path)
            else:
                other_info = other.entries[path]
                if (info.is_dir == other_info.is_dir and 
                    info.is_symlink == other_info.is_symlink):
                    # Check for modifications
                    if not info.is_dir:
                        if info.is_symlink and info.symlink_target != other_info.symlink_target:
                            # Symlink target changed
                            renamed.append((path, info.symlink_target or ""))
                        elif (info.mtime != other_info.mtime or 
                              info.size != other_info.size):
                            # File content changed
                            modified.append(path)
        
        # Find deleted files
        for path in other.entries:
            if path not in self.entries:
                deleted.append(path)
        
        return created, deleted, modified, renamed


class FallbackMonitor(MonitorBase):
    """
    [Class intent]
    Fallback file system monitor using directory polling.
    
    [Design principles]
    - Cross-platform compatibility
    - Efficient polling algorithm
    - Accurate change detection
    
    [Implementation details]
    - Uses periodic polling to detect file system changes
    - Compares directory snapshots to identify changes
    - Dispatches events for created, deleted, and modified files
    """
    
    def __init__(self, watch_manager: WatchManager, event_dispatcher: EventDispatcher) -> None:
        """
        [Function intent]
        Initialize the fallback monitor.
        
        [Design principles]
        - Clean initialization
        - Resource setup
        
        [Implementation details]
        - Calls parent constructor
        - Initializes data structures for tracking watches
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
        """
        super().__init__(watch_manager, event_dispatcher)
        self._watches: Dict[str, DirectorySnapshot] = {}
        self._monitor_thread = None
        self._poll_interval = 1.0  # seconds
    
    def start(self) -> None:
        """
        [Function intent]
        Start the fallback monitor.
        
        [Design principles]
        - Clean startup sequence
        
        [Implementation details]
        - Starts the polling thread
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("Fallback monitor already running")
                return
            
            # Start the polling thread
            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._polling_loop,
                daemon=True,
                name="FSMonitor-Fallback"
            )
            self._monitor_thread.start()
            
            logger.debug("Started fallback monitor")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the fallback monitor.
        
        [Design principles]
        - Clean shutdown sequence
        
        [Implementation details]
        - Sets running flag to false
        - Waits for polling thread to terminate
        """
        with self._lock:
            if not self._running:
                logger.debug("Fallback monitor already stopped")
                return
            
            # Set running flag to false
            self._running = False
            
            # Wait for monitoring thread to terminate
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)
            
            # Clear watches
            self._watches.clear()
            
            logger.debug("Stopped fallback monitor")
    
    def add_watch(self, path: str) -> str:
        """
        [Function intent]
        Add a watch for a path.
        
        [Design principles]
        - Platform-agnostic watch creation
        
        [Implementation details]
        - Creates a directory snapshot for the path
        - Stores the snapshot for comparison
        
        Args:
            path: Absolute path to watch
            
        Returns:
            The path itself as the watch descriptor
        """
        with self._lock:
            if not self._running:
                logger.warning("Fallback monitor not running, watch will not be added")
                raise WatchCreationError("Monitor not running")
            
            try:
                # Create a snapshot of the directory
                snapshot = DirectorySnapshot(path, recursive=True)
                self._watches[path] = snapshot
                
                logger.debug(f"Added watch for {path}")
                return path
            except Exception as e:
                logger.error(f"Error adding watch for {path}: {e}")
                raise WatchCreationError(f"Failed to add watch for {path}: {e}")
    
    def remove_watch(self, path: str, descriptor: str) -> None:
        """
        [Function intent]
        Remove a watch for a path.
        
        [Design principles]
        - Simple watch removal
        
        [Implementation details]
        - Removes the directory snapshot for the path
        
        Args:
            path: Absolute path that was being watched
            descriptor: The path itself (unused)
        """
        with self._lock:
            if not self._running:
                logger.debug("Fallback monitor not running, watch will not be removed")
                return
            
            try:
                # Remove the watch
                self._watches.pop(path, None)
                
                logger.debug(f"Removed watch for {path}")
            except Exception as e:
                logger.warning(f"Error removing watch for {path}: {e}")
    
    def set_poll_interval(self, interval: float) -> None:
        """
        [Function intent]
        Set the polling interval.
        
        [Design principles]
        - Runtime configuration
        
        [Implementation details]
        - Updates the polling interval
        
        Args:
            interval: Polling interval in seconds
        """
        self._poll_interval = max(0.1, interval)
        logger.debug(f"Set polling interval to {self._poll_interval}s")
    
    def _polling_loop(self) -> None:
        """
        [Function intent]
        Main loop for the polling thread.
        
        [Design principles]
        - Regular polling
        - Efficient change detection
        
        [Implementation details]
        - Periodically checks for changes in watched directories
        - Dispatches events for detected changes
        """
        last_poll_time = 0
        
        while self._running:
            try:
                # Sleep until next poll interval
                now = time.time()
                sleep_time = max(0, self._poll_interval - (now - last_poll_time))
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # Update last poll time
                last_poll_time = time.time()
                
                # Check for changes
                self._check_for_changes()
            
            except Exception as e:
                if self._running:
                    logger.error(f"Error in polling loop: {e}")
                    time.sleep(1)  # Sleep to avoid tight loop on error
    
    def _check_for_changes(self) -> None:
        """
        [Function intent]
        Check for changes in watched directories.
        
        [Design principles]
        - Snapshot comparison
        - Complete change detection
        
        [Implementation details]
        - Creates new snapshots and compares with old ones
        - Dispatches events for detected changes
        - Updates stored snapshots
        """
        with self._lock:
            if not self._running:
                return
            
            # Make a copy of watch paths to avoid modification during iteration
            watch_paths = list(self._watches.keys())
        
        # Check each watch
        for path in watch_paths:
            try:
                with self._lock:
                    if not self._running or path not in self._watches:
                        continue
                    
                    # Get the previous snapshot
                    old_snapshot = self._watches[path]
                
                # Create a new snapshot
                new_snapshot = DirectorySnapshot(path, recursive=True)
                
                # Compare snapshots
                created, deleted, modified, renamed = new_snapshot.compare(old_snapshot)
                
                # Dispatch events for changes
                for create_path in created:
                    try:
                        info = FileInfo.from_path(create_path)
                        if info:
                            if info.is_dir:
                                self.dispatch_event(EventType.DIRECTORY_CREATED, create_path)
                            elif info.is_symlink:
                                self.dispatch_event(EventType.SYMLINK_CREATED, create_path, 
                                                  None, info.symlink_target)
                            else:
                                self.dispatch_event(EventType.FILE_CREATED, create_path)
                    except Exception as e:
                        logger.warning(f"Error processing created path {create_path}: {e}")
                
                for delete_path in deleted:
                    try:
                        old_info = old_snapshot.entries.get(delete_path)
                        if old_info:
                            if old_info.is_dir:
                                self.dispatch_event(EventType.DIRECTORY_DELETED, delete_path)
                            elif old_info.is_symlink:
                                self.dispatch_event(EventType.SYMLINK_DELETED, delete_path)
                            else:
                                self.dispatch_event(EventType.FILE_DELETED, delete_path)
                    except Exception as e:
                        logger.warning(f"Error processing deleted path {delete_path}: {e}")
                
                for modify_path in modified:
                    try:
                        info = FileInfo.from_path(modify_path)
                        if info and not info.is_dir:
                            self.dispatch_event(EventType.FILE_MODIFIED, modify_path)
                    except Exception as e:
                        logger.warning(f"Error processing modified path {modify_path}: {e}")
                
                for rename_path, new_target in renamed:
                    try:
                        old_info = old_snapshot.entries.get(rename_path)
                        info = FileInfo.from_path(rename_path)
                        if info and info.is_symlink and old_info and old_info.is_symlink:
                            self.dispatch_event(
                                EventType.SYMLINK_TARGET_CHANGED, 
                                rename_path,
                                old_info.symlink_target,
                                info.symlink_target
                            )
                    except Exception as e:
                        logger.warning(f"Error processing renamed path {rename_path}: {e}")
                
                # Update the stored snapshot
                with self._lock:
                    if self._running and path in self._watches:
                        self._watches[path] = new_snapshot
            
            except Exception as e:
                logger.error(f"Error checking for changes in {path}: {e}")
