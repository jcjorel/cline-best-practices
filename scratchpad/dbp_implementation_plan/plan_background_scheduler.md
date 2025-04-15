# Background Task Scheduler Implementation Plan

## Overview

This document outlines the implementation plan for the Background Task Scheduler component, which is responsible for monitoring file changes and scheduling metadata extraction tasks in a resource-efficient manner.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - Documentation Monitoring section
- [design/BACKGROUND_TASK_SCHEDULER.md](../../doc/design/BACKGROUND_TASK_SCHEDULER.md) - Detailed specification
- [CONFIGURATION.md](../../doc/CONFIGURATION.md) - Configuration parameters
- [SECURITY.md](../../doc/SECURITY.md) - Security considerations

## Requirements

The Background Task Scheduler component must:
1. Run continuously from startup until shutdown
2. Monitor the codebase for file changes in near real-time using system-specific file notification mechanisms
3. Maintain a thread-safe change detection queue with debounce functionality
4. Manage worker threads for metadata extraction
5. Respect system resource constraints
6. Follow .gitignore patterns for file exclusion
7. Implement proper error handling and recovery strategies
8. Adhere to all security principles defined in SECURITY.md
9. Provide progress reporting and status information

## Design

### Architecture Overview

The Background Task Scheduler follows a publisher-subscriber architecture with a work queue:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│   File System       │─────▶│  Change Detection   │─────▶│ Worker Thread Pool  │
│   Monitor           │      │  Queue              │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                                                    │
                                                                    │
                                                                    ▼
