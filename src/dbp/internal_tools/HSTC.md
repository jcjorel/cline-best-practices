# Hierarchical Semantic Tree Context: internal_tools

## Directory Purpose
This directory implements a specialized component for the DBP system that provides internal LLM tools used by the LLM Coordinator. It consists of an execution engine, context assemblers, LLM interfaces, and response handlers that work together to provide various LLM-powered tools for codebase context retrieval, documentation analysis, and expert architect advice. The component follows the core Component protocol, initializes all necessary parts, and registers tool execution methods with the LLM Coordinator's ToolRegistry.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports the internal tools component and its main classes for use within the DBP system.
  
source_file_design_principles: |
  - Provides clean imports for component and key classes
  - Maintains hierarchical package structure
  - Prevents circular imports
  
source_file_constraints: |
  - Should only export necessary classes and functions
  - Must not contain implementation logic
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-15T10:00:00Z"
    summary: "Initial creation of internal_tools package"
    details: "Created __init__.py with exports for key internal tools classes"
```

### `component.py`
```yaml
source_file_intent: |
  Implements the InternalToolsComponent class, conforming to the core Component
  protocol. This component encapsulates the specialized internal LLM tools,
  initializing their dependencies (context assemblers, LLM interfaces, response
  handlers, execution engine) and registering the tool execution functions with
  the LLM Coordinator's ToolRegistry.
  
source_file_design_principles: |
  - Conforms to the Component protocol (`src/dbp/core/component.py`).
  - Declares dependency on the `llm_coordinator` component to access its ToolRegistry.
  - Initializes all internal tool parts (assemblers, LLMs, handlers, engine).
  - Registers the actual tool execution methods from the engine with the coordinator's registry.
  - Acts as a container and initializer for the internal tools subsystem.
  - Design Decision: Dedicated Component for Internal Tools (2025-04-15)
    * Rationale: Groups the implementation of all specialized tools under a single manageable component within the application framework.
    * Alternatives considered: Implementing tools directly within the coordinator (less modular).
  
source_file_constraints: |
  - Depends on the core component framework and the `llm_coordinator` component.
  - Requires all helper classes within the `internal_tools` package to be implemented.
  - Assumes configuration for internal tools is available via InitializationContext.
  - Placeholder logic exists in the execution engine and LLM interfaces.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/INTERNAL_LLM_TOOLS.md
  - kind: system
    dependency: src/dbp/core/component.py
  - kind: other
    dependency: src/dbp/llm_coordinator/component.py
  - kind: other
    dependency: src/dbp/internal_tools/execution_engine.py
  
change_history:
  - timestamp: "2025-04-20T01:49:11Z"
    summary: "Completed dependency injection refactoring"
    details: "Added dependencies parameter to initialize method, converted to use get_dependency() for dependency resolution, updated imports and documentation for dependency injection"
  - timestamp: "2025-04-15T10:15:55Z"
    summary: "Initial creation of InternalToolsComponent"
    details: "Implemented Component protocol methods, initialization of internal parts, and tool registration logic."
```

### `execution_engine.py`
```yaml
source_file_intent: |
  Implements the core execution engine for internal LLM tools, orchestrating 
  the context assembly, LLM interactions, and response handling into a unified workflow.
  
source_file_design_principles: |
  - Provides high-level execution methods for each internal tool type
  - Coordinates interactions between context assemblers, LLM interfaces, and response handlers
  - Maintains abstract workflow logic separate from specific implementations
  - Implements consistent error handling and logging
  
source_file_constraints: |
  - Must handle different LLM provider interfaces
  - Must support various context assembly strategies
  - Must provide consistent response formatting
  
dependencies:
  - kind: codebase
    dependency: src/dbp/internal_tools/context_assemblers.py
  - kind: codebase
    dependency: src/dbp/internal_tools/llm_interface.py
  - kind: codebase
    dependency: src/dbp/internal_tools/response_handlers.py
  
