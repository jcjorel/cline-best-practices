# File System Monitoring Implementation Plan

## Overview

This document details the implementation plan for the File System Monitoring component of the Documentation-Based Programming (DBP) system. According to the project documentation, this component is responsible for detecting changes in the codebase and triggering appropriate processing of modified files.

## Requirements

From the project documentation, specifically [DESIGN.md](../doc/DESIGN.md) and [BACKGROUND_TASK_SCHEDULER.md](../doc/design/BACKGROUND_TASK_SCHEDULER.md), the File System Monitor must:

1. Detect file changes within 10 seconds of modification
2. Use system-specific file notification APIs to minimize resource usage
   - `inotify()` on Linux/WSL environments
   - `FSEvents` on macOS
   - `ReadDirectoryChangesW` on Windows
3. Respect .gitignore patterns and dynamically update exclusions when .gitignore files change
4. Exclude `<project_root>/scratchpad/` directory and any file/directory with "deprecated" in the path
5. Implement a debounced change detection queue with configurable delay
6. Consume minimal resources (<5% CPU, <100MB RAM)
7. Operate with complete project isolation for security
8. Follow existing filesystem permissions

## Implementation Components

### 1. Platform-Specific File Watcher

This component will provide a unified interface for different operating system file notification mechanisms:

```python
class FileWatcherFactory:
    @staticmethod
    def create_file_watcher(config):
        """Create appropriate file watcher based on platform."""
        import platform
        system = platform.system().lower()
        
        if system == "linux":
            return InotifyFileWatcher(config)
        elif system == "darwin":
            return FSEventsFileWatcher(config)
        elif system == "windows":
            return WindowsFileWatcher(config)
        else:
            # Fallback for unsupported platforms
            return PollingFileWatcher(config)

class BaseFileWatcher:
    """Abstract base class for file watchers."""
    
    def __init__(self, config):
        self.config = config
        self.callbacks = []
        
    def add_directory(self, path):
        """Add a directory to watch."""
        pass
        
    def remove_directory(self, path):
        """Remove a directory from watch list."""
        pass
        
    def register_callback(self, callback):
        """Register a callback for file change events."""
        self.callbacks.append(callback)
        
    def start(self):
        """Start watching for file changes."""
        pass
        
    def stop(self):
        """Stop watching for file changes."""
        pass
        
    def is_running(self):
        """Check if watcher is running."""
        pass
```

#### Linux Implementation (inotify)

```python
class InotifyFileWatcher(BaseFileWatcher):
    def __init__(self, config):
        super().__init__(config)
        self.watches = {}  # Map of paths to watch descriptors
        self.inotify_fd = None
        self.watch_thread = None
        self.running = False
        
    def start(self):
        """Start inotify watcher."""
        import inotify_simple
        
        self.inotify_fd = inotify_simple.INotify()
        self.running = True
        
        # Start thread to process inotify events
        self.watch_thread = threading.Thread(target=self._watch_thread_func)
        self.watch_thread.daemon = True
        self.watch_thread.start()
        
    def _watch_thread_func(self):
        """Thread function to process inotify events."""
        import inotify_simple
        
        while self.running:
            # Wait for events with timeout to allow for clean shutdown
            events = self.inotify_fd.read(timeout=1000)
            for event in events:
                # Process event and notify callbacks
                path = self._get_path_for_descriptor(event.wd)
                if path:
                    for callback in self.callbacks:
                        callback(path, self._event_type_to_action(event))
```

#### macOS Implementation (FSEvents)

```python
class FSEventsFileWatcher(BaseFileWatcher):
    def __init__(self, config):
        super().__init__(config)
        self.stream_refs = {}
        self.running = False
        
    def start(self):
        """Start FSEvents watcher."""
        from FSEvents import FSEventStreamCreate, FSEventStreamStart
        
        # Set up FSEvents streams for each watched directory
        for path in self.watched_directories:
            stream_ref = FSEventStreamCreate(
                # Configuration parameters
            )
            FSEventStreamStart(stream_ref)
            self.stream_refs[path] = stream_ref
            
        self.running = True
```

#### Windows Implementation (ReadDirectoryChangesW)

```python
class WindowsFileWatcher(BaseFileWatcher):
    def __init__(self, config):
        super().__init__(config)
        self.watches = {}
        self.running = False
        
    def start(self):
        """Start Windows directory change notification."""
        import win32file
        import win32con
        
        # Set up directory watches using ReadDirectoryChangesW
        for path in self.watched_directories:
            # Configure and start watch
            pass
            
        self.running = True
```

