# Hierarchical Semantic Tree Context - Core Module

This directory contains core system components that provide foundational functionality for the Document-Based Programming (DBP) system.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'component.py':
**Intent:** Defines the simplified Component base class that all system components must extend. Provides a clean and minimal interface for component lifecycle management and dependency declaration following KISS principles.

**Design principles:**
- Ultra-simple interface for component lifecycle management
- Explicit dependency declaration via simple properties
- Clear initialization status tracking
- Minimal required methods (initialize, shutdown)
- Single responsibility for lifecycle management

**Constraints:**
- Must be straightforward enough for all components to implement correctly
- Must provide clear indication of initialization status
- Must not introduce complexity in dependency declaration
- Requires components to set _initialized flag properly

**Change History:**
- 2025-04-20T00:35:54Z : Removed deprecated dependencies property
- 2025-04-19T23:31:00Z : Added dependency injection support to Component
- 2025-04-17T23:18:30Z : Added strong typing to Component.initialize() method
- 2025-04-17T23:10:30Z : Enhanced InitializationContext with typed configuration

### Filename 'file_access.py':
**Intent:** Implements the FileAccessService class, which provides a standard interface for accessing file content across the DBP system. This service is used by components like doc_relationships to read file contents without having to implement their own file access logic.

**Design principles:**
- Simple, focused interface for file operations
- Error handling with clear reporting
- Minimal dependencies to ensure wide reusability
- Follows a service pattern for consistent file access across components

**Constraints:**
- Must handle file read errors gracefully with appropriate logging
- Should support basic file encoding detection
- Does not handle writing to files (read-only service)

**Change History:**
- 2025-04-18T15:40:30Z : Initial creation of FileAccessService

### Filename 'file_access_component.py':
**Intent:** Implements the FileAccessComponent class which provides a file access service to the application. This component manages the FileAccessService and makes it available to other components through the component system.

**Design principles:**
- Conforms to the Component protocol (src/dbp/core/component.py)
- Provides a centralized service for file operations
- Minimal dependencies to ensure early initialization
- Single responsibility for file access operations

**Constraints:**
- Must be initialized early in the component lifecycle
- Should not have dependencies on high-level components

**Change History:**
- 2025-04-19T23:46:00Z : Added dependency injection support
- 2025-04-18T15:41:30Z : Initial creation of FileAccessComponent

### Filename 'fs_utils.py':
**Intent:** Provides filesystem utility functions used across different components in the DBP system. Functions for directory creation, path manipulation, and file operations that maintain consistency across the application and handle common error cases.

**Design principles:**
- Single Responsibility: Each function does one thing well and handles its error cases.
- Defensive Programming: Functions validate inputs and handle edge cases gracefully.
- Comprehensive Logging: All operations are logged with appropriate detail level.
- Error Transparency: Filesystem errors are caught, logged, and re-raised with context.
- Design Decision: Centralized Filesystem Operations (2025-04-17)
  * Rationale: Ensures consistent directory creation and path handling across components
  * Alternatives considered: Component-specific implementations (rejected due to duplication)

**Constraints:**
- Must not depend on other DBP components to avoid circular dependencies
- Must handle relative/absolute paths consistently
- Should not modify any global state

**Change History:**
- 2025-04-17T12:03:38Z : Updated path resolution to be Git root-relative
- 2025-04-17T11:46:24Z : Initial creation

### Filename 'lifecycle.py':
**Intent:** Implements the simplified LifecycleManager class, which manages the overall application lifecycle (startup, shutdown) using the ultra-simple component system. Serves as the main entry point for the DBP application.

**Design principles:**
- Ultra-simple application lifecycle management
- Direct component registration rather than through factories
- Clear and straightforward startup/shutdown processes
- Minimal error handling focused on clear reporting
- Single responsibility for application lifecycle

**Constraints:**
- Must handle basic signal interrupts for graceful shutdown
- Uses direct import of components rather than factories
- Initialization errors fail fast with clear reporting
- Maintains backward compatibility with existing entry points

