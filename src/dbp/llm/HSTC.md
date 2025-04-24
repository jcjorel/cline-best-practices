# Hierarchical Semantic Tree Context: llm

## Directory Purpose
The llm directory implements interfaces and clients for interacting with large language models used throughout the Documentation-Based Programming system. It provides a unified abstraction layer for different LLM providers (primarily Amazon Bedrock models like Claude and Nova), handles prompt management, and implements specialized clients for specific model types. This component ensures consistent interaction patterns with LLMs regardless of the underlying model provider, handles authentication, request formatting, and response parsing according to each model's specific requirements.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Marks the llm directory as a Python package and defines its public interface.
  
source_file_design_principles: |
  - Minimal package initialization
  - Clear definition of public interfaces
  - Explicit version information
  
source_file_constraints: |
  - No side effects during import
  - No heavy dependencies loaded during initialization
  
dependencies:
  - kind: system
    dependency: Python package system
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of __init__.py in HSTC.md"
```

### `bedrock_base.py`
```yaml
source_file_intent: |
  Implements base classes and common functionality for Amazon Bedrock-based LLM clients.
  
source_file_design_principles: |
  - Abstract base classes for Bedrock clients
  - Common authentication and configuration handling
  - Shared request/response processing
  
source_file_constraints: |
  - Must handle Bedrock API version changes gracefully
  - Must implement proper error handling and retries
  - Must provide common interfaces for all Bedrock models
  
dependencies:
  - kind: system
    dependency: boto3
  - kind: codebase
    dependency: src/dbp/config/component.py
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of bedrock_base.py in HSTC.md"
```

### `bedrock_client_common.py`
```yaml
source_file_intent: |
  Implements common client functionality shared across different Bedrock model implementations.
  
source_file_design_principles: |
  - Reusable client components
  - Consistent error handling
  - Shared parameter validation
  
source_file_constraints: |
  - Must maintain compatibility with different Bedrock models
  - Must handle API changes gracefully
  
dependencies:
  - kind: system
    dependency: boto3
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of bedrock_client_common.py in HSTC.md"
```

### `bedrock_manager.py`
```yaml
source_file_intent: |
  Implements a manager for Bedrock LLM clients, handling model selection, fallbacks, and client lifecycle.
  
source_file_design_principles: |
  - Dynamic model selection based on task requirements
  - Client pooling and reuse
  - Fallback strategies for model availability issues
  
source_file_constraints: |
  - Must provide efficient client management
  - Must handle authentication failures gracefully
  - Must support configuration updates at runtime
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  - kind: codebase
    dependency: src/dbp/llm/claude3_7_client.py
  - kind: codebase
    dependency: src/dbp/llm/nova_lite_client.py
  - kind: codebase
    dependency: src/dbp/config/component.py
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of bedrock_manager.py in HSTC.md"
```

### `claude3_7_client.py`
```yaml
source_file_intent: |
  Implements a specialized client for the Claude 3.7 language model via Amazon Bedrock.
  
source_file_design_principles: |
  - Claude-specific request formatting
  - Message history management
  - Response handling for Claude's specific output format
  
source_file_constraints: |
  - Must support Claude's message-based API
  - Must handle context window limitations
  - Must implement proper token counting
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  - kind: system
    dependency: boto3
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of claude3_7_client.py in HSTC.md"
```

### `nova_lite_client.py`
```yaml
source_file_intent: |
  Implements a specialized client for the Nova Lite language model via Amazon Bedrock.
  
source_file_design_principles: |
  - Nova-specific request formatting
  - Efficient context management
  - Response parsing for Nova's output formats
  
source_file_constraints: |
  - Must support Nova's completion-style API
  - Must handle token limits efficiently
  - Must provide streaming capabilities
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock_base.py
  - kind: system
    dependency: boto3
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of nova_lite_client.py in HSTC.md"
```

### `prompt_manager.py`
```yaml
source_file_intent: |
  Implements utilities for loading, formatting, and managing prompts used with language models.
  
source_file_design_principles: |
  - Template-based prompt management
  - Variable substitution in prompts
  - Prompt versioning and caching
  
source_file_constraints: |
  - Must support model-specific prompt formatting
  - Must handle variable substitution safely
  - Must validate prompt templates
  
dependencies:
  - kind: codebase
    dependency: src/dbp/internal_tools/prompt_loader.py
  - kind: system
    dependency: Template rendering library (e.g., Jinja2)
  
change_history:
  - timestamp: "2025-04-24T23:28:15Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of prompt_manager.py in HSTC.md"
