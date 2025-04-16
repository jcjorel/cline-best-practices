###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the BackgroundTaskSchedulerComponent class, conforming to the core
# Component protocol. This component encapsulates the background task scheduling
# subsystem, including the change queue, worker pool, status reporter, and controller.
# It manages the lifecycle of the scheduler and provides an interface for status checks.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Declares dependencies ('fs_monitor', 'metadata_extraction').
# - Initializes internal scheduler parts (queue, pool, reporter, controller) during `initialize`.
# - Starts the scheduler controller based on configuration.
# - Provides methods to get status, force processing, and clear the queue.
# - Handles graceful shutdown via the controller.
# - Design Decision: Component Facade for Scheduler (2025-04-15)
#   * Rationale: Presents the scheduler subsystem as a single component within the framework.
#   * Alternatives considered: Exposing controller/queue directly (less standard).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and other system components like
#   'fs_monitor' and 'metadata_extraction'.
# - Assumes configuration for the scheduler is available via InitializationContext.
# - Integration with fs_monitor for receiving change events needs refinement (current fs_monitor pushes to its own queue, doesn't support listeners as planned here).
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/BACKGROUND_TASK_SCHEDULER.md
# - scratchpad/dbp_implementation_plan/plan_background_scheduler.md
# - src/dbp/core/component.py
# - All other files in src/dbp/scheduler/
# - src/dbp/fs_monitor/__init__.py (Dependency)
# - src/dbp/metadata_extraction/component.py (Dependency)
###############################################################################
# [GenAI tool change history]
# 2025-04-16T18:38:53Z : Changed component name from "background_scheduler" to "scheduler" by CodeAssistant
# * Updated name property to return "scheduler" to match the system's expected name
# 2025-04-16T18:33:41Z : Renamed component class from BackgroundTaskSchedulerComponent to SchedulerComponent by CodeAssistant
# * Updated class name to match the expected name in the component system
# * Updated all related error messages to use the new name
# 2025-04-15T10:04:25Z : Initial creation of BackgroundTaskSchedulerComponent by CodeAssistant
# * Implemented Component protocol methods, initialization of internal parts, and control methods.
###############################################################################

import logging
import time
from typing import List, Optional, Any, Dict

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    # Import config type if defined, else use Any
    # from ..config import AppConfig, SchedulerConfig # Example
    Config = Any
    SchedulerConfig = Any # Placeholder for specific config model if available
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for SchedulerComponent.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    Config = Any
    SchedulerConfig = Any

# Imports for internal scheduler services
try:
    from .queue import ChangeDetectionQueue, FileChange, ChangeType
    from .worker import WorkerThreadPool
    from .status import StatusReporter
    from .controller import SchedulerController
    # Import dependencies for type hints
    from ..fs_monitor import FileSystemMonitor # Assuming base class or factory import
    from ..metadata_extraction.component import MetadataExtractionComponent
