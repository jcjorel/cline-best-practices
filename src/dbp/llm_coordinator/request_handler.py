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
# Implements the RequestHandler class for the LLM Coordinator. This class is
# responsible for validating incoming CoordinatorRequest objects, ensuring they
# contain required fields, applying default values for optional parameters like
# timeouts and budgets, and potentially enriching the request context.
###############################################################################
# [Source file design principles]
# - Provides a dedicated class for request validation and preprocessing.
# - Ensures requests conform to the expected structure before being processed by the coordinator LLM.
# - Applies default configuration values consistently.
# - Uses standard Python validation techniques and error handling.
# - Design Decision: Separate Request Handler (2025-04-15)
#   * Rationale: Isolates request validation logic from the core coordination and LLM interaction logic, improving modularity and testability.
#   * Alternatives considered: Validating within the CoordinatorLLM or main component (mixes concerns).
###############################################################################
# [Source file constraints]
# - Depends on the `CoordinatorRequest` data model from `data_models.py`.
# - Requires access to the LLM Coordinator configuration for default values.
# - Validation logic should be kept in sync with the `CoordinatorRequest` definition.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
# - scratchpad/dbp_implementation_plan/plan_llm_coordinator.md
# - src/dbp/llm_coordinator/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:06:50Z : Initial creation of RequestHandler class by CodeAssistant
# * Implemented request validation and default value application logic.
###############################################################################

import logging
from typing import Optional, Any, Dict
from datetime import datetime, timezone

# Assuming data_models.py defines CoordinatorRequest
try:
    from .data_models import CoordinatorRequest
    # Import config type if defined
    # from ...config import LLMCoordinatorConfig # Example
    LLMCoordinatorConfig = Any # Placeholder
except ImportError:
    logging.getLogger(__name__).error("Failed to import dependencies for RequestHandler.", exc_info=True)
    # Placeholders
    CoordinatorRequest = object
    LLMCoordinatorConfig = object

logger = logging.getLogger(__name__)

class RequestValidationError(ValueError):
    """Custom exception for request validation errors."""
    pass

class RequestHandler:
    """
    Handles incoming CoordinatorRequests, performing validation and applying defaults.
    """

    def __init__(self, config: LLMCoordinatorConfig, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the RequestHandler.

        Args:
            config: The LLMCoordinatorConfig object containing default values.
            logger_override: Optional logger instance.
        """
        self.config = config or {} # Use empty dict if config is None
        self.logger = logger_override or logger
        self.logger.debug("RequestHandler initialized.")

    def validate_and_prepare_request(self, request: CoordinatorRequest) -> CoordinatorRequest:
        """
        Validates the incoming request and applies default values where needed.

        Args:
            request: The CoordinatorRequest object to validate.

        Returns:
            The validated (and potentially modified) CoordinatorRequest object.

        Raises:
            RequestValidationError: If the request fails validation checks.
        """
        self.logger.debug(f"Validating request ID: {request.request_id}")

        if not isinstance(request, CoordinatorRequest):
            msg = "Invalid request object type provided."
            self.logger.error(msg)
            raise RequestValidationError(msg)

        # 1. Check required fields
        if not request.request_id:
            raise RequestValidationError("request_id is missing or empty.")
        if not request.query: # Check if query is present and not empty/None
            raise RequestValidationError("query field is missing or empty.")

        # 2. Apply default values from configuration if not set in the request
        # Use get() on config assuming it's dict-like or has appropriate accessors
        if request.max_execution_time_ms is None:
            default_time = self.config.get('default_max_execution_time_ms', 30000) # Default 30s
            request.max_execution_time_ms = int(default_time)
            self.logger.debug(f"Applied default max_execution_time_ms: {request.max_execution_time_ms}")

        if request.max_cost_budget is None:
            default_budget = self.config.get('default_max_cost_budget', 1.0) # Default $1.0
            request.max_cost_budget = float(default_budget)
            self.logger.debug(f"Applied default max_cost_budget: {request.max_cost_budget}")

        # 3. Ensure context and parameters are dictionaries if None
        if request.context is None:
            request.context = {}
        if request.parameters is None:
            request.parameters = {}

        # 4. Enrich context (optional)
        # Example: Add current timestamp if not already present
        if "request_timestamp_utc" not in request.context:
            request.context["request_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            self.logger.debug("Added request_timestamp_utc to request context.")

        # Add more validation rules as needed (e.g., check budget/time limits against configured maximums)

        self.logger.debug(f"Request validation successful for ID: {request.request_id}")
        return request
