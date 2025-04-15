# LLM Coordinator Implementation Plan

## Overview

This document outlines the implementation plan for the LLM Coordinator component, which is responsible for managing and orchestrating the LLM (Language Learning Model) instances that power the Documentation-Based Programming system's intelligent features.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - MCP Server Implementation section
- [design/LLM_COORDINATION.md](../../doc/design/LLM_COORDINATION.md) - Detailed architecture
- [SECURITY.md](../../doc/SECURITY.md) - Security considerations
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](../../doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - Data models

## Requirements

The LLM Coordinator component must:
1. Manage the hierarchical LLM coordination pattern with a Coordinator LLM and specialized Internal Tool LLMs
2. Handle asynchronous job management for parallel execution of multiple internal tools
3. Provide standardized interfaces for LLM interactions
4. Implement cost budget constraints and timeout management
5. Support various LLM models for different tasks
6. Handle response formation and delivery
7. Provide robust error handling and recovery mechanisms
8. Adhere to security principles defined in SECURITY.md
9. Integrate with the MCP server architecture

## Design

### Architecture Overview

The LLM Coordinator follows a hierarchical architecture with asynchronous job management:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Request Handler    │─────▶│  Coordinator LLM    │─────▶│  Job Manager        │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │                            │
                                       │                            ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Job Queue          │
                               ┌─────────────────────┐    │                     │
                               │                     │    └─────────────────────┘
                               │  Tool Registry      │               │
                               │                     │               ▼
                               └─────────────────────┘    ┌─────────────────────┐
                                       │                  │                     │
                                       │                  │  Internal Tool      │
                                       ▼                  │  Execution Engine   │
                               ┌─────────────────────┐    │                     │
                               │                     │    └─────────────────────┘
                               │  Response Formatter │◀────────────┘
                               │                     │
                               └─────────────────────┘
```

### Core Classes and Interfaces

1. **LLMCoordinatorComponent**

```python
class LLMCoordinatorComponent(Component):
    """Component for coordinating LLM instances."""
    
    @property
    def name(self) -> str:
        return "llm_coordinator"
    
    @property
    def dependencies(self) -> list[str]:
        return ["background_scheduler"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the LLM coordinator component."""
        self.config = context.config.llm_coordinator
        self.logger = context.logger.get_child("llm_coordinator")
        
        # Create coordinator subcomponents
        self.request_handler = RequestHandler(self.config, self.logger)
        self.tool_registry = ToolRegistry(self.config, self.logger)
        self.job_manager = JobManager(self.config, self.logger)
        self.response_formatter = ResponseFormatter(self.logger)
        
        # Create the coordinator LLM
        self.coordinator_llm = CoordinatorLLM(
            config=self.config.coordinator_llm,
            logger=self.logger.get_child("coordinator_llm"),
            tool_registry=self.tool_registry
        )
        
        # Create internal tools execution engine
        self.internal_tool_engine = InternalToolExecutionEngine(
            config=self.config,
            logger=self.logger.get_child("internal_tool_engine"),
            job_manager=self.job_manager
        )
        
        # Register internal tools
        self._register_internal_tools()
        
        self._initialized = True
    
    def _register_internal_tools(self) -> None:
        """Register internal tools with the tool registry."""
        # Register the five internal tools described in the documentation
        self.tool_registry.register_tool(
            "coordinator_get_codebase_context",
            self.internal_tool_engine.execute_codebase_context_tool
        )
        
        self.tool_registry.register_tool(
            "coordinator_get_codebase_changelog_context",
            self.internal_tool_engine.execute_codebase_changelog_tool
        )
        
        self.tool_registry.register_tool(
            "coordinator_get_documentation_context",
            self.internal_tool_engine.execute_documentation_context_tool
        )
        
        self.tool_registry.register_tool(
            "coordinator_get_documentation_changelog_context",
            self.internal_tool_engine.execute_documentation_changelog_tool
        )
        
        self.tool_registry.register_tool(
            "coordinator_get_expert_architect_advice",
            self.internal_tool_engine.execute_expert_architect_advice_tool
        )
    
    def process_request(self, request: CoordinatorRequest) -> CoordinatorResponse:
        """
        Process a request through the LLM coordinator.
        
        Args:
            request: The coordinator request to process
        
        Returns:
            Coordinator response with results
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Processing request {request.request_id}")
        
        try:
            # Hand the request to the request handler
            validated_request = self.request_handler.validate_request(request)
            
            # Process with coordinator LLM to determine required tools
            tool_jobs = self.coordinator_llm.process_request(validated_request)
            
            # Schedule jobs
            job_ids = self.job_manager.schedule_jobs(tool_jobs)
            
            # Wait for all jobs to complete
            job_results = self.job_manager.wait_for_jobs(job_ids)
            
            # Format the response
            response = self.response_formatter.format_response(
                request=validated_request,
                job_results=job_results
            )
            
            self.logger.info(f"Request {request.request_id} processed successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing request {request.request_id}: {e}")
            return self.response_formatter.format_error_response(
                request=request,
                error=str(e)
            )
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down LLM coordinator component")
        if hasattr(self, 'job_manager'):
            self.job_manager.shutdown()
        if hasattr(self, 'coordinator_llm'):
            self.coordinator_llm.shutdown()
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **RequestHandler**

```python
class RequestHandler:
    """Handles and validates incoming coordinator requests."""
    
    def __init__(self, config: LLMCoordinatorConfig, logger: Logger):
        self.config = config
        self.logger = logger
    
    def validate_request(self, request: CoordinatorRequest) -> CoordinatorRequest:
        """
        Validate and possibly enhance an incoming request.
        
        Args:
            request: The request to validate
            
        Returns:
            Validated and possibly enhanced request
        
        Raises:
            ValidationError: If the request is invalid
        """
        # Check required fields
        if not request.request_id:
            raise ValidationError("request_id is required")
        
        if not request.query:
            raise ValidationError("query is required")
        
        # Apply defaults if not specified
        if request.max_execution_time_ms is None:
            request.max_execution_time_ms = self.config.default_max_execution_time_ms
        
        if request.max_cost_budget is None:
            request.max_cost_budget = self.config.default_max_cost_budget
        
        # Enhance context if needed
        if request.context is None:
            request.context = {}
        
        # Add current date/time if not present
        if "current_date_time" not in request.context:
            request.context["current_date_time"] = datetime.now().isoformat()
        
        return request
```

3. **CoordinatorLLM**

```python
class CoordinatorLLM:
    """Coordinator LLM instance that processes requests and determines required tools."""
    
    def __init__(self, config: CoordinatorLLMConfig, logger: Logger, tool_registry: ToolRegistry):
        self.config = config
        self.logger = logger
        self.tool_registry = tool_registry
        self._model = self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the Amazon Nova Lite model."""
        self.logger.info(f"Initializing coordinator LLM with model {self.config.model_id}")
        
        # Model initialization with AWS Bedrock SDK
        # For now, this is a placeholder. The actual implementation will depend on the AWS Bedrock SDK.
        # We will rely on the Job Management component for future implementation.
        return None
    
    def process_request(self, request: CoordinatorRequest) -> List[InternalToolJob]:
        """
        Process a request and determine which internal tools to invoke.
        
        Args:
            request: The request to process
            
        Returns:
            List of internal tool jobs to execute
        """
        self.logger.info(f"Processing request {request.request_id} with coordinator LLM")
        
        # Create a prompt for the coordinator LLM
        prompt = self._create_prompt(request)
        
        # Invoke the model
        response = self._invoke_model(prompt)
        
        # Parse the response to determine required tools
        try:
            tool_jobs = self._parse_response(response, request)
            self.logger.info(f"Identified {len(tool_jobs)} tool jobs for request {request.request_id}")
            return tool_jobs
        except Exception as e:
            self.logger.error(f"Error parsing coordinator LLM response: {e}")
            raise CoordinatorError(f"Failed to parse coordinator LLM response: {e}")
    
    def _create_prompt(self, request: CoordinatorRequest) -> str:
        """Create a prompt for the coordinator LLM."""
        # Load the coordinator prompt template
        prompt_template_path = os.path.join(
            self.config.prompt_templates_dir,
            "coordinator_prompt_template.txt"
        )
        
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except Exception as e:
            self.logger.error(f"Error loading coordinator prompt template: {e}")
            raise CoordinatorError(f"Failed to load coordinator prompt template: {e}")
        
        # Format the template with the request data
        return prompt_template.format(
            request_id=request.request_id,
            query=request.query,
            context=json.dumps(request.context),
            available_tools=self.tool_registry.get_available_tools_description(),
            parameters=json.dumps(request.parameters) if request.parameters else "{}"
        )
    
    def _invoke_model(self, prompt: str) -> str:
        """Invoke the coordinator LLM model with the given prompt."""
        try:
            # This is a placeholder for the actual model invocation
            # In the real implementation, this would use the AWS Bedrock SDK
            # For now, we'll return a mock response
            self.logger.debug(f"Invoking coordinator LLM with prompt: {prompt[:100]}...")
            
            # Mock response - would normally come from the model
            return "Mock response that would determine tools to use"
            
        except Exception as e:
            self.logger.error(f"Error invoking coordinator LLM: {e}")
            raise CoordinatorError(f"Failed to invoke coordinator LLM: {e}")
    
    def _parse_response(self, response: str, request: CoordinatorRequest) -> List[InternalToolJob]:
        """Parse the coordinator LLM response to determine required tools."""
        # This is a placeholder implementation
        # In the real implementation, this would parse the structured output from the LLM
        
        # For now, we'll create a mock job list
        mock_jobs = []
        
        # Add a job for codebase context
        mock_jobs.append(
            InternalToolJob(
                job_id=str(uuid.uuid4()),
                parent_request_id=request.request_id,
                tool_name="coordinator_get_codebase_context",
                parameters={},
                context=request.context,
                priority=1,
                creation_timestamp=datetime.now(),
                cost_budget=request.max_cost_budget * 0.3,  # Allocate 30% of budget
                max_execution_time_ms=request.max_execution_time_ms * 0.3  # Allocate 30% of time
            )
        )
        
        # Add a job for documentation context
        mock_jobs.append(
            InternalToolJob(
                job_id=str(uuid.uuid4()),
                parent_request_id=request.request_id,
                tool_name="coordinator_get_documentation_context",
                parameters={},
                context=request.context,
                priority=2,
                creation_timestamp=datetime.now(),
                cost_budget=request.max_cost_budget * 0.3,  # Allocate 30% of budget
                max_execution_time_ms=request.max_execution_time_ms * 0.3  # Allocate 30% of time
            )
        )
        
        # In a real implementation, we would parse the LLM response to determine the tools
        # and create appropriate job objects
        
        return mock_jobs
    
    def shutdown(self) -> None:
        """Shutdown the coordinator LLM."""
        self.logger.info("Shutting down coordinator LLM")
        # Cleanup resources if needed
```

4. **ToolRegistry**

```python
class ToolRegistry:
    """Registry for internal LLM tools."""
    
    def __init__(self, config: LLMCoordinatorConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._tools = {}  # Dict[str, Callable]
        self._lock = threading.RLock()
    
    def register_tool(self, tool_name: str, tool_function: Callable) -> None:
        """
        Register an internal tool.
        
        Args:
            tool_name: Name of the tool
            tool_function: Function that implements the tool
        """
        with self._lock:
            self.logger.info(f"Registering tool: {tool_name}")
            self._tools[tool_name] = tool_function
    
    def get_tool(self, tool_name: str) -> Callable:
        """
        Get a registered tool function.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            The tool function
            
        Raises:
            ToolNotFoundError: If the tool is not registered
        """
        with self._lock:
            if tool_name not in self._tools:
                raise ToolNotFoundError(f"Tool not found: {tool_name}")
            return self._tools[tool_name]
    
    def list_tools(self) -> List[str]:
        """
        Get a list of registered tool names.
        
        Returns:
            List of tool names
        """
        with self._lock:
            return list(self._tools.keys())
    
    def get_available_tools_description(self) -> str:
        """
        Get a description of all available tools.
        
        Returns:
            Description of available tools
        """
        with self._lock:
            descriptions = []
            for tool_name in self._tools:
                descriptions.append(f"- {tool_name}: Available for use")
            
            return "\n".join(descriptions)
```

5. **JobManager**

```python
class JobManager:
    """Manages internal tool jobs."""
    
    def __init__(self, config: LLMCoordinatorConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._jobs = {}  # Dict[str, InternalToolJob]
        self._results = {}  # Dict[str, InternalToolJobResult]
        self._pending_jobs = set()  # Set[str]
        self._running_jobs = set()  # Set[str]
        self._completed_jobs = set()  # Set[str]
        self._job_completion_events = {}  # Dict[str, Event]
        self._lock = threading.RLock()
    
    def schedule_jobs(self, jobs: List[InternalToolJob]) -> List[str]:
        """
        Schedule internal tool jobs for execution.
        
        Args:
            jobs: List of jobs to schedule
            
        Returns:
            List of job IDs
        """
        job_ids = []
        
        with self._lock:
            for job in jobs:
                job_id = job.job_id
                
                # Store the job
                self._jobs[job_id] = job
                
                # Mark job as pending
                self._pending_jobs.add(job_id)
                
                # Create completion event
                self._job_completion_events[job_id] = threading.Event()
                
                # Schedule execution
                threading.Thread(
                    target=self._execute_job,
                    args=(job,),
                    daemon=True
                ).start()
                
                job_ids.append(job_id)
                
                self.logger.info(f"Scheduled job: {job_id} for tool: {job.tool_name}")
        
        return job_ids
    
    def wait_for_jobs(self, job_ids: List[str]) -> Dict[str, InternalToolJobResult]:
        """
        Wait for jobs to complete.
        
        Args:
            job_ids: List of job IDs to wait for
            
        Returns:
            Dictionary mapping job ID to result
        """
        results = {}
        
        # Wait for each job to complete
        for job_id in job_ids:
            try:
                # Get completion event
                event = self._job_completion_events.get(job_id)
                
                if event is None:
                    self.logger.error(f"Job completion event not found for job: {job_id}")
                    results[job_id] = self._create_error_result(
                        job_id=job_id,
                        error_message="Job completion event not found"
                    )
                    continue
                
                # Wait with timeout
                if not event.wait(self.config.job_wait_timeout_seconds):
                    self.logger.warning(f"Timed out waiting for job: {job_id}")
                    results[job_id] = self._create_error_result(
                        job_id=job_id,
                        error_message="Job timed out"
                    )
                    continue
                
                # Get result
                with self._lock:
                    result = self._results.get(job_id)
                    
                    if result is None:
                        self.logger.error(f"Job result not found for job: {job_id}")
                        results[job_id] = self._create_error_result(
                            job_id=job_id,
                            error_message="Job result not found"
                        )
                        continue
                
                results[job_id] = result
            
            except Exception as e:
                self.logger.error(f"Error waiting for job {job_id}: {e}")
                results[job_id] = self._create_error_result(
                    job_id=job_id,
                    error_message=f"Error waiting for job: {e}"
                )
        
        return results
    
    def _execute_job(self, job: InternalToolJob) -> None:
        """Execute an internal tool job."""
        job_id = job.job_id
        
        try:
            # Mark job as running
            with self._lock:
                self._pending_jobs.remove(job_id)
                self._running_jobs.add(job_id)
            
            self.logger.info(f"Executing job: {job_id} for tool: {job.tool_name}")
            
            # Get tool registry from LLM Coordinator component
            tool_registry = None  # In actual implementation, this would come from the component
            
            # Look up the tool
            tool_function = tool_registry.get_tool(job.tool_name)
            
            # Execute the tool with timing and budget constraints
            start_time = time.time()
            
            # Set up timeout
            timeout_seconds = job.max_execution_time_ms / 1000
            
            result = None
            error_details = None
            is_partial_result = False
            
            try:
                # This is where we would execute the tool with a timeout
                # For now, we'll just mock the result
                result = {"mock_result": f"Result for {job.tool_name}"}
            
            except TimeoutError:
                is_partial_result = True
                error_details = {
                    "code": "TIMEOUT",
                    "message": "Job execution timed out",
                    "reason": "Timeout"
                }
            
            except Exception as e:
                error_details = {
                    "code": "EXECUTION_ERROR",
                    "message": str(e),
                    "reason": "InternalError"
                }
            
            # Calculate execution time
            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)
            
            # Create result
            job_result = InternalToolJobResult(
                job_id=job_id,
                tool_name=job.tool_name,
                status="Failed" if error_details else "Completed",
                start_timestamp=datetime.fromtimestamp(start_time),
                end_timestamp=datetime.fromtimestamp(end_time),
                execution_time_ms=execution_time_ms,
                result_payload=result,
                is_partial_result=is_partial_result,
                error_details=error_details,
                metadata={
                    "model_used": job.tool_name.replace("coordinator_", ""),
                    "token_usage": {
                        "input": 0,  # Placeholder
                        "output": 0,  # Placeholder
                        "total": 0    # Placeholder
                    }
                }
            )
            
            # Store result
            with self._lock:
                self._results[job_id] = job_result
                self._running_jobs.remove(job_id)
                self._completed_jobs.add(job_id)
            
            # Notify completion
            self._job_completion_events[job_id].set()
            
            self.logger.info(f"Job completed: {job_id} for tool: {job.tool_name}")
        
        except Exception as e:
            self.logger.error(f"Error executing job {job_id}: {e}")
            
            with self._lock:
                # Mark job as completed
                if job_id in self._running_jobs:
                    self._running_jobs.remove(job_id)
                if job_id in self._pending_jobs:
                    self._pending_jobs.remove(job_id)
                self._completed_jobs.add(job_id)
                
                # Create error result
                self._results[job_id] = self._create_error_result(
                    job_id=job_id,
                    error_message=str(e)
                )
            
            # Notify completion
            if job_id in self._job_completion_events:
                self._job_completion_events[job_id].set()
    
    def _create_error_result(self, job_id: str, error_message: str) -> InternalToolJobResult:
        """Create an error result for a job."""
        return InternalToolJobResult(
            job_id=job_id,
            tool_name="unknown",
            status="Failed",
            start_timestamp=datetime.now(),
            end_timestamp=datetime.now(),
            execution_time_ms=0,
            result_payload=None,
            is_partial_result=False,
            error_details={
                "code": "EXECUTION_ERROR",
                "message": error_message,
                "reason": "InternalError"
            },
            metadata={}
        )
    
    def shutdown(self) -> None:
        """Shutdown the job manager."""
        self.logger.info("Shutting down job manager")
        # Cleanup resources if needed
```

6. **InternalToolExecutionEngine**

```python
class InternalToolExecutionEngine:
    """Engine for executing internal LLM tools."""
    
    def __init__(self, config: LLMCoordinatorConfig, logger: Logger, job_manager: JobManager):
        self.config = config
        self.logger = logger
        self.job_manager = job_manager
        self._bedrock_clients = {}  # Dict[str, BedrockClient]
    
    def execute_codebase_context_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Execute the codebase context tool."""
        self.logger.info(f"Executing codebase context tool for job: {job.job_id}")
        
        # This is a placeholder implementation
        # In the real implementation, this would:
        # 1. Create a prompt for the tool's LLM instance
        # 2. Invoke the model
        # 3. Process the response
        
        # For now, we'll return a mock result
        return {
            "relevant_files": [
                {
                    "path": "src/main.py",
                    "intent": "Entry point for the application",
                    "reference_docs": ["design/architecture.md"]
                },
                {
                    "path": "src/utils.py",
                    "intent": "Utility functions used throughout the application",
                    "reference_docs": ["design/utilities.md"]
                }
            ],
            "codebase_organization": {
                "structure": "Standard Python package structure",
                "modules": ["core", "utils", "api"]
            }
        }
    
    def execute_codebase_changelog_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Execute the codebase changelog tool."""
        self.logger.info(f"Executing codebase changelog tool for job: {job.job_id}")
        
        # Placeholder implementation
        return {
            "recent_changes": [
                {
                    "timestamp": "2025-04-10T14:30:00Z",
                    "file": "src/api.py",
                    "summary": "Added authentication endpoints"
                },
                {
                    "timestamp": "2025-04-12T09:15:00Z",
                    "file": "src/models.py",
                    "summary": "Updated user model with MFA support"
                }
            ]
        }
    
    def execute_documentation_context_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Execute the documentation context tool."""
        self.logger.info(f"Executing documentation context tool for job: {job.job_id}")
        
        # Placeholder implementation
        return {
            "relevant_docs": [
                {
                    "path": "doc/DESIGN.md",
                    "summary": "Overall system design and architecture"
                },
                {
                    "path": "doc/API.md",
                    "summary": "API documentation and usage examples"
                }
            ],
            "relationships": {
                "DESIGN.md": ["API.md", "SECURITY.md"],
                "API.md": ["CONFIGURATION.md"]
            }
        }
    
    def execute_documentation_changelog_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Execute the documentation changelog tool."""
        self.logger.info(f"Executing documentation changelog tool for job: {job.job_id}")
        
        # Placeholder implementation
        return {
            "recent_doc_changes": [
                {
                    "timestamp": "2025-04-08T16:45:00Z",
                    "file": "doc/API.md",
                    "summary": "Updated API documentation with authentication details"
                },
                {
                    "timestamp": "2025-04-11T10:20:00Z",
                    "file": "doc/SECURITY.md",
                    "summary": "Added MFA security considerations"
                }
            ]
        }
    
    def execute_expert_architect_advice_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Execute the expert architect advice tool."""
        self.logger.info(f"Executing expert architect advice tool for job: {job.job_id}")
        
        # Placeholder implementation
        return {
            "advice": "Based on the codebase analysis, I recommend implementing the feature using the existing authentication framework rather than creating a new one.",
            "rationale": "The current framework already supports the required functionality and has been thoroughly tested.",
            "implementation_approach": [
                "Extend the UserModel class",
                "Add new methods to AuthenticationService",
                "Update API documentation"
            ]
        }
    
    def _get_bedrock_client(self, model_id: str) -> BedrockClient:
        """Get or create a Bedrock client for the specified model."""
        if model_id not in self._bedrock_clients:
            self._bedrock_clients[model_id] = BedrockClient(
                model_id=model_id,
                logger=self.logger.get_child(f"bedrock-{model_id}")
            )
        
        return self._bedrock_clients[model_id]


class BedrockClient:
    """Client for interacting with AWS Bedrock."""
    
    def __init__(self, model_id: str, logger: Logger):
        self.model_id = model_id
        self.logger = logger
        # Initialize AWS Bedrock client
        # This is a placeholder
    
    def invoke_model(self, prompt: str, temperature: float = 0.0, max_tokens: int = 4096) -> str:
        """Invoke the model with the given prompt."""
        self.logger.debug(f"Invoking model {self.model_id} with prompt: {prompt[:100]}...")
        
        # This is a placeholder for the actual model invocation
        # In the real implementation, this would use the AWS Bedrock SDK
        return f"Mock response from {self.model_id}"
```

7. **ResponseFormatter**

```python
class ResponseFormatter:
    """Formats responses from internal tool results."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def format_response(self, request: CoordinatorRequest, job_results: Dict[str, InternalToolJobResult]) -> CoordinatorResponse:
        """
        Format a response from job results.
        
        Args:
            request: Original coordinator request
            job_results: Dictionary mapping job ID to result
            
        Returns:
            Formatted coordinator response
        """
        self.logger.info(f"Formatting response for request: {request.request_id}")
        
        # Determine overall status
        status = "Success"
        for result in job_results.values():
            if result.status == "Failed":
                status = "PartialSuccess"
                break
        
        # Create job summaries
        job_summaries = []
        for job_id, result in job_results.items():
            job_summaries.append({
                "jobId": job_id,
                "toolName": result.tool_name,
                "status": result.status,
                "executionTimeMs": result.execution_time_ms,
                "costIncurred": 0.0,  # Placeholder
                "isPartialResult": result.is_partial_result
            })
        
        # Calculate total execution time and cost
        total_execution_time_ms = sum(result.execution_time_ms for result in job_results.values())
        total_cost_incurred = 0.0  # Placeholder
        
        # Collect models used
        models_used = set()
        for result in job_results.values():
            if "model_used" in result.metadata:
                models_used.add(result.metadata["model_used"])
        
        # Calculate token usage
        total_input_tokens = 0
        total_output_tokens = 0
        for result in job_results.values():
            if "token_usage" in result.metadata:
                total_input_tokens += result.metadata["token_usage"].get("input", 0)
                total_output_tokens += result.metadata["token_usage"].get("output", 0)
        
        # Consolidate results
        consolidated_results = {}
        for result in job_results.values():
            if result.result_payload:
                consolidated_results[result.tool_name] = result.result_payload
        
        # Determine if budgets were exceeded
        cost_budget_exceeded = total_cost_incurred > request.max_cost_budget if request.max_cost_budget is not None else False
        time_budget_exceeded = total_execution_time_ms > request.max_execution_time_ms if request.max_execution_time_ms is not None else False
        
        # Calculate budget utilization percentages
        cost_utilization_percent = (total_cost_incurred / request.max_cost_budget * 100) if request.max_cost_budget is not None and request.max_cost_budget > 0 else 0
        time_utilization_percent = (total_execution_time_ms / request.max_execution_time_ms * 100) if request.max_execution_time_ms is not None and request.max_execution_time_ms > 0 else 0
        
        # Create response
        return CoordinatorResponse(
            request_id=request.request_id,
            status=status,
            results=consolidated_results,
            job_summaries=job_summaries,
            metadata={
                "totalExecutionTimeMs": total_execution_time_ms,
                "totalCostIncurred": total_cost_incurred,
                "modelsUsed": list(models_used),
                "tokenUsage": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens
                }
            },
            budget_info={
                "costBudgetExceeded": cost_budget_exceeded,
                "timeBudgetExceeded": time_budget_exceeded,
                "costUtilizationPercent": cost_utilization_percent,
                "timeUtilizationPercent": time_utilization_percent
            }
        )
    
    def format_error_response(self, request: CoordinatorRequest, error: str) -> CoordinatorResponse:
        """
        Format an error response.
        
        Args:
            request: Original coordinator request
            error: Error message
            
        Returns:
            Error coordinator response
        """
        self.logger.info(f"Formatting error response for request: {request.request_id}")
        
        return CoordinatorResponse(
            request_id=request.request_id,
            status="Failed",
            results={},
            job_summaries=[],
            metadata={
                "totalExecutionTimeMs": 0,
                "totalCostIncurred": 0.0,
                "modelsUsed": [],
                "tokenUsage": {
                    "input": 0,
                    "output": 0,
                    "total": 0
                }
            },
            budget_info={
                "costBudgetExceeded": False,
                "timeBudgetExceeded": False,
                "costUtilizationPercent": 0.0,
                "timeUtilizationPercent": 0.0
            },
            error_details={
                "message": error,
                "failedJobs": []
            }
        )
```

### Data Model Classes

1. **CoordinatorRequest**

```python
@dataclass
class CoordinatorRequest:
    """Request for the LLM coordinator."""
    
    request_id: str
    query: Union[str, Dict]
    context: Optional[Dict] = None
    parameters: Optional[Dict] = None
    max_execution_time_ms: Optional[int] = None
    max_cost_budget: Optional[float] = None
```

2. **CoordinatorResponse**

```python
@dataclass
class CoordinatorResponse:
    """Response from the LLM coordinator."""
    
    request_id: str
    status: str  # Success, PartialSuccess, Failed
    results: Dict
    job_summaries: List[Dict]
    metadata: Dict
    budget_info: Dict
    error_details: Optional[Dict] = None
```

3. **InternalToolJob**

```python
@dataclass
class InternalToolJob:
    """Job for an internal LLM tool."""
    
    job_id: str
    parent_request_id: str
    tool_name: str
    parameters: Dict
    context: Dict
    priority: int
    creation_timestamp: datetime
    cost_budget: float
    max_execution_time_ms: int
    status: str = "Queued"
```

4. **InternalToolJobResult**

```python
@dataclass
class InternalToolJobResult:
    """Result of an internal LLM tool job."""
    
    job_id: str
    tool_name: str
    status: str  # Completed, Failed, Aborted
    start_timestamp: datetime
    end_timestamp: datetime
    execution_time_ms: int
    result_payload: Optional[Dict]
    is_partial_result: bool
    error_details: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)
```

### Configuration Classes

```python
@dataclass
class CoordinatorLLMConfig:
    """Configuration for coordinator LLM."""
    
    model_id: str  # AWS Bedrock model ID for coordinator
    temperature: float  # Temperature parameter for LLM
    max_tokens: int  # Maximum tokens for LLM response
    prompt_templates_dir: str  # Directory containing prompt templates
    response_format: str  # JSON or text
```

@dataclass
class LLMCoordinatorConfig:
    """Configuration for LLM coordinator."""
    
    coordinator_llm: CoordinatorLLMConfig
    default_max_execution_time_ms: int  # Default maximum execution time
    default_max_cost_budget: float  # Default maximum cost budget
    job_wait_timeout_seconds: int  # Timeout for waiting for job completion
    max_parallel_jobs: int  # Maximum number of parallel jobs
```

Default configuration values:

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `coordinator_llm.model_id` | AWS Bedrock model ID | `"amazon.nova-lite-v3"` | Valid model ID |
| `coordinator_llm.temperature` | Temperature parameter | `0.0` | `0.0-1.0` |
| `coordinator_llm.max_tokens` | Maximum tokens | `4096` | `1-8192` |
| `coordinator_llm.prompt_templates_dir` | Prompt templates directory | `"doc/llm/prompts"` | Valid directory path |
| `coordinator_llm.response_format` | Response format | `"json"` | `"json", "text"` |
| `default_max_execution_time_ms` | Default max execution time | `30000` | `1000-300000` |
| `default_max_cost_budget` | Default max cost budget | `1.0` | `0.1-10.0` |
| `job_wait_timeout_seconds` | Job wait timeout | `60` | `10-300` |
| `max_parallel_jobs` | Maximum parallel jobs | `5` | `1-10` |

## Implementation Plan

### Phase 1: Core Structure
1. Implement LLMCoordinatorComponent as a system component
2. Define data model classes (CoordinatorRequest, CoordinatorResponse, etc.)
3. Create configuration classes
4. Implement request handling and validation

### Phase 2: Coordinator LLM Integration
1. Implement CoordinatorLLM for request processing
2. Create prompt template loading and formatting
3. Implement response parsing and job creation
4. Integrate with AWS Bedrock SDK

### Phase 3: Job Management and Tool Execution
1. Implement JobManager for asynchronous job management
2. Create InternalToolExecutionEngine for tool execution
3. Implement ToolRegistry for tool registration
4. Create BedrockClient for model invocation

### Phase 4: Response Formation and Error Handling
1. Implement ResponseFormatter for response formatting
2. Create error handling and reporting
3. Implement budget management and constraints
4. Add timeout handling and partial result support

## Security Considerations

The LLM Coordinator component implements these security measures:
- Secure handling of AWS Bedrock credentials
- Input validation for all requests
- Resource constraints through budgeting
- Timeout management for LLM invocations
- Error isolation through job-based architecture
- Access controls for prompt templates
- No external data transmission
- Thread safety for concurrent operations

## Testing Strategy

### Unit Tests
- Test request validation and enhancement
- Test prompt template loading and formatting
- Test response parsing and job creation
- Test job scheduling and execution
- Test response formatting and error handling

### Integration Tests
- Test coordinator LLM with AWS Bedrock
- Test internal tools with sample data
- Test job management with concurrent jobs
- Test budget constraints and timeout handling

### End-to-End Tests
- Test complete request processing workflow
- Test error handling and recovery
- Test resource management and constraints
- Test security measures

## Dependencies on Other Plans

This plan depends on:
- Background Task Scheduler plan (for dependency)
- Component Initialization plan (for component framework)

## Implementation Timeline

1. Core Structure - 2 days
2. Coordinator LLM Integration - 3 days
3. Job Management and Tool Execution - 3 days
4. Response Formation and Error Handling - 2 days

Total: 10 days

## Future Enhancements

- Adaptive model selection based on request complexity
- Enhanced caching of similar requests
- Improved budget distribution based on historical performance
- Request prioritization based on user feedback
- Enhanced monitoring and observability features