except ImportError as e:
    logging.getLogger(__name__).error(f"SchedulerComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    ChangeDetectionQueue = object
    FileChange = object
    ChangeType = object
    WorkerThreadPool = object
    StatusReporter = object
    SchedulerController = object
    FileSystemMonitor = object
    MetadataExtractionComponent = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class SchedulerComponent(Component):
    """
    DBP system component responsible for scheduling and executing background tasks,
    primarily metadata extraction based on file system changes.
    """
    _initialized: bool = False
    _controller: Optional[SchedulerController] = None
    _change_queue: Optional[ChangeDetectionQueue] = None # Hold reference if needed externally
    _status_reporter: Optional[StatusReporter] = None # Hold reference

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "scheduler"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Needs fs_monitor to get changes and metadata_extraction to process them.
        # Also implicitly depends on config.
        return ["fs_monitor", "metadata_extraction"]

    def initialize(self, context: InitializationContext):
        """
        Initializes the background task scheduler component, setting up the
        queue, worker pool, status reporter, and controller.

        Args:
            context: The initialization context.
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger # Use logger from context
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get scheduler-specific configuration
            # Using context.config.get assumes config manager provides dict-like access
            scheduler_config = context.config.get(self.name, {}) # Get config specific to this component

            # Get dependent components from the registry via context
            fs_monitor_component = context.get_component("fs_monitor")
            metadata_extraction_component = context.get_component("metadata_extraction")

            # --- Instantiate scheduler parts ---
            # NOTE: The plan suggests creating a new queue here and registering a listener.
            # However, fs_monitor already has its own queue. Reconciling this:
            # Option A (Follow Plan): Create new queue, modify fs_monitor to support listeners (requires fs_monitor change).
            # Option B (Adapt): Use the queue *from* fs_monitor. This requires fs_monitor to expose its queue.
            # Option C (Current): Implement as planned, but note the integration issue.
            self._change_queue = ChangeDetectionQueue(config=scheduler_config, logger_override=self.logger.getChild("queue"))
            self._status_reporter = StatusReporter(logger_override=self.logger.getChild("status"))
            worker_pool = WorkerThreadPool(
                config=scheduler_config,
                logger_override=self.logger.getChild("worker_pool"),
                metadata_extraction_component=metadata_extraction_component # Pass dependency
            )
            self._controller = SchedulerController(
                change_queue=self._change_queue,
                worker_pool=worker_pool,
                status_reporter=self._status_reporter,
                config=scheduler_config,
                logger_override=self.logger.getChild("controller")
            )

            # --- Connect to File System Monitor ---
            # Register ourselves as a listener for file change events
            if fs_monitor_component and hasattr(fs_monitor_component, 'register_change_listener'):
                success = fs_monitor_component.register_change_listener(self._on_file_change)
                if success:
                    self.logger.info("Successfully registered change listener with File System Monitor.")
                else:
                    self.logger.warning("Failed to register change listener with File System Monitor.")
            else:
                self.logger.warning("FileSystemMonitor component does not support register_change_listener or is not available.")


            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized.")

            # Start the controller automatically if enabled in config
            if scheduler_config.get('enabled', True):
                 self.start()
            else:
                 self.logger.info("Scheduler is disabled in configuration. Not starting automatically.")


        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def start(self):
        """Starts the background task scheduler controller and worker pool."""
        if not self.is_initialized or self._controller is None:
            raise ComponentNotInitializedError(self.name)
        self.logger.info("Starting background task scheduler via component...")
        self._controller.start()

    def stop(self):
        """Stops the background task scheduler controller and worker pool."""
        if not self.is_initialized or self._controller is None:
            # Log warning but don't raise error if called before init or after shutdown
            self.logger.warning(f"Attempted to stop scheduler component '{self.name}' but it's not initialized or controller is missing.")
            return
        self.logger.info("Stopping background task scheduler via component...")
        self._controller.stop()

    def shutdown(self) -> None:
        """Performs graceful shutdown of the scheduler component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        if self._controller and self._controller.is_running:
            self.stop()
        self._controller = None
        self._change_queue = None
        self._status_reporter = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # --- Public API Methods ---

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieves the current status and statistics of the scheduler.

        Returns:
            A dictionary containing status information (e.g., running state, queue size, worker count, stats).
        """
        if not self.is_initialized or self._controller is None or self._change_queue is None or self._status_reporter is None:
            # Return default/empty status if not initialized
            return {"running": False, "queue_size": 0, "pending_size": 0, "active_workers": 0, "stats": {}}

        # Combine status from controller and reporter
        status = {
            "running": self._controller.is_running,
            "queue_size": self._change_queue.get_pending_count() if hasattr(self._change_queue, 'get_pending_count') else 0,
            "pending_size": self._change_queue.get_pending_count() if hasattr(self._change_queue, 'get_pending_count') else 0,
            "active_workers": self._controller.worker_pool.get_active_worker_count(),
            "processing_files": self._controller.worker_pool.get_processing_files(),
            "stats": self._status_reporter.get_stats()
        }
        return status

    def force_process_file(self, file_path: str):
        """
        Adds a file path directly to the processing queue, bypassing debouncing.
        Useful for manually triggering processing.

        Args:
            file_path: The absolute path of the file to process.
        """
        if not self.is_initialized or self._change_queue is None:
            raise ComponentNotInitializedError(self.name)
        self.logger.info(f"Forcing processing for file: {file_path}")
        # Create a dummy FileChange event (type MODIFIED is usually safe)
        change_event = FileChange(
            path=file_path,
            change_type=ChangeType.MODIFIED, # Or maybe a specific 'FORCED' type?
            timestamp=time.time()
        )
        # Use the internal method to bypass debounce timer
        self._change_queue._add_change_to_queue(change_event)

    def clear_queue(self):
        """Clears all pending and queued file changes."""
        if not self.is_initialized or self._change_queue is None:
            raise ComponentNotInitializedError(self.name)
        self.logger.info("Clearing scheduler change queue...")
        self._change_queue.clear()

    def _on_file_change(self, change: FileChange):
        """
        Callback method intended to receive file change events from the FileSystemMonitor.
        NOTE: This integration point needs refinement based on fs_monitor capabilities.

        Args:
            change: The FileChange event from the monitor.
        """
        if not self.is_initialized or self._change_queue is None:
            self.logger.warning("Received file change event but scheduler component is not ready.")
            return
        self.logger.debug(f"Received file change via listener: {change.path} ({change.change_type.name})")
        self._change_queue.add_change(change)
