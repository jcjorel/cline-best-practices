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
# Implements the worker thread pool mechanism for the Background Task Scheduler.
# Includes the `WorkerThread` class, which processes individual file changes by
# invoking the Metadata Extraction service, and the `WorkerThreadPool` class,
# which manages the lifecycle and coordination of multiple worker threads.
###############################################################################
# [Source file design principles]
# - Uses a fixed-size thread pool (`concurrent.futures.ThreadPoolExecutor` could be an alternative).
# - Each `WorkerThread` runs in a loop, fetching batches of changes from the queue.
# - Delegates actual file processing (metadata extraction) to the injected service.
# - Includes error handling for file reading and metadata extraction failures.
# - Reports processing status (success/failure) to a `StatusReporter`.
# - `WorkerThreadPool` manages starting, stopping, and monitoring worker threads.
# - Design Decision: Custom Thread Pool (2025-04-15)
#   * Rationale: Provides direct control over thread lifecycle and task processing logic compared to standard library executors, allowing for custom status reporting and error handling integration.
#   * Alternatives considered: `concurrent.futures.ThreadPoolExecutor` (less control over individual thread state/reporting).
###############################################################################
# [Source file constraints]
# - Depends on `queue.py` for the `ChangeDetectionQueue`.
# - Depends on the `MetadataExtractionComponent` (or its service) for processing files.
# - Requires a `StatusReporter` instance for reporting outcomes.
# - Thread safety relies on the safety of the queue and injected components.
# - Number of worker threads should be configured carefully based on system resources.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/BACKGROUND_TASK_SCHEDULER.md
# other:- src/dbp/scheduler/queue.py
# other:- src/dbp/metadata_extraction/component.py (Dependency)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:03:00Z : Initial creation of worker classes by CodeAssistant
# * Implemented WorkerThread processing loop and WorkerThreadPool management.
###############################################################################

import logging
import threading
from threading import RLock
import time
import os
import queue # Using standard library queue for worker availability tracking
from typing import Optional, Any, List

# Assuming necessary imports
try:
    from .queue import ChangeDetectionQueue, FileChange, ChangeType
    # Assuming StatusReporter is defined elsewhere (e.g., in status.py or component.py)
    # Define placeholder if not available
    try:
         from .status import StatusReporter # Assuming status.py
    except ImportError:
         class StatusReporter: # Placeholder
              def report_success(self, path: str): pass
              def report_failure(self, path: str, error: str): pass
              def get_stats(self): return {}
    # Import the component providing the extraction service
    from ..metadata_extraction.component import MetadataExtractionComponent, ComponentNotInitializedError
    # Import config type if defined
    # from ..config import SchedulerConfig # Example
    SchedulerConfig = Any
