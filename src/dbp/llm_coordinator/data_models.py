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
# Defines the core data structures (using dataclasses) for the LLM Coordinator
# component. This includes request/response formats and structures for managing
# internal tool jobs and their results.
###############################################################################
# [Source file design principles]
# - Uses standard Python dataclasses for simple data representation.
# - Defines clear structures for requests, responses, jobs, and results.
# - Includes type hints for clarity and static analysis.
# - Aligns with the data models specified in the LLM Coordinator design documents.
# - Design Decision: Dataclasses for Data Structures (2025-04-15)
#   * Rationale: Lightweight and standard way to define data structures without the overhead or validation complexity of Pydantic for these internal transfer objects.
#   * Alternatives considered: Pydantic (more validation, potentially overkill here), Plain dictionaries (no structure).
###############################################################################
# [Source file constraints]
# - Requires Python 3.7+ for dataclasses.
# - Assumes consistency in usage across the coordinator components.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
# - doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md
# - scratchpad/dbp_implementation_plan/plan_llm_coordinator.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T16:25:27Z : Fixed field order in InternalToolJob dataclass by CodeAssistant
# * Moved required fields 'parent_request_id' and 'tool_name' before optional fields with default values.
# 2025-04-15T16:24:12Z : Fixed field order in CoordinatorRequest dataclass by CodeAssistant
# * Moved required 'query' field before optional fields with default values to fix TypeError.
# 2025-04-15T10:06:00Z : Initial creation of LLM Coordinator data models by CodeAssistant
# * Defined CoordinatorRequest, CoordinatorResponse, InternalToolJob, InternalToolJobResult.
###############################################################################

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import uuid

@dataclass
class CoordinatorRequest:
    """Represents a request submitted to the LLM Coordinator."""
    query: Union[str, Dict[str, Any]] # The main query or instruction
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Optional[Dict[str, Any]] = None # Supporting context data
    parameters: Optional[Dict[str, Any]] = None # Specific parameters for the request/tools
    max_execution_time_ms: Optional[int] = None # Optional override for total time budget
    max_cost_budget: Optional[float] = None # Optional override for total cost budget

@dataclass
class InternalToolJob:
    """Represents a job for a specific internal tool to be executed."""
    parent_request_id: str # Links back to the originating CoordinatorRequest
    tool_name: str # Name of the internal tool to execute
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameters: Dict[str, Any] = field(default_factory=dict) # Parameters specific to this tool
    context: Dict[str, Any] = field(default_factory=dict) # Context relevant to this job
    priority: int = 1 # Job priority (lower value means higher priority)
    creation_timestamp: datetime = field(default_factory=datetime.now)
    cost_budget: Optional[float] = None # Max cost allocated to this specific job
    max_execution_time_ms: Optional[int] = None # Max time allocated to this specific job
    status: str = "Queued" # e.g., Queued, Running, Completed, Failed, Aborted

@dataclass
class InternalToolJobResult:
    """Represents the result of executing an InternalToolJob."""
    job_id: str
    tool_name: str
    status: str # e.g., Completed, Failed, TimedOut, BudgetExceeded
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    result_payload: Optional[Dict[str, Any]] = None # The actual data returned by the tool
    is_partial_result: bool = False # Indicates if the result is incomplete due to limits
    error_details: Optional[Dict[str, Any]] = None # Details if status is Failed
    metadata: Dict[str, Any] = field(default_factory=dict) # e.g., model_used, token_usage

@dataclass
class CoordinatorResponse:
    """Represents the final response from the LLM Coordinator for a request."""
    request_id: str
    status: str # e.g., Success, PartialSuccess, Failed
    results: Dict[str, Any] = field(default_factory=dict) # Consolidated results from tool jobs
    job_summaries: List[Dict[str, Any]] = field(default_factory=list) # Summary of each executed job
    metadata: Dict[str, Any] = field(default_factory=dict) # Overall metadata (total time, cost, models)
    budget_info: Dict[str, Any] = field(default_factory=dict) # Info about budget usage/exceeded status
    error_details: Optional[Dict[str, Any]] = None # Details if the overall request failed
