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
# Implements the LLMCoordinatorComponent class, the main entry point for the LLM
# coordination subsystem within the DBP application framework. It conforms to the
# Component protocol, initializes all necessary sub-components (request handler,
# coordinator LLM, tool registry, job manager, response formatter), registers
# internal tools, and provides the primary interface (`process_request`) for
# handling coordinated LLM tasks.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Encapsulates the entire LLM coordination logic.
# - Declares dependencies on other components (e.g., background_scheduler, config).
# - Initializes and wires together internal sub-components during the `initialize` phase.
# - Registers the defined internal LLM tools with the `ToolRegistry`.
# - Provides a high-level `process_request` method that orchestrates the flow.
# - Handles component shutdown gracefully.
# - Design Decision: Component Facade for LLM Coordination (2025-04-15)
#   * Rationale: Presents the complex LLM coordination logic as a single, manageable component.
#   * Alternatives considered: Exposing individual coordinator parts (more complex integration).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and other system components.
# - Requires all sub-components (`RequestHandler`, `CoordinatorLLM`, etc.) to be implemented.
# - Assumes configuration for the coordinator is available via InitializationContext.
# - Placeholder logic exists for the `InternalToolExecutionEngine` and actual tool execution.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
# - src/dbp/core/component.py
# - All other files in src/dbp/llm_coordinator/
###############################################################################
# [GenAI tool change history]
# 2025-04-20T01:33:21Z : Completed dependency injection refactoring by CodeAssistant
# * Removed dependencies property
# * Made dependencies parameter required in initialize method
# * Removed conditional logic for backwards compatibility
# 2025-04-20T00:25:54Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter
# * Added dependency validation for config_manager component
# * Enhanced method documentation for dependency injection pattern
# 2025-04-17T23:34:30Z : Updated to use strongly-typed configuration by CodeAssistant
# * Updated initialize() method signature to use InitializationContext
# * Refactored configuration access to use type-safe get_typed_config() method
# * Added support for strongly-typed configuration in sub-components
# * Improved type safety for configuration access
# 2025-04-16T17:33:57Z : Fixed component initialization configuration access by CodeAssistant
# * Modified initialize method to properly access configuration through the config_manager component
# * Updated configuration passing to sub-components
# 2025-04-15T10:10:00Z : Initial creation of LLMCoordinatorComponent by CodeAssistant
# * Implemented Component protocol, initialization of sub-components, tool registration, and process_request method.
###############################################################################

import logging
from typing import List, Optional, Any, Dict

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    # Import config type if defined, else use Any
    # from ..config import AppConfig, LLMCoordinatorConfig # Example
    Config = Any
    LLMCoordinatorConfig = Any # Placeholder
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for LLMCoordinatorComponent.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    Config = Any
    LLMCoordinatorConfig = Any

# Imports for internal coordinator services
try:
    from .data_models import CoordinatorRequest, CoordinatorResponse, InternalToolJob, InternalToolJobResult
    from .request_handler import RequestHandler, RequestValidationError
    from .tool_registry import ToolRegistry, ToolNotFoundError
    from .job_manager import JobManager, JobExecutionError
    from .coordinator_llm import CoordinatorLLM, CoordinatorError
    from .response_formatter import ResponseFormatter
    # Placeholder for the execution engine - needs to be implemented
    # from .execution_engine import InternalToolExecutionEngine
    class InternalToolExecutionEngine: # Placeholder
         def __init__(self, *args, **kwargs): logger.warning("Using Placeholder InternalToolExecutionEngine")
         def execute_codebase_context_tool(self, job): return {"mock": "codebase_context"}
         def execute_codebase_changelog_tool(self, job): return {"mock": "codebase_changelog"}
         def execute_documentation_context_tool(self, job): return {"mock": "doc_context"}
         def execute_documentation_changelog_tool(self, job): return {"mock": "doc_changelog"}
         def execute_expert_architect_advice_tool(self, job): return {"mock": "expert_advice"}

