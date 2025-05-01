# Hierarchical Semantic Tree Context: llm_coordinator

## Directory Purpose
This directory implements the LLM Coordination subsystem for the DBP system, which orchestrates interactions between Large Language Models and internal tools. It serves as a central hub for processing natural language requests, determining required tool operations, executing tool jobs, and formatting responses. The LLMCoordinatorComponent follows the core Component protocol and acts as a facade for the complex coordination logic, exposing a simplified interface while managing internal sub-components for request handling, tool registry, job management, LLM interactions, and response formatting.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports the LLM Coordinator component and its main classes for use within the DBP system.
  
source_file_design_principles: |
  - Provides clean imports for component and key classes
  - Maintains hierarchical package structure
  - Prevents circular imports
  
source_file_constraints: |
  - Should only export necessary classes and functions
  - Must not contain implementation logic
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-15T09:00:00Z"
    summary: "Initial creation of llm_coordinator package"
    details: "Created __init__.py with exports for key coordinator classes"
```

### `component.py`
```yaml
source_file_intent: |
  Implements the LLMCoordinatorComponent class, the main entry point for the LLM
  coordination subsystem within the DBP application framework. It conforms to the
  Component protocol, initializes all necessary sub-components (request handler,
  coordinator LLM, tool registry, job manager, response formatter), registers
  internal tools, and provides the primary interface (`process_request`) for
  handling coordinated LLM tasks.
  
source_file_design_principles: |
  - Conforms to the Component protocol (`src/dbp/core/component.py`).
  - Encapsulates the entire LLM coordination logic.
  - Declares dependencies on other components (e.g., background_scheduler, config).
  - Initializes and wires together internal sub-components during the `initialize` phase.
  - Registers the defined internal LLM tools with the `ToolRegistry`.
  - Registers a singleton of GeneralQueryMCPTool instance to the mcp_server component.
  - Uses internal MCP tools that must not be exposed to the mcp_server component.
  - Internal MCP tools are for the sole usage of LLM coordinator and other internal components.
  - Only the GeneralQueryMCPTool is exposed to the MCP API via the http server as "dbp_general_query".
  - Provides a high-level `process_request` method that orchestrates the flow.
  - Handles component shutdown gracefully.
  - Design Decision: Component Facade for LLM Coordination (2025-04-15)
    * Rationale: Presents the complex LLM coordination logic as a single, manageable component.
    * Alternatives considered: Exposing individual coordinator parts (more complex integration).
  
source_file_constraints: |
  - Depends on the core component framework and other system components.
  - Requires all sub-components (`RequestHandler`, `CoordinatorLLM`, etc.) to be implemented.
  - Assumes configuration for the coordinator is available via InitializationContext.
  - Placeholder logic exists for the `InternalToolExecutionEngine` and actual tool execution.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  - kind: system
    dependency: src/dbp/core/component.py
  - kind: system
    dependency: src/dbp/config/component.py
  - kind: system
    dependency: src/dbp/mcp_server/component.py
  - kind: other
    dependency: src/dbp/llm_coordinator/data_models.py
  - kind: other
    dependency: src/dbp/llm_coordinator/request_handler.py
  - kind: other
    dependency: src/dbp/llm_coordinator/tool_registry.py
  - kind: other
    dependency: src/dbp/llm_coordinator/job_manager.py
  - kind: other
    dependency: src/dbp/llm_coordinator/coordinator_llm.py
  - kind: other
    dependency: src/dbp/llm_coordinator/response_formatter.py
  - kind: other
    dependency: src/dbp/llm_coordinator/general_query_tool.py
  
change_history:
  - timestamp: "2025-04-26T01:49:00Z"
    summary: "Fixed MCP tool registration method name"
    details: "Changed register_tool to register_mcp_tool to align with server interface, updated tool registration to correctly pass tool name as a separate argument"
  - timestamp: "2025-04-20T01:33:21Z"
    summary: "Completed dependency injection refactoring"
    details: "Removed dependencies property, made dependencies parameter required in initialize method, removed conditional logic for backwards compatibility"
  - timestamp: "2025-04-20T00:25:54Z"
    summary: "Added dependency injection support"
    details: "Updated initialize() method to accept dependencies parameter, added dependency validation for config_manager component, enhanced method documentation for dependency injection pattern"
```

### `coordinator_llm.py`
```yaml
source_file_intent: |
  Implements the CoordinatorLLM class responsible for processing natural language
  requests, determining required tool operations, and generating tool jobs.
  
