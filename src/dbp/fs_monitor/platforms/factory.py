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
# This file implements a factory for creating platform-specific file system monitors.
# It detects the current operating system and creates the appropriate monitor
# implementation, with graceful fallback mechanisms for unsupported platforms.
###############################################################################
# [Source file design principles]
# - Platform detection and selection
# - Graceful fallback to polling implementation
# - Lazy loading of platform-specific modules
# - Clean error handling and reporting
# - Single point of monitor instantiation
###############################################################################
# [Source file constraints]
# - Must handle all supported platforms (Linux, macOS, Windows)
# - Must provide meaningful error messages on failure
# - Must not cause import errors on unsupported platforms
# - Must fall back to polling monitor when native implementation fails
# - Must log clear information about which monitor is being used
###############################################################################
# [Dependencies]
# system:platform
# system:logging
# system:typing
# codebase:src/dbp/fs_monitor/platforms/monitor_base.py
# codebase:src/dbp/fs_monitor/dispatch/event_dispatcher.py
# codebase:src/dbp/fs_monitor/watch_manager.py
# codebase:src/dbp/fs_monitor/core/exceptions.py
# codebase:src/dbp/fs_monitor/platforms/linux.py
# codebase:src/dbp/fs_monitor/platforms/fallback.py
# codebase:src/dbp/fs_monitor/platforms/macos.py
# codebase:src/dbp/fs_monitor/platforms/windows.py
###############################################################################
# [GenAI tool change history]
# 2025-04-29T00:58:00Z : Updated imports to match new directory structure by CodeAssistant
# * Changed imports to use the new module structure with core/, dispatch/, and platforms/ subdirectories
# * Updated dependencies section to reflect the new file locations
# * Updated FallbackMonitor references to PollingMonitor for consistency
# 2025-04-29T00:18:00Z : Initial implementation of monitor factory for fs_monitor redesign by CodeAssistant
# * Created factory function for creating platform-specific monitors
# * Implemented platform detection logic
# * Added support for graceful fallback to polling monitor
###############################################################################

import platform
import logging
from typing import Optional

# Import from new module structure
from .monitor_base import MonitorBase
from ..dispatch.event_dispatcher import EventDispatcher
from ..watch_manager import WatchManager
from ..core.exceptions import WatchCreationError

logger = logging.getLogger(__name__)


def create_platform_monitor(
    watch_manager: WatchManager, 
    event_dispatcher: EventDispatcher,
    polling_fallback_enabled: bool = True,
    polling_interval: float = 1.0,
    hash_size: int = 4096
) -> MonitorBase:
    """
    [Function intent]
    Create the appropriate platform-specific monitor.
    
    [Design principles]
    - Platform detection and selection
    - Graceful fallback
    - Configuration-driven behavior
    
    [Implementation details]
    - Detects the current platform
    - Creates the appropriate monitor
    - Falls back to polling monitor if native monitor fails
    - Configures polling parameters when using fallback
    
    Args:
        watch_manager: Reference to the watch manager
        event_dispatcher: Reference to the event dispatcher
        polling_fallback_enabled: Whether to fall back to polling if platform-specific monitor fails
        polling_interval: Polling interval in seconds for the fallback monitor
        hash_size: Number of bytes to hash for file change detection in fallback monitor
        
    Returns:
        Platform-specific monitor instance
        
    Raises:
        WatchCreationError: If no monitor can be created
    """
    system = platform.system().lower()
    
    # Try to create the appropriate monitor
    monitor = None
    
    try:
        if system == 'linux':
            from .linux import LinuxMonitor
            monitor = LinuxMonitor(watch_manager, event_dispatcher)
            logger.info("Created Linux monitor (inotify)")
        elif system == 'darwin':
            from .macos import MacOSMonitor
            monitor = MacOSMonitor(watch_manager, event_dispatcher)
            logger.info("Created macOS monitor (FSEvents)")
        elif system == 'windows':
            from .windows import WindowsMonitor
            monitor = WindowsMonitor(watch_manager, event_dispatcher)
            logger.info("Created Windows monitor (ReadDirectoryChangesW)")
        else:
            logger.warning(f"Unsupported platform: {system}")
    except Exception as e:
        logger.error(f"Error creating platform monitor: {e}")
    
    # Fall back to polling monitor if native monitor failed or platform is unsupported
    if monitor is None:
        if not polling_fallback_enabled:
            raise WatchCreationError("Platform-specific monitor failed and polling fallback is disabled")
        
        try:
            from .fallback import PollingMonitor
            monitor = PollingMonitor(watch_manager, event_dispatcher)
            monitor.set_poll_interval(polling_interval)
            logger.warning("Using fallback polling monitor")
        except Exception as e:
            logger.error(f"Error creating fallback monitor: {e}")
            raise WatchCreationError(f"Failed to create any monitor: {e}")
    
    return monitor
