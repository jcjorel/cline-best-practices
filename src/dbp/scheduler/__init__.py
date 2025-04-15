# src/dbp/scheduler/__init__.py

"""
Background Task Scheduler package for the Documentation-Based Programming system.

Manages a queue of file change events, debounces them, and uses a worker thread
pool to process the changes (e.g., trigger metadata extraction) in the background.

Key components:
- BackgroundTaskSchedulerComponent: The main component conforming to the core framework.
- ChangeDetectionQueue: Manages debounced file change events.
- WorkerThreadPool: Manages worker threads for processing changes.
- StatusReporter: Tracks the status and statistics of processing tasks.
- SchedulerController: Controls the start/stop lifecycle of the scheduler.
"""

# Expose key classes for easier import from the package level
from .queue import ChangeDetectionQueue, FileChange, ChangeType
from .worker import WorkerThreadPool # WorkerThread is internal detail
from .status import StatusReporter
from .controller import SchedulerController
from .component import BackgroundTaskSchedulerComponent, ComponentNotInitializedError

__all__ = [
    "BackgroundTaskSchedulerComponent",
    "ChangeDetectionQueue",
    "FileChange",
    "ChangeType",
    "WorkerThreadPool", # Expose pool if external control is needed? Maybe not.
    "StatusReporter",
    "SchedulerController", # Expose controller if external start/stop needed? Maybe not.
    "ComponentNotInitializedError",
]
