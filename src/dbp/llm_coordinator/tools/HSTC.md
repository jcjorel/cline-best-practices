# Hierarchical Semantic Tree Context: tools

## Directory Purpose
This directory contains tool implementations used by the LLM coordinator to enable interactions between LLMs and various system capabilities. It provides the foundation for both LangChain-compatible and custom tools that can be registered with the tool registry and exposed to LLMs through the coordinator. The architecture follows a modular approach with a common base class for all tools, standardized interfaces, and MCP integration for external accessibility, enabling LLMs to interact with system functionality through a consistent interface.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  This file exports tool implementations for the LLM coordinator module.
  It provides a convenient import point for all available LLM tools.
  
source_file_design_principles: |
  - Export only essential components to keep the API surface clean
  - Provide clear import paths for tool implementations
  - Document all exports to make usage intuitive
  
source_file_constraints: |
  - Must not contain implementation logic, only exports
  - Must maintain backward compatibility for any exports
  
dependencies:
  - kind: unknown
    dependency: None yet, will import tools as they are implemented
  
change_history:
  - timestamp: "2025-05-02T10:47:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Created empty module for tool exports"
```

### `base.py`
```yaml
source_file_intent: |
  Defines the base classes and interfaces for LLM tools within the coordinator.
  Provides a foundation for implementing both LangChain-compatible and custom tools
  that can be registered with the tool registry and used by LLMs.
  
source_file_design_principles: |
  - Clean separation between tool interface and implementation
  - Compatibility with LangChain tool specifications
  - Support for both synchronous and asynchronous execution
  - Strong type checking and validation
  
source_file_constraints: |
  - Must remain compatible with LangChain tool specifications
  - Must provide both sync and async interfaces
  - Must validate inputs against schemas
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm/common/exceptions.py
  - kind: codebase
    dependency: src/dbp/llm/common/tool_registry.py
  - kind: system
    dependency: typing
  - kind: system
    dependency: pydantic
  - kind: system
    dependency: langchain_core
  
change_history:
  - timestamp: "2025-05-02T10:47:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Created placeholder for base tool classes"
```

### `dbp_general_query.py`
```yaml
source_file_intent: |
  Implements a general query MCP tool for interacting with LLMs. This tool enables
  external MCP clients to execute queries against the LLM infrastructure with
  streaming support and context-aware processing.
  
source_file_design_principles: |
  - MCP integration for external accessibility
  - Streaming-first approach
  - Delegation to AgentManager for processing
  - Clean error handling and reporting
  - Context-aware query processing
  
source_file_constraints: |
  - Must implement MCP tool interface correctly
  - Must support streaming responses
  - Must provide proper parameter validation
  - Must handle error conditions gracefully
  
dependencies:
  - kind: codebase
    dependency: src/dbp/mcp_server/adapter.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/agent_manager.py
  - kind: codebase
    dependency: src/dbp/llm_coordinator/exceptions.py
  - kind: system
    dependency: logging
  - kind: system
    dependency: asyncio
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-02T11:40:00Z"
    summary: "Initial creation for LangChain/LangGraph integration"
    details: "Created GeneralQueryTool for MCP integration, added streaming response handling, implemented parameter validation"
```

End of HSTC.md file
