ARK # LLM Coordination Architecture Implementation Plan

## Overview

This document details the implementation plan for the LLM Coordination Architecture of the Documentation-Based Programming system. Based on the project documentation, this component orchestrates multiple LLM instances to efficiently process queries and perform specialized tasks through a hierarchical system.

## LLM Coordination Architecture Requirements

From the project documentation, the LLM Coordination Architecture must:

1. Implement a hierarchical LLM coordination pattern with a coordinator LLM and specialized internal tool LLMs
2. Support asynchronous job management with parallel execution of internal tools
3. Provide cost budgeting for responsible resource utilization
4. Implement timeout management for execution constraints
5. Use standardized prompt templates from the `doc/llm/prompts/` directory
6. Support multiple LLM models (Amazon Nova Lite and Claude 3.x models)
7. Integrate with AWS Bedrock for model interactions
8. Ensure security through isolated execution contexts and input/output validation

## Implementation Components

### 1. Coordinator LLM

The Coordinator LLM manages incoming requests and orchestrates internal tools:

```python
class CoordinatorLLM:
    def __init__(self, config):
        """Initialize coordinator with configuration."""
        self.config = config
        self.prompt_template_path = os.path.join(
            "doc", "llm", "prompts", "coordinator_main.md"
        )
        self.prompt_template = self._load_prompt_template()
        self.aws_bedrock_client = None
        
    def _load_prompt_template(self):
        """Load prompt template from file."""
        # Read template file
        # Validate template content
        # Return template
        
    def initialize(self):
        """Initialize AWS Bedrock client and verify access."""
        # Set up AWS Bedrock client
        # Verify model availability
        # Set up error handling
        
    def process_request(self, request):
        """Process incoming request using LLM coordination."""
        # Create coordinator context
        # Determine required internal tools
        # Create and queue jobs
        # Collect results
        # Format response
        
    def _create_prompt(self, context, query, parameters):
        """Create prompt for LLM based on template."""
        # Fill template with context, query, and parameters
        # Format prompt according to model requirements
        
    def _invoke_model(self, prompt, model="amazon.nova-lite"):
        """Invoke AWS Bedrock model with prompt."""
        # Set up request parameters
        # Invoke model
        # Process response
        # Handle errors
        
    def _handle_timeout(self, job_id, max_time):
        """Handle timeout for a job."""
        # Set up timeout mechanism
        # Gracefully terminate on timeout
        # Return partial results
```

### 2. Job Management System

The Job Management System handles asynchronous execution of internal tools:

```python
class JobManager:
    def __init__(self, db_session):
        """Initialize job manager with database session."""
        self.db_session = db_session
        self.active_jobs = {}
        self.lock = threading.Lock()
        
    def create_job(self, parent_request_id, tool_name, parameters, context):
        """Create a new job with unique ID."""
        # Generate UUID
        # Create job record in database
        # Set initial status
        # Return job ID
        
    def queue_job(self, job_id, priority=0):
        """Queue a job for execution."""
        # Add job to queue with priority
        # Update job status
        
    def start_job(self, job_id):
        """Start execution of a job."""
        # Update job status
        # Record start timestamp
        # Return job parameters
        
    def complete_job(self, job_id, result, cost=None):
        """Mark job as completed with result."""
        # Update job status
        # Record completion timestamp
        # Store result
        # Update cost information
        
    def fail_job(self, job_id, error, reason=None):
        """Mark job as failed with error details."""
        # Update job status
        # Record error information
        # Update metadata
        
    def abort_job(self, job_id, reason):
        """Abort a job before completion."""
        # Update job status
        # Record abort reason
        # Clean up resources
        
    def get_job_status(self, job_id):
        """Get current job status and metadata."""
        # Query job record
        # Return status and metadata
        
    def get_jobs_for_request(self, request_id):
        """Get all jobs for a request."""
        # Query jobs by parent request ID
        # Return job information
```

### 3. Internal Tool Manager

The Internal Tool Manager creates and manages internal LLM tools:

```python
class InternalToolManager:
    def __init__(self, config, job_manager):
        """Initialize tool manager with configuration."""
        self.config = config
        self.job_manager = job_manager
        self.tools = {}
        self.prompt_templates = {}
        
    def initialize(self):
        """Initialize internal tools."""
        # Load all prompt templates
        # Register all tools
        # Verify tool availability
        
    def register_tool(self, name, model_type, handler_function):
        """Register an internal tool."""
        # Store tool information
        # Load associated prompt template
        # Validate handler function
        
    def execute_tool(self, job_id, tool_name, parameters, context):
        """Execute an internal tool asynchronously."""
        # Get tool information
        # Create execution context
        # Run in thread pool
        # Return execution promise
        
    def _load_prompt_templates(self):
        """Load all prompt templates from doc/llm/prompts/ directory."""
        # List prompt template files
        # Load each template
        # Validate template format
        # Store templates by tool name
```

### 4. Internal Tool Implementations

Each internal tool will be implemented as a separate class:

```python
class CodebaseContextTool:
    def __init__(self, config, prompt_template):
        """Initialize tool with configuration."""
        self.config = config
        self.prompt_template = prompt_template
        self.aws_bedrock_client = None
        
    def initialize(self):
        """Initialize AWS Bedrock client."""
        # Set up AWS Bedrock client
        # Verify model availability
        
    def execute(self, job_id, parameters, context, max_cost=None, max_time=None):
        """Execute the tool with parameters and context."""
        # Prepare tool-specific context
        # Create prompt from template
        # Invoke LLM model
        # Process and validate response
        # Return results
        
    def _prepare_context(self, parameters, context):
        """Prepare context specific to this tool."""
        # Extract file headers
        # Compute metadata statistics
        # Filter relevant files based on query
        # Format context for LLM
```

Similar classes will be implemented for each internal tool:
- DocumentationContextTool
- CodebaseChangelogContextTool
- DocumentationChangelogContextTool
- ExpertArchitectAdviceTool

### 5. Read Files Tool

The Read Files Tool will be available to all LLM instances:

```python
class ReadFilesTool:
    def __init__(self, base_path):
        """Initialize tool with base path."""
        self.base_path = base_path
        
    def execute(self, file_paths):
        """Read specified files and return content."""
        # Validate file paths
        # Read file content
        # Return file metadata and content
        
    def _validate_path(self, file_path):
        """Validate file path is safe and within allowed boundaries."""
        # Check for path traversal
        # Verify file is in allowed directories
        # Return validated path
```

### 6. Budget and Resource Manager

The Budget and Resource Manager controls resource utilization:

```python
class BudgetManager:
    def __init__(self):
        """Initialize budget manager."""
        self.cost_tracking = {}
        
    def create_budget(self, job_id, max_cost=None, max_time=None):
        """Create a budget for a job."""
        # Initialize cost tracking
        # Set budget limits
        # Start time tracking
        
    def update_usage(self, job_id, input_tokens, output_tokens, model_type):
        """Update cost usage for a job."""
        # Calculate cost based on token usage and model pricing
        # Update tracking information
        # Check if budget exceeded
        
    def is_budget_exceeded(self, job_id):
        """Check if job has exceeded its budget."""
        # Compare current usage to budget
        # Return exceeded status
        
    def get_usage_info(self, job_id):
        """Get current usage information for a job."""
        # Return token counts, cost, and time usage
        
    def get_total_cost(self, request_id):
        """Get total cost for all jobs in a request."""
        # Aggregate costs across all jobs
        # Return total usage statistics
```

### 7. Response Formatter

The Response Formatter prepares final responses:

```python
class ResponseFormatter:
    def __init__(self):
        """Initialize response formatter."""
        pass
        
    def format_response(self, request, jobs, total_execution_time, total_cost):
        """Format final response from job results."""
        # Collect results from all jobs
        # Aggregate metadata
        # Create consistent response format
        # Include budget utilization information
        
    def format_partial_result(self, request, completed_jobs, pending_jobs, reason):
        """Format partial results when not all jobs completed."""
        # Collect results from completed jobs
        # Include reason for partial results
        # Format consistent response
        
    def format_error_response(self, request, error, failed_jobs=None):
        """Format error response."""
        # Create error response structure
        # Include detailed error information
        # Add failed job information if available
```

## Implementation Process

### 1. Core Framework Implementation

1. Define the CoordinatorLLM class
2. Implement prompt template loading
3. Create AWS Bedrock client initialization
4. Implement basic request processing
5. Add error handling for core operations

