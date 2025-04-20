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
# Implements the SchedulerController class, which acts as the central control
# unit for the Background Task Scheduler. It manages the lifecycle (start/stop)
# of the worker thread pool and coordinates the overall scheduling process.
###############################################################################
# [Source file design principles]
# - Provides simple `start` and `stop` methods to control the scheduler.
# - Holds references to the core scheduler components (queue, worker pool, reporter).
# - Delegates task execution management to the `WorkerThreadPool`.
# - Maintains a simple running state.
# - Design Decision: Separate Controller Class (2025-04-15)
#   * Rationale: Separates the high-level control logic (start/stop) from the detailed implementation of the queue and workers, improving modularity.
#   * Alternatives considered: Combining control logic into the main component (less separation of concerns).
###############################################################################
# [Source file constraints]
# - Depends on `queue.py`, `worker.py`, and `status.py`.
# - Requires instances of the queue, worker pool, and status reporter to be injected.
# - Assumes the worker pool correctly handles thread management.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/BACKGROUND_TASK_SCHEDULER.md
# - src/dbp/scheduler/queue.py
# - src/dbp/scheduler/worker.py
# - src/dbp/scheduler/status.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:04:00Z : Initial creation of SchedulerController class by CodeAssistant
# * Implemented start, stop, and status check methods.
###############################################################################

import logging
import threading
from typing import Optional, Any

# Assuming necessary imports from sibling modules
try:
    from .queue import ChangeDetectionQueue
    from .worker import WorkerThreadPool
    from .status import StatusReporter
    # Import config type if defined
    # from ..config import SchedulerConfig # Example
    SchedulerConfig = Any
except ImportError as e:
    logging.getLogger(__name__).error(f"SchedulerController ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    ChangeDetectionQueue = object
    WorkerThreadPool = object
    StatusReporter = object
    SchedulerConfig = object

logger = logging.getLogger(__name__)

class SchedulerController:
    """
    Controls the overall operation of the Background Task Scheduler,
    managing the worker pool and coordinating the processing of tasks from the queue.
    """

    def __init__(
        self,
        change_queue: ChangeDetectionQueue,
        worker_pool: WorkerThreadPool,
        status_reporter: StatusReporter,
        config: SchedulerConfig,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initializes the SchedulerController.

        Args:
            change_queue: The queue holding file change events.
            worker_pool: The pool managing worker threads.
            status_reporter: The reporter for tracking task status.
            config: Scheduler configuration object.
            logger_override: Optional logger instance.
        """
        self.change_queue = change_queue
        self.worker_pool = worker_pool
        self.status_reporter = status_reporter
        self.config = config
        self.logger = logger_override or logger
        self._lock = threading.RLock() # Lock for managing running state
        self._is_running = False
        self.logger.debug("SchedulerController initialized.")

    def start(self):
        """
        Starts the scheduler by activating the worker pool.
        The worker pool will then start consuming tasks from the change queue.
        """
        with self._lock:
            if self._is_running:
                self.logger.warning("SchedulerController is already running.")
                return

            self.logger.info("Starting SchedulerController...")
            try:
                # Start the worker pool, passing it the queue and reporter
                self.worker_pool.start(self.change_queue, self.status_reporter)
                self._is_running = True
                self.logger.info("SchedulerController started successfully.")
            except Exception as e:
                 self.logger.error(f"Failed to start WorkerThreadPool: {e}", exc_info=True)
                 self._is_running = False # Ensure state reflects failure
                 # Should we attempt to stop the pool if start failed partially?
                 try:
                      self.worker_pool.stop()
                 except Exception as stop_e:
                      self.logger.error(f"Error stopping worker pool during failed start: {stop_e}")
                 raise RuntimeError("Failed to start the scheduler's worker pool.") from e


    def stop(self):
        """
        Stops the scheduler gracefully by signaling the worker pool to stop
        and waiting for worker threads to complete their current tasks.
        """
        with self._lock:
            if not self._is_running:
                self.logger.warning("SchedulerController is not running.")
                return

            self.logger.info("Stopping SchedulerController...")
            self._is_running = False # Set flag immediately

        # Stop the worker pool (handles joining threads)
        # This should be done outside the main lock if worker threads might need it,
        # but WorkerThreadPool uses its own lock.
        try:
            self.worker_pool.stop()
            self.logger.info("SchedulerController stopped successfully.")
        except Exception as e:
            self.logger.error(f"Error occurred while stopping the worker pool: {e}", exc_info=True)
            # Continue shutdown even if pool stop fails

    @property
    def is_running(self) -> bool:
        """Checks if the scheduler controller considers itself active."""
        # Check both internal flag and worker pool status for robustness
        # return self._is_running and self.worker_pool.is_active
        return self._is_running # Rely on internal flag managed by start/stop
