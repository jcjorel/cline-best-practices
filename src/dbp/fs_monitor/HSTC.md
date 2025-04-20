# Hierarchical Semantic Tree Context - File System Monitor Module

This directory contains the file system monitoring components for the Document-Based Programming (DBP) system. It provides cross-platform file system change detection with platform-specific optimizations and a fallback polling mechanism.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'component.py':
**Intent:** Implements the FileSystemMonitorComponent class which provides file system change detection functionality to the application. This component monitors the file system for changes and notifies interested components.

**Design principles:**
- Conforms to the Component protocol (`src/dbp/core/component.py`)
- Encapsulates platform-specific file system monitoring implementations
- Provides cross-platform and fallback monitoring capabilities
- Uses factory pattern to create appropriate monitor for the current platform
- Operates with a change queue for efficient event processing

**Constraints:**
- Depends on the core component framework and other system components
- Platform-specific implementations may have their own dependencies
- Expects configuration for monitoring settings via InitializationContext

**Change History:**
- 2025-04-20T01:41:39Z : Completed dependency injection refactoring
- 2025-04-19T23:56:00Z : Added dependency injection support
- 2025-04-17T23:22:30Z : Updated to use strongly-typed configuration
- 2025-04-16T20:04:42Z : Initial creation of FileSystemMonitorComponent

### Filename 'base.py':
**Intent:** Defines the base components for the file system monitoring system, including event types, event data structure, and the abstract base class for platform-specific file system monitors.

**Design principles:**
- Uses Enum for clear definition of change types.
- Defines a structured ChangeEvent class for consistent event data.
- Employs an Abstract Base Class (ABC) to enforce a common interface for all monitor implementations.
- Includes basic thread safety considerations (RLock).
- Design Decision: Abstract Base Class for Monitors (2025-04-14)
  * Rationale: Ensures all platform-specific monitors adhere to a consistent API, simplifying the factory and usage.
  * Alternatives considered: Duck typing (less explicit contract).

**Constraints:**
- Requires Python 3's `abc` and `enum` modules.
- Platform-specific implementations must inherit from FileSystemMonitor and implement the abstract methods.

**Change History:**
- 2025-04-15T09:40:40Z : Initial creation of base monitor components

### Filename 'factory.py':
**Intent:** Implements the FileSystemMonitorFactory, responsible for detecting the current operating system and creating the most appropriate FileSystemMonitor instance (e.g., LinuxFileSystemMonitor, MacOSFileSystemMonitor, WindowsFileSystemMonitor, or FallbackFileSystemMonitor).

**Design principles:**
- Uses the Factory pattern to decouple monitor creation logic from the rest of the system.
- Detects the operating system using Python's `platform` module.
- Attempts to instantiate the preferred native monitor for the detected OS.
- Gracefully falls back to the polling monitor if native libraries are missing or fail to initialize.
- Instantiates and configures the ChangeDetectionQueue and GitIgnoreFilter needed by the monitors.
- Design Decision: Factory Pattern for Monitor Creation (2025-04-14)
  * Rationale: Centralizes the logic for selecting the correct monitor implementation based on the environment, simplifying system setup.
  * Alternatives considered: Conditional imports/instantiation in main application logic (less clean separation).

**Constraints:**
- Depends on all platform-specific monitor implementations (`linux.py`, `macos.py`, `windows.py`, `fallback.py`).
- Depends on `queue.py` and `filter.py`.
- Requires necessary libraries (inotify, fsevents, pywin32) to be installed for native monitors to be chosen.

**Change History:**
- 2025-04-15T09:45:55Z : Initial creation of FileSystemMonitorFactory

### Filename 'linux.py':
**Intent:** Implements the Linux-specific file system monitor using the inotify API. This provides efficient native change detection on Linux systems with minimal overhead.

**Design principles:**
- Leverages the inotify Linux API for efficient event notification
- Maps low-level inotify events to the standard ChangeEvent model
- Implements proper cleanup of watch descriptors and file handles
- Handles recursive directory monitoring with appropriate event filtering
- Design Decision: Mandatory inotify Support (2025-04-14)
  * Rationale: Ensures reliable and efficient file monitoring on Linux
  * Alternatives considered: Optional fallback to polling (rejected for reliability)

**Constraints:**
- Requires the inotify Python library to be installed
- Only works on Linux systems with inotify support
- Has watch descriptor limits that vary by system configuration

**Change History:**
- 2025-04-16T14:18:00Z : Added detection of inotify watch limits
- 2025-04-16T11:36:30Z : Fixed recursive directory watching
- 2025-04-15T09:52:30Z : Initial implementation of LinuxFileSystemMonitor

### Filename 'macos.py':
**Intent:** Implements the macOS-specific file system monitor using the FSEvents API. This provides efficient native change detection on macOS systems with minimal overhead.

