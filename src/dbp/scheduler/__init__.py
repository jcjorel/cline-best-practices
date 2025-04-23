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
# Scheduler package for the Documentation-Based Programming system.
# Implements background task scheduling and management.
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T20:13:29Z : Updated class name from BackgroundTaskSchedulerComponent to SchedulerComponent by CodeAssistant
# * Updated all references to reflect the class name change in component.py
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


# src/dbp/scheduler/__init__.py

"""
Background Task Scheduler package for the Documentation-Based Programming system.

Manages a queue of file change events, debounces them, and uses a worker thread
pool to process the changes (e.g., trigger metadata extraction) in the background.

Key components:
- SchedulerComponent: The main component conforming to the core framework.
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
from .component import SchedulerComponent, ComponentNotInitializedError

__all__ = [
    "SchedulerComponent",
    "ChangeDetectionQueue",
    "FileChange",
    "ChangeType",
    "WorkerThreadPool", # Expose pool if external control is needed? Maybe not.
    "StatusReporter",
    "SchedulerController", # Expose controller if external start/stop needed? Maybe not.
    "ComponentNotInitializedError",
]
