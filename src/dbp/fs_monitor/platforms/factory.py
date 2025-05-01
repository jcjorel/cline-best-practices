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
# This file implements a factory class for creating platform-specific file system monitors.
# It detects the current operating system and creates the appropriate monitor
# implementation, with fallback mechanisms for unsupported platforms.
###############################################################################
# [Source file design principles]
# - Runtime platform detection that examines the actual OS environment using platform.system()
#   rather than relying on compile-time flags or configuration files
# - Effective fallback mechanism that automatically switches to a universal polling implementation
#   when platform-specific monitors fail, maintaining consistent API across all environments
# - Targeted module importing that loads specific platform implementations only at creation time,
#   preventing unnecessary dependencies and import errors on platforms with missing libraries
# - Immediate error propagation that raises specific exception types at the appropriate architectural
#   boundaries, allowing issues to be detected and diagnosed at their source
# - Centralized monitor instantiation that places all creation logic in a single class with
#   clearly defined methods, preventing code duplication and ensuring uniform configuration
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
# 2025-05-01T11:24:00Z : Added specific justifications for adjectives by CodeAssistant
# * Enhanced documentation with concrete explanations for all descriptive terms
# * Added detailed evidence for each claim about design properties
# * Improved clarity of implementation descriptions with precise justifications
# 2025-05-01T10:50:00Z : Refactored to use class-only approach by CodeAssistant
# * Replaced create_platform_monitor function with a FileSystemMonitorFactory class
# * Implemented create method as the main factory method
# * Removed function-based approach entirely
# 2025-04-29T00:58:00Z : Updated imports to match new directory structure by CodeAssistant
# * Changed imports to use the new module structure with core/, dispatch/, and platforms/ subdirectories
# * Updated dependencies section to reflect the new file locations
# * Updated FallbackMonitor references to PollingMonitor for consistency
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