**Change History:**
- 2025-04-20T19:21:00Z : Added watchdog keepalive calls
- 2025-04-19T23:43:00Z : Added ComponentRegistry integration
- 2025-04-18T17:02:00Z : Fixed component registration import mechanism
- 2025-04-17T17:28:22Z : Standardized log format for consistency

### Filename 'log_utils.py':
**Intent:** Provides logging utility functions and custom formatters used across different components in the DBP system. Ensures consistent logging format and behavior throughout the application.

**Design principles:**
- Single Responsibility: Focused only on logging-related utilities
- Consistent Formatting: Provides standard formatters for unified log appearance
- Reusability: Utilities can be imported by any component requiring logging
- Design Decision: Centralized Logging Formatters (2025-04-17)
  * Rationale: Ensures consistent log formatting across all components
  * Alternatives considered: Per-component formatters (rejected due to inconsistency)

**Constraints:**
- Must not depend on other DBP components to avoid circular dependencies
- Must maintain compatibility with Python's standard logging module
- Should handle different log format requirements flexibly

**Change History:**
- 2025-04-18T13:54:00Z : Fixed log level name truncation
- 2025-04-17T17:35:32Z : Enhanced root logger configuration for consistent format
- 2025-04-17T17:18:15Z : Added centralized setup_application_logging function
- 2025-04-17T17:09:30Z : Enhanced MillisecondFormatter to remove duplicate level prefixes

### Filename 'registry.py':
**Intent:** Implements a centralized component registry that allows components to be registered with their dependencies in one place. This provides a cleaner way to manage component dependencies and registration compared to defining dependencies in each component class.

**Design principles:**
- Centralized component registration with explicit dependency declaration
- Clear separation between component definition and dependency declaration
- Support for conditional component registration based on configuration
- KISS approach to dependency management without complex abstractions
- Compatibility with the existing ComponentSystem for backward compatibility

**Constraints:**
- Must work with the existing Component and ComponentSystem classes
- Must provide a simple and clear API for component registration
- Must not introduce complex abstractions or patterns
- Should support a transition period where both approaches are supported

**Change History:**
- 2025-04-19T23:37:00Z : Initial creation of ComponentRegistry

### Filename 'system.py':
**Intent:** Implements the ComponentSystem class, a minimalist system for managing component lifecycle (registration, initialization, shutdown) that replaces the previous complex orchestration system with a much simpler KISS approach.

**Design principles:**
- Ultra-simple component management with minimal code complexity
- Dictionary-based component registry instead of complex classes
- Direct dependency validation without complex graph algorithms
- Sequential initialization based on simple dependency order
- Clear error reporting rather than sophisticated recovery

**Constraints:**
- Components must implement the Component interface
- Initialization errors fail fast rather than attempting recovery
- All components are stored in a single dictionary
- No complex transactions or rollbacks beyond basic cleanup

**Change History:**
- 2025-04-20T19:15:00Z : Added watchdog keepalive to prevent deadlocks
- 2025-04-20T00:38:24Z : Removed backward compatibility code
- 2025-04-19T23:36:00Z : Added dependency injection support to ComponentSystem
- 2025-04-17T23:12:30Z : Added typed configuration to initialization context

### Filename 'watchdog.py':
**Intent:** Implements a watchdog mechanism to detect and handle system deadlocks. Provides functionality to monitor process activity and automatically terminate stuck processes to prevent system-wide failures.

**Design principles:**
- Thread-safe activity monitoring with configurable timeout threshold
- Uses condition variables for efficient waiting instead of polling
- Provides detailed process diagnostics to aid debugging of deadlocks
- Automatic process termination with comprehensive exit information
- Non-invasive monitoring that minimizes performance impact

**Constraints:**
- Must be thread-safe to handle concurrent access from multiple components
- Diagnostic collection must not interfere with normal process operation
- Must gracefully handle exceptions during diagnostic collection
- Should capture sufficient debug information for post-mortem analysis

**Change History:**
- 2025-04-20T10:43:35Z : Created watchdog module with conditional variable mechanism
