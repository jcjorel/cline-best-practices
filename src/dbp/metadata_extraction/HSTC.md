# Hierarchical Semantic Tree Context: metadata_extraction

## Directory Purpose
This directory implements the Metadata Extraction component of the Documentation-Based Programming system. It provides functionality to extract structured metadata from source code and documentation files using Large Language Models (specifically Amazon Bedrock). The component analyzes file content to identify elements like headers, functions, classes, and documentation blocks, transforming them into structured data models that can be stored in the system's database. This extracted metadata forms the foundation for consistency analysis and recommendation generation in the broader DBP system.

## Child Directories
<!-- No child directories with HSTC.md -->

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Metadata Extraction package for the Documentation-Based Programming system.
  Provides functionality to extract metadata from code and documentation files.
  
source_file_design_principles: |
  - Exports only the essential classes and functions needed by other components
  - Maintains a clean public API with implementation details hidden
  - Uses explicit imports rather than wildcard imports
  
source_file_constraints: |
  - Must avoid circular imports
  - Should maintain backward compatibility for public interfaces
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-16T14:10:50Z"
    summary: "Fixed import path for LLMPromptManager by CodeAssistant"
    details: "Changed import from local prompts module to centralized llm.prompt_manager, added PromptLoadError import with alias to maintain backward compatibility"
  - timestamp: "2025-04-15T21:58:23Z"
    summary: "Added GenAI header to comply with documentation standards by CodeAssistant"
    details: "Added complete header template with appropriate sections"
```

### `bedrock_client.py`
```yaml
source_file_intent: |
  Implements the BedrockClient class for making LLM API calls to Amazon Bedrock
  to extract metadata from source code and documentation files.
  
source_file_design_principles: |
  - Encapsulates all Bedrock API interaction details
  - Handles authentication and connection management
  - Provides clean error handling for API failures
  
source_file_constraints: |
  - Must handle AWS credentials securely
  - Should implement appropriate retry logic
  - Must maintain compatibility with selected Bedrock models
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-15T14:30:00Z"
    summary: "Created BedrockClient implementation by CodeAssistant"
    details: "Implemented Amazon Bedrock API client with error handling and retry logic"
```

### `component.py`
```yaml
source_file_intent: |
  Implements the MetadataExtractionComponent class, which conforms to the core
  Component protocol. This component encapsulates the entire metadata extraction
  subsystem, initializing its internal services (prompt manager, Bedrock client,
  parser, processor, writer, extraction service) and providing the main interface
  for triggering metadata extraction.
  
source_file_design_principles: |
  - Conforms to the Component protocol defined in `src/dbp/core/component.py`.
  - Declares its dependencies (e.g., 'database', 'config_manager_comp').
  - Initializes all internal services during its `initialize` phase.
  - Provides a clear public method (`extract_and_store_metadata`) to perform extraction.
  - Delegates the core extraction logic to the `MetadataExtractionService`.
  - Manages its own initialization state.
  - Design Decision: Component Facade (2025-04-15)
    * Rationale: Presents the complex metadata extraction subsystem as a single, manageable component within the application's lifecycle framework.
    * Alternatives considered: Exposing the service directly (less aligned with the component model).
  
source_file_constraints: |
  - Depends on the core component framework (`Component`, `InitializationContext`).
  - Depends on the centralized LLMPromptManager from src/dbp/llm package.
  - Depends on helper classes within the `metadata_extraction` package.
  - Requires dependent components (like 'database') to be registered and initialized first.
  - Assumes configuration for metadata extraction is available via the InitializationContext.
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/COMPONENT_INITIALIZATION.md
  - kind: system
    dependency: src/dbp/core/component.py
  - kind: other
    dependency: All other files in src/dbp/metadata_extraction/
  
change_history:
  - timestamp: "2025-04-20T01:17:51Z"
    summary: "Completed dependency injection refactoring by CodeAssistant"
    details: "Removed dependencies property, made dependencies parameter required in initialize method, removed conditional logic for backwards compatibility"
  - timestamp: "2025-04-20T00:06:45Z"
    summary: "Added dependency injection support by CodeAssistant"
    details: "Updated initialize() method to accept dependencies parameter, added dictionary-based dependency injection pattern, enhanced method documentation for dependency handling"
  - timestamp: "2025-04-16T12:40:00Z"
    summary: "Updated to use centralized LLMPromptManager by Cline"
    details: "Switched to import LLMPromptManager from dbp.llm instead of local module, removed dependency on local prompts.py module that was deprecated"
```

### `data_structures.py`
```yaml
source_file_intent: |
  Defines the data structures used for representing extracted metadata
  from code files, including functions, classes, and documentation.
  
source_file_design_principles: |
  - Uses Pydantic models for strong typing and validation
  - Provides conversion methods for database integration
  - Structures data in a hierarchical way matching source code organization
  
source_file_constraints: |
  - Must align with database schema
  - Should represent all necessary metadata fields
  - Must support serialization/deserialization
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-15T13:45:00Z"
    summary: "Created metadata data structure models by CodeAssistant"
    details: "Implemented Pydantic models for extracted metadata representation"
```

### `database_writer.py`
```yaml
source_file_intent: |
  Implements the DatabaseWriter class for persisting extracted metadata
  to the database using the appropriate repositories.
  
source_file_design_principles: |
  - Abstracts database operations from the extraction service
  - Handles transaction management for data consistency
  - Manages repository interactions
  
source_file_constraints: |
  - Depends on DatabaseManager
  - Must implement proper error handling
  - Should handle both new entries and updates
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-15T15:30:00Z"
    summary: "Created database writer by CodeAssistant"
    details: "Implemented logic for storing extracted metadata in the database"
```

### `response_parser.py`
```yaml
source_file_intent: |
  Implements the ResponseParser class for parsing and validating
  LLM responses from Bedrock into structured data formats.
  
source_file_design_principles: |
  - Robust parsing of JSON responses from LLMs
  - Error handling for malformed responses
  - Validation against expected schema
  
source_file_constraints: |
  - Must handle various LLM response formats
  - Should validate against the data structures schema
  - Must provide clear error information
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-15T14:45:00Z"
    summary: "Created response parser by CodeAssistant"
    details: "Implemented parsing and validation of LLM extraction responses"
```

### `result_processor.py`
```yaml
source_file_intent: |
  Implements the ExtractionResultProcessor for transforming parsed LLM responses
  into fully structured FileMetadata objects.
  
source_file_design_principles: |
  - Transforms raw parsed data into domain models
  - Applies additional processing and enrichment
  - Handles data normalization
  
source_file_constraints: |
  - Must produce valid FileMetadata objects
  - Should handle partial or incomplete extraction results
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-15T15:00:00Z"
    summary: "Created extraction result processor by CodeAssistant"
    details: "Implemented transformation logic for parsed LLM outputs into domain models"
```

### `service.py`
```yaml
source_file_intent: |
  Implements the MetadataExtractionService class that orchestrates
  the entire metadata extraction workflow.
  
source_file_design_principles: |
  - Serves as the facade for the extraction subsystem
  - Coordinates the workflow across helper services
  - Provides a clear entry point for extraction operations
  
source_file_constraints: |
  - Depends on all other helper services
  - Must handle extraction failures gracefully
  - Should implement caching if appropriate
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-15T16:00:00Z"
    summary: "Created metadata extraction service by CodeAssistant"
    details: "Implemented the main orchestration service for metadata extraction"
```

<!-- End of HSTC.md file -->
