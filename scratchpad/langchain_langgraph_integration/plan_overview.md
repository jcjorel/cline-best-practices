# Implementation Plan: LangChain/LangGraph Integration for DBP

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Documentation References

The following documentation files provide necessary context for this implementation plan:

1. [doc/DESIGN.md](../../doc/DESIGN.md) - General architecture principles and system design
2. [doc/design/LLM_COORDINATION.md](../../doc/design/LLM_COORDINATION.md) - Current LLM coordination architecture
3. [doc/DESIGN_DECISIONS.md](../../doc/DESIGN_DECISIONS.md) - Project-wide design decisions
4. [doc/DATA_MODEL.md](../../doc/DATA_MODEL.md) - Database schema and data structures
5. [doc/CONFIGURATION.md](../../doc/CONFIGURATION.md) - Configuration parameters
6. [doc/llm/prompts/README.md](../../doc/llm/prompts/README.md) - Prompt management
7. [src/dbp/llm/HSTC.md](../../src/dbp/llm/HSTC.md) - LLM directory context
8. [src/dbp/llm_coordinator/HSTC.md](../../src/dbp/llm_coordinator/HSTC.md) - LLM Coordinator context

These documentation files provide:
- **DESIGN.md**: Core architectural principles including component design and error handling approach
- **LLM_COORDINATION.md**: Current LLM coordination architecture that will be replaced with LangChain/LangGraph
- **DESIGN_DECISIONS.md**: Project-level design decisions impacting implementation approach
- **DATA_MODEL.md**: Data structures relevant to LLM interactions and coordinator state
- **CONFIGURATION.md**: Configuration parameters needed for LLM integrations
- **prompts/README.md**: Information about the prompt management system that will be preserved
- **LLM HSTC.md**: Current implementation details of the LLM module
- **LLM_COORDINATOR HSTC.md**: Current implementation details of the LLM coordinator

## Project Overview

This plan outlines the comprehensive overhaul of the LLM and LLM coordinator components using LangChain and LangGraph. The key requirements include:

1. Complete replacement of existing code with no backward compatibility
2. Exclusive support for streaming responses using AsyncIO
3. Focused support for Amazon Bedrock using only the Converse API
4. Implementation of LLM named configurations
5. Dynamic tool registration/unregistration system
6. Prompt management facilities for doc/llm/prompts
7. Strict "raise on error" approach with no fallbacks

The implementation will be split into 12 focused phases to ensure manageable implementation steps.

## Implementation Phases

### Phase 1: Project Setup & Dependencies
- Create directory structure
- Update requirements.txt
- Delete legacy files

### Phase 2: Base Interfaces
- Define core exceptions
- Create abstract base classes
- Establish interfaces

### Phase 3: AsyncIO Streaming Foundation
- Implement streaming interfaces
- Create chunk-based streaming
- Build stream emulation

### Phase 4: Prompt Management
- Create prompt loading mechanism
- Implement template substitution
- Build caching system

### Phase 5: Tool Registration System
- Implement dynamic tool registry
- Create schema validation
- Develop registration mechanisms

### Phase 6: LLM Configuration Registry
- Design configuration system
- Implement configuration validation
- Create management interface

### Phase 7: Bedrock Base Implementation
- Create core Bedrock client
- Implement authentication
- Build formatting utilities

### Phase 8: Claude Model Implementation
- Create Claude-specific client
- Implement reasoning support
- Build parameter handling

### Phase 9: Nova Model Implementation
- Create Nova-specific client
- Build parameter handling
- Implement response processing

### Phase 10: LangChain Integration
- Create LangChain adapters
- Implement LLM wrappers
- Build chain factories

### Phase 11: LangGraph Integration
- Implement state management
- Create graph builder
- Build node definitions

### Phase 12: LLM Coordinator Implementation
- Create agent manager
- Implement DBP general query tool
- Build MCP tool integration

## Implementation Plan Files

The complete implementation is documented in the following files:

1. [plan_overview.md](./plan_overview.md) - This file, containing the high-level overview
2. [plan_progress.md](./plan_progress.md) - Tracks implementation progress
3. [plan_phase1.md](./plan_phase1.md) - Project Setup & Dependencies
4. [plan_phase2.md](./plan_phase2.md) - Base Interfaces
5. [plan_phase3.md](./plan_phase3.md) - AsyncIO Streaming Foundation
6. [plan_phase4.md](./plan_phase4.md) - Prompt Management
7. [plan_phase5.md](./plan_phase5.md) - Tool Registration System
8. [plan_phase6.md](./plan_phase6.md) - LLM Configuration Registry
9. [plan_phase7.md](./plan_phase7.md) - Bedrock Base Implementation
10. [plan_phase8.md](./plan_phase8.md) - Claude Model Implementation
11. [plan_phase9.md](./plan_phase9.md) - Nova Model Implementation
12. [plan_phase10.md](./plan_phase10.md) - LangChain Integration
13. [plan_phase11.md](./plan_phase11.md) - LangGraph Integration
14. [plan_phase12.md](./plan_phase12.md) - LLM Coordinator Implementation

## Key Design Decisions

1. **Streaming-Only Interface**: All LLM interactions will use a streaming interface, with non-streaming models emulated through chunking.

2. **Exclusive Use of Bedrock Converse API**: All Bedrock interactions will use only the Converse API, avoiding other API endpoints.

3. **Raise on Error**: Following the project's strict error handling policy, all components will throw exceptions with no fallbacks.

4. **Chunk-Based Streaming**: Streaming will be implemented at the chunk level (not token level) for consistent interfaces.

5. **Dynamic Tool Registration**: Tools will be dynamically registrable and unregistrable at runtime through a central registry.

6. **LangGraph for Workflows**: Agent workflows will be implemented using LangGraph's StateGraph for flexible agent patterns.

## Directory Structure

```
src/dbp/
├── llm/
│   ├── __init__.py              # Export core components
│   ├── common/
│   │   ├── __init__.py          # Export common utilities
│   │   ├── base.py              # Abstract interfaces
│   │   ├── streaming.py         # AsyncIO streaming support
│   │   ├── prompt_manager.py    # Prompt template management
│   │   ├── tool_registry.py     # Dynamic tool registration
│   │   ├── config_registry.py   # LLM configurations
│   │   └── exceptions.py        # Error types
│   ├── bedrock/
│   │   ├── __init__.py          # Export Bedrock components
│   │   ├── base.py              # Bedrock foundation
│   │   ├── converse_client.py   # Converse API implementation ONLY
│   │   └── models/
│   │       ├── __init__.py      # Export model clients
│   │       ├── claude3.py       # Claude implementation with reasoning
│   │       └── nova.py          # Nova implementation
│   └── manager.py               # Central LLM manager
├── llm_coordinator/
    ├── __init__.py              # Export coordinator components
    ├── component.py             # MCP component implementation
    ├── graph_builder.py         # LangGraph construction
    ├── state_manager.py         # Graph state management
    ├── agent_manager.py         # Agent workflow management
    └── tools/
        ├── __init__.py          # Export tool implementations
        ├── base.py              # Base tool class
        └── dbp_general_query.py # General query MCP tool
```

## Key Technical Excerpts

### Streaming Interface (from LLM_COORDINATION.md)

The LLM coordination architecture includes the following data models:

```python
CoordinatorRequest {
  requestId: UUID           // Unique identifier for the request
  query: String | Object    // User query (natural language or structured)
  context: {                // Context information for processing
    projectFiles: String[], // List of all files in the project
    currentDateTime: String, // Current date and time
    businessContext: String  // Content from PR-FAQ.md and WORKING_BACKWARDS.md
  }
  parameters: Object        // Additional parameters for request processing
  maxExecutionTimeMs: Integer // Maximum execution time for the entire request
  maxCostBudget: Number     // Maximum allowed cost for the entire request
}
```

These models will be translated to LangChain/LangGraph structures while maintaining their core functionality.

### Error Handling Policy (from DESIGN.md)

The project implements strict error handling with no fallbacks:

```
2. "Throw on Error" Error Handling Strategy

- Implement "throw on error" behavior for ALL error conditions without exception
- Never silently catch errors - always include both error logging and error re-throwing
- Do not return null, undefined, or empty objects as a response to error conditions
- Construct descriptive error messages that specify: 1) the exact component that failed and 2) the precise reason for the failure
- Never implement fallback mechanisms or graceful degradation behavior without explicit user approval
```

This policy will be strictly adhered to in the new implementation.