┌─────────────────────┐                                 ┌─────────────────────┐
│                     │                                 │                     │
│   Status Reporter   │◀────────────────────────────────│ Metadata Extraction │
│                     │                                 │     Service         │
└─────────────────────┘                                 └─────────────────────┘
```

### Core Classes and Interfaces

1. **BackgroundTaskSchedulerComponent**

```python
class BackgroundTaskSchedulerComponent(Component):
    """Component for scheduling background tasks."""
    
    @property
    def name(self) -> str:
        return "background_scheduler"
    
    @property
    def dependencies(self) -> list[str]:
        return ["fs_monitor", "metadata_extraction"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the background task scheduler component."""
        self.config = context.config.scheduler
        self.logger = context.logger.get_child("background_scheduler")
        self.fs_monitor = context.get_component("fs_monitor")
        self.metadata_extraction = context.get_component("metadata_extraction")
        
        # Create scheduler components
        self.change_queue = ChangeDetectionQueue(self.config, self.logger)
        self.worker_pool = WorkerThreadPool(
            self.config,
            self.logger,
            self.metadata_extraction
        )
        self.status_reporter = StatusReporter(self.logger)
        
        # Connect components
        self.fs_monitor.register_change_listener(self._on_file_change)
        
        # Initialize scheduler controller
        self.controller = SchedulerController(
            change_queue=self.change_queue,
            worker_pool=self.worker_pool,
            status_reporter=self.status_reporter,
            config=self.config,
            logger=self.logger
        )
        
        self._initialized = True
        
        # Start the controller if enabled in config
        if self.config.enabled:
            self.start()
    
    def start(self) -> None:
        """Start the background scheduler."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info("Starting background task scheduler")
        self.controller.start()
    
    def stop(self) -> None:
        """Stop the background scheduler."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info("Stopping background task scheduler")
        self.controller.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the scheduler."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return {
            "running": self.controller.is_running(),
            "queue_size": self.change_queue.size(),
            "active_workers": self.worker_pool.active_count(),
            "processed_files": self.status_reporter.get_processed_count(),
            "failed_files": self.status_reporter.get_failed_count(),
            "stats": self.status_reporter.get_stats()
        }
    
    def force_process_file(self, file_path: str) -> None:
        """
        Force processing of a specific file.
        
        Args:
            file_path: Path to the file to process
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.change_queue.add_change(FileChange(
            path=file_path,
            change_type=ChangeType.MODIFIED,
            timestamp=time.time()
        ))
    
    def clear_queue(self) -> None:
        """Clear the change detection queue."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.change_queue.clear()
    
    def _on_file_change(self, change: FileChange) -> None:
        """Handle file change notification from file system monitor."""
        if not self._initialized:
            return
        
        self.change_queue.add_change(change)
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down background task scheduler")
        if hasattr(self, 'controller'):
            self.controller.stop()
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **ChangeDetectionQueue**

```python
class ChangeType(Enum):
    """Types of file changes."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChange:
    """Represents a change to a file."""
    path: str
    change_type: ChangeType
    timestamp: float
    old_path: Optional[str] = None  # For RENAMED changes


class ChangeDetectionQueue:
    """Thread-safe queue for file change events with debounce functionality."""
    
    def __init__(self, config: SchedulerConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._queue = {}  # Dict[str, FileChange]
        self._pending_changes = {}  # Dict[str, Timer]
        self._lock = threading.RLock()
        self._event = threading.Event()
    
    def add_change(self, change: FileChange) -> None:
        """
        Add a change to the queue with debounce.
        
        Args:
            change: FileChange object
        """
        with self._lock:
            path = change.path
            
            # Cancel any pending timers for this path
            self._cancel_pending_timer(path)
            
            # Create a new timer to add the change after debounce delay
            timer = Timer(
                interval=self.config.delay_seconds,
                function=self._add_change_immediately,
                args=(change,)
            )
            timer.daemon = True
            self._pending_changes[path] = timer
            timer.start()
            
            # If this path has been waiting for max delay, process immediately
            if self._should_process_immediately(path, change.timestamp):
                self._add_change_immediately(change)
    
    def _add_change_immediately(self, change: FileChange) -> None:
        """
        Add a change to the queue immediately.
        
        Args:
            change: FileChange object
        """
        with self._lock:
            path = change.path
            
            # Cancel any pending timer
            self._cancel_pending_timer(path)
            
            # Add to queue
            self._queue[path] = change
            
            # Notify waiting threads
            self._event.set()
    
    def _cancel_pending_timer(self, path: str) -> None:
        """
        Cancel a pending timer for a path.
        
        Args:
            path: File path
        """
        if path in self._pending_changes:
            self._pending_changes[path].cancel()
            del self._pending_changes[path]
    
    def _should_process_immediately(self, path: str, timestamp: float) -> bool:
        """
        Check if a path has been waiting for maximum delay.
        
        Args:
            path: File path
            timestamp: Current timestamp
        
        Returns:
            True if path should be processed immediately
        """
        # Get the earliest change time for this path
        earliest = None
        if path in self._queue:
            earliest = self._queue[path].timestamp
        
        # If no earlier change, or if max delay has passed, process immediately
        if earliest is None:
            return False
        
        return (timestamp - earliest) >= self.config.max_delay_seconds
    
    def get_next_batch(self, batch_size: int) -> List[FileChange]:
        """
        Get the next batch of changes.
        
        Args:
            batch_size: Maximum number of changes to return
        
        Returns:
            List of FileChange objects
        """
        with self._lock:
            if not self._queue:
                self._event.clear()
                return []
            
            # Get batch_size items or all items if fewer
            paths = list(self._queue.keys())[:batch_size]
            changes = [self._queue[path] for path in paths]
            
            # Remove processed items
            for path in paths:
                del self._queue[path]
            
            # If queue is now empty, clear event
            if not self._queue:
                self._event.clear()
            
            return changes
    
    def wait_for_changes(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for changes to be available.
        
        Args:
            timeout: Timeout in seconds, or None to wait indefinitely
        
        Returns:
            True if changes are available, False if timed out
        """
        return self._event.wait(timeout)
    
    def size(self) -> int:
        """
        Get the current queue size.
        
        Returns:
            Number of changes in the queue
        """
        with self._lock:
            return len(self._queue)
    
    def clear(self) -> None:
        """Clear the queue."""
        with self._lock:
            self._queue.clear()
            
            # Cancel all pending timers
            for timer in self._pending_changes.values():
                timer.cancel()
            self._pending_changes.clear()
            
            self._event.clear()
```

3. **WorkerThreadPool**

```python
class WorkerThreadPool:
    """Pool of worker threads for processing file changes."""
    
    def __init__(
        self,
        config: SchedulerConfig,
        logger: Logger,
        metadata_extraction: Component
    ):
        self.config = config
        self.logger = logger
        self.metadata_extraction = metadata_extraction
        self._workers = []
        self._active = False
        self._lock = threading.RLock()
        self._available_workers = queue.Queue()
    
    def start(self, change_queue: ChangeDetectionQueue, status_reporter: StatusReporter) -> None:
        """
        Start the worker pool.
        
        Args:
            change_queue: Queue of file changes to process
            status_reporter: Reporter for status updates
        """
        with self._lock:
            if self._active:
                return
            
            self._active = True
            
            # Create and start worker threads
            for i in range(self.config.worker_threads):
                worker = WorkerThread(
                    worker_id=i,
                    change_queue=change_queue,
                    metadata_extraction=self.metadata_extraction,
                    status_reporter=status_reporter,
                    config=self.config,
                    logger=self.logger,
                    available_queue=self._available_workers
                )
                worker.daemon = True
                self._workers.append(worker)
                worker.start()
                self._available_workers.put(worker)
    
    def stop(self) -> None:
        """Stop all worker threads."""
        with self._lock:
            if not self._active:
                return
            
            self._active = False
            
            # Signal all workers to stop
            for worker in self._workers:
                worker.stop()
            
            # Wait for all workers to finish
            for worker in self._workers:
                worker.join(timeout=1.0)
            
            self._workers = []
            
            # Clear available workers queue
            while not self._available_workers.empty():
                try:
                    self._available_workers.get_nowait()
                except queue.Empty:
                    break
    
    def active_count(self) -> int:
        """
        Get the number of active workers.
        
        Returns:
            Number of active workers
        """
        with self._lock:
            return sum(1 for worker in self._workers if worker.is_active())
    
    def is_active(self) -> bool:
        """
        Check if the worker pool is active.
        
        Returns:
            True if the worker pool is active
        """
        with self._lock:
            return self._active


class WorkerThread(threading.Thread):
    """Worker thread for processing file changes."""
    
    def __init__(
        self,
        worker_id: int,
        change_queue: ChangeDetectionQueue,
        metadata_extraction: Component,
        status_reporter: StatusReporter,
        config: SchedulerConfig,
        logger: Logger,
        available_queue: Queue
    ):
        super().__init__(name=f"Worker-{worker_id}")
        self.worker_id = worker_id
        self.change_queue = change_queue
        self.metadata_extraction = metadata_extraction
        self.status_reporter = status_reporter
        self.config = config
        self.logger = logger.get_child(f"worker-{worker_id}")
        self.available_queue = available_queue
        self._active = True
        self._currently_processing = None
        self._lock = threading.RLock()
    
    def run(self) -> None:
        """Main worker loop."""
        self.logger.debug("Worker thread started")
        
        while self._active:
            try:
                # Wait for changes
                if not self.change_queue.wait_for_changes(timeout=1.0):
                    continue
                
                # Get a batch of changes
                batch_size = self.config.batch_size
                changes = self.change_queue.get_next_batch(batch_size)
                
                if not changes:
                    continue
                
                # Process each change
                for change in changes:
                    if not self._active:
                        break
                    
                    try:
                        self._process_change(change)
                    except Exception as e:
                        self.logger.error(f"Error processing change for {change.path}: {e}")
                        self.status_reporter.report_failure(change.path, str(e))
            
            except Exception as e:
                self.logger.error(f"Unexpected error in worker thread: {e}")
                time.sleep(1.0)  # Avoid tight loop if persistent error
        
        self.logger.debug("Worker thread stopped")
    
    def stop(self) -> None:
        """Signal the worker to stop."""
        self._active = False
    
    def is_active(self) -> bool:
        """
        Check if the worker is active.
        
        Returns:
            True if the worker is active
        """
        return self._active and self.is_alive()
    
    def get_current_task(self) -> Optional[str]:
        """
        Get the path of the file currently being processed.
        
        Returns:
            Path of the file or None
        """
        with self._lock:
            return self._currently_processing
    
    def _process_change(self, change: FileChange) -> None:
        """
        Process a file change.
        
        Args:
            change: FileChange object
        """
        path = change.path
        change_type = change.change_type
        
        with self._lock:
            self._currently_processing = path
        
        try:
            self.logger.debug(f"Processing {change_type} for {path}")
            
            if change_type == ChangeType.DELETED:
                # Handle deleted file
                # This will involve removing metadata from database
                self.status_reporter.report_success(path)
                return
            
            # For created, modified, or renamed files, extract metadata
            if not os.path.exists(path):
                self.logger.warning(f"File {path} no longer exists")
                self.status_reporter.report_failure(path, "File no longer exists")
                return
            
            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read {path}: {e}")
                self.status_reporter.report_failure(path, f"Failed to read file: {e}")
                return
            
            # Extract metadata
            try:
                metadata = self.metadata_extraction.extract_metadata(path, content)
                if metadata:
                    self.status_reporter.report_success(path)
                else:
                    self.status_reporter.report_failure(path, "Metadata extraction returned None")
            except Exception as e:
                self.logger.error(f"Metadata extraction failed for {path}: {e}")
                self.status_reporter.report_failure(path, f"Metadata extraction failed: {e}")
        
        finally:
            with self._lock:
                self._currently_processing = None
                
                # Make this worker available again
                self.available_queue.put(self)
```

4. **StatusReporter**

```python
class StatusReporter:
    """Reports and tracks status of metadata extraction tasks."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self._lock = threading.RLock()
        self._processed_count = 0
        self._failed_count = 0
        self._recent_failures = collections.deque(maxlen=100)
        self._recent_successes = collections.deque(maxlen=100)
        self._start_time = time.time()
    
    def report_success(self, file_path: str) -> None:
        """
        Report successful processing of a file.
        
        Args:
            file_path: Path to the processed file
        """
        with self._lock:
            self._processed_count += 1
            self._recent_successes.append((file_path, time.time()))
    
    def report_failure(self, file_path: str, error: str) -> None:
        """
        Report failed processing of a file.
        
        Args:
            file_path: Path to the processed file
            error: Error message
        """
        with self._lock:
            self._failed_count += 1
            self._recent_failures.append((file_path, time.time(), error))
    
    def get_processed_count(self) -> int:
        """
        Get the number of successfully processed files.
        
        Returns:
            Number of successfully processed files
        """
        with self._lock:
            return self._processed_count
    
    def get_failed_count(self) -> int:
        """
        Get the number of failed files.
        
        Returns:
            Number of failed files
        """
        with self._lock:
            return self._failed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about processing.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            current_time = time.time()
            uptime = current_time - self._start_time
            
            return {
                "processed_count": self._processed_count,
                "failed_count": self._failed_count,
                "uptime_seconds": uptime,
                "files_per_second": self._processed_count / uptime if uptime > 0 else 0,
                "recent_failures": list(self._recent_failures),
                "recent_successes": list(self._recent_successes)
            }
```

5. **SchedulerController**

```python
class SchedulerController:
    """Controls the operation of the background task scheduler."""
    
    def __init__(
        self,
        change_queue: ChangeDetectionQueue,
        worker_pool: WorkerThreadPool,
        status_reporter: StatusReporter,
        config: SchedulerConfig,
        logger: Logger
    ):
        self.change_queue = change_queue
        self.worker_pool = worker_pool
        self.status_reporter = status_reporter
        self.config = config
        self.logger = logger
        self._running = False
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self.logger.info("Starting scheduler controller")
        self._running = True
        
        # Start the worker pool
        self.worker_pool.start(self.change_queue, self.status_reporter)
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        self.logger.info("Stopping scheduler controller")
        self._running = False
        
        # Stop the worker pool
        self.worker_pool.stop()
    
    def is_running(self) -> bool:
        """
        Check if the scheduler is running.
        
        Returns:
            True if the scheduler is running
        """
        return self._running
```

### Configuration Parameters

The Background Task Scheduler component will be configured through these parameters defined in CONFIGURATION.md:

```python
@dataclass
class SchedulerConfig:
    """Configuration for background task scheduler."""
    enabled: bool  # Whether the scheduler is enabled
    delay_seconds: int  # Debounce delay before processing changes
    max_delay_seconds: int  # Maximum delay for any file
    worker_threads: int  # Number of worker threads
    max_queue_size: int  # Maximum size of change queue
    batch_size: int  # Files processed in one batch
```

Default configuration values (as defined in CONFIGURATION.md):

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `enabled` | Enable the background scheduler | `true` | `true, false` |
| `delay_seconds` | Debounce delay before processing changes | `10` | `1-60` |
| `max_delay_seconds` | Maximum delay for any file | `120` | `30-600` |
| `worker_threads` | Number of worker threads | `2` | `1-8` |
| `max_queue_size` | Maximum size of change queue | `1000` | `100-10000` |
| `batch_size` | Files processed in one batch | `20` | `1-100` |

## Implementation Plan

### Phase 1: Core Structure
1. Implement BackgroundTaskSchedulerComponent as a system component
2. Define ChangeDetectionQueue with debounce functionality
3. Create configuration class for scheduler
4. Implement basic task scheduling and control functions

### Phase 2: Worker Thread Management
1. Implement WorkerThreadPool for managing worker threads
2. Create WorkerThread for processing file changes
3. Implement thread synchronization mechanisms
4. Add worker thread lifecycle management

### Phase 3: Status Reporting and Progress Tracking
1. Implement StatusReporter for tracking processing status
2. Create progress reporting functions
3. Implement statistics gathering
4. Add error handling and reporting

### Phase 4: Integration and Performance Optimization
1. Integrate with File System Monitor component
2. Integrate with Metadata Extraction component
3. Implement resource usage monitoring
4. Add throttling mechanisms for high system load

## Security Considerations

The Background Task Scheduler component implements these security measures:
- All processing performed locally with no external data transmission
- File access follows filesystem permissions
- Resource usage limitations to prevent system impact
- No arbitrary code execution
- Thread safety for multi-threaded access
- Error isolation to prevent system-wide failures

## Testing Strategy

### Unit Tests
- Test ChangeDetectionQueue with various change scenarios
- Test debounce functionality with different timing patterns
- Test worker thread pool with mock tasks
- Test error handling and recovery

### Integration Tests
- Test integration with File System Monitor
- Test integration with Metadata Extraction
- Test full file change workflow from detection to processing
- Test system under load with many file changes

### System Tests
- Test performance with large codebases
- Test resource usage under various loads
- Test resilience to errors and system issues
- Test shutdown and cleanup during system termination

## Dependencies on Other Plans

This plan depends on:
- File System Monitoring plan (for change detection)
- Metadata Extraction plan (for processing files)
- Component Initialization plan (for component framework)

## Implementation Timeline

1. Core Structure - 2 days
2. Worker Thread Management - 2 days
3. Status Reporting - 1 day
4. Integration and Optimization - 2 days

Total: 7 days

## Future Enhancements

- Adaptive scheduling based on system load
- Priority-based file processing
- Enhanced monitoring and diagnostics
- Integration with version control for smarter processing
- Distributed processing across multiple machines
