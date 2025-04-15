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