except ImportError as e:
    logging.getLogger(__name__).error(f"LLMCoordinatorComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    CoordinatorRequest = object
    CoordinatorResponse = object
    InternalToolJob = object
    InternalToolJobResult = object
    RequestHandler = object
    RequestValidationError = Exception
    ToolRegistry = object
    ToolNotFoundError = Exception
    JobManager = object
    JobExecutionError = Exception
    CoordinatorLLM = object
    CoordinatorError = Exception
    ResponseFormatter = object
    InternalToolExecutionEngine = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class LLMCoordinatorComponent(Component):
    """
    DBP system component responsible for coordinating LLM interactions,
    managing internal tools, and orchestrating job execution.
    """
    _initialized: bool = False
    _request_handler: Optional[RequestHandler] = None
    _coordinator_llm: Optional[CoordinatorLLM] = None
    _tool_registry: Optional[ToolRegistry] = None
    _job_manager: Optional[JobManager] = None
    _response_formatter: Optional[ResponseFormatter] = None
    _internal_tool_engine: Optional[InternalToolExecutionEngine] = None # Placeholder

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "llm_coordinator"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
        """
        [Function intent]
        Initializes the LLM Coordinator component and its sub-components.
        
        [Implementation details]
        Uses the strongly-typed configuration for component setup.
        Creates internal coordinator parts (request handler, LLM, tool registry, job manager, formatter).
        Registers internal LLM tools with the registry.
        
        [Design principles]
        Explicit initialization with strong typing.
        Dependency injection for improved performance and testability.
        
        Args:
            context: Initialization context with typed configuration and resources
            dependencies: Dictionary of pre-resolved dependencies {name: component_instance}
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get component-specific configuration using strongly-typed config
            typed_config = context.get_typed_config()
            coordinator_config = typed_config.llm_coordinator
            
            self.logger.debug("Using injected dependencies")
            config_manager = self.get_dependency(dependencies, "config_manager")
            default_config = config_manager.get_default_config(self.name)
            
            # Instantiate sub-components with strongly-typed config when possible
            self._request_handler = RequestHandler(
                config=default_config,  # Keep default for now until subcomponent is updated
                logger_override=self.logger.getChild("request_handler")
            )
            self._tool_registry = ToolRegistry(
                config=default_config,  # Keep default for now until subcomponent is updated
                logger_override=self.logger.getChild("tool_registry")
            )
            # JobManager needs the ToolRegistry to potentially execute tools
            self._job_manager = JobManager(
                config=default_config,  # Keep default for now until subcomponent is updated
                tool_registry=self._tool_registry, 
                logger_override=self.logger.getChild("job_manager")
            )
            self._response_formatter = ResponseFormatter(
                logger_override=self.logger.getChild("response_formatter")
            )
            self._coordinator_llm = CoordinatorLLM(
                config=coordinator_config.coordinator_llm,  # Use strongly-typed configuration 
                tool_registry=self._tool_registry,
                logger_override=self.logger.getChild("coordinator_llm")
            )
            # Instantiate the execution engine (placeholder)
            self._internal_tool_engine = InternalToolExecutionEngine(
                 config=default_config,
                 logger=self.logger.getChild("internal_tool_engine"),
                 job_manager=self._job_manager # Pass job manager if engine needs it
            )

            # Register internal tools
            self._register_internal_tools()

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _register_internal_tools(self):
        """Registers the internal tool execution functions with the ToolRegistry."""
        if not self._tool_registry or not self._internal_tool_engine:
             self.logger.error("Cannot register internal tools: ToolRegistry or ExecutionEngine not initialized.")
             return

        self.logger.debug("Registering internal LLM tools...")
        try:
            # Map tool names to their execution methods in the engine
            tool_map = {
                "coordinator_get_codebase_context": self._internal_tool_engine.execute_codebase_context_tool,
                "coordinator_get_codebase_changelog_context": self._internal_tool_engine.execute_codebase_changelog_tool,
                "coordinator_get_documentation_context": self._internal_tool_engine.execute_documentation_context_tool,
                "coordinator_get_documentation_changelog_context": self._internal_tool_engine.execute_documentation_changelog_tool,
                "coordinator_get_expert_architect_advice": self._internal_tool_engine.execute_expert_architect_advice_tool,
            }
            for name, func in tool_map.items():
                self._tool_registry.register_tool(name, func)
            self.logger.info(f"Registered {len(tool_map)} internal tools.")
        except Exception as e:
             self.logger.error(f"Failed to register internal tools: {e}", exc_info=True)
             # This might be a critical failure depending on design
             raise RuntimeError("Failed to register essential internal tools.") from e


    def shutdown(self) -> None:
        """Shuts down the LLM Coordinator component and its sub-components."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        if self._job_manager:
            self._job_manager.shutdown() # Signal job manager to stop accepting new jobs
        if self._coordinator_llm:
             self._coordinator_llm.shutdown() # Allow coordinator LLM client cleanup
        # Reset references
        self._request_handler = None
        self._coordinator_llm = None
        self._tool_registry = None
        self._job_manager = None
        self._response_formatter = None
        self._internal_tool_engine = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # --- Public API Method ---

    def process_request(self, request: CoordinatorRequest) -> CoordinatorResponse:
        """
        Processes a high-level request by coordinating internal LLM tool executions.

        Args:
            request: The CoordinatorRequest object containing the query and context.

        Returns:
            A CoordinatorResponse object with the consolidated results or error details.

        Raises:
            ComponentNotInitializedError: If the component is not initialized.
        """
        if not self.is_initialized or not all([self._request_handler, self._coordinator_llm, self._job_manager, self._response_formatter]):
            raise ComponentNotInitializedError(self.name)

        self.logger.info(f"Processing coordinator request ID: {request.request_id}")
        try:
            # 1. Validate and prepare the request
            validated_request = self._request_handler.validate_and_prepare_request(request)

            # 2. Ask Coordinator LLM to determine required tool jobs
            tool_jobs: List[InternalToolJob] = self._coordinator_llm.process_request(validated_request)

            if not tool_jobs:
                 self.logger.info(f"Coordinator LLM determined no tool jobs needed for request {request.request_id}.")
                 # Return a success response with empty results? Or specific status?
                 return self._response_formatter.format_response(request, {}) # Format empty success

            # 3. Schedule the jobs for execution
            job_ids = self._job_manager.schedule_jobs(tool_jobs)
            if not job_ids:
                 # This might happen if scheduling fails immediately
                 self.logger.error(f"Failed to schedule any jobs for request {request.request_id}.")
                 return self._response_formatter.format_error_response(request, "Failed to schedule internal tool jobs.")

            # 4. Wait for the scheduled jobs to complete
            job_results = self._job_manager.wait_for_jobs(job_ids)

            # 5. Format the final response
            response = self._response_formatter.format_response(validated_request, job_results)

            self.logger.info(f"Successfully processed coordinator request ID: {request.request_id}")
            return response

        except (RequestValidationError, CoordinatorError, JobExecutionError) as e:
             self.logger.error(f"Error processing coordinator request {request.request_id}: {e}", exc_info=True)
             return self._response_formatter.format_error_response(request, str(e))
        except Exception as e:
             self.logger.critical(f"Unexpected critical error processing coordinator request {request.request_id}: {e}", exc_info=True)
             return self._response_formatter.format_error_response(request, f"Unexpected internal error: {e}")
