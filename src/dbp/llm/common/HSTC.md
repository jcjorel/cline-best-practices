# Hierarchical Semantic Tree Context: common

## Directory Purpose
This directory implements the provider-agnostic foundation for LLM interactions within the DBP application, establishing common interfaces and utilities used across all LLM providers. It defines a streaming-first approach for all model interactions, comprehensive error handling, configuration management, and utility components. The architecture ensures consistent patterns across diverse model providers while abstracting away implementation details, enabling seamless model swapping and standardized error handling throughout the LLM subsystem.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Package initialization file for common LLM interfaces and utilities.
  Exports the provider-agnostic base classes and shared utilities
  used across all LLM providers.
  
source_file_design_principles: |
  - Export all common interfaces from this package
  - Provide clean imports for shared LLM components
  - Keep initialization minimal to prevent circular dependencies
  
source_file_constraints: |
  - Should only export common interfaces and utilities
  - Must not import provider-specific implementations
  - Must not contain implementation logic
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  
change_history:
  - timestamp: "2025-05-02T07:10:00Z"
    summary: "Initial creation of common LLM package"
    details: "Created common LLM package for provider-agnostic interfaces and added exports for base interfaces and types"
```

### `base.py`
```yaml
source_file_intent: |
  Defines the abstract base classes and interfaces for all LLM model clients,
  regardless of provider. This establishes a common streaming-only interface that 
  all model clients must implement, enabling consistent interaction patterns across
  different LLM providers for both single-shot and conversational scenarios.
  
source_file_design_principles: |
  - Provide a provider-agnostic interface for LLM clients
  - Use streaming as the universal interaction pattern, including for models without native streaming
  - Support both single-shot and conversational interactions consistently
  - Define clear abstract methods that all implementations must support
  - Separate common functionality from provider-specific implementations
  - Enable seamless swapping between different LLM providers
  - Follow the abstract base class pattern for client implementation
  
source_file_constraints: |
  - Must not contain provider-specific parameters or logic
  - Must define a broad interface that works for various LLM providers
  - Must provide structured logging for all operations
  - Must be compatible with diverse model response formats
  - Must not introduce dependencies on specific cloud providers
  - Must only expose streaming interfaces, even for non-streaming models
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  - kind: system
    dependency: abc
  - kind: system
    dependency: logging
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-02T07:08:00Z"
    summary: "Created provider-agnostic base interface"
    details: "Implemented streaming-only interface as per requirements, added support for both single-shot and conversational patterns, created ModelClientBase abstract base class for all providers, and added common exception types for LLM operations"
```

### `exceptions.py`
```yaml
source_file_intent: |
  Defines all exceptions used across the LLM module. This centralizes error types
  to ensure consistent error handling and reporting throughout the codebase.
  Provides specific exception types for different failure scenarios.
  
source_file_design_principles: |
  - All exceptions derive from a common base class for unified handling
  - Exceptions include descriptive error messages and contextual information
  - Each exception type represents a distinct failure scenario
  - Error information is structured to support easy logging and debugging
  - No catch-all handlers or silent failure modes (follows "raise on error" principle)
  
source_file_constraints: |
  - Must not suppress or transform exceptions from lower levels
  - Custom exceptions must provide enough context for troubleshooting
  - Exceptions should be fine-grained to support specific error handling
  
dependencies:
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-02T10:32:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Created exception hierarchy for LLM module"
```

### `prompt_manager.py`
```yaml
source_file_intent: |
  Implements a system for loading, managing, and formatting prompts for LLM interactions,
  supporting template variables, versioning, and prompt validation.
  
source_file_design_principles: |
  - Template-based prompt management
  - Filesystem-based prompt loading
  - Variable substitution in templates
  - Prompt versioning and caching
  - Support for different model-specific formatting
  
source_file_constraints: |
  - Must handle different prompt formats for different models
  - Must support template variables efficiently
  - Must validate prompt templates
  - Must handle prompt loading errors gracefully
  
dependencies:
  - kind: system
    dependency: jinja2
  - kind: system
    dependency: pathlib
  
change_history:
  - timestamp: "2025-05-02T08:15:00Z"
    summary: "Initial implementation of LLM prompt manager"
    details: "Created prompt loading, formatting, and template substitution system"
```

### `streaming.py`
```yaml
source_file_intent: |
  Provides utilities for handling streaming responses from LLM providers,
  including chunking, parsing, and transforming streamed content.
  
source_file_design_principles: |
  - Consistent handling of streamed responses across providers
  - Error handling for interrupted streams
  - Efficient processing of stream chunks
  - Support for both token and message-level streaming
  
source_file_constraints: |
  - Must work with different streaming formats from various providers
  - Must handle stream interruptions gracefully
  - Must provide performance-optimized stream processing
  
dependencies:
  - kind: system
    dependency: asyncio
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  
change_history:
  - timestamp: "2025-05-02T09:20:00Z"
    summary: "Initial implementation of streaming utilities"
    details: "Created helpers for processing and transforming LLM response streams"
```

### `tool_registry.py`
```yaml
source_file_intent: |
  Implements a registry for managing LLM tools and function calling capabilities
  across different model providers and ensuring consistent tool definitions.
  
source_file_design_principles: |
  - Centralized tool registration and discovery
  - Provider-agnostic tool definitions
  - Support for dynamic tool loading
  - Validation of tool schemas and parameters
  
source_file_constraints: |
  - Must support different tool formats for various LLM providers
  - Must ensure consistent tool behavior across providers
  - Must validate tool definitions against provider requirements
  
dependencies:
  - kind: system
    dependency: typing
  - kind: system
    dependency: json
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  
change_history:
  - timestamp: "2025-05-02T11:45:00Z"
    summary: "Initial implementation of LLM tool registry"
    details: "Created system for registering, validating, and using LLM tools across providers"
```

### `config_registry.py`
```yaml
source_file_intent: |
  Manages configuration settings for LLM clients and provides a centralized
  registry for model-specific configuration profiles.
  
source_file_design_principles: |
  - Centralized configuration management
  - Support for different configuration profiles
  - Environment-aware configuration loading
  - Validation of configuration parameters
  
source_file_constraints: |
  - Must support different configuration needs for various providers
  - Must validate configuration against model requirements
  - Must handle configuration overrides and defaults
  
dependencies:
  - kind: system
    dependency: typing
  - kind: system
    dependency: json
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  
change_history:
  - timestamp: "2025-05-02T12:30:00Z"
    summary: "Initial implementation of configuration registry"
    details: "Created system for managing and validating LLM configuration profiles"
```

End of HSTC.md file