#### Fallback Polling Implementation

```python
class PollingFileWatcher(BaseFileWatcher):
    def __init__(self, config):
        super().__init__(config)
        self.watched_paths = {}  # Path -> last_modified_time
        self.running = False
        self.poll_thread = None
        
    def start(self):
        """Start polling for file changes."""
        self.running = True
        
        # Start thread for polling
        self.poll_thread = threading.Thread(target=self._poll_thread_func)
        self.poll_thread.daemon = True
        self.poll_thread.start()
        
    def _poll_thread_func(self):
        """Thread function to poll for changes."""
        while self.running:
            self._check_for_changes()
            time.sleep(self.config.get('monitor.poll_interval_seconds', 5))
```

### 2. Exclusion Pattern Manager

This component will handle the exclusion patterns, including .gitignore files and mandatory exclusions:

```python
class ExclusionPatternManager:
    def __init__(self, config):
        """Initialize exclusion pattern manager."""
        self.config = config
        self.gitignore_patterns = {}  # path -> patterns
        self.additional_patterns = config.get('monitor.ignore_patterns', [])
        self.mandatory_patterns = [
            "**/scratchpad/**",              # Exclude scratchpad directory
            "**/*deprecated*/**",            # Exclude deprecated directories
            "**/.*",                         # Hidden files and dirs
            "**/__pycache__/**",             # Python cache
            "**/node_modules/**",            # Node.js modules
        ]
        
    def load_gitignore(self, root_path):
        """Load all .gitignore files in the directory tree."""
        # Find and parse all .gitignore files
        for dirpath, _, filenames in os.walk(root_path):
            if '.gitignore' in filenames:
                gitignore_path = os.path.join(dirpath, '.gitignore')
                with open(gitignore_path, 'r') as f:
                    patterns = f.readlines()
                self.gitignore_patterns[dirpath] = [p.strip() for p in patterns if p.strip() and not p.startswith('#')]
    
    def should_exclude(self, path):
        """Check if a path should be excluded."""
        # Check mandatory exclusions first
        for pattern in self.mandatory_patterns:
            if self._matches_pattern(path, pattern):
                return True
                
        # Check additional configured exclusions
        for pattern in self.additional_patterns:
            if self._matches_pattern(path, pattern):
                return True
                
        # Check .gitignore patterns
        rel_path = os.path.relpath(path, self.root_path)
        for gitignore_dir, patterns in self.gitignore_patterns.items():
            if self._is_under_directory(path, gitignore_dir):
                for pattern in patterns:
                    if self._matches_gitignore_pattern(rel_path, pattern):
                        return True
                        
        return False
        
    def _matches_pattern(self, path, pattern):
        """Check if path matches a glob pattern."""
        # Use fnmatch or pathlib for pattern matching
        
    def _matches_gitignore_pattern(self, rel_path, pattern):
        """Check if path matches a gitignore pattern."""
        # Handle gitignore-specific pattern syntax
        
    def _is_under_directory(self, path, directory):
        """Check if path is under the specified directory."""
        # Path comparison logic
```

### 3. Change Detection Queue

This component will buffer file change events, implement debouncing, and handle duplicates:

```python
class ChangeDetectionQueue:
    def __init__(self, config):
        """Initialize change detection queue."""
        self.config = config
        self.queue = {}  # path -> {timestamp, event_type}
        self.queue_lock = threading.Lock()
        self.default_delay = config.get('scheduler.delay_seconds', 10)
        self.max_delay = config.get('scheduler.max_delay_seconds', 120)
        self.max_queue_size = config.get('scheduler.max_queue_size', 1000)
        self.batch_size = config.get('scheduler.batch_size', 20)
        self.consumer_thread = None
        self.running = False
        self.callbacks = []
        
    def add_event(self, path, event_type, timestamp=None):
        """Add file event to queue with debounce logic."""
        if timestamp is None:
            timestamp = time.time()
            
        with self.queue_lock:
            # Limit queue size
            if len(self.queue) >= self.max_queue_size:
                # Process oldest entries if queue gets too large
                self._process_oldest_entries()
                
            # Update existing entry or add new one
            if path in self.queue:
                # Keep the earlier timestamp but update event type if needed
                self.queue[path]['event_type'] = self._merge_event_types(
                    self.queue[path]['event_type'], 
                    event_type
                )
            else:
                self.queue[path] = {
                    'timestamp': timestamp,
                    'event_type': event_type
                }
    
    def register_callback(self, callback):
        """Register a callback for processed events."""
        self.callbacks.append(callback)
        
    def start(self):
        """Start the consumer thread."""
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consumer_thread_func)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
        
    def stop(self):
        """Stop the consumer thread."""
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=1.0)
            
    def _consumer_thread_func(self):
        """Thread function to process queued events."""
        while self.running:
            ready_events = self._get_ready_events()
            if ready_events:
                # Group events in batches
                batches = [ready_events[i:i+self.batch_size] 
                           for i in range(0, len(ready_events), self.batch_size)]
                           
                # Process each batch
                for batch in batches:
                    for callback in self.callbacks:
                        try:
                            callback(batch)
                        except Exception as e:
                            logger.error(f"Error in event callback: {e}")
            else:
                # Sleep if no events are ready
                time.sleep(0.1)
    
    def _get_ready_events(self):
        """Get events that are ready for processing (debounce time elapsed)."""
        now = time.time()
        ready_events = []
        
        with self.queue_lock:
            paths_to_remove = []
            
            for path, data in self.queue.items():
                time_elapsed = now - data['timestamp']
                
                # Process if debounce time elapsed or maximum delay reached
                if (time_elapsed >= self.default_delay or 
                    time_elapsed >= self.max_delay):
                    ready_events.append({
                        'path': path,
                        'event_type': data['event_type'],
                        'timestamp': data['timestamp']
                    })
                    paths_to_remove.append(path)
                    
            # Remove processed events from queue
            for path in paths_to_remove:
                del self.queue[path]
                
        return ready_events
        
    def _process_oldest_entries(self):
        """Process oldest entries when queue gets too large."""
        # Sort by timestamp and remove oldest entries
        
    def _merge_event_types(self, old_type, new_type):
        """Merge event types - handle cases like create+modify, etc."""
        # Logic to combine event types sensibly
```

### 4. File System Monitor Coordinator

This component will coordinate the different parts of the file monitoring system:

```python
class FileSystemMonitor:
    def __init__(self, config):
        """Initialize file system monitor."""
        self.config = config
        self.exclusion_manager = ExclusionPatternManager(config)
        self.change_queue = ChangeDetectionQueue(config)
        self.file_watcher = FileWatcherFactory.create_file_watcher(config)
        self.watched_directories = set()
        self.running = False
        
    def initialize(self, root_directories):
        """Initialize the monitor with root directories."""
        if isinstance(root_directories, str):
            root_directories = [root_directories]
            
        # Load gitignore patterns
        for root_dir in root_directories:
            self.exclusion_manager.load_gitignore(root_dir)
            
        # Register file watcher callback
        self.file_watcher.register_callback(self._on_file_change)
        
        # Add directories to watch
        for root_dir in root_directories:
            self.add_directory(root_dir)
            
    def add_directory(self, directory):
        """Add directory to watch list."""
        if directory in self.watched_directories:
            return
            
        self.watched_directories.add(directory)
        
        # Recursively add all subdirectories that aren't excluded
        for dirpath, dirnames, filenames in os.walk(directory):
            # Filter out excluded directories to avoid watching them
            dirnames[:] = [d for d in dirnames 
                          if not self.exclusion_manager.should_exclude(os.path.join(dirpath, d))]
                          
            # Add this directory to the watcher
            self.file_watcher.add_directory(dirpath)
    
    def register_change_callback(self, callback):
        """Register a callback for processed file changes."""
        self.change_queue.register_callback(callback)
        
    def start(self):
        """Start the file system monitor."""
        if self.running:
            return
            
        self.running = True
        self.file_watcher.start()
        self.change_queue.start()
        
    def stop(self):
        """Stop the file system monitor."""
        if not self.running:
            return
            
        self.running = False
        self.file_watcher.stop()
        self.change_queue.stop()
        
    def _on_file_change(self, path, event_type):
        """Callback for file changes detected by watcher."""
        # Skip excluded files
        if self.exclusion_manager.should_exclude(path):
            return
            
        # Special handling for .gitignore changes
        if os.path.basename(path) == '.gitignore':
            self._handle_gitignore_change(path)
            
        # Add to change queue
        self.change_queue.add_event(path, event_type)
        
    def _handle_gitignore_change(self, gitignore_path):
        """Handle changes to .gitignore files."""
        # Reload gitignore patterns
        directory = os.path.dirname(gitignore_path)
        self.exclusion_manager.load_gitignore(directory)
        
        # Schedule re-evaluation of exclusions
        # This may require removing watches from newly excluded directories
        # and adding watches to newly included directories
```

