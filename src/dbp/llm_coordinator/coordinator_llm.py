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
# Implements the CoordinatorLLM class, which acts as the central "brain" of the
# LLM coordination system. It receives a processed request, formulates a prompt
# for a high-level LLM (like Amazon Nova Lite), invokes that LLM, and parses its
# response to determine which specialized internal tools need to be executed
# to fulfill the original request.
###############################################################################
# [Source file design principles]
# - Encapsulates the logic for interacting with the primary coordinator LLM.
# - Uses the LLMPromptManager (or similar logic) to create context-rich prompts.
# - Includes placeholders for actual LLM invocation (via BedrockClient or similar).
# - Parses the LLM's response to identify required tool calls and their parameters.
# - Translates the LLM's plan into a list of executable InternalToolJob objects.
# - Handles errors during LLM interaction or response parsing.
# - Design Decision: Dedicated Coordinator LLM Class (2025-04-15)
#   * Rationale: Separates the high-level reasoning and planning task (done by this LLM) from the execution of specific sub-tasks (done by internal tools).
#   * Alternatives considered: Single LLM for all tasks (less scalable, harder to optimize prompts), Rule-based coordinator (less flexible).
###############################################################################
# [Source file constraints]
# - Depends on `ToolRegistry` to know available tools for the prompt.
# - Depends on `LLMPromptManager` (or equivalent logic) for prompt creation.
# - Depends on `BedrockClient` (or equivalent) for LLM invocation (currently placeholder).
# - Relies heavily on the coordinator LLM's ability to understand the request and correctly identify necessary tool calls based on the provided prompt and tool descriptions.
# - Response parsing logic needs to be robust to variations in the LLM's output format.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
# - scratchpad/dbp_implementation_plan/plan_llm_coordinator.md
# - src/dbp/llm_coordinator/data_models.py
# - src/dbp/llm_coordinator/tool_registry.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:08:30Z : Initial creation of CoordinatorLLM class by CodeAssistant
# * Implemented structure, placeholder LLM invocation, and mock response parsing.
###############################################################################

import logging
import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

# Assuming necessary imports
try:
    from .data_models import CoordinatorRequest, InternalToolJob
    from .tool_registry import ToolRegistry
    # Import config types if defined
    # from ...config import CoordinatorLLMConfig # Example
    CoordinatorLLMConfig = Any # Placeholder
    # Import Bedrock client if used directly, or assume it's handled elsewhere
    # from ..metadata_extraction.bedrock_client import BedrockClient # Example
