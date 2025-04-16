# Query Command Implementation Plan

## Documentation References

⚠️ **CRITICAL: ALL TEAM MEMBERS MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

The following documentation files provide the context and requirements for implementing the query command:

- [DESIGN.md](../../doc/DESIGN.md) - Core system architecture and principles
- [DATA_MODEL.md](../../doc/DATA_MODEL.md) - Data structures and MCP CLI client model
- [CONFIGURATION.md](../../doc/CONFIGURATION.md) - Configuration parameters
- [DOCUMENT_RELATIONSHIPS.md](../../doc/DOCUMENT_RELATIONSHIPS.md) - Documentation dependency relationships
- [SECURITY.md](../../doc/SECURITY.md) - Security principles for the system

### Documentation Relevance

- **DESIGN.md**: Defines the LLM Coordination Architecture that the query command will interact with, including the Coordinator LLM, internal tools, and asynchronous job management.
- **DATA_MODEL.md**: Outlines the MCPClientAPI data structures that the query command will utilize.
- **CONFIGURATION.md**: Specifies how the CLI client connects to the MCP server and the default parameters (code-dir: ./src, doc-dir: ./doc).
- **DOCUMENT_RELATIONSHIPS.md**: Provides context on how documentation files relate to each other, which will be important for query responses.
- **SECURITY.md**: Defines security considerations for local processing and network binding.

## Implementation Overview

The query command will provide a simple interface for users to send natural language queries to the Documentation-Based Programming system. It will be the only interface for querying the system, replacing the previously mentioned analyze/recommend/apply/relationships commands.

### Key Design Decisions

1. **Single Command Approach**: Implement a unified "query" command that handles all types of queries through a single entry point.
2. **Plain Text Queries**: Accept plain text queries without requiring structured parameters.
3. **Server-Side Directory Configuration**: Rely on the server's configured code and documentation directories rather than specifying them in the CLI.
4. **Progress Indicator**: Show progress to the user while the LLM processes the query.
5. **Flexible Output Formatting**: Support multiple output formats (formatted, JSON, YAML) for query results.

## Implementation Phases

### Phase 1: API Extension

Extend the MCPClientAPI to support the new general query functionality by adding a method that communicates with the coordinator LLM.

### Phase 2: Command Handler Implementation

Create the QueryCommandHandler class that extends BaseCommandHandler, implementing the necessary methods to process user queries and display results.

### Phase 3: Integration and Registration

Register the new command handler and ensure it's properly integrated with the CLI system.

### Phase 4: Testing and Documentation

Develop comprehensive tests for the new command and update documentation to reflect the new functionality.

## Implementation Files

The following files will be created or modified as part of this plan:

1. [plan_progress.md](./plan_progress.md) - Tracks implementation progress
2. [plan_api_extension.md](./plan_api_extension.md) - Details of the API extension
3. [plan_command_handler.md](./plan_command_handler.md) - QueryCommandHandler implementation details
4. [plan_integration.md](./plan_integration.md) - Integration and registration details
5. [plan_testing.md](./plan_testing.md) - Testing strategy and test cases

## Essential Source Documentation Excerpts

### From DESIGN.md - LLM Coordination Architecture

```
The system implements a hierarchical LLM coordination pattern:

1. **Coordinator LLM**: An instance of Amazon Nova Lite with a dedicated system prompt manages incoming requests
2. **Internal Tool LLMs**: Specialized LLM instances handle specific context types and processing tasks
3. **Asynchronous Job Management**: Parallel execution of multiple internal tools for improved performance
```

### From DESIGN.md - MCP-Exposed Tools

```
1. **dbp_general_query**
   - **Purpose**: Retrieve various types of codebase metadata
   - **Implementation**: Uses the LLM coordination architecture described above
   - **Processing**: Coordinator LLM determines which internal tools are required based on query
   - **Response**: Consolidated results from all executed internal tools
```

### From DATA_MODEL.md - MCP Request/Response Model

```python
MCPRequest {
  requestId: UUID          // Unique identifier for the request
  serverName: String       // Target MCP server name
  requestType: Enum        // Tool, Resource
  toolName: String         // If tool request, name of the tool
  resourceUri: String      // If resource request, URI of the resource
  parameters: Object       // Key-value pairs of parameters for tool requests
  timestamp: Timestamp     // When request was initiated
}

MCPResponse {
  requestId: UUID          // Matching the request ID
  serverName: String       // Source MCP server name
  status: Enum             // Success, Error, Pending
  result: Object           // Response data from the server
  errorDetails: {          // Present only if status is Error
    code: String,          // Error code
    message: String,       // Error message
    details: Object        // Additional error details
  }
  timestamp: Timestamp     // When response was received
}
```

### From CONFIGURATION.md - Directory Configuration

```
There is no need to specify in the CLI where are located source code and documentation as it is a server concept only that come from configuration. Default value for code-dir is ./src and default value for doc-dir is ./doc (all managed at server side)
```

Follow the plan_progress.md file for the current status of implementation and to track progress through each phase.