## Integration with Background Task Scheduler

The File System Monitor will integrate with the Background Task Scheduler as described in [BACKGROUND_TASK_SCHEDULER.md](../doc/design/BACKGROUND_TASK_SCHEDULER.md):

```python
class FileSystemMonitorService:
    def __init__(self, config, metadata_extraction_service):
        """Initialize file system monitor service."""
        self.config = config
        self.monitor = FileSystemMonitor(config)
        self.metadata_extraction_service = metadata_extraction_service
        
    def initialize(self, root_directories):
        """Initialize the monitoring service."""
        self.monitor.initialize(root_directories)
        self.monitor.register_change_callback(self._on_changes_detected)
        
    def start(self):
        """Start the monitoring service."""
        self.monitor.start()
        
    def stop(self):
        """Stop the monitoring service."""
        self.monitor.stop()
        
    def _on_changes_detected(self, changes):
        """Handle detected file changes."""
        for change in changes:
            self.metadata_extraction_service.schedule_extraction(
                change['path'], 
                change['event_type'],
                change['timestamp']
            )
```

## Error Handling Strategy

Following the "throw on error" principle from the project documentation:

1. All file system operations will include proper error handling
2. Errors will be caught, logged, and re-thrown with clear context
3. Error messages will include both what failed and why it failed
4. Critical errors in the monitoring system will trigger service restart
5. Non-critical errors (like temporary file access issues) will be logged and retried

```python
def _safe_file_operation(func, *args, **kwargs):
    """Execute a file operation with proper error handling."""
    try:
        return func(*args, **kwargs)
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        raise FileAccessError(f"Permission denied: {str(e)}")
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise FileAccessError(f"File not found: {str(e)}")
    except OSError as e:
        logger.error(f"OS error: {e}")
        raise FileSystemError(f"OS error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during file operation: {e}")
        raise FileSystemError(f"Unexpected error: {str(e)}")
```

## Performance Considerations

To meet the <5% CPU and <100MB RAM requirements:

1. **Efficient Event Batching**: Process events in batches to reduce thread overhead
2. **Targeted File Watching**: Only watch directories with relevant file types
3. **Minimal In-Memory State**: Keep minimal state in memory
4. **Debounced Processing**: Group rapid changes to the same file
5. **Resource Monitoring**: Monitor CPU and memory usage, adjust behavior if needed
6. **Optimized Pattern Matching**: Use efficient algorithms for exclusion pattern matching

## Security Considerations

As outlined in SECURITY.md:

1. All file access will respect filesystem permissions
2. No external connections will be established
3. Strict path validation to prevent directory traversal
4. Complete separation between different projects
5. Resource limits to prevent denial of service

## Implementation Order

1. Implement the platform-specific file watchers
2. Create the exclusion pattern manager with .gitignore support
3. Develop the change detection queue with debouncing
4. Build the file system monitor coordinator
5. Integrate with the background task scheduler
6. Add comprehensive error handling and logging
7. Implement performance optimization and monitoring
8. Add security validation and safety checks

## Testing Strategy

1. **Unit Tests**: Test individual components with mock file systems
2. **Integration Tests**: Test the complete monitoring system with real files
3. **Performance Tests**: Verify resource usage meets requirements
4. **Stress Tests**: Test with large number of file changes
5. **Cross-Platform Tests**: Verify correct functioning on all supported platforms

## Platform-Specific Considerations

### Linux

- Utilize inotify with appropriate watch limits
- Handle potential "too many open files" errors
- Consider using inotify-tools or python-inotify libraries

### macOS

- Use FSEvents API for efficient monitoring
- Handle special macOS filesystem behaviors (e.g., .DS_Store files)
- Consider using pyobjc or watchdog libraries

### Windows

- Use ReadDirectoryChangesW through win32file
- Handle long path limitations
- Consider using pywin32 or watchdog libraries
