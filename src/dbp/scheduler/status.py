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
# Implements the StatusReporter class, responsible for tracking and reporting
# the status of background processing tasks managed by the scheduler. It keeps
# counts of successes and failures, tracks recent events, and calculates basic
# performance metrics like uptime and processing rate.
###############################################################################
# [Source file design principles]
# - Provides thread-safe methods for reporting task outcomes (success/failure).
# - Uses `collections.deque` for efficiently storing recent events (successes/failures).
# - Calculates basic statistics on demand (processed count, failed count, uptime, rate).
# - Uses RLock for thread safety when updating internal counters and deques.
# - Design Decision: Centralized Status Tracking (2025-04-15)
#   * Rationale: Consolidates status information in one place, making it easy to query the overall health and progress of the background processing system.
#   * Alternatives considered: Each worker tracking its own status (harder to aggregate), Using external monitoring system (overkill for basic stats).
###############################################################################
# [Source file constraints]
# - The `maxlen` for deques limits the history of recent events.
# - Statistics like processing rate are simple averages over the total uptime.
# - Assumes timestamps are reasonably accurate for uptime calculation.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/BACKGROUND_TASK_SCHEDULER.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:03:35Z : Initial creation of StatusReporter class by CodeAssistant
# * Implemented methods for reporting success/failure and retrieving statistics.
###############################################################################

import logging
import threading
import time
import collections
from typing import Dict, Any, Optional, Deque, Tuple

logger = logging.getLogger(__name__)

class StatusReporter:
    """
    Tracks and reports the status and statistics of background processing tasks.
    This class is designed to be thread-safe.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None, max_history: int = 100):
        """
        Initializes the StatusReporter.

        Args:
            logger_override: Optional logger instance to use.
            max_history: The maximum number of recent success/failure events to store.
        """
        self.logger = logger_override or logger
        self._lock = threading.RLock() # Lock for thread-safe updates

        # Core statistics counters
        self._processed_count: int = 0
        self._failed_count: int = 0
        self._start_time: float = time.monotonic() # Use monotonic clock for uptime

        # History tracking using double-ended queues
        if max_history <= 0:
             logger.warning("max_history must be positive. Defaulting to 100.")
             max_history = 100
        # Store tuples of (file_path, timestamp) for successes
        self._recent_successes: Deque[Tuple[str, float]] = collections.deque(maxlen=max_history)
        # Store tuples of (file_path, timestamp, error_message) for failures
        self._recent_failures: Deque[Tuple[str, float, str]] = collections.deque(maxlen=max_history)

        self.logger.debug(f"StatusReporter initialized (max_history={max_history}).")

    def report_success(self, file_path: str):
        """
        Records the successful processing of a file.

        Args:
            file_path: The path of the file that was processed successfully.
        """
        with self._lock:
            self._processed_count += 1
            timestamp = time.time() # Use wall clock time for history records
            self._recent_successes.append((file_path, timestamp))
            # Log less frequently to avoid noise, maybe only if debug is enabled
            # self.logger.debug(f"Reported success for: {file_path}")

    def report_failure(self, file_path: str, error: str):
        """
        Records the failed processing of a file.

        Args:
            file_path: The path of the file that failed processing.
            error: A string describing the reason for failure.
        """
        with self._lock:
            self._failed_count += 1
            timestamp = time.time()
            error_summary = (error[:100] + '...') if len(error) > 103 else error # Truncate long errors
            self._recent_failures.append((file_path, timestamp, error_summary))
            self.logger.warning(f"Reported failure for: {file_path}. Reason: {error_summary}")

    def get_processed_count(self) -> int:
        """Returns the total number of successfully processed files since startup."""
        with self._lock:
            return self._processed_count

    def get_failed_count(self) -> int:
        """Returns the total number of failed processing attempts since startup."""
        with self._lock:
            return self._failed_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Retrieves a dictionary containing current processing statistics.

        Returns:
            A dictionary with keys like 'processed_count', 'failed_count',
            'uptime_seconds', 'files_per_second', 'recent_failures', 'recent_successes'.
        """
        with self._lock:
            current_time = time.monotonic()
            uptime = current_time - self._start_time
            total_processed = self._processed_count + self._failed_count

            return {
                "processed_count": self._processed_count,
                "failed_count": self._failed_count,
                "total_attempts": total_processed,
                "uptime_seconds": round(uptime, 2),
                "files_per_second": round(self._processed_count / uptime, 2) if uptime > 0 else 0,
                # Return copies of the deques
                "recent_failures": list(self._recent_failures),
                "recent_successes": list(self._recent_successes)
            }

    def reset_stats(self):
        """Resets all statistics counters and history."""
        with self._lock:
            self.logger.info("Resetting status reporter statistics.")
            self._processed_count = 0
            self._failed_count = 0
            self._recent_successes.clear()
            self._recent_failures.clear()
            self._start_time = time.monotonic() # Reset uptime start