change_history:
  - timestamp: "2025-04-15T11:00:00Z"
    summary: "Initial implementation of execution engine"
    details: "Created InternalToolExecutionEngine class with methods for each tool type"
```

### `context_assemblers.py`
```yaml
source_file_intent: |
  Implements context assembly strategies for different LLM tool types,
  gathering relevant information from the codebase, documentation, and other sources.
  
source_file_design_principles: |
  - Strategy pattern for different context assembly approaches
  - Customized assembly logic for each tool type
  - Efficient context window management
  - Prioritization of most relevant context
  
source_file_constraints: |
  - Must handle large codebase with selective context inclusion
  - Must respect context window size limitations
  - Must prioritize most recent or relevant information
  
dependencies:
  - kind: codebase
    dependency: src/dbp/internal_tools/file_access.py
  
change_history:
  - timestamp: "2025-04-15T12:00:00Z"
    summary: "Initial implementation of context assemblers"
    details: "Created base context assembler and specialized implementations for different tool types"
```

### `llm_interface.py`
```yaml
source_file_intent: |
  Provides interfaces to different LLM providers and manages prompt construction,
  request formatting, and response parsing for internal LLM tools.
  
source_file_design_principles: |
  - Abstracts provider-specific implementation details
  - Supports multiple LLM providers through common interface
  - Handles proper prompt formatting for each provider
  - Implements retry logic and error handling
  
source_file_constraints: |
  - Must support different LLM provider APIs
  - Must handle rate limiting and quotas
  - Must implement proper authentication
  
dependencies:
  - kind: codebase
    dependency: src/dbp/internal_tools/prompt_loader.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock_manager.py
  
change_history:
  - timestamp: "2025-04-15T13:00:00Z"
    summary: "Initial implementation of LLM interfaces"
    details: "Created base LLM interface and provider-specific implementations"
```

### `response_handlers.py`
```yaml
source_file_intent: |
  Processes and formats LLM responses into standardized output structures
  for different internal tool types.
  
source_file_design_principles: |
  - Strategy pattern for different response handling approaches
  - Consistent output formatting
  - Error detection and recovery
  - Response validation
  
source_file_constraints: |
  - Must handle malformed or unexpected responses
  - Must provide consistent output structure
  - Must detect and handle hallucinations
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-15T14:00:00Z"
    summary: "Initial implementation of response handlers"
    details: "Created base response handler and specialized implementations for different tool types"
```

### `file_access.py`
```yaml
source_file_intent: |
  Provides utilities for accessing and reading files from the codebase
  and documentation, with caching and filtering capabilities.
  
source_file_design_principles: |
  - Efficient file access with caching
  - Filtering capabilities for different file types
  - Support for various file formats
  - Thread-safe operation
  
source_file_constraints: |
  - Must handle large repositories efficiently
  - Must implement proper error handling for file access issues
  - Must support filtering based on file patterns
  
dependencies:
  - kind: codebase
    dependency: src/dbp/core/file_access.py
  
change_history:
  - timestamp: "2025-04-15T15:00:00Z"
    summary: "Initial implementation of file access utilities"
    details: "Created specialized file access utilities for internal tools"
```

### `prompt_loader.py`
```yaml
source_file_intent: |
  Loads and manages prompts for different internal LLM tools,
  supporting template rendering and prompt versioning.
  
source_file_design_principles: |
  - Template-based prompt management
  - Support for prompt versioning
  - Efficient prompt loading and caching
  - Variable substitution
  
source_file_constraints: |
  - Must support different prompt formats
  - Must handle template variables
  - Must ensure prompt consistency
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/prompt_manager.py
  
change_history:
  - timestamp: "2025-04-15T16:00:00Z"
    summary: "Initial implementation of prompt loader"
    details: "Created prompt loading and templating utilities for internal tools"
```

End of HSTC.md file
