# Hierarchical Semantic Tree Context: llm

## Directory Purpose
This directory implements the LLM (Large Language Model) services for the DBP application, providing a unified framework for interacting with different Foundation Models through Amazon Bedrock. It offers model-specific clients, a central manager for coordinating client usage, common utilities for handling prompts and responses, and abstraction layers to support multiple model types. The architecture ensures consistent interaction patterns, efficient resource management, and robust error handling while hiding provider-specific implementation details from the rest of the application.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports the LLM client classes and utilities for use throughout the DBP system.
  
source_file_design_principles: |
  - Provides clean imports for LLM classes
  - Maintains hierarchical package structure
  - Prevents circular imports
  
source_file_constraints: |
  - Should only export necessary classes and functions
  - Must not contain implementation logic
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-16T09:00:00Z"
    summary: "Initial creation of llm package"
    details: "Created __init__.py with exports for key LLM classes"
```

### `bedrock_base.py`
```yaml
source_file_intent: |
  Defines the base class for all AWS Bedrock model clients, establishing a common
  interface and shared functionality that all model-specific clients must implement.
  
source_file_design_principles: |
  - Abstract base class pattern for consistent client interfaces
  - Standardized initialization and configuration
  - Common error handling and logging
  - Shared AWS client management
  - Consistent method signatures across model types
  
source_file_constraints: |
  - Must work with multiple model types with different parameter requirements
  - Must handle AWS credentials and region information consistently
  - Must provide clear error handling for API failures
  - Should not contain model-specific implementation details
  
dependencies:
  - kind: system
    dependency: abc
  - kind: system
    dependency: boto3
  
change_history:
  - timestamp: "2025-04-16T10:00:00Z"
    summary: "Initial implementation of BedrockModelClientBase"
    details: "Created abstract base class for Bedrock model clients with common functionality"
```

### `bedrock_client_common.py`
```yaml
source_file_intent: |
  Provides shared utilities and helper functions for AWS Bedrock clients, including
  request formatting, response parsing, error handling, and common operations.
  
source_file_design_principles: |
  - Code reuse across different model clients
  - Consistent request and response formatting
  - Standardized error handling and logging
  - Common utility functions for AWS API interactions
  
source_file_constraints: |
  - Must support different model types with varying API formats
  - Must handle API errors consistently
  - Must provide clear debugging information
  
dependencies:
  - kind: system
    dependency: boto3
  - kind: system
    dependency: json
  
change_history:
  - timestamp: "2025-04-16T11:00:00Z"
    summary: "Initial implementation of common Bedrock client utilities"
    details: "Created shared functions for request formatting, response parsing, and error handling"
```

### `bedrock_manager.py`
```yaml
source_file_intent: |
  Implements a central manager for all Bedrock model clients. This manager
  serves as the main entry point for all Bedrock LLM operations, providing
  a unified interface for accessing various model clients and handling their
  lifecycle.
  
source_file_design_principles: |
  - Centralize Bedrock client management across the application
  - Lazily initialize model clients only when needed
  - Cache clients for reuse to optimize resource usage
  - Provide a simple interface for retrieving clients by name
  - Handle configuration loading and default values
  - Support clean shutdown of all active clients
  
source_file_constraints: |
  - Must support multiple model types with different parameter requirements
  - Must not hardcode AWS credentials or region information
  - Must handle model unavailability gracefully
  - Must be thread-safe for concurrent access from multiple components
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  - kind: system
    dependency: boto3
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  - kind: codebase
    dependency: src/dbp/llm/nova_lite_client.py
  - kind: codebase
    dependency: src/dbp/llm/claude3_7_client.py
  - kind: codebase
    dependency: src/dbp/llm/prompt_manager.py
  
change_history:
  - timestamp: "2025-04-16T13:00:00Z"
    summary: "Initial creation of Bedrock client manager"
    details: "Implemented client registry and lazy initialization, added support for configuration-based client creation, created interface for retrieving model clients by name"
```

### `claude3_7_client.py`
```yaml
source_file_intent: |
  Implements a specific client for Anthropic's Claude 3.7 models through AWS Bedrock,
  handling the unique requirements and capabilities of this model family.
  
source_file_design_principles: |
  - Extends the abstract BedrockModelClientBase class
  - Implements Claude-specific request formatting
  - Handles Claude-specific response parsing
  - Optimizes for Claude's unique capabilities
  - Provides Claude-specific parameter validation
  
source_file_constraints: |
  - Must comply with Claude API requirements
  - Must handle Claude's specific input/output formats
  - Must respect Claude's token limits
  - Must properly format system prompts for Claude
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock_client_common.py
  
change_history:
  - timestamp: "2025-04-16T14:00:00Z"
    summary: "Initial implementation of Claude 3.7 client"
    details: "Created Claude-specific client with specialized prompt formatting and parameter handling"
```

### `nova_lite_client.py`
```yaml
source_file_intent: |
  Implements a specific client for Amazon's Nova Lite models through AWS Bedrock,
  handling the unique requirements and capabilities of this model family.
  
source_file_design_principles: |
  - Extends the abstract BedrockModelClientBase class
  - Implements Nova-specific request formatting
  - Handles Nova-specific response parsing
  - Optimizes for Nova Lite's capabilities
  - Provides Nova-specific parameter validation
  
source_file_constraints: |
  - Must comply with Nova Lite API requirements
  - Must handle Nova's specific input/output formats
  - Must respect Nova's token limits
  - Must properly format system prompts for Nova
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock_client_common.py
  
change_history:
  - timestamp: "2025-04-16T15:00:00Z"
    summary: "Initial implementation of Nova Lite client"
    details: "Created Nova Lite-specific client with specialized prompt formatting and parameter handling"
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
  - timestamp: "2025-04-16T16:00:00Z"
    summary: "Initial implementation of LLM prompt manager"
    details: "Created prompt loading, formatting, and template substitution system"
```

End of HSTC.md file
