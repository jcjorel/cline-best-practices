# Hierarchical Semantic Tree Context: platforms

## Directory Purpose
This directory implements platform-specific file system monitor implementations for the DBP system's fs_monitor component. It provides concrete monitor classes for different operating systems (Linux, macOS, Windows) and a fallback polling monitor, all following a common interface defined by the MonitorBase abstract class. The directory includes a factory pattern implementation that selects the appropriate monitor based on the runtime platform, providing transparent platform detection and graceful fallback mechanisms.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports platform-specific file system monitor implementations, providing access to
  the concrete monitor implementations for different operating systems and a fallback
  polling monitor. Serves as the central access point for all platform-specific code.
  
source_file_design_principles: |
  - Explicit exports of all public platform-specific monitor implementations
  - Simplified import paths for commonly used monitor classes
  - Maintains clean separation between public API and implementation details
  - Abstracts platform-specific implementation details from consumers
  
source_file_constraints: |
  - Should not include implementation code, only re-exports from submodules
  - Must maintain backwards compatibility for public APIs
  
dependencies:
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/monitor_base.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/linux.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/macos.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/windows.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/fallback.py
  
change_history:
  - timestamp: "2025-04-30T06:00:00Z"
    summary: "Updated fallback monitor import"
    details: "Changed import from \"from .fallback import PollingMonitor\" to \"from .fallback import FallbackMonitor as PollingMonitor\", fixed \"cannot import name 'PollingMonitor'\" error"
  - timestamp: "2025-04-29T00:51:00Z"
    summary: "Created platforms/__init__.py as part of fs_monitor reorganization"
    details: "Added exports for platform-specific monitor implementations, added header documentation"
```

### `factory.py`
```yaml
source_file_intent: |
  This file implements a factory class for creating platform-specific file system monitors.
  It detects the current operating system and creates the appropriate monitor
  implementation, with fallback mechanisms for unsupported platforms.
  
source_file_design_principles: |
  - Runtime platform detection that examines the actual OS environment using platform.system()
    rather than relying on compile-time flags or configuration files
  - Effective fallback mechanism that automatically switches to a universal polling implementation
    when platform-specific monitors fail, maintaining consistent API across all environments
  - Targeted module importing that loads specific platform implementations only at creation time,
    preventing unnecessary dependencies and import errors on platforms with missing libraries
  - Immediate error propagation that raises specific exception types at the appropriate architectural
    boundaries, allowing issues to be detected and diagnosed at their source
  - Centralized monitor instantiation that places all creation logic in a single class with
    clearly defined methods, preventing code duplication and ensuring uniform configuration
  
source_file_constraints: |
  - Must handle all supported platforms (Linux, macOS, Windows)
  - Must provide meaningful error messages on failure
  - Must not cause import errors on unsupported platforms
  - Must fall back to polling monitor when native implementation fails
  - Must log clear information about which monitor is being used
  
dependencies:
  - kind: system
    dependency: platform
  - kind: system
    dependency: logging
  - kind: system
    dependency: typing
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/monitor_base.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/dispatch/event_dispatcher.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/watch_manager.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/core/exceptions.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/linux.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/fallback.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/macos.py
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/windows.py
  
change_history:
  - timestamp: "2025-05-01T11:24:00Z"
    summary: "Added specific justifications for adjectives"
    details: "Enhanced documentation with concrete explanations for all descriptive terms, added detailed evidence for each claim about design properties, improved clarity of implementation descriptions with precise justifications"
  - timestamp: "2025-05-01T10:50:00Z"
    summary: "Refactored to use class-only approach"
    details: "Replaced create_platform_monitor function with a FileSystemMonitorFactory class, implemented create method as the main factory method, removed function-based approach entirely"
  - timestamp: "2025-04-29T00:58:00Z"
    summary: "Updated imports to match new directory structure"
    details: "Changed imports to use the new module structure with core/, dispatch/, and platforms/ subdirectories, updated dependencies section to reflect the new file locations, updated FallbackMonitor references to PollingMonitor for consistency"
```

### `monitor_base.py`
```yaml
source_file_intent: |
  Defines the base components for the file system monitoring system, including
  event types, event data structure, and the abstract base class for platform-specific
  file system monitors.
  
source_file_design_principles: |
  - Uses Enum for clear definition of change types.
  - Defines a structured ChangeEvent class for consistent event data.
  - Employs an Abstract Base Class (ABC) to enforce a common interface for all
    monitor implementations.
  - Includes basic thread safety considerations (RLock).
  - Design Decision: Abstract Base Class for Monitors (2025-04-14)
    * Rationale: Ensures all platform-specific monitors adhere to a consistent API, simplifying the factory and usage.
    * Alternatives considered: Duck typing (less explicit contract).
  
