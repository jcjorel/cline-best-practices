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
# Implements the ResponseFormatter class for the LLM Coordinator. This class is
# responsible for taking the results collected from individual internal tool jobs
# (managed by JobManager) and consolidating them into a final, structured
# CoordinatorResponse object. It calculates overall status, aggregates metadata,
# and formats error details if necessary.
###############################################################################
# [Source file design principles]
# - Consolidates results from multiple asynchronous jobs into a single response.
# - Determines the overall status (Success, PartialSuccess, Failed) based on individual job outcomes.
# - Aggregates metadata like total execution time, cost (placeholder), models used, and token counts.
# - Formats job summaries and error details clearly.
# - Uses the `CoordinatorResponse` data model for the final output structure.
# - Design Decision: Separate Response Formatter (2025-04-15)
#   * Rationale: Isolates the logic for assembling the final response from the job execution and coordination logic, improving clarity and maintainability.
#   * Alternatives considered: Formatting within the CoordinatorLLM or main component (mixes concerns).
###############################################################################
# [Source file constraints]
# - Depends on the `CoordinatorRequest` and `CoordinatorResponse` data models.
# - Relies on `InternalToolJobResult` objects containing accurate status and metadata.
# - Calculation of total cost requires accurate cost information per job result (currently placeholder).
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
# - scratchpad/dbp_implementation_plan/plan_llm_coordinator.md
# - src/dbp/llm_coordinator/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:09:20Z : Initial creation of ResponseFormatter class by CodeAssistant
# * Implemented logic to format successful and error responses from job results.
###############################################################################

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# Assuming data_models defines the necessary structures
try:
    from .data_models import CoordinatorRequest, CoordinatorResponse, InternalToolJobResult
