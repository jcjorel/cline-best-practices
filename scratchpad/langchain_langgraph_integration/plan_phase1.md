# Phase 1: Project Setup & Dependencies

This phase establishes the foundation for the LangChain/LangGraph integration by setting up the directory structure, updating dependencies, and removing legacy files that are no longer needed.

## Objectives

1. Create the necessary directory structure for the new implementation
2. Update requirements.txt with LangChain/LangGraph dependencies
3. Delete legacy files that will be replaced by the new implementation

## Directory Structure Creation

### LLM Module Structure

Create the following directory structure:

```
src/dbp/llm/
├── __init__.py                # Main module exports
├── common/
│   ├── __init__.py            # Common utilities exports
│   ├── base.py                # Abstract interfaces
│   ├── streaming.py           # AsyncIO streaming support
│   ├── prompt_manager.py      # Prompt template management
│   ├── tool_registry.py       # Dynamic tool registration
│   ├── config_registry.py     # LLM configurations
│   └── exceptions.py          # Error types
├── bedrock/
│   ├── __init__.py            # Bedrock module exports
│   ├── base.py                # Bedrock foundation
│   ├── converse_client.py     # Converse API implementation
│   └── models/
│       ├── __init__.py        # Models module exports
│       ├── claude3.py         # Claude implementation
│       └── nova.py            # Nova implementation
└── manager.py                 # Central LLM manager
```

### LLM Coordinator Module Structure

Create the following directory structure:

```
src/dbp/llm_coordinator/
├── __init__.py                # Main module exports
├── component.py               # MCP component implementation
├── graph_builder.py           # LangGraph construction
├── state_manager.py           # Graph state management
├── agent_manager.py           # Agent workflow management
└── tools/
    ├── __init__.py            # Tools module exports
    ├── base.py                # Base tool class
    └── dbp_general_query.py   # General query MCP tool
```

## Requirements Update

Add the following dependencies to requirements.txt:

```
# LangChain/LangGraph dependencies
langchain>=0.1.0                  # Core LangChain library
langchain-core>=0.1.0             # LangChain core utilities
langchain_community>=0.0.13       # LangChain community integrations
langchain-experimental>=0.0.34    # Experimental LangChain features
langgraph>=0.0.15                 # LangGraph workflow library
boto3>=1.28.0                     # AWS SDK for Bedrock access
pydantic>=2.4.0                   # Data validation for LangChain
asyncio>=3.4.3                    # AsyncIO for streaming support
aiohttp>=3.8.5                    # Async HTTP client for streaming
```

## Legacy Files to Delete

The following files are no longer needed and should be deleted:

### LLM Module Files

```
src/dbp/llm/__init__.py               # Will be replaced with a new version
src/dbp/llm/bedrock_base.py           # Replaced by llm/bedrock/base.py
src/dbp/llm/bedrock_client_common.py  # Replaced by llm/bedrock/converse_client.py
src/dbp/llm/bedrock_manager.py        # Replaced by llm/manager.py
src/dbp/llm/claude3_7_client.py       # Replaced by llm/bedrock/models/claude3.py
src/dbp/llm/nova_lite_client.py       # Replaced by llm/bedrock/models/nova.py
src/dbp/llm/prompt_manager.py         # Replaced by llm/common/prompt_manager.py
```

### LLM Coordinator Module Files

```
src/dbp/llm_coordinator/__init__.py         # Will be replaced with a new version
src/dbp/llm_coordinator/component.py        # Will be replaced with a new version
src/dbp/llm_coordinator/coordinator_llm.py  # Functionality moved to agent_manager.py
src/dbp/llm_coordinator/data_models.py      # Models integrated into state_manager.py
src/dbp/llm_coordinator/general_query_tool.py # Replaced by tools/dbp_general_query.py
src/dbp/llm_coordinator/job_manager.py      # Functionality in agent_manager.py
src/dbp/llm_coordinator/request_handler.py  # Functionality in component.py
src/dbp/llm_coordinator/response_formatter.py # Functionality in component.py
src/dbp/llm_coordinator/tool_registry.py    # Replaced by llm/common/tool_registry.py
```

## Implementation Steps

1. **Create Directory Structure**
   - Create all necessary directories as outlined above
   - Create empty placeholder files for all modules

2. **Update Requirements**
   - Add LangChain and LangGraph dependencies to requirements.txt
   - Ensure compatibility with existing dependencies

3. **Delete Legacy Files**
   - Verify that legacy files are not imported elsewhere
   - Delete or rename legacy files to avoid conflicts

## Notes

- The new directory structure follows best practices for Python module organization
- Empty files will be created as placeholders and populated in subsequent phases
- Legacy files will only be deleted once all their functionality is reimplemented

## Next Steps

After completing this phase:
1. Proceed to Phase 2 (Base Interfaces)
2. Create the common exceptions and base interfaces
3. Establish fundamental abstract classes needed for the implementation
