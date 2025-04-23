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
# Implements the FileSystemMonitorFactory, responsible for detecting the current
# operating system and creating the most appropriate FileSystemMonitor instance
# (e.g., LinuxFileSystemMonitor, MacOSFileSystemMonitor, WindowsFileSystemMonitor,
# or FallbackFileSystemMonitor).
###############################################################################
# [Source file design principles]
# - Uses the Factory pattern to decouple monitor creation logic from the rest of the system.
# - Detects the operating system using Python's `platform` module.
# - Attempts to instantiate the preferred native monitor for the detected OS.
# - Gracefully falls back to the polling monitor if native libraries are missing or fail to initialize.
# - Instantiates and configures the ChangeDetectionQueue and GitIgnoreFilter needed by the monitors.
# - Design Decision: Factory Pattern for Monitor Creation (2025-04-14)
#   * Rationale: Centralizes the logic for selecting the correct monitor implementation based on the environment, simplifying system setup.
#   * Alternatives considered: Conditional imports/instantiation in main application logic (less clean separation).
###############################################################################
# [Source file constraints]
# - Depends on all platform-specific monitor implementations (`linux.py`, `macos.py`, `windows.py`, `fallback.py`).
# - Depends on `queue.py` and `filter.py`.
# - Requires necessary libraries (inotify, fsevents, pywin32) to be installed for native monitors to be chosen.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:45:55Z : Initial creation of FileSystemMonitorFactory by CodeAssistant
# * Implemented platform detection and instantiation logic for monitors.
###############################################################################

import platform
import logging
import os
from typing import Optional, Any

# Assuming base, linux, macos, windows, fallback, queue, filter are accessible
try:
    from .base import FileSystemMonitor
    # Import with separate statements to avoid syntax errors
    from .linux import LinuxFileSystemMonitor
    from .linux import HAS_INOTIFY
    # Import with separate statements to avoid syntax errors
    from .macos import MacOSFileSystemMonitor
    from .macos import HAS_FSEVENTS
    # Import with separate statements to avoid syntax errors
    from .windows import WindowsFileSystemMonitor
    from .windows import HAS_WIN32
    from .fallback import FallbackFileSystemMonitor
    from .queue import ChangeDetectionQueue
    from .filter import GitIgnoreFilter
except ImportError:
    # Fallback imports if run standalone or structure differs
    from base import FileSystemMonitor
    try: from linux import LinuxFileSystemMonitor, HAS_INOTIFY
    except ImportError: LinuxFileSystemMonitor, HAS_INOTIFY = None, False
    try:
        from macos import MacOSFileSystemMonitor
        from macos import HAS_FSEVENTS
    except ImportError:
        MacOSFileSystemMonitor, HAS_FSEVENTS = None, False
    try:
        from windows import WindowsFileSystemMonitor
        from windows import HAS_WIN32
    except ImportError:
        WindowsFileSystemMonitor, HAS_WIN32 = None, False
    from fallback import FallbackFileSystemMonitor
    from queue import ChangeDetectionQueue
    from filter import GitIgnoreFilter


logger = logging.getLogger(__name__)

class FileSystemMonitorFactory:
    """
    Factory class responsible for creating the appropriate FileSystemMonitor
    instance based on the current operating system and available libraries.
    """

    @staticmethod
    def create_monitor(config: Any, project_root: Optional[str] = None) -> FileSystemMonitor:
        """
        Creates and returns the best available FileSystemMonitor instance.

        It attempts to use native OS-specific monitors first (inotify on Linux,
        FSEvents on macOS, ReadDirectoryChangesW on Windows) and falls back to
        a polling-based monitor if native options are unavailable or fail.

        Args:
            config: The configuration object (e.g., ConfigurationManager instance)
                    needed for monitor, queue, and filter initialization.
            project_root: The root directory of the project being monitored, used
                          by the GitIgnoreFilter.

        Returns:
            An initialized instance of a FileSystemMonitor subclass.

        Raises:
            RuntimeError: If no monitor (not even fallback) can be created.
        """
        logger.info("Creating File System Monitor...")

        # 1. Create dependencies: Filter and Queue
        try:
            filter_obj = GitIgnoreFilter(config, project_root)
        except Exception as e:
             logger.error(f"Failed to create GitIgnoreFilter: {e}", exc_info=True)
             # Decide if we can proceed without a filter or if it's critical
             filter_obj = None # Proceed without filter on error? Or raise? Let's proceed.

        try:
            change_queue = ChangeDetectionQueue(config)
            if filter_obj:
                change_queue.set_filter(filter_obj)
        except Exception as e:
             logger.error(f"Failed to create ChangeDetectionQueue: {e}", exc_info=True)
             raise RuntimeError("Could not create essential ChangeDetectionQueue.") from e


        # 2. Determine platform and attempt to create native monitor
        system = platform.system()
        monitor: Optional[FileSystemMonitor] = None

        logger.info(f"Detected Operating System: {system}")

        if system == 'Linux':
            if not HAS_INOTIFY or not LinuxFileSystemMonitor:
                error_msg = "inotify library is required for Linux file system monitoring. Install it using 'pip install inotify'."
                logger.critical(error_msg)
                raise ImportError(error_msg)
                
            try:
                monitor = LinuxFileSystemMonitor(config, change_queue)
                logger.info("Selected LinuxFileSystemMonitor (inotify).")
            except Exception as e:
                error_msg = f"Failed to initialize LinuxFileSystemMonitor: {e}"
                logger.critical(error_msg)
                raise RuntimeError(error_msg) from e

        elif system == 'Darwin': # macOS
            if HAS_FSEVENTS and MacOSFileSystemMonitor:
                try:
                    monitor = MacOSFileSystemMonitor(config, change_queue)
                    logger.info("Selected MacOSFileSystemMonitor (FSEvents).")
                except ImportError:
                    logger.warning("fsevents library import failed despite check, falling back.")
                except Exception as e:
                    logger.error(f"Failed to initialize MacOSFileSystemMonitor: {e}. Falling back.", exc_info=True)
            else:
                logger.warning("fsevents library not available on macOS. Falling back to polling.")

        elif system == 'Windows':
            if HAS_WIN32 and WindowsFileSystemMonitor:
                try:
                    monitor = WindowsFileSystemMonitor(config, change_queue)
                    logger.info("Selected WindowsFileSystemMonitor (ReadDirectoryChangesW).")
                except ImportError:
                    logger.warning("pywin32 library import failed despite check, falling back.")
                except Exception as e:
                    logger.error(f"Failed to initialize WindowsFileSystemMonitor: {e}. Falling back.", exc_info=True)
            else:
                logger.warning("pywin32 library not available on Windows. Falling back to polling.")

        # 3. If we reached here without a monitor on Linux, it's an error
        if monitor is None and system == 'Linux':
            error_msg = "Could not create appropriate file system monitor for Linux. This is a fatal error."
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
            
        # For other platforms, still allow fallback as necessary
        elif monitor is None and system != 'Linux':
            logger.warning("Using FallbackFileSystemMonitor (polling). This may be less efficient.")
            try:
                monitor = FallbackFileSystemMonitor(config, change_queue)
                logger.info("Selected FallbackFileSystemMonitor (polling).")
            except Exception as e:
                 logger.critical(f"Failed to initialize FallbackFileSystemMonitor: {e}", exc_info=True)
                 raise RuntimeError("Unable to create any file system monitor.") from e

        return monitor
