# Hierarchical Semantic Tree Context: models

## Directory Purpose
This directory contains model-specific implementations for different Amazon Bedrock foundation models, each providing specialized handling for unique model parameters, input formatting requirements, and response processing patterns. It extends the common Bedrock base implementation with model-specific optimizations, formatting logic, and parameter tuning. Each model client handles the unique requirements of specific foundation models while maintaining a consistent interface to ensure they integrate seamlessly with the rest of the application.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Package initialization file for the AWS Bedrock model implementations.
  Exports the specific model client classes for various foundation models
  available through AWS Bedrock.
  
source_file_design_principles: |
  - Export all model-specific client implementations
  - Provide clean imports for model client classes
  - Keep initialization minimal to prevent circular dependencies
  
source_file_constraints: |
  - Should only export model-specific client implementations
  - Must not contain implementation logic
  - Must maintain backward compatibility with existing code
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  
change_history:
  - timestamp: "2025-05-02T12:14:00Z" 
    summary: "Consolidated Claude model implementations"
    details: "Removed Claude37SonnetClient export, added ClaudeClient export from claude3.py, consolidated to use single Claude implementation"
  - timestamp: "2025-05-02T07:26:00Z"
    summary: "Initial creation of models package"
    details: "Created package initialization file for model implementations and added exports for model-specific client classes"
```


### `claude3.py`
```yaml
source_file_intent: |
  Implements specialized Bedrock clients for various models in the Anthropic Claude 3 family,
  handling model-specific request formatting, invocation parameters, and response processing
  for both single-shot and conversational interactions.
  
source_file_design_principles: |
  - Implement the BedrockModelClientBase interface for Claude 3 models
  - Share common Claude-specific request and response formats
  - Provide optimal default parameters for each Claude 3 variant
  - Support the streaming-only interface pattern
  - Handle Claude system prompts efficiently
  
source_file_constraints: |
  - Must adhere to Claude 3-specific API requirements
  - Must handle Claude 3 error conditions appropriately
  - Must process responses according to Claude 3's output format
  - Must implement the streaming-only interface
  - Must support all Claude 3 variants (Haiku, Sonnet, Opus)
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/common/prompt_manager.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/base.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/client_common.py
  - kind: system
    dependency: logging
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-02T07:26:00Z"
    summary: "Refactored and moved to bedrock/models directory"
    details: "Relocated from src/dbp/llm/claude3_client.py to current location, updated imports to reflect new directory structure, refactored to use streaming-only invoke interface"
  - timestamp: "2025-04-16T13:30:00Z" 
    summary: "Initial creation of Claude 3 client implementations"
    details: "Created base Claude 3 client with specialized variants for Haiku, Sonnet, and Opus"
```

### `nova.py`
```yaml
source_file_intent: |
  Implements specialized Bedrock clients for Amazon's Nova and Nova Lite models,
  handling model-specific request formatting, invocation parameters, and response
  processing for both single-shot and conversational interactions.
  
source_file_design_principles: |
  - Implement the BedrockModelClientBase interface for Nova models
  - Handle Nova-specific request and response formats
  - Provide optimal default parameters for Nova variants
  - Support the streaming-only interface pattern
  - Optimize for Nova's unique capabilities
  
source_file_constraints: |
  - Must adhere to Nova-specific API requirements
  - Must handle Nova error conditions appropriately
  - Must process responses according to Nova's output format
  - Must implement the streaming-only interface
  - Must support both Nova and Nova Lite variants
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/common/prompt_manager.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/base.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/client_common.py
  - kind: system
    dependency: logging
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-02T07:26:00Z"
    summary: "Refactored and moved to bedrock/models directory"
    details: "Relocated from src/dbp/llm/nova_client.py to current location, updated imports to reflect new directory structure, refactored to use streaming-only invoke interface"
  - timestamp: "2025-04-16T14:00:00Z"
    summary: "Initial creation of Nova model clients"
    details: "Created clients for Nova and Nova Lite models with optimized parameter settings"
```

End of HSTC.md file