except ImportError as e:
    logging.getLogger(__name__).error(f"CoordinatorLLM ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    CoordinatorRequest = object
    InternalToolJob = object
    ToolRegistry = object
    CoordinatorLLMConfig = object


logger = logging.getLogger(__name__)

class CoordinatorError(Exception):
    """Custom exception for errors originating from the CoordinatorLLM."""
    pass

class CoordinatorLLM:
    """
    Represents the primary coordinating LLM instance.
    It processes incoming requests, determines the necessary internal tool calls,
    and generates a list of jobs for the JobManager.
    """

    def __init__(self, config: CoordinatorLLMConfig, tool_registry: ToolRegistry, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the CoordinatorLLM.

        Args:
            config: Configuration specific to this coordinator LLM instance.
            tool_registry: The registry containing available internal tools.
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.tool_registry = tool_registry
        self.logger = logger_override or logger
        # Placeholder for the actual LLM client (e.g., BedrockClient)
        self._model_client = self._initialize_model_client()
        self.logger.debug("CoordinatorLLM initialized.")

    def _initialize_model_client(self):
        """Initializes the client used to invoke the LLM model."""
        model_id = self.config.get('model_id', 'amazon.titan-text-lite-v1') # Default model
        self.logger.info(f"Initializing model client for coordinator LLM: {model_id}")
        # Placeholder: In a real implementation, instantiate BedrockClient or similar
        # client = BedrockClient(config=self.config, logger_override=self.logger)
        # return client
        return None # Return None for placeholder

    def process_request(self, request: CoordinatorRequest) -> List[InternalToolJob]:
        """
        Processes a validated request by invoking the coordinator LLM and parsing
        its response to generate a list of internal tool jobs.

        Args:
            request: The validated CoordinatorRequest object.

        Returns:
            A list of InternalToolJob objects to be scheduled.

        Raises:
            CoordinatorError: If prompt creation, LLM invocation, or response parsing fails.
        """
        self.logger.info(f"CoordinatorLLM processing request ID: {request.request_id}")

        try:
            # 1. Create the prompt for the coordinator LLM
            prompt = self._create_prompt(request)

            # 2. Invoke the coordinator LLM model
            llm_response_text = self._invoke_model(prompt)

            # 3. Parse the LLM's response to determine tool calls
            tool_jobs = self._parse_llm_response(llm_response_text, request)

            self.logger.info(f"CoordinatorLLM identified {len(tool_jobs)} jobs for request {request.request_id}.")
            return tool_jobs

        except Exception as e:
            self.logger.error(f"Error during CoordinatorLLM processing for request {request.request_id}: {e}", exc_info=True)
            # Wrap unexpected errors in CoordinatorError
            if not isinstance(e, CoordinatorError):
                 raise CoordinatorError(f"Unexpected error in coordinator processing: {e}") from e
            else:
                 raise e


    def _create_prompt(self, request: CoordinatorRequest) -> str:
        """Creates the detailed prompt for the coordinator LLM."""
        self.logger.debug(f"Creating coordinator prompt for request: {request.request_id}")
        # Load the coordinator prompt template from the configured directory
        template_dir = self.config.get('prompt_templates_dir', 'doc/llm/prompts')
        template_path = os.path.join(template_dir, "coordinator_main_prompt.txt") # Example filename

        try:
            # TODO: Replace with actual template loading logic (similar to LLMPromptManager)
            # For now, using a simplified placeholder template structure.
            prompt_template = """
INSTRUCTIONS:
Analyze the user query and context below. Determine which of the available internal tools are needed to fulfill the request.
Output a JSON list of tool calls, including the 'tool_name' and necessary 'parameters' for each call.
If no tools are needed, output an empty JSON list [].

USER QUERY:
{query}

CONTEXT:
{context}

PARAMETERS PROVIDED:
{parameters}

AVAILABLE INTERNAL TOOLS:
{available_tools}

REQUIRED TOOL CALLS (JSON List):
"""
            # --- End Placeholder Template ---

            # Prepare context and parameters for formatting
            context_str = json.dumps(request.context, indent=2) if request.context else "{}"
            parameters_str = json.dumps(request.parameters, indent=2) if request.parameters else "{}"
            query_str = json.dumps(request.query) if isinstance(request.query, dict) else request.query
            tools_desc = self.tool_registry.get_available_tools_description()

            # Format the prompt
            prompt = prompt_template.format(
                query=query_str,
                context=context_str,
                parameters=parameters_str,
                available_tools=tools_desc
            )
            self.logger.debug(f"Coordinator prompt created (length: {len(prompt)}).")
            return prompt

        except KeyError as e:
             self.logger.error(f"Missing key in coordinator prompt template formatting: {e}")
             raise CoordinatorError(f"Prompt template formatting error: Missing key {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to load or format coordinator prompt template from {template_path}: {e}", exc_info=True)
            raise CoordinatorError(f"Failed to create coordinator prompt: {e}") from e

    def _invoke_model(self, prompt: str) -> str:
        """Invokes the configured coordinator LLM (placeholder)."""
        self.logger.debug(f"Invoking coordinator LLM (Model ID: {self.config.get('model_id', 'N/A')})...")
        if not self._model_client:
            self.logger.warning("Coordinator LLM client not initialized. Using mock response.")
            # --- Mock Response ---
            # Simulate LLM determining which tools to call based on a query
            # This should be replaced by actual LLM call and parsing logic
            mock_tool_calls = [
                 {"tool_name": "coordinator_get_codebase_context", "parameters": {"query_focus": "relevant files"}},
                 {"tool_name": "coordinator_get_documentation_context", "parameters": {"query_focus": "design principles"}}
            ]
            return json.dumps(mock_tool_calls)
            # --- End Mock Response ---

        try:
            # --- Actual Bedrock Invocation (using placeholder client) ---
            # response_text = self._model_client.invoke_model(prompt)
            # return response_text
            # --- End Actual Invocation ---
            raise NotImplementedError("Actual Bedrock client invocation is not implemented yet.")

        except Exception as e:
            self.logger.error(f"Failed to invoke coordinator LLM: {e}", exc_info=True)
            raise CoordinatorError(f"Coordinator LLM invocation failed: {e}") from e

    def _parse_llm_response(self, llm_response_text: str, request: CoordinatorRequest) -> List[InternalToolJob]:
        """Parses the LLM response to extract tool calls and create job objects."""
        self.logger.debug("Parsing coordinator LLM response...")
        try:
            # Expecting a JSON list of tool calls, potentially in markdown
            # TODO: Use ResponseParser logic if response might be in markdown
            tool_calls_data = json.loads(llm_response_text)

            if not isinstance(tool_calls_data, list):
                raise ValueError("LLM response is not a JSON list.")

            jobs: List[InternalToolJob] = []
            for i, call_data in enumerate(tool_calls_data):
                if not isinstance(call_data, dict):
                    self.logger.warning(f"Skipping invalid tool call item (not a dict) at index {i}: {call_data}")
                    continue

                tool_name = call_data.get("tool_name")
                parameters = call_data.get("parameters", {})

                if not tool_name or not isinstance(tool_name, str):
                    self.logger.warning(f"Skipping invalid tool call at index {i}: missing or invalid 'tool_name'. Data: {call_data}")
                    continue
                if not isinstance(parameters, dict):
                     self.logger.warning(f"Invalid 'parameters' for tool '{tool_name}' at index {i} (not a dict). Using empty dict. Data: {call_data}")
                     parameters = {}

                # Check if the tool exists in the registry
                if not self.tool_registry.is_registered(tool_name):
                     self.logger.error(f"Coordinator LLM requested unregistered tool: '{tool_name}'. Skipping job.")
                     continue # Skip jobs for unregistered tools

                # Create the job object
                # Distribute budget/time (simple equal distribution for now)
                num_jobs = len(tool_calls_data) if len(tool_calls_data) > 0 else 1
                job_cost_budget = (request.max_cost_budget / num_jobs) if request.max_cost_budget else None
                job_time_budget = int(request.max_execution_time_ms / num_jobs) if request.max_execution_time_ms else None

                job = InternalToolJob(
                    # job_id generated by default factory
                    parent_request_id=request.request_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    context=request.context or {}, # Pass original request context
                    priority=i + 1, # Simple priority based on order from LLM
                    # creation_timestamp generated by default factory
                    cost_budget=job_cost_budget,
                    max_execution_time_ms=job_time_budget,
                    # status defaults to "Queued"
                )
                jobs.append(job)
                self.logger.debug(f"Created job for tool '{tool_name}' with params: {parameters}")

            return jobs

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse coordinator LLM response as JSON: {e}. Response text: {llm_response_text[:200]}...")
            raise CoordinatorError(f"Invalid JSON response from coordinator LLM: {e}") from e
        except Exception as e:
            self.logger.error(f"Error parsing LLM response or creating jobs: {e}", exc_info=True)
            raise CoordinatorError(f"Failed to process coordinator LLM response: {e}") from e

    def shutdown(self):
        """Placeholder for any shutdown logic needed by the coordinator LLM client."""
        self.logger.info("CoordinatorLLM shutdown.")
        # Add cleanup for the _model_client if necessary
        pass