except ImportError:
    logging.getLogger(__name__).error("Failed to import data models for ResponseFormatter.", exc_info=True)
    # Placeholders
    CoordinatorRequest = object
    CoordinatorResponse = object
    InternalToolJobResult = object

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """
    Formats the final CoordinatorResponse based on the results of executed
    internal tool jobs.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ResponseFormatter.

        Args:
            logger_override: Optional logger instance.
        """
        self.logger = logger_override or logger
        self.logger.debug("ResponseFormatter initialized.")

    def format_response(self, request: CoordinatorRequest, job_results: Dict[str, InternalToolJobResult]) -> CoordinatorResponse:
        """
        Formats a successful or partially successful response based on job results.

        Args:
            request: The original CoordinatorRequest.
            job_results: A dictionary mapping job IDs to their InternalToolJobResult objects.

        Returns:
            A populated CoordinatorResponse object.
        """
        self.logger.debug(f"Formatting response for request ID: {request.request_id} with {len(job_results)} job results.")

        consolidated_results: Dict[str, Any] = {}
        job_summaries: List[Dict[str, Any]] = []
        failed_jobs: List[Dict[str, Any]] = []
        all_successful = True
        any_successful = False
        total_execution_time_ms = 0
        total_cost_incurred = 0.0 # Placeholder for cost calculation
        models_used: set[str] = set()
        total_input_tokens = 0
        total_output_tokens = 0
        cost_budget_exceeded = False # Track if any job exceeded budget
        time_budget_exceeded = False # Track if any job exceeded time

        for job_id, result in job_results.items():
            if not isinstance(result, InternalToolJobResult):
                 self.logger.warning(f"Invalid job result type for job ID '{job_id}'. Skipping.")
                 all_successful = False
                 failed_jobs.append({"jobId": job_id, "error": "Invalid result object"})
                 continue

            # Aggregate execution time
            total_execution_time_ms += result.execution_time_ms or 0

            # Aggregate cost (Placeholder)
            # job_cost = result.metadata.get("cost_incurred", 0.0)
            # total_cost_incurred += job_cost
            # if job.cost_budget and job_cost > job.cost_budget:
            #     cost_budget_exceeded = True

            # Aggregate token usage
            token_usage = result.metadata.get("token_usage", {})
            total_input_tokens += token_usage.get("input", 0)
            total_output_tokens += token_usage.get("output", 0)

            # Track models used
            if model := result.metadata.get("model_used"):
                models_used.add(model)

            # Check for time budget exceeded (per job)
            # This assumes the job object is accessible or time limit was passed down
            # if job.max_execution_time_ms and result.execution_time_ms > job.max_execution_time_ms:
            #     time_budget_exceeded = True
            # Simplified check based on status for now
            if result.status == "TimedOut":
                 time_budget_exceeded = True


            # Create job summary
            summary = {
                "jobId": job_id,
                "toolName": result.tool_name,
                "status": result.status,
                "executionTimeMs": result.execution_time_ms,
                "isPartialResult": result.is_partial_result,
                # "costIncurred": job_cost, # Placeholder
                "error": result.error_details.get("message") if result.error_details else None
            }
            job_summaries.append(summary)

            # Consolidate results and track status
            if result.status == "Completed":
                any_successful = True
                # Merge results, potentially handling conflicts if multiple tools return same keys
                if result.result_payload:
                    for key, value in result.result_payload.items():
                        # Simple merge: last tool writing a key wins. Could be more sophisticated.
                        consolidated_results[key] = value
            else:
                all_successful = False
                failed_jobs.append({
                    "jobId": job_id,
                    "toolName": result.tool_name,
                    "status": result.status,
                    "error": result.error_details or {"message": "Unknown error"}
                })

        # Determine overall status
        if all_successful:
            overall_status = "Success"
        elif any_successful:
            overall_status = "PartialSuccess"
        else:
            overall_status = "Failed"

        # Calculate overall budget utilization (if applicable)
        cost_util_percent = 0.0
        time_util_percent = 0.0
        if request.max_cost_budget and request.max_cost_budget > 0:
             cost_util_percent = (total_cost_incurred / request.max_cost_budget) * 100
        if request.max_execution_time_ms and request.max_execution_time_ms > 0:
             time_util_percent = (total_execution_time_ms / request.max_execution_time_ms) * 100

        # Check overall budget limits
        overall_cost_exceeded = request.max_cost_budget is not None and total_cost_incurred > request.max_cost_budget
        overall_time_exceeded = request.max_execution_time_ms is not None and total_execution_time_ms > request.max_execution_time_ms

        response = CoordinatorResponse(
            request_id=request.request_id,
            status=overall_status,
            results=consolidated_results,
            job_summaries=job_summaries,
            metadata={
                "totalExecutionTimeMs": total_execution_time_ms,
                "totalCostIncurred": total_cost_incurred, # Placeholder
                "modelsUsed": sorted(list(models_used)),
                "tokenUsage": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens
                }
            },
            budget_info={
                # Report if *any* job exceeded its budget or if overall budget exceeded
                "costBudgetExceeded": cost_budget_exceeded or overall_cost_exceeded,
                "timeBudgetExceeded": time_budget_exceeded or overall_time_exceeded,
                "costUtilizationPercent": round(cost_util_percent, 2),
                "timeUtilizationPercent": round(time_util_percent, 2)
            },
            error_details={"failedJobs": failed_jobs} if failed_jobs else None
        )

        self.logger.info(f"Formatted response for request {request.request_id} with status: {overall_status}")
        return response

    def format_error_response(self, request: CoordinatorRequest, error_message: str, status: str = "Failed") -> CoordinatorResponse:
        """
        Formats an error response when the coordinator fails before or during job execution.

        Args:
            request: The original CoordinatorRequest (may be None if request parsing failed).
            error_message: The description of the error.
            status: The overall status to set (usually "Failed").

        Returns:
            An error CoordinatorResponse object.
        """
        req_id = getattr(request, 'request_id', 'unknown')
        self.logger.debug(f"Formatting error response for request ID: {req_id}")

        return CoordinatorResponse(
            request_id=req_id,
            status=status,
            results={},
            job_summaries=[],
            metadata={ # Default empty metadata
                "totalExecutionTimeMs": 0,
                "totalCostIncurred": 0.0,
                "modelsUsed": [],
                "tokenUsage": {"input": 0, "output": 0, "total": 0}
            },
            budget_info={ # Default budget info
                "costBudgetExceeded": False,
                "timeBudgetExceeded": False,
                "costUtilizationPercent": 0.0,
                "timeUtilizationPercent": 0.0
            },
            error_details={
                "code": "COORDINATOR_ERROR",
                "message": error_message,
                "failedJobs": [] # No specific jobs failed if error was before execution
            }
        )