except ImportError as e:
    logging.getLogger(__name__).error(f"Worker ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    ChangeDetectionQueue = object
    FileChange = object
    ChangeType = object
    StatusReporter = object
    MetadataExtractionComponent = object
    ComponentNotInitializedError = Exception
    SchedulerConfig = object


logger = logging.getLogger(__name__)

class WorkerThread(threading.Thread):
    """
    A background thread that continuously fetches file changes from a queue
    and processes them using the Metadata Extraction service.
    """

    def __init__(
        self,
        worker_id: int,
        change_queue: ChangeDetectionQueue,
        metadata_extraction_component: MetadataExtractionComponent,
        status_reporter: StatusReporter,
        config: SchedulerConfig,
        logger_override: Optional[logging.Logger] = None,
    ):
        """
        Initializes the WorkerThread.

        Args:
            worker_id: A unique identifier for this worker thread.
            change_queue: The queue from which to fetch file changes.
            metadata_extraction_component: The component used to process files.
            status_reporter: The reporter to notify about processing outcomes.
            config: Scheduler configuration object.
            logger_override: Optional logger instance.
        """
        thread_name = f"Worker-{worker_id}"
        super().__init__(name=thread_name, daemon=True)
        self.worker_id = worker_id
        self.change_queue = change_queue
        self.metadata_extraction_component = metadata_extraction_component
        self.status_reporter = status_reporter
        self.config = config
        self.logger = (logger_override or logger).getChild(thread_name)
        self._stop_event = threading.Event() # Event to signal thread termination
        self._is_processing = False # Flag to indicate if currently processing a file
        self._current_file = None # Path of the file being processed

    def run(self):
        """The main loop executed by the worker thread."""
        self.logger.info("Worker thread started.")
        while not self._stop_event.is_set():
            try:
                # Wait for changes to become available in the queue
                # Use a timeout to periodically check the stop event
                changes_available = self.change_queue.wait_for_changes(timeout=1.0)

                if self._stop_event.is_set(): # Check stop event after waiting
                    break

                if not changes_available:
                    continue # Timeout, loop again

                # Get a batch of changes to process
                batch_size = int(self.config.batch_size) # Access property directly, will throw if not defined
                changes = self.change_queue.get_next_batch(batch_size)

                if not changes:
                    continue # No changes were ready after all

                self.logger.debug(f"Processing batch of {len(changes)} changes.")
                for change in changes:
                    if self._stop_event.is_set(): # Check stop event before processing each item
                        self.logger.info("Stop signal received during batch processing.")
                        break
                    self._process_change(change)

            except Exception as e:
                # Log unexpected errors in the main loop
                self.logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                # Avoid tight loop on unexpected errors
                time.sleep(5)

        self.logger.info("Worker thread stopped.")

    def stop(self):
        """Signals the worker thread to stop processing."""
        self.logger.debug("Stop signal received.")
        self._stop_event.set()
        # Wake up the thread if it's waiting on the queue event
        # This requires access to the queue's internal event, which isn't ideal.
        # The timeout in wait_for_changes helps ensure timely shutdown.

    def is_processing(self) -> bool:
        """Returns True if the worker is currently processing a file."""
        return self._is_processing

    def get_current_file(self) -> Optional[str]:
         """Returns the path of the file currently being processed."""
         return self._current_file

    def _process_change(self, change: FileChange):
        """Processes a single file change event."""
        path = change.path
        change_type = change.change_type
        self.logger.info(f"Processing {change_type.name} for: {path}")

        self._is_processing = True
        self._current_file = path
        start_time = time.monotonic()

        try:
            # --- Handle DELETED ---
            if change_type == ChangeType.DELETED:
                self.logger.debug(f"Handling deletion for: {path}")
                # TODO: Implement logic to remove metadata from database/cache
                # Example: self.metadata_extraction_component.remove_metadata(path)
                # For now, just report success
                self.status_reporter.report_success(path)
                return # Nothing more to do for deleted files

            # --- Handle CREATED, MODIFIED, RENAMED ---
            # For these types, we need to read the file and extract metadata.
            # Check if file exists first (it might have been deleted quickly after event)
            if not os.path.exists(path):
                self.logger.warning(f"File not found during processing: {path} (change type: {change_type.name})")
                self.status_reporter.report_failure(path, "File not found during processing")
                return

            # Read file content
            try:
                # Consider adding size limits or other checks before reading
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                self.logger.debug(f"Read {len(content)} bytes from: {path}")
            except Exception as e:
                self.logger.error(f"Failed to read file {path}: {e}", exc_info=True)
                self.status_reporter.report_failure(path, f"Failed to read file: {e}")
                return

            # Extract and store metadata using the component's service
            try:
                # Need project_id - how does the worker know this?
                # This needs to be passed down or retrieved based on path.
                # Assuming a placeholder project_id for now.
                # TODO: Resolve how project_id is determined for extraction.
                project_id = 1 # Placeholder

                metadata = self.metadata_extraction_component.extract_and_store_metadata(
                    file_path=path,
                    file_content=content,
                    project_id=project_id # Pass the correct project ID
                )

                if metadata:
                    self.logger.info(f"Successfully processed and stored metadata for: {path}")
                    self.status_reporter.report_success(path)
                else:
                    # Error should have been logged by the service/writer
                    self.logger.warning(f"Metadata extraction/storage returned None for: {path}")
                    # Status reporter might have already been called by service on failure
                    # self.status_reporter.report_failure(path, "Metadata extraction/storage failed")
            except ComponentNotInitializedError:
                 self.logger.error(f"Metadata Extraction component not initialized while processing {path}.")
                 self.status_reporter.report_failure(path, "Metadata Extraction component not ready.")
            except Exception as e:
                self.logger.error(f"Metadata extraction/storage failed unexpectedly for {path}: {e}", exc_info=True)
                self.status_reporter.report_failure(path, f"Extraction/storage error: {e}")

        except Exception as e:
             # Catch-all for unexpected errors during processing logic
             self.logger.error(f"Unexpected error processing change for {path}: {e}", exc_info=True)
             self.status_reporter.report_failure(path, f"Unexpected processing error: {e}")
        finally:
            self._is_processing = False
            self._current_file = None
            duration = time.monotonic() - start_time
            self.logger.debug(f"Finished processing {path} in {duration:.3f} seconds.")


class WorkerThreadPool:
    """Manages a pool of WorkerThreads."""

    def __init__(
        self,
        config: SchedulerConfig,
        logger_override: Optional[logging.Logger] = None,
        metadata_extraction_component: Optional[MetadataExtractionComponent] = None # Pass dependency
    ):
        """
        Initializes the WorkerThreadPool.

        Args:
            config: Scheduler configuration object.
            logger_override: Optional logger instance.
            metadata_extraction_component: The component used for processing.
        """
        self.config = config
        self.logger = logger_override or logger
        if metadata_extraction_component is None:
             # This dependency is crucial
             raise ValueError("MetadataExtractionComponent must be provided to WorkerThreadPool.")
        self.metadata_extraction_component = metadata_extraction_component
        self._workers: List[WorkerThread] = []
        self._lock = RLock()
        self._is_active = False # Indicates if the pool is running

    def start(self, change_queue: ChangeDetectionQueue, status_reporter: StatusReporter):
        """
        Creates and starts the configured number of worker threads.

        Args:
            change_queue: The queue from which workers will fetch tasks.
            status_reporter: The reporter for workers to use.
        """
        with self._lock:
            if self._is_active:
                self.logger.warning("WorkerThreadPool is already active.")
                return

            num_workers = int(self.config.worker_threads)
            self.logger.info(f"Starting WorkerThreadPool with {num_workers} worker threads...")
            self._workers = [] # Clear any previous workers

            for i in range(num_workers):
                worker = WorkerThread(
                    worker_id=i,
                    change_queue=change_queue,
                    metadata_extraction_component=self.metadata_extraction_component,
                    status_reporter=status_reporter,
                    config=self.config,
                    logger_override=self.logger # Pass parent logger
                )
                self._workers.append(worker)
                worker.start()

            self._is_active = True
            self.logger.info("WorkerThreadPool started.")

    def stop(self):
        """Signals all worker threads to stop and waits for them to join."""
        with self._lock:
            if not self._is_active:
                self.logger.warning("WorkerThreadPool is not active.")
                return
            self.logger.info("Stopping WorkerThreadPool...")
            self._is_active = False # Set flag first

            # Signal all workers to stop
            for worker in self._workers:
                worker.stop()

            # Wait for all workers to finish
            self.logger.debug("Waiting for worker threads to join...")
            for worker in self._workers:
                worker.join(timeout=5.0) # Add timeout for joining
                if worker.is_alive():
                     self.logger.warning(f"Worker thread {worker.getName()} did not join cleanly.")

            self._workers = [] # Clear worker list
            self.logger.info("WorkerThreadPool stopped.")

    def get_active_worker_count(self) -> int:
        """Returns the number of currently active (running and processing) worker threads."""
        with self._lock:
            # Count threads that are alive and potentially processing
            return sum(1 for worker in self._workers if worker.is_alive())

    def get_processing_files(self) -> List[str]:
         """Returns a list of file paths currently being processed by workers."""
         with self._lock:
              return [file for worker in self._workers if (file := worker.get_current_file()) is not None]

    @property
    def is_active(self) -> bool:
        """Checks if the thread pool is currently active."""
        return self._is_active
