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
# Implements the JobManager class for the LLM Coordinator. This class handles
# the asynchronous execution and lifecycle management of internal tool jobs.
# It schedules jobs, tracks their status (pending, running, completed, failed),
# waits for their completion, and collects their results.
###############################################################################
# [Source file design principles]
# - Manages a collection of InternalToolJob objects.
# - Uses threading to execute jobs asynchronously (could be adapted for asyncio or other concurrency models).
# - Tracks job states (pending, running, completed).
# - Uses threading.Event for signaling job completion, allowing efficient waiting.
# - Provides methods to schedule jobs and wait for their results.
# - Includes timeout logic for waiting on jobs.
# - Handles errors during job execution and stores results appropriately.
# - Design Decision: Thread-Based Asynchronous Execution (2025-04-15)
#   * Rationale: Simple standard library approach for managing concurrent I/O-bound or potentially CPU-bound LLM tool executions.
#   * Alternatives considered: Asyncio (adds complexity if rest of system isn't async), Process pool (heavier weight).
###############################################################################
# [Source file constraints]
# - Depends on `data_models.py` for job and result structures.
# - Requires an execution engine or function registry to actually run the tools (injected or accessed).
# - Performance depends on the number of concurrent jobs and the efficiency of the underlying tool execution.
# - Error handling within `_execute_job` needs to be robust.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
# - scratchpad/dbp_implementation_plan/plan_llm_coordinator.md
# - src/dbp/llm_coordinator/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:07:50Z : Initial creation of JobManager class by CodeAssistant
# * Implemented job scheduling, status tracking, result collection, and basic execution logic (placeholder).
###############################################################################

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Set

# Assuming data_models and tool_registry are accessible
try:
    from .data_models import InternalToolJob, InternalToolJobResult
    from .tool_registry import ToolRegistry, ToolNotFoundError
    # Import config type if defined
    # from ...config import LLMCoordinatorConfig # Example
    LLMCoordinatorConfig = Any # Placeholder