source_file_design_principles: |
  - Uses a large language model to analyze requests and determine required tools
  - Implements robust error handling and retries for LLM operations
  - Provides flexible prompt construction and parsing
  - Supports multiple LLM providers through common interface
  
source_file_constraints: |
  - Must handle different LLM provider APIs
  - Requires properly formatted prompts for effective tool selection
  - Must validate and parse LLM responses correctly
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock_manager.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/tool_registry.py
  
change_history:
  - timestamp: "2025-04-15T10:00:00Z"
    summary: "Initial implementation of CoordinatorLLM"
    details: "Created CoordinatorLLM class with request processing and tool job generation"
```

### `data_models.py`
```yaml
source_file_intent: |
  Defines data models used throughout the LLM coordinator component for
  representing requests, responses, jobs, and their results.
  
source_file_design_principles: |
  - Type-safe data representation using strongly-typed models
  - Clear separation between different data types
  - Consistent validation and serialization
  
source_file_constraints: |
  - Must support serialization for storage and transport
  - Must provide proper validation of input data
  - Must maintain backwards compatibility for existing clients
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-15T09:30:00Z"
    summary: "Initial implementation of coordinator data models"
    details: "Created data models for coordinator requests, responses, jobs, and results"
```

### `general_query_tool.py`
```yaml
source_file_intent: |
  Implements the GeneralQueryMCPTool class that exposes the LLM coordinator's
  capabilities as an MCP tool for natural language query processing.
  
source_file_design_principles: |
  - Follows MCP tool interface requirements
  - Bridges between MCP server API and internal coordinator logic
  - Provides user-friendly error messages and progress reporting
  - Handles authentication and authorization
  
source_file_constraints: |
  - Must implement MCPTool interface
  - Must adhere to MCP schema conventions
  - Requires JobManager access for query execution
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/mcp_tool.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/job_manager.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  
change_history:
  - timestamp: "2025-04-15T14:00:00Z"
    summary: "Initial implementation of GeneralQueryMCPTool"
    details: "Created MCP tool interface for general natural language queries"
```

### `job_manager.py`
```yaml
source_file_intent: |
  Implements the JobManager class for scheduling, executing, and tracking
  internal tool jobs within the LLM coordinator.
  
source_file_design_principles: |
  - Supports concurrent job execution
  - Provides job tracking and result storage
  - Handles job prioritization and resource allocation
  - Implements timeout and cancellation mechanisms
  
source_file_constraints: |
  - Must handle concurrent job execution safely
  - Must provide proper error handling for job failures
  - Must track job progress and results
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/tool_registry.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  
change_history:
  - timestamp: "2025-04-15T12:00:00Z"
    summary: "Initial implementation of JobManager"
    details: "Created job scheduling, execution, and tracking mechanisms"
```

### `request_handler.py`
```yaml
source_file_intent: |
  Implements the RequestHandler class for validating and preparing
  natural language requests for the LLM coordinator.
  
source_file_design_principles: |
  - Input validation and sanitization
  - Request normalization and enrichment
  - Consistent error handling for invalid requests
  
source_file_constraints: |
  - Must validate all input parameters
  - Must handle different request formats
  - Must provide clear error messages for validation failures
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  
change_history:
  - timestamp: "2025-04-15T10:30:00Z"
    summary: "Initial implementation of RequestHandler"
    details: "Created request validation and preparation functionality"
```

### `response_formatter.py`
```yaml
source_file_intent: |
  Implements the ResponseFormatter class for formatting LLM coordinator
  responses, combining job results, and handling error cases.
  
source_file_design_principles: |
  - Consistent response formatting
  - Combining multiple job results
  - Clear error message presentation
  - Response validation
  
source_file_constraints: |
  - Must handle different response formats
  - Must combine results from multiple jobs
  - Must provide consistent error formatting
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  
change_history:
  - timestamp: "2025-04-15T13:00:00Z"
    summary: "Initial implementation of ResponseFormatter"
    details: "Created response formatting and result combination functionality"
```

### `tool_registry.py`
```yaml
source_file_intent: |
  Implements the ToolRegistry class for registering, retrieving, and
  managing internal tool functions used by the LLM coordinator.
  
source_file_design_principles: |
  - Simple registration and lookup interface
  - Tool metadata management
  - Thread-safe operation
  - Support for tool versioning
  
source_file_constraints: |
  - Must handle concurrent access safely
  - Must validate tool registrations
  - Must provide lookup by tool name
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  
change_history:
  - timestamp: "2025-04-15T11:30:00Z"
    summary: "Initial implementation of ToolRegistry"
    details: "Created tool registration and lookup functionality"
```

End of HSTC.md file