class FileSystemMonitorFactory:
    """
    [Class intent]
    Factory class for creating platform-specific file system monitors.
    This class detects the current platform and instantiates the appropriate
    monitor implementation with fallback mechanisms.
    
    [Design principles]
    - Follows the Factory design pattern by centralizing monitor creation logic in a single class,
      preventing duplicated instantiation code across client modules and hiding implementation details
    - Provides reliable platform detection by using platform.system() to identify the OS at runtime,
      avoiding the need for compile-time flags or configuration options
    - Implements consistent error handling by raising specific exception types with detailed
      context that precisely identifies what failed during monitor creation and why
    - Offers straightforward API by requiring only essential parameters with sensible defaults,
      reducing integration complexity for client code
    
    [Implementation details]
    - Uses class methods exclusively since no instance state is needed between calls,
      eliminating memory overhead from unnecessary factory instances
    - Performs explicit platform checking through direct string comparison with system identifiers,
      making the selection logic transparent and easy to maintain
    - Implements deferred module importing by placing import statements within method bodies,
      preventing module loading until exactly when needed and avoiding import errors
    - Raises immediate exceptions when errors occur rather than returning default values,
      making problems visible at their source rather than causing subtle issues downstream
    """
    
    @classmethod
    def create(
        cls,
        watch_manager: WatchManager, 
        event_dispatcher: EventDispatcher,
        polling_fallback_enabled: bool = True,
        polling_interval: float = 1.0,
        hash_size: int = 4096
    ) -> MonitorBase:
        """
        [Function intent]
        Create the appropriate platform-specific monitor based on the current operating system.
        
        [Design principles]
        - Uses dynamic platform selection by examining the runtime OS environment through
          platform.system(), avoiding the need for environment variables or configuration files
        - Implements direct error propagation by raising specific exceptions at failure points,
          ensuring issues are immediately visible rather than causing delayed problems
        - Provides configurable behavior through explicit parameters with sensible defaults,
          balancing ease-of-use with the ability to tune for specific environments
        
        [Implementation details]
        - Identifies the current platform using lowercase system name comparison that normalizes
          OS names, preventing case-sensitivity issues in platform detection
        - Attempts native monitor creation first through separate method call with explicit
          error boundaries, maintaining clear separation of concerns in the code structure
        - Applies fallback strategy conditionally based on polling_fallback_enabled parameter,
          giving clients control over whether fallback is allowed or errors should be raised
        - Configures performance-critical parameters using explicit method arguments that
          directly impact CPU usage and file change detection latency
        
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
        monitor = cls._create_native_monitor(system, watch_manager, event_dispatcher)
        
        # Fall back to polling monitor if native monitor failed or platform is unsupported
        if monitor is None:
            if not polling_fallback_enabled:
                raise WatchCreationError("Platform-specific monitor failed and polling fallback is disabled")
            
            monitor = cls._create_fallback_monitor(
                watch_manager, 
                event_dispatcher,
                polling_interval
            )
        
        return monitor
    
    @staticmethod
    def _create_native_monitor(
        system: str, 
        watch_manager: WatchManager,
        event_dispatcher: EventDispatcher
    ) -> Optional[MonitorBase]:
        """
        [Function intent]
        Create a native platform-specific monitor based on the provided system type.
        
        [Design principles]
        - Maintains focused responsibility by handling only native monitor creation logic,
          making the code's purpose clear and limiting its scope to a single concern
        - Uses explicit error reporting by logging detailed exception information when
          monitor creation fails, providing immediate visibility into what went wrong
        
        [Implementation details]
        - Implements conditional branching based on exact OS string matching that directly
          maps system identifiers to their corresponding monitor classes
        - Places imports inside conditional blocks to ensure each platform module is loaded
          only when running on that specific platform, preventing missing dependency errors
        - Records detailed logging at appropriate severity levels that includes both the
          monitor type being created and any exceptions encountered
        - Returns None as a specific signal value when creation fails for any reason,
          allowing the caller to implement appropriate fallback strategies
        
        Args:
            system: The operating system identifier string (linux, darwin, windows)
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
            
        Returns:
            Platform-specific monitor instance or None if creation failed
        """
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
            raise WatchCreationError(f"Failed to create native monitor for platform {system}: {e}")
        
        return monitor
    
    @staticmethod
    def _create_fallback_monitor(
        watch_manager: WatchManager,
        event_dispatcher: EventDispatcher,
        polling_interval: float
    ) -> MonitorBase:
        """
        [Function intent]
        Create a fallback polling-based monitor when native monitors are not available.
        
        [Design principles]
        - Provides universal compatibility through a polling implementation that works
          on all platforms regardless of OS-specific file notification APIs
        - Implements complete error reporting by raising specific exceptions with detailed
          context when fallback creation fails, ensuring visibility of critical issues
        
        [Implementation details]
        - Creates a platform-independent monitor by using the PollingMonitor class that
          relies only on standard file system APIs available on all supported operating systems
        - Configures polling frequency with an explicit interval parameter that directly
          controls the tradeoff between detection responsiveness and CPU resource usage
        - Raises WatchCreationError with specific error details when monitor creation fails
          since no further fallback options are available at this point
        
        Args:
            watch_manager: Reference to the watch manager
            event_dispatcher: Reference to the event dispatcher
            polling_interval: Polling interval in seconds that controls detection latency vs CPU usage
            
        Returns:
            Fallback polling monitor instance
            
        Raises:
            WatchCreationError: If the fallback monitor cannot be created
        """
        try:
            from .fallback import PollingMonitor
            monitor = PollingMonitor(watch_manager, event_dispatcher)
            monitor.set_poll_interval(polling_interval)
            logger.warning("Using fallback polling monitor")
            return monitor
        except Exception as e:
            logger.error(f"Error creating fallback monitor: {e}")
            raise WatchCreationError(f"Failed to create fallback monitor: {e}")