### 2. Job Management Implementation

1. Define the JobManager class
2. Implement job creation and queuing
3. Create job status tracking
4. Add job completion and error handling
5. Implement job querying functionality

### 3. Internal Tool Manager Implementation

1. Define the InternalToolManager class
2. Implement prompt template loading
3. Create tool registration and verification
4. Add asynchronous execution functionality
5. Implement tool execution error handling

### 4. Individual Tool Implementation

For each internal tool:
1. Define the tool class
2. Implement context preparation
3. Create prompt generation
4. Add LLM invocation
5. Implement response processing and validation

### 5. Read Files Tool Implementation

1. Define the ReadFilesTool class
2. Implement path validation
3. Create file reading functionality
4. Add error handling for file operations
5. Implement response formatting

### 6. Budget Management Implementation

1. Define the BudgetManager class
2. Implement cost calculation for different models
3. Create usage tracking
4. Add budget checking functionality
5. Implement usage reporting

### 7. Response Formatting Implementation

1. Define the ResponseFormatter class
2. Implement result aggregation
3. Create consistent response formats
4. Add partial result handling
5. Implement error response formatting

## Integration Points

The LLM Coordination Architecture integrates with several other system components:

1. **Database Layer**: Job and result persistence
2. **MCP Server**: Exposing tools to clients
3. **Metadata Extraction**: Accessing code and documentation metadata
4. **Configuration Manager**: Loading configuration settings
5. **File System**: Reading prompt templates and project files

## Error Handling Strategy

Following the project's "throw on error" principle:

1. All LLM operations will include comprehensive error handling
2. Errors will be caught, logged with context, and propagated
3. Error messages will clearly indicate what failed and why
4. Budget and timeout exceptions will return partial results with appropriate indicators

## Performance Considerations

To meet performance requirements:

1. Implement parallel execution of internal tools
2. Use asynchronous processing where applicable
3. Optimize prompt templates for efficiency
4. Implement efficient token usage through prompt design
5. Cache results where appropriate
6. Implement connection pooling for AWS Bedrock clients
7. Use resource limits to prevent overloading

## Thread Safety and Concurrency

1. Implement thread-safe job management
2. Use proper locking for shared resources
3. Design for concurrent tool execution
4. Handle asynchronous result collection
5. Ensure thread safety in budget tracking

## Testing Strategy

1. **Unit Tests**: Test each component with mock LLM responses
2. **Integration Tests**: Test coordinator with mock tool implementations
3. **Budget Tests**: Verify budget enforcement mechanisms
4. **Timeout Tests**: Verify timeout handling
5. **Error Handling Tests**: Test various error scenarios
6. **Concurrency Tests**: Verify behavior under concurrent requests

## Security Considerations

As outlined in SECURITY.md:

1. Implement isolated execution contexts
2. Validate all inputs passed between LLM instances
3. Apply rate limits to prevent resource exhaustion
4. Validate responses before passing to coordinator
5. Implement audit logging of inter-LLM communications
6. Enforce resource quotas for each LLM instance
7. Implement error compartmentalization
8. Ensure secure credential management for AWS Bedrock

## AWS Integration

The system will integrate with AWS Bedrock:

1. **Authentication**: Secure management of AWS credentials
2. **Model Selection**: Using appropriate models for different tasks
3. **Error Handling**: Managing AWS-specific errors and retry logic
4. **Cost Management**: Tracking token usage and costs
5. **Exception Handling**: Managing service limits and throttling

## Implementation Milestones

1. **Milestone 1**: Basic coordinator LLM implementation
   - Prompt template loading
   - AWS Bedrock client integration
   - Basic request processing

2. **Milestone 2**: Job management system
   - Job creation and tracking
   - Asynchronous execution
   - Status reporting

3. **Milestone 3**: Internal tools framework
   - Tool registration
   - Tool execution
   - Prompt template integration

4. **Milestone 4**: Individual tool implementations
   - All internal tools
   - Read Files tool
   - Context preparation logic

5. **Milestone 5**: Budget management
   - Cost tracking
   - Usage limits
   - Partial result handling

6. **Milestone 6**: Integration and testing
   - End-to-end testing
   - Performance optimization
   - Security validation
