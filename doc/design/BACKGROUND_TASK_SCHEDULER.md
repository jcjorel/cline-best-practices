# Background Task Scheduler

This document details the design and implementation of the Background Task Scheduler component in the Documentation-Based Programming system, which is responsible for monitoring file changes and extracting metadata from codebase files.

## Component Overview

The Background Task Scheduler is a critical component that:

- Runs continuously from MCP server startup until shutdown
- Monitors the codebase for file changes in near real-time
- Maintains an in-memory metadata cache synchronized with persistent storage
- Extracts metadata from new or modified files using LLM capabilities
- Updates the SQLite database with extracted metadata
- Provides thread-safe access to metadata for other components

## Architecture

The Background Task Scheduler follows a publisher-subscriber pattern with these key components:

```
┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│                   │      │                   │      │                   │
│  File System      │─────▶│  Change Detection │─────▶│  Metadata         │
│  Monitor          │      │  Queue            │      │  Extraction       │
│                   │      │                   │      │  Worker           │
└───────────────────┘      └───────────────────┘      └───────────────────┘
                                                              │
                                                              ▼
┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│                   │      │                   │      │                   │
│  In-Memory        │◀─────│  Database         │◀─────│  LLM Processing   │
│  Metadata Cache   │      │  Persistence      │      │  Results          │
│                   │      │  Layer            │      │                   │
└───────────────────┘      └───────────────────┘      └───────────────────┘
```

### 1. File System Monitor

- Uses system-specific file notification mechanisms:
  - `inotify()` on Linux/WSL environments
  - `FSEvents` on macOS
  - `ReadDirectoryChangesW` on Windows
- Registers for appropriate file system events (create, modify, delete, rename)
- Filters events based on .gitignore patterns and system configurations
- Emits change events to the Change Detection Queue

### 2. Change Detection Queue

- Thread-safe queue implementation that buffers file change events
- Implements duplicate event elimination based on file path
- Sorts events by timestamp (oldest to newest)
- Respects configurable delay before processing (debounce mechanism)
- Enforces maximum delay threshold (default: 2 minutes)

### 3. Metadata Extraction Worker

- Consumes events from the Change Detection Queue
- Determines if metadata extraction is necessary based on:
  - File existence
  - File size change
  - Missing metadata in database
  - File modification timestamp
- Creates Amazon Nova Lite LLM instances for metadata extraction
- Manages concurrent extraction operations within resource limits

### 4. LLM Processing

- Provides context to LLM instances including:
  - File content
  - Template standards (e.g., GENAI_HEADER_TEMPLATE.txt)
  - Expected output JSON schema
- Extracts structured metadata including:
  - File header sections (intent, design principles, etc.)
  - Function and class definitions
  - Documentation references
  - Change history
- Validates extraction results against schema

### 5. Database Persistence Layer

- Manages SQLite database connections with connection pooling
- Implements transactions for atomic operations
- Handles concurrent access with proper locking mechanisms
- Updates database schema as needed
- Performs periodic maintenance operations (vacuum, etc.)

### 6. In-Memory Metadata Cache

- Provides fast access to frequently used metadata
- Implements efficient data structures for quick lookups
- Maintains consistency with database through synchronization
- Provides thread-safe access methods
- Implements cache invalidation strategies

## Operational Workflow

### Startup Sequence

1. System initializes the SQLite database connection
2. Loads existing metadata from database into memory cache
3. Initializes file system monitoring with appropriate platform-specific implementation
4. Starts the Change Detection Queue
5. Creates and starts Metadata Extraction Worker threads
6. Begins processing any detected changes

### File Change Detection

1. File system event occurs (create, modify, delete, rename)
2. File System Monitor receives notification
3. Event is filtered against .gitignore patterns
4. If not filtered, event is added to Change Detection Queue
5. Duplicate events for same file path are eliminated
6. Timer starts for debounce period

### Metadata Extraction Process

1. After debounce period (or maximum delay threshold), file is dequeued
2. System checks current file state:
   - If deleted: Remove metadata from cache and database
   - If created/modified: Continue to extraction
3. System determines if extraction is necessary:
   - No existing metadata, or
   - File size changed, or
   - Content hash changed
4. If extraction needed:
   - Check if file changed during decision process
   - If changed again, requeue for later processing
   - If stable, proceed with extraction
5. Create Amazon Nova Lite instance
6. Provide file content and extraction context
7. Process LLM response
8. Validate extracted metadata
9. Update database and in-memory cache

### Concurrency Control

1. Database layer implements proper transaction isolation
2. Memory cache uses read-write locks for thread safety
3. Queue operations are atomic and thread-safe
4. Extraction worker pool limits concurrent operations
5. Deadlock prevention through consistent lock acquisition order

