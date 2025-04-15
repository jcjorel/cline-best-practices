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
# Llm Coordinator package for the Documentation-Based Programming system.
# Coordinates multiple LLM instances for efficient processing of queries.
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
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


# src/dbp/llm_coordinator/__init__.py

"""
LLM Coordination package for the Documentation-Based Programming system.

This package manages the interaction with Large Language Models (LLMs),
orchestrating calls to a primary coordinator LLM and specialized internal
tool LLMs to fulfill complex requests. It handles request validation,
job management, response formatting, and budget/timeout constraints.

Key components:
- LLMCoordinatorComponent: The main component conforming to the core framework.
- CoordinatorRequest/CoordinatorResponse: Data models for requests and responses.
- InternalToolJob/InternalToolJobResult: Data models for internal tool tasks.
- RequestHandler: Validates incoming requests.
- CoordinatorLLM: Interacts with the primary coordinating LLM.
- ToolRegistry: Manages available internal tools.
- JobManager: Handles asynchronous execution of internal tool jobs.
- ResponseFormatter: Consolidates job results into the final response.
"""

# Expose key classes and data models for easier import
from .data_models import (
    CoordinatorRequest,
    CoordinatorResponse,
    InternalToolJob,
    InternalToolJobResult
)
from .request_handler import RequestHandler, RequestValidationError
from .tool_registry import ToolRegistry, ToolNotFoundError
from .job_manager import JobManager, JobExecutionError
from .coordinator_llm import CoordinatorLLM, CoordinatorError
from .response_formatter import ResponseFormatter
from .component import LLMCoordinatorComponent, ComponentNotInitializedError

# Placeholder for InternalToolExecutionEngine if it were implemented here
# from .execution_engine import InternalToolExecutionEngine

__all__ = [
    # Main Component
    "LLMCoordinatorComponent",
    # Data Models
    "CoordinatorRequest",
    "CoordinatorResponse",
    "InternalToolJob",
    "InternalToolJobResult",
    # Core Classes (expose if needed externally, otherwise keep internal)
    "RequestHandler",
    "ToolRegistry",
    "JobManager",
    "CoordinatorLLM",
    "ResponseFormatter",
    # "InternalToolExecutionEngine", # Expose if implemented and needed
    # Exceptions
    "ComponentNotInitializedError",
    "RequestValidationError",
    "ToolNotFoundError",
    "JobExecutionError",
    "CoordinatorError",
]