source_file_constraints: |
  - Requires Python 3's `abc` and `enum` modules.
  - Platform-specific implementations must inherit from FileSystemMonitor and
    implement the abstract methods.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-05-01T11:42:00Z"
    summary: "Fixed MonitorBase initialization"
    details: "Fixed variable reference errors in __init__ method, replaced references to undefined 'config' and 'change_queue' variables, used proper '_watch_manager' and '_event_dispatcher' variables, fixed \"name 'config' is not defined\" error"
  - timestamp: "2025-04-29T08:33:30Z"
    summary: "Centralized log file filtering logic"
    details: "Removed local _is_log_file() method in favor of centralized implementation, updated import to use shared path_utils.is_log_file function, updated dispatch_event to use centralized is_log_file implementation"
  - timestamp: "2025-04-15T09:40:40Z"
    summary: "Initial creation of base monitor components"
    details: "Defined ChangeType, ChangeEvent, and FileSystemMonitor ABC."
```

### `fallback.py`
```yaml
source_file_intent: |
  Implements a platform-independent file system monitor using polling 
  for environments where native file system notification APIs are unavailable.
  
source_file_design_principles: |
  - Universal compatibility across all operating systems
  - Configurable polling interval to balance resource usage and responsiveness
  - File change detection based on size, modification time, and content hashing
  - Handles common edge cases like temporary file renames and atomic writes
  
source_file_constraints: |
  - Higher latency and CPU usage compared to native monitoring solutions
  - Must be used as a last resort when platform-specific monitors are unavailable
  - Requires careful configuration to avoid excessive resource consumption
  
dependencies:
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/monitor_base.py
  
change_history:
  - timestamp: "2025-04-30T06:05:00Z"
    summary: "Renamed PollingMonitor to FallbackMonitor"
    details: "Renamed class for consistency with naming conventions, kept PollingMonitor as alias for backward compatibility"
  - timestamp: "2025-04-29T01:10:00Z"
    summary: "Improved polling efficiency"
    details: "Added content hash caching, optimized directory traversal, reduced CPU usage on large directories" 
  - timestamp: "2025-04-15T10:30:00Z"
    summary: "Created fallback polling monitor"
    details: "Implemented polling-based file system monitor as fallback for systems without native monitoring support"
```

### `linux.py`
```yaml
source_file_intent: |
  Implements a Linux-specific file system monitor using the inotify API
  for efficient file system change detection on Linux systems.
  
source_file_design_principles: |
  - Leverages native inotify API for optimal performance and resource usage
  - Maps inotify events to the common ChangeEvent model
  - Handles recursive directory watching and descriptor management
  
source_file_constraints: |
  - Linux-specific implementation, requires inotify support in the kernel
  - Depends on the pyinotify library for inotify bindings
  - Must handle inotify descriptor limits and watch resource cleanup
  
dependencies:
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/monitor_base.py
  - kind: system
    dependency: pyinotify
  
change_history:
  - timestamp: "2025-04-29T01:05:00Z"
    summary: "Updated to new directory structure"
    details: "Adapted imports to new module structure, updated class relationships"
  - timestamp: "2025-04-15T10:15:00Z"
    summary: "Created Linux monitor implementation"
    details: "Implemented inotify-based file system monitor for Linux"
```

### `macos.py`
```yaml
source_file_intent: |
  Implements a macOS-specific file system monitor using the FSEvents API
  for efficient file system change detection on macOS/Darwin systems.
  
source_file_design_principles: |
  - Utilizes native FSEvents API for optimal performance on macOS
  - Maps FSEvents callbacks to the common ChangeEvent model
  - Handles volume mount events and system sleep/wake cycles
  
source_file_constraints: |
  - macOS-specific implementation, requires Darwin kernel
  - Depends on the pyobjc-framework-FSEvents package
  - Must manage callback references to prevent premature garbage collection
  
dependencies:
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/monitor_base.py
  - kind: system
    dependency: pyobjc-framework-FSEvents
  
change_history:
  - timestamp: "2025-04-29T01:08:00Z"
    summary: "Updated to new directory structure"
    details: "Adapted imports to new module structure, updated class relationships"
  - timestamp: "2025-04-15T10:20:00Z"
    summary: "Created macOS monitor implementation"
    details: "Implemented FSEvents-based file system monitor for macOS"
```

### `windows.py`
```yaml
source_file_intent: |
  Implements a Windows-specific file system monitor using the 
  ReadDirectoryChangesW API for file system change detection on Windows.
  
source_file_design_principles: |
  - Uses native Windows API for optimal performance on Windows systems
  - Maps Windows file notifications to the common ChangeEvent model
  - Handles asynchronous completion notifications and overlapped I/O
  
source_file_constraints: |
  - Windows-specific implementation, requires Windows OS
  - Depends on the pywin32 package for Windows API access
  - Must properly manage Windows handles and notification buffers
  
dependencies:
  - kind: codebase
    dependency: src/dbp/fs_monitor/platforms/monitor_base.py
  - kind: system
    dependency: win32file
  - kind: system
    dependency: win32con
  
change_history:
  - timestamp: "2025-04-29T01:12:00Z"
    summary: "Updated to new directory structure"
    details: "Adapted imports to new module structure, updated class relationships"
  - timestamp: "2025-04-15T10:25:00Z"
    summary: "Created Windows monitor implementation"
    details: "Implemented ReadDirectoryChangesW-based file system monitor for Windows"
```

End of HSTC.md file
