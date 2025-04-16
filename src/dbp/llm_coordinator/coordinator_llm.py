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
# 2025-04-16T13:20:00Z : Refactored to use centralized Bedrock client management by Cline
# * Integrated with the new BedrockClientManager for model access
# * Updated _invoke_model to use the standardized client interface
# * Added proper client lifecycle management in shutdown method
# * Enhanced error handling for model-specific response formats
# 2025-04-16T12:03:00Z : Integrated LLMPromptManager for prompt loading by Cline
# * Added usage of LLMPromptManager for template-based prompts
# * Updated _create_prompt to load from doc/llm/prompts/ directory
# * Enhanced error handling and structured logging
# 2025-04-15T10:08:30Z : Initial creation of CoordinatorLLM class by CodeAssistant
# * Implemented structure, placeholder LLM invocation, and mock response parsing.
###############################################################################

import logging
import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import boto3
from botocore.config import Config

# Import from llm module - throw on error with logging
try:
    from ..llm import (
        LLMPromptManager, 
        PromptLoadError, 
        BedrockClientManager,
        BedrockClientError
    )
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import LLM dependencies: {e}", exc_info=True)
    # Fail fast on missing dependencies
    raise ImportError("Required LLM dependencies could not be imported") from e

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

    def __init__(
        self, 
        config: CoordinatorLLMConfig, 
        tool_registry: ToolRegistry, 
        bedrock_manager: Optional[BedrockClientManager] = None,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initializes the CoordinatorLLM.

        Args:
            config: Configuration specific to this coordinator LLM instance.
            tool_registry: The registry containing available internal tools.
            bedrock_manager: Optional BedrockClientManager instance for model access.
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.tool_registry = tool_registry
        self.logger = logger_override or logger
        
        # Initialize the prompt manager
        self.prompt_manager = LLMPromptManager(config=self.config, logger_override=self.logger.getChild("prompts"))
        
        # Use provided bedrock manager or create a new one
        self.bedrock_manager = bedrock_manager or self._initialize_bedrock_manager()
        
        # Default model name
        self.model_name = self.config.get("model_name", "nova-lite")
        
        # Model client will be retrieved lazily when needed
        self._model_client = None
        
        self.logger.debug({
            "message": "CoordinatorLLM initialized",
            "model_name": self.model_name
        })

    def _initialize_bedrock_manager(self) -> BedrockClientManager:
        """
        Get the singleton Bedrock client manager instance.
        
        Returns:
            BedrockClientManager: The configured manager singleton instance
        """
        # Extract Bedrock-specific configuration
        bedrock_config = self.config.get("bedrock", {})
        region = bedrock_config.get("region") or os.getenv('AWS_REGION', 'us-east-1')
        
        # We'll reuse the coordinator's prompt manager to avoid duplication
        
        self.logger.info({
            "message": "Getting Bedrock client manager instance",
            "region": region,
            "component": "CoordinatorLLM"
        })
        
        try:
            # Get the singleton instance
            manager = BedrockClientManager.get_instance(
                config=self.config,
                default_region=region,
                prompt_manager=self.prompt_manager,
                logger_override=self.logger.getChild("bedrock")
            )
            
            # Mark that we didn't create this manager (so we won't shut it down)
            self._external_bedrock_manager = True
            
            self.logger.info({
                "message": "Bedrock client manager instance retrieved successfully",
                "component": "CoordinatorLLM"
            })
            
            return manager
            
        except Exception as e:
            self.logger.error({
                "message": "Failed to get Bedrock client manager instance",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "component": "CoordinatorLLM"
            })
            raise CoordinatorError(f"Failed to get Bedrock client manager instance: {str(e)}") from e
            
    def _get_model_client(self):
        """
        Get the model client, initializing it if necessary.
        
        Returns:
            The initialized model client
        """
        if self._model_client:
            return self._model_client
            
        try:
            # Get the client from the manager
            self.logger.debug({
                "message": "Getting model client",
                "model_name": self.model_name
            })
            
            client = self.bedrock_manager.get_client(self.model_name)
            self._model_client = client
            
            self.logger.info({
                "message": "Model client retrieved successfully",
                "model_name": self.model_name
            })
            
            return client
            
        except (ValueError, BedrockClientError) as e:
            self.logger.error({
                "message": "Failed to get model client",
                "model_name": self.model_name,
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            raise CoordinatorError(f"Failed to get model client for {self.model_name}: {str(e)}") from e

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
        """
        Creates the detailed prompt for the coordinator LLM.
        
        [Function intent]
        Loads the prompt template for query classification and formats it with
        the request's data to create a comprehensive prompt for the LLM.
        
        [Implementation details]
        - Uses LLMPromptManager to load the template from doc/llm/prompts/
        - Formats the query, context, parameters, and available tools
        - Handles formatting exceptions with appropriate error messages
        
        Args:
            request (CoordinatorRequest): The request to create a prompt for
            
        Returns:
            str: The formatted prompt ready for LLM invocation
            
        Raises:
            CoordinatorError: If prompt loading or formatting fails
        """
        self.logger.debug(f"Creating coordinator prompt for request: {request.request_id}")

        try:
            # Prepare context and parameters for formatting
            context_str = json.dumps(request.context, indent=2) if request.context else "{}"
            parameters_str = json.dumps(request.parameters, indent=2) if request.parameters else "{}"
            query_str = json.dumps(request.query) if isinstance(request.query, dict) else request.query
            tools_desc = self.tool_registry.get_available_tools_description()
            
            # Format the prompt using the prompt manager
            prompt = self.prompt_manager.format_prompt(
                "coordinator_general_query_classifier",
                query=query_str,
                context=context_str,
                parameters=parameters_str,
                available_tools=tools_desc
            )
            
            self.logger.debug({
                "message": "Coordinator prompt created",
                "request_id": request.request_id,
                "prompt_length": len(prompt)
            })
            
            return prompt

        except PromptLoadError as e:
            self.logger.error({
                "message": "Failed to load prompt template",
                "request_id": request.request_id,
                "error_type": "PromptLoadError",
                "error_details": str(e)
            })
            raise CoordinatorError(f"Failed to load coordinator prompt template: {e}") from e
        except KeyError as e:
            self.logger.error({
                "message": "Missing key in prompt template formatting",
                "request_id": request.request_id,
                "error_type": "KeyError",
                "error_details": str(e)
            })
            raise CoordinatorError(f"Prompt template formatting error: Missing key {e}") from e
        except Exception as e:
            self.logger.error({
                "message": "Failed to create coordinator prompt", 
                "request_id": request.request_id,
                "error_type": type(e).__name__,
                "error_details": str(e)
            }, exc_info=True)
            raise CoordinatorError(f"Failed to create coordinator prompt: {e}") from e

    def _invoke_model(self, prompt: str) -> str:
        """
        Invoke the coordinator LLM with a prompt.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            str: The model's response text
            
        Raises:
            CoordinatorError: If LLM invocation fails
        """
        request_id = str(uuid.uuid4())
        
        self.logger.debug({
            "message": "Invoking coordinator LLM",
            "request_id": request_id,
            "model_name": self.model_name,
            "prompt_length": len(prompt)
        })
        
        # Use mock response if model client not available
        use_mock = self.config.get("use_mock_response", False)
        
        if use_mock:
            self.logger.warning({
                "message": "Using mock LLM response (configured via use_mock_response)",
                "request_id": request_id,
                "model_name": self.model_name
            })
            
            # Generate mock response - tool calls for specific tasks
            mock_tool_calls = [
                {"tool_name": "coordinator_get_codebase_context", "parameters": {"query_focus": "relevant files"}},
                {"tool_name": "coordinator_get_documentation_context", "parameters": {"query_focus": "design principles"}}
            ]
            return json.dumps(mock_tool_calls)
        
        try:
            # Get model client from manager (will initialize if needed)
            client = self._get_model_client()
            
            # Set invocation parameters from config or defaults
            temperature = self.config.get("temperature", 0.7)
            max_tokens = self.config.get("max_tokens", 2000)
            top_p = self.config.get("top_p", 0.9)
            
            # Invoke the model
            response = client.invoke_model(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
            
            # Extract the response text based on the model type
            response_text = None
            
            # Handle Nova Lite response format
            if self.model_name == "nova-lite":
                response_text = response.get("output", {}).get("text", "")
            # Add handling for other model response formats as needed
            else:
                # Try some common response formats
                if "text" in response:
                    response_text = response["text"]
                elif "output" in response and "text" in response["output"]:
                    response_text = response["output"]["text"]
                elif isinstance(response, str):
                    response_text = response
                else:
                    # Default to string representation of the full response
                    self.logger.warning({
                        "message": "Unrecognized response format, using raw response",
                        "request_id": request_id,
                        "model_name": self.model_name,
                        "response_type": type(response).__name__
                    })
                    response_text = json.dumps(response)
            
            if not response_text:
                raise CoordinatorError(f"Empty response from model {self.model_name}")
            
            self.logger.info({
                "message": "LLM invocation successful",
                "request_id": request_id,
                "model_name": self.model_name,
                "response_length": len(response_text) if response_text else 0
            })
            
            return response_text
            
        except (ValueError, BedrockClientError) as e:
            self.logger.error({
                "message": "Failed during LLM invocation",
                "request_id": request_id,
                "model_name": self.model_name,
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            raise CoordinatorError(f"LLM invocation failed: {str(e)}") from e
            
        except Exception as e:
            self.logger.error({
                "message": "Unexpected error during LLM invocation",
                "request_id": request_id,
                "model_name": self.model_name,
                "error_type": type(e).__name__,
                "error_details": str(e)
            }, exc_info=True)
            raise CoordinatorError(f"Unexpected error during LLM invocation: {str(e)}") from e

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
        """
        Clean up resources and prepare for shutdown.
        
        This method cleans up any resources held by the CoordinatorLLM,
        ensuring proper shutdown of model clients and related components.
        """
        self.logger.info({
            "message": "Shutting down CoordinatorLLM",
            "model_name": self.model_name
        })
        
        # Release model client reference
        self._model_client = None
        
        # Shutdown the bedrock manager if we created it (not if it was passed in)
        if self.bedrock_manager and not hasattr(self, '_external_bedrock_manager'):
            try:
                self.bedrock_manager.shutdown_all()
                self.logger.debug({
                    "message": "Bedrock client manager shutdown successful"
                })
            except Exception as e:
                self.logger.error({
                    "message": "Error during Bedrock client manager shutdown",
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                })
        
        self.logger.info({
            "message": "CoordinatorLLM shutdown completed"
        })