## Performance Considerations

### Efficient File Monitoring

The scheduler uses native operating system file notification APIs rather than polling to minimize resource usage:
- Uses `inotify()` on Linux/WSL environments
- Uses `FSEvents` on macOS
- Uses `ReadDirectoryChangesW` on Windows

This approach provides immediate notification of changes while consuming minimal system resources.

### Optimized Change Detection

Multiple optimizations reduce unnecessary processing:
- File size comparison before content analysis
- Metadata existence check to avoid reprocessing
- Duplicate event elimination in queue
- Debounce mechanism to handle rapid changes

### Resource Management

The scheduler implements several techniques to manage resource usage:
- Limited worker thread pool size
- Configurable concurrency limits
- Prioritization of high-impact files
- Batch processing where appropriate
- Memory-efficient data structures

### Memory vs. Database Trade-offs

The system balances in-memory performance with persistence:
- Frequently accessed metadata kept in memory
- Complete metadata stored in database
- Lazy loading for rarely accessed items
- Memory pressure monitoring
- Configurable cache sizes

## Error Handling and Recovery

### Robust Error Recovery

The scheduler is designed to gracefully handle various failure scenarios:
- Failed LLM extraction attempts are retried with exponential backoff
- Database connection failures trigger reconnection strategies
- File access errors are logged and retried
- Worker thread crashes are detected and new threads spawned

### Consistency Maintenance

To ensure metadata consistency:
- Atomic database transactions for related changes
- Validation of LLM extraction results before storage
- Periodic consistency checks between memory and database
- Automatic recovery mechanisms for detected inconsistencies

## Configuration Parameters

The Background Task Scheduler exposes configuration parameters (managed through CONFIGURATION.md):

| Parameter | Description | Default | Valid Range |
|-----------|-------------|---------|------------|
| `scheduler.enabled` | Enable the background scheduler | `true` | `true, false` |
| `scheduler.delay_seconds` | Debounce delay before processing changes | `10` | `1-60` |
| `scheduler.max_delay_seconds` | Maximum delay for any file | `120` | `30-600` |
| `scheduler.worker_threads` | Number of worker threads | `2` | `1-8` |
| `scheduler.max_queue_size` | Maximum size of change queue | `1000` | `100-10000` |
| `scheduler.batch_size` | Files processed in one batch | `20` | `1-100` |

## Relationship to Other Components

The Background Task Scheduler interfaces with several other system components:

- **MCP Server**: Receives initialization and shutdown signals
- **LLM Coordination Architecture**: Uses LLM instances for metadata extraction
- **Consistency Analysis Engine**: Provides metadata for consistency checks
- **Recommendation Generator**: Triggers on metadata changes
- **Python CLI Client**: Reports status and statistics

For detailed interface specifications, refer to the respective component documentation.

## Design Decisions

### Design Decision: Native File System Notification APIs

- **Decision**: Use platform-specific file system notification APIs instead of polling
- **Rationale**: Native APIs provide immediate notification with minimal resource usage
- **Alternatives Considered**: 
  - Periodic polling (rejected due to performance impact)
  - Generic cross-platform libraries (rejected due to overhead)

### Design Decision: Two-Tier Storage Architecture

- **Decision**: Use both in-memory cache and SQLite database for metadata storage
- **Rationale**: Balances performance (memory) with persistence (database)
- **Alternatives Considered**: 
  - Memory-only (rejected due to lack of persistence)
  - Database-only (rejected due to performance impact)

### Design Decision: Debounced Processing with Maximum Threshold

- **Decision**: Implement debounce mechanism with maximum delay threshold
- **Rationale**: Prevents excessive processing during rapid changes while ensuring timeliness
- **Alternatives Considered**: 
  - Immediate processing (rejected due to resource consumption)
  - Fixed intervals (rejected due to variable workload patterns)

## Security Considerations

The Background Task Scheduler adheres to the security principles outlined in SECURITY.md:

- **Data Locality**: All processing performed locally, no data leaves the system
- **Isolation**: Complete separation between indexed projects
- **No Code Execution**: System never executes code from monitored files
- **Resource Constraints**: Limited CPU and memory usage with intelligent throttling
- **Access Control**: Follows existing filesystem permissions

## Future Enhancements

Potential future enhancements for the Background Task Scheduler:

1. **Adaptive Scheduling**: Dynamic adjustment of processing parameters based on system load
2. **Priority-Based Processing**: Process high-impact files first based on usage patterns
3. **Pre-emptive Extraction**: Predict likely file modifications and prepare resources
4. **Distributed Operation**: Support for distributed codebase monitoring across networked systems
5. **Enhanced LLM Models**: Integration with more advanced models as they become available