except ImportError as e:
    logging.getLogger(__name__).error(f"JobManager ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    InternalToolJob = object
    InternalToolJobResult = object
    ToolRegistry = object
    ToolNotFoundError = Exception
    LLMCoordinatorConfig = object

logger = logging.getLogger(__name__)

class JobExecutionError(Exception):
    """Custom exception for errors during job execution."""
    pass

class JobManager:
    """
    Manages the scheduling, execution, and result collection of asynchronous
    internal tool jobs for the LLM Coordinator.
    """

    def __init__(self, config: LLMCoordinatorConfig, tool_registry: ToolRegistry, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the JobManager.

        Args:
            config: The LLMCoordinatorConfig object.
            tool_registry: The registry containing the internal tool functions.
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.tool_registry = tool_registry
        self.logger = logger_override or logger
        self._jobs: Dict[str, InternalToolJob] = {} # job_id -> Job object
        self._results: Dict[str, InternalToolJobResult] = {} # job_id -> Result object
        self._pending_jobs: Set[str] = set() # Job IDs waiting to run
        self._running_jobs: Set[str] = set() # Job IDs currently running
        self._completed_jobs: Set[str] = set() # Job IDs that have finished (success or fail)
        self._job_completion_events: Dict[str, threading.Event] = {} # job_id -> Event
        self._lock = threading.RLock() # Lock for managing job states and results
        self._shutdown_flag = False # Flag to signal shutdown

        # Get config values
        self._job_wait_timeout = float(self.config.get('job_wait_timeout_seconds', 60.0))
        self._max_parallel_jobs = int(self.config.get('max_parallel_jobs', 5))
        # TODO: Implement logic to limit parallel jobs if needed (e.g., using a Semaphore or ThreadPoolExecutor)

        self.logger.debug("JobManager initialized.")

    def schedule_jobs(self, jobs: List[InternalToolJob]) -> List[str]:
        """
        Schedules a list of internal tool jobs for asynchronous execution.

        Args:
            jobs: A list of InternalToolJob objects to schedule.

        Returns:
            A list of the job IDs that were scheduled.
        """
        if self._shutdown_flag:
             self.logger.warning("JobManager is shutting down. Cannot schedule new jobs.")
             return []

        scheduled_ids: List[str] = []
        with self._lock:
            for job in jobs:
                if not isinstance(job, InternalToolJob):
                    self.logger.warning(f"Skipping invalid job object: {type(job)}")
                    continue

                job_id = job.job_id
                if job_id in self._jobs:
                    self.logger.warning(f"Job ID '{job_id}' already exists. Skipping.")
                    continue

                # Store job details
                self._jobs[job_id] = job
                self._pending_jobs.add(job_id)
                self._job_completion_events[job_id] = threading.Event()
                scheduled_ids.append(job_id)

                # Start execution in a new thread
                # Consider using a bounded thread pool executor for better resource management
                # based on self._max_parallel_jobs
                thread = threading.Thread(
                    target=self._execute_job_wrapper,
                    args=(job,),
                    daemon=True, # Allow main thread to exit even if jobs are running (adjust if needed)
                    name=f"Job-{job.tool_name}-{job_id[:8]}"
                )
                thread.start()
                self.logger.info(f"Scheduled job '{job_id}' for tool '{job.tool_name}'.")

        return scheduled_ids

    def wait_for_jobs(self, job_ids: List[str], timeout_override: Optional[float] = None) -> Dict[str, InternalToolJobResult]:
        """
        Waits for a specified list of jobs to complete and returns their results.

        Args:
            job_ids: A list of job IDs to wait for.
            timeout_override: Optional timeout in seconds to wait for each job,
                              overriding the default configured timeout.

        Returns:
            A dictionary mapping job IDs to their corresponding InternalToolJobResult.
            If a job times out or an error occurs, an error result is included.
        """
        results: Dict[str, InternalToolJobResult] = {}
        wait_timeout = timeout_override if timeout_override is not None else self._job_wait_timeout

        self.logger.debug(f"Waiting for {len(job_ids)} jobs with timeout {wait_timeout}s: {job_ids}")

        for job_id in job_ids:
            event = None
            with self._lock: # Get event under lock
                 event = self._job_completion_events.get(job_id)

            if event is None:
                self.logger.error(f"No completion event found for job ID '{job_id}'. Cannot wait.")
                results[job_id] = self._create_error_result(job_id, "Job not found or never scheduled.")
                continue

            # Wait for the event to be set
            try:
                wait_start = time.monotonic()
                if not event.wait(timeout=wait_timeout):
                    # Timeout occurred
                    self.logger.warning(f"Timeout ({wait_timeout}s) waiting for job '{job_id}'.")
                    results[job_id] = self._create_error_result(job_id, f"Job timed out after {wait_timeout}s.", status="TimedOut")
                    # TODO: Consider attempting to cancel the job thread if possible
                    continue
                wait_duration = time.monotonic() - wait_start
                self.logger.debug(f"Job '{job_id}' completed. Wait duration: {wait_duration:.3f}s")

            except Exception as e:
                 self.logger.error(f"Error while waiting for job '{job_id}': {e}", exc_info=True)
                 results[job_id] = self._create_error_result(job_id, f"Error waiting for job: {e}")
                 continue


            # Retrieve the result (should be available now)
            with self._lock:
                result = self._results.get(job_id)
                if result is None:
                    # This indicates an issue if the event was set but no result stored
                    self.logger.error(f"Job '{job_id}' event was set, but no result found in registry.")
                    results[job_id] = self._create_error_result(job_id, "Internal error: Job finished but result missing.")
                else:
                    results[job_id] = result

        return results

    def _execute_job_wrapper(self, job: InternalToolJob):
        """Wrapper to execute a job and handle result/error storage."""
        job_id = job.job_id
        start_timestamp = datetime.now(timezone.utc)
        result_payload = None
        error_details = None
        is_partial = False
        status = "Failed" # Default to Failed

        try:
            # Mark job as running
            with self._lock:
                if job_id not in self._pending_jobs:
                     self.logger.warning(f"Job '{job_id}' was not in pending state before execution attempt.")
                     # Decide how to handle: error out or proceed? Let's proceed cautiously.
                self._pending_jobs.discard(job_id)
                self._running_jobs.add(job_id)
                job.status = "Running" # Update job status

            self.logger.info(f"Executing job '{job_id}' (Tool: {job.tool_name})...")

            # --- Actual Tool Execution ---
            # This part needs the actual execution logic, potentially calling
            # an InternalToolExecutionEngine or directly the tool function.
            # It should handle timeouts and budget constraints internally if possible.
            # For now, using placeholder logic.

            tool_function = self.tool_registry.get_tool(job.tool_name)
            # TODO: Implement actual execution with timeout/budget control
            # result_payload = tool_function(job) # Ideal call
            time.sleep(0.1) # Simulate work
            result_payload = {"mock_result": f"Result from {job.tool_name} for {job_id}"} # Placeholder
            status = "Completed"
            # --- End Placeholder ---

        except ToolNotFoundError as e:
             error_message = f"Tool '{job.tool_name}' not found."
             self.logger.error(f"Job '{job_id}' failed: {error_message}")
             error_details = {"code": "TOOL_NOT_FOUND", "message": error_message}
        except TimeoutError: # Assuming the execution logic raises TimeoutError
             error_message = f"Job '{job_id}' exceeded execution time limit."
             self.logger.warning(error_message)
             error_details = {"code": "TIMEOUT", "message": error_message}
             status = "TimedOut" # Specific status for timeout
             is_partial = True # Result might be partial if timeout occurred mid-execution
        except Exception as e:
            error_message = f"Execution error in job '{job_id}': {e}"
            self.logger.error(error_message, exc_info=True)
            error_details = {"code": "EXECUTION_ERROR", "message": str(e)}
        finally:
            end_timestamp = datetime.now(timezone.utc)
            execution_time_ms = int((end_timestamp - start_timestamp).total_seconds() * 1000)

            # Create the result object
            job_result = InternalToolJobResult(
                job_id=job_id,
                tool_name=job.tool_name,
                status=status,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                execution_time_ms=execution_time_ms,
                result_payload=result_payload if status == "Completed" else None, # Only include payload on success
                is_partial_result=is_partial,
                error_details=error_details,
                metadata={} # TODO: Populate metadata (e.g., token counts) if available
            )

            # Store result and update job state
            with self._lock:
                self._results[job_id] = job_result
                self._running_jobs.discard(job_id)
                self._completed_jobs.add(job_id)
                job.status = status # Update final status on original job object (optional)

            # Signal completion
            event = self._job_completion_events.get(job_id)
            if event:
                event.set()
            else:
                 self.logger.error(f"Completion event missing for job '{job_id}' after execution.")

            self.logger.info(f"Job '{job_id}' finished with status '{status}' in {execution_time_ms}ms.")


    def _create_error_result(self, job_id: str, error_message: str, status: str = "Failed") -> InternalToolJobResult:
        """Helper to create a standardized error result object."""
        return InternalToolJobResult(
            job_id=job_id,
            tool_name=self._jobs.get(job_id, InternalToolJob(parent_request_id='', tool_name='unknown')).tool_name, # Get tool name if possible
            status=status,
            start_timestamp=None, # Indicate it might not have started
            end_timestamp=datetime.now(timezone.utc),
            execution_time_ms=None,
            result_payload=None,
            is_partial_result=False,
            error_details={"code": "JOB_ERROR", "message": error_message},
            metadata={}
        )

    def get_job_status(self, job_id: str) -> Optional[str]:
         """Gets the current status of a job."""
         with self._lock:
              if job_id in self._running_jobs: return "Running"
              if job_id in self._pending_jobs: return "Pending"
              if job_id in self._completed_jobs:
                   result = self._results.get(job_id)
                   return result.status if result else "Completed (Result Missing)"
              return None # Not found

    def shutdown(self):
        """Signals the job manager to stop accepting new jobs (doesn't cancel running jobs)."""
        self.logger.info("JobManager shutdown initiated. No new jobs will be scheduled.")
        self._shutdown_flag = True
        # Note: This doesn't actively stop running threads here.
        # Stopping is typically managed by the component/lifecycle manager
        # which would call stop on the worker pool using this JobManager.
