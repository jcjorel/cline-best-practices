# MCP Server Dependency Minimization Plan

## Overview

The goal is to modify the MCP server component to minimize its dependencies while maintaining integration with the config_manager. This will allow for progressive integration testing of components, starting with a partially functional MCP server that serves MCP requests with error responses rather than trying to access unavailable components.

## Current Dependencies

The MCP server component currently depends on:

1. **Core Framework**:
   - Component and InitializationContext from core/component.py
   - fs_utils for directory creation
   - config_manager (to be preserved)

2. **System Components**:
   - consistency_analysis
   - recommendation_generator
   - doc_relationships
   - llm_coordinator
   - metadata_extraction
   - memory_cache

3. **Internal Modules**:
   - adapter.py (SystemComponentAdapter)
   - auth.py (AuthenticationProvider)
   - error_handler.py (ErrorHandler)
   - registry.py (ToolRegistry, ResourceProvider)
   - server.py (MCPServer)
   - tools.py (GeneralQueryTool, CommitMessageTool, etc.)
   - resources.py (various resource implementations)

## Minimization Strategy

1. **Keep Core Integration**:
   - Maintain integration with Component, InitializationContext from core/component.py
   - Keep config_manager dependency
   - Preserve fs_utils for directory creation

2. **Modify SystemComponentAdapter**:
   - Update to return mock components or null objects instead of trying to access actual system components
   - Comment out actual component access code
   - Add explanatory logs indicating this is a "standalone mode" for progressive testing

3. **Simplify Tool Implementations**:
   - Modify tools to return standardized error responses
   - Remove logic that attempts to access other system components
   - Add documentation explaining the expected behavior in full integration mode

4. **Update Internal Dependencies**:
   - Keep internal module interfaces intact
   - Simplify implementations to avoid external dependencies

5. **Add Diagnostic Capabilities**:
   - Add logging to clearly indicate when the MCP server is running in minimized dependency mode
   - Provide diagnostic endpoints to verify server operation

## Implementation Phases

### Phase 1: Create Modified Component.py

Create a modified version of the component.py file that:
- Comments out references to other system components
- Maintains config_manager dependency
- Returns error responses for tools

### Phase 2: Update SystemComponentAdapter

Modify the adapter to:
- Return mock objects instead of actual component instances
- Log clearly that it's operating in reduced dependency mode

### Phase 3: Simplify Tools and Resources

Update tools and resources to:
- Return standardized error responses
- Not attempt to access unavailable components

### Phase 4: Update Server Configuration

Ensure server can start and run with minimal configuration:
- Maintain proper initialization
- Advertise the same tools/resources but with limited functionality

## Testing Strategy

1. Verify the MCP server can initialize with only config_manager
2. Test that tools return proper error responses
3. Confirm server responds to health checks correctly
4. Validate that API endpoints function and return expected error responses

## Future Integration Path

Once the minimized MCP server is working:

1. Progressively re-enable integration with one component at a time
2. Test each integration step thoroughly
3. Complete full integration once all components are validated

## Files to Modify

1. `src/dbp/mcp_server/component.py`
2. `src/dbp/mcp_server/adapter.py`
3. `src/dbp/mcp_server/tools.py`
4. `src/dbp/mcp_server/resources.py` (if needed)