**Design principles:**
- Leverages the FSEvents macOS API for efficient event notification
- Handles macOS-specific event flags and attributes
- Provides accurate event type classification from FSEvents data
- Supports both file and directory level monitoring
- Design Decision: Optional FSEvents Support (2025-04-14)
  * Rationale: Enables efficient monitoring when available but allows fallback
  * Alternatives considered: Mandatory requirement (rejected for flexibility)

**Constraints:**
- Requires the pyobjc-framework-FSEvents package to be installed
- Only works on macOS systems
- Event granularity differs from other implementations

**Change History:**
- 2025-04-16T10:24:00Z : Fixed event coalescing issues
- 2025-04-16T09:18:30Z : Enhanced path normalization for case-insensitive FS
- 2025-04-15T09:58:15Z : Initial implementation of MacOSFileSystemMonitor

### Filename 'windows.py':
**Intent:** Implements the Windows-specific file system monitor using the Win32 ReadDirectoryChangesW API. This provides efficient native change detection on Windows systems with minimal overhead.

**Design principles:**
- Leverages the Windows ReadDirectoryChangesW API for event notification
- Maps Windows-specific notification actions to the standard ChangeEvent model
- Handles completion ports and overlapped I/O for efficient monitoring
- Supports both synchronous and asynchronous notification models
- Design Decision: Optional Win32 Support (2025-04-14)
  * Rationale: Enables efficient monitoring when available but allows fallback
  * Alternatives considered: Mandatory requirement (rejected for flexibility)

**Constraints:**
- Requires the pywin32 package to be installed
- Only works on Windows systems
- Has buffer size limitations that need careful configuration

**Change History:**
- 2025-04-16T16:37:00Z : Added buffer size configuration option
- 2025-04-16T14:53:30Z : Fixed UNC path handling
- 2025-04-15T10:05:45Z : Initial implementation of WindowsFileSystemMonitor

### Filename 'fallback.py':
**Intent:** Implements a platform-independent file system monitor using periodic directory scanning. This provides a reliable fallback mechanism when native APIs are unavailable or fail.

**Design principles:**
- Uses simple polling with configurable intervals
- Maintains a snapshot of directory states for comparison
- Detects all change types: create, modify, delete, rename
- Handles nested directories with recursive scanning
- Design Decision: Polling-Based Fallback (2025-04-14)
  * Rationale: Ensures monitoring works on any platform even without native APIs
  * Alternatives considered: No fallback (rejected for robustness)

**Constraints:**
- Higher CPU and disk usage than native monitors
- Less immediate detection of changes (delay based on polling interval)
- May miss short-lived files between polling intervals
- Performance scales poorly with large directory structures

**Change History:**
- 2025-04-16T13:57:00Z : Optimized directory scanning algorithm
- 2025-04-16T12:24:30Z : Added detection of file moves via heuristics
- 2025-04-15T10:12:15Z : Initial implementation of FallbackFileSystemMonitor

### Filename 'queue.py':
**Intent:** Implements the ChangeDetectionQueue class that manages detected file system events. It provides thread-safe event queuing, batching, filtering, and distribution to registered listeners.

**Design principles:**
- Thread-safe implementation for concurrent producer/consumer access
- Supports event filtering to exclude unwanted notifications
- Implements event batching for efficient processing
- Provides both synchronous and asynchronous notification models
- Design Decision: Centralized Event Queue (2025-04-14)
  * Rationale: Decouples event producers from consumers and enables filtering
  * Alternatives considered: Direct callbacks (less flexible, harder to manage)

**Constraints:**
- Memory usage scales with event rate and processing speed
- Requires careful synchronization to prevent race conditions
- Needs proper implementation of event distribution to listeners

**Change History:**
- 2025-04-16T15:46:00Z : Added event batching capability
- 2025-04-16T13:12:30Z : Enhanced thread synchronization
- 2025-04-15T10:18:45Z : Initial implementation of ChangeDetectionQueue

### Filename 'filter.py':
**Intent:** Implements event filtering mechanisms, particularly the GitIgnoreFilter class that prevents change notifications for files and directories that match patterns in .gitignore files.

**Design principles:**
- Respects standard .gitignore syntax and semantics
- Efficiently caches parsed ignore patterns
- Supports both file and directory level filtering
- Cascades patterns from parent directories down to children
- Design Decision: GitIgnore-Based Filtering (2025-04-14)
  * Rationale: Leverages existing ignore rules that projects already maintain
  * Alternatives considered: Custom ignore files (more complex for users)

**Constraints:**
- Must accurately implement .gitignore pattern matching
- Needs to handle pattern inheritance from parent directories
- Required to efficiently check paths against potentially many patterns
- Should update when .gitignore files themselves change

**Change History:**
- 2025-04-16T17:23:00Z : Added automatic .gitignore file reloading on change
- 2025-04-16T14:57:30Z : Fixed pattern inheritance from parent directories
- 2025-04-15T10:25:30Z : Initial implementation of GitIgnoreFilter
