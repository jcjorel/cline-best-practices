# Hierarchical Semantic Tree Context: bedrock

## Directory Purpose
This directory implements the AWS Bedrock integration for the DBP application's LLM subsystem, providing specialized client implementations for various Bedrock foundation models. It implements the provider-agnostic interfaces defined in the common directory, with a focus on the Bedrock Converse API for all interactions. The architecture ensures consistent error handling, efficient streaming operations, and complete AWS credential management while abstracting Bedrock-specific implementation details behind common interfaces for seamless integration with the rest of the application.

## Child Directories

### models
This directory contains model-specific implementations for different Amazon Bedrock foundation models, each providing specialized handling for unique model parameters, input formatting requirements, and response processing patterns. It enables the system to leverage the unique capabilities of each model while presenting a consistent interface to the application.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Package initialization file for the AWS Bedrock LLM provider implementation.
  Exports the Bedrock-specific client classes and interfaces for use by
  the rest of the application.
  
source_file_design_principles: |
  - Export all Bedrock-specific interfaces and client classes
  - Provide clean imports for Bedrock components
  - Keep initialization minimal to prevent circular dependencies
  
source_file_constraints: |
  - Should only export Bedrock-specific interfaces and classes
  - Must not contain implementation logic
  - Must maintain backward compatibility with existing code
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  
change_history:
  - timestamp: "2025-05-02T07:20:00Z"
    summary: "Initial creation of AWS Bedrock package"
    details: "Created Bedrock LLM provider package initialization file and added exports for Bedrock interfaces and errors"
```

### `base.py`
```yaml
source_file_intent: |
  Provides foundational Amazon Bedrock integration focusing exclusively on 
  the Converse API. This base class serves as the foundation for all 
  Bedrock model clients, handling authentication, streaming API interactions, 
  and comprehensive error management.
  
source_file_design_principles: |
  - Exclusive use of Converse API for all interactions 
  - Streaming as the primary interaction pattern
  - Asynchronous interface for non-blocking operations
  - Comprehensive error handling and reporting
  - Clean separation of common Bedrock functionality from model specifics
  - Thread-safe AWS client management
  - Support for both chat and completion formats
  
source_file_constraints: |
  - Must not contain model-specific parameters or logic
  - Must handle AWS credentials and region configuration properly
  - Must provide structured logging for all operations
  - Must be compatible with all Bedrock foundation models
  - Must use only the Converse API for all interactions
  - Must implement full asynchronous interface
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/base.py
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: codebase
    dependency: src/dbp/llm/common/streaming.py
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/design/LLM_COORDINATION.md
  - kind: system
    dependency: boto3
  - kind: system
    dependency: botocore
  - kind: system
    dependency: asyncio
  
change_history:
  - timestamp: "2025-05-02T11:13:00Z"
    summary: "Enhanced for LangChain/LangGraph integration"
    details: "Updated to use Converse API exclusively, implemented fully async interface for all operations, added streaming support with AsyncIO generators, enhanced error handling and classification"
  - timestamp: "2025-05-02T07:15:00Z"
    summary: "Refactored and moved to bedrock directory"
    details: "Relocated from src/dbp/llm/bedrock_base.py to current location, extended ModelClientBase to specialize for Bedrock, refactored to use streaming-only interface"
```

### `client_common.py`
```yaml
source_file_intent: |
  Provides common utilities and functions for Amazon Bedrock clients that are
  shared across different model implementations. This includes response and
  request formatting, streaming response processing, and error mapping that
  are specific to the Bedrock Converse API but not tied to a particular model.
  
source_file_design_principles: |
  - Clean separation of common functionality from model-specific code
  - Consistent error handling and response processing
  - Utilities for working with streaming responses
  - Reusable components for all Bedrock model clients
  - Support for asynchronous operations
  - Standardized message and response formats
  
source_file_constraints: |
  - Must not contain model-specific parameters or logic
  - Must be compatible with all Bedrock foundation models
  - Must focus only on common functionality
  - Must support the Converse API format
  - Must maintain stateless utilities
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: codebase
    dependency: src/dbp/llm/common/streaming.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/base.py
  - kind: system
    dependency: json
  - kind: system
    dependency: asyncio
  
change_history:
  - timestamp: "2025-05-02T11:16:00Z"
    summary: "Enhanced for LangChain/LangGraph integration"
    details: "Implemented Converse API response processing, added async streaming helpers, created standardized format conversion utilities, added specialized error mapping"
  - timestamp: "2025-05-02T07:15:00Z"
    summary: "Refactored and moved to bedrock directory"
    details: "Relocated from src/dbp/llm/bedrock_client_common.py to current location, updated imports to reflect new directory structure"
```

### `converse_client.py`
```yaml
source_file_intent: |
  Implements a specialized client for Amazon Bedrock's Converse API,
  providing a higher-level interface for interacting with all Bedrock
  models through a unified conversational interface. This client handles
  model-agnostic conversational interactions in a consistent manner.
  
source_file_design_principles: |
  - Unified interface for all Bedrock models
  - Streamlined conversational API access
  - Specialized handling of conversational context
  - Support for stateful conversations
  - Consistent error handling
  - Streaming as primary interaction mode
  
source_file_constraints: |
  - Must be compatible with all Bedrock foundation models
  - Must maintain conversation state properly
  - Must implement streaming for all interactions
  - Must provide clear error messages
  - Must handle conversation context efficiently
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/bedrock/base.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/client_common.py
  - kind: codebase
    dependency: src/dbp/llm/common/streaming.py
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-02T11:18:00Z"
    summary: "Enhanced for LangChain/LangGraph integration"
    details: "Implemented unified Converse API client, added conversation state management, implemented fully async streaming interface"
  - timestamp: "2025-05-02T07:30:00Z"
    summary: "Initial implementation of Bedrock Converse client"
    details: "Created specialized client for the Bedrock Converse API"
```

End of HSTC.md file
