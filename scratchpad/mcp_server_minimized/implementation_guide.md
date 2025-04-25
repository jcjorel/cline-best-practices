# MCP Server Dependency Minimization - Implementation Guide

This guide provides step-by-step instructions for implementing a minimized version of the MCP server component that can operate with only the config_manager dependency. This approach enables progressive component integration testing and resolves difficulties in debugging the whole codebase when all components are integrated together.

## Overview

The minimized MCP server:
- Maintains the same interface as the original component
- Returns standardized error responses for all tool and resource requests
- Clearly logs operation in "standalone mode"
- Depends only on the core framework and config_manager
- Enables gradual re-integration of other components for testing

## Files to Replace/Modify

1. **`src/dbp/mcp_server/adapter.py`**: Replace with `modified_adapter.py`
   - Implements mock component instances for all system components
   - Maintains connection to config_manager
   - Provides clear logging about standalone mode operation

2. **`src/dbp/mcp_server/tools.py`**: Replace with `modified_tools.py`
   - Tools maintain the same interface but return standardized error responses
   - Preserves input/output schema definitions
   - Includes clear documentation about standalone mode operation

3. **`src/dbp/mcp_server/component.py`**: Replace with `modified_component.py`
   - Removes dependencies on all system components except config_manager
   - Implements initialization process that avoids accessing unavailable components
   - Maintains directory creation functionality
   - Provides clear logging about standalone mode operation

## Implementation Steps

### 1. Create Backup of Original Files

```bash
mkdir -p src/dbp/mcp_server/original_backup
cp src/dbp/mcp_server/adapter.py src/dbp/mcp_server/original_backup/
cp src/dbp/mcp_server/tools.py src/dbp/mcp_server/original_backup/
cp src/dbp/mcp_server/component.py src/dbp/mcp_server/original_backup/
```

### 2. Replace Files with Minimized Versions

```bash
cp scratchpad/mcp_server_minimized/modified_adapter.py src/dbp/mcp_server/adapter.py
cp scratchpad/mcp_server_minimized/modified_tools.py src/dbp/mcp_server/tools.py
cp scratchpad/mcp_server_minimized/modified_component.py src/dbp/mcp_server/component.py
```

### 3. Optionally Modify Resources File

If you're using resources, you may need to create a minimized version of `resources.py` as well, following a similar approach to the tools file. The implementation details would be:

1. Maintain the same interface as the original
2. Return standardized error responses
3. Include clear logging about standalone mode operation

### 4. Update Imports (if needed)

If there are other files in the MCP server module that directly import from system components, you may need to update them to handle missing imports gracefully:

```python
try:
    # Try to import the actual component
    from ..some_component.component import SomeComponent
except ImportError:
    # Create a mock implementation if import fails
    class SomeComponent:
        """Mock implementation for standalone mode"""
        pass
```

## Testing the Implementation

### 1. Verify Server Initialization

```bash
# Use a script that initializes the MCP server component
python -m src.dbp.mcp_server.__main__ --standalone-mode
```

Look for logs indicating "STANDALONE MODE" operation and successful initialization.

### 2. Test Server API Endpoints

Access the server endpoints and verify they return standardized error responses:

```bash
curl -X POST "http://localhost:8000/mcp/tool/dbp_general_query" \
     -H "Content-Type: application/json" \
     -d '{"query": "Test query"}'
```

Expected response:
```json
{
  "result": {
    "status": "error",
    "error_code": "STANDALONE_MODE",
    "message": "Tool 'dbp_general_query' is running in standalone mode - actual functionality is unavailable",
    "details": "The MCP server is running with minimal dependencies for progressive integration testing."
  },
  "metadata": {
    "execution_path": "standalone_mode",
    "execution_time_ms": 105,
    "standalone": true,
    "error_details": {
      "type": "StandaloneOperationError",
      "message": "Component dependencies are not available in standalone mode"
    }
  }
}
```

## Progressive Component Integration

After successfully operating the minimized MCP server, you can progressively integrate other components:

1. Start with the simplest component dependencies
2. Modify the adapter to use actual components instead of mock ones
3. Update the component initialization to include these dependencies
4. Test the server with each newly integrated component

## Reverting to Full Integration

When ready to return to full component integration:

```bash
# Restore original files
cp src/dbp/mcp_server/original_backup/adapter.py src/dbp/mcp_server/
cp src/dbp/mcp_server/original_backup/tools.py src/dbp/mcp_server/
cp src/dbp/mcp_server/original_backup/component.py src/dbp/mcp_server/
```

## Implementation Notes

1. **Error Responses**: All tool and resource responses include detailed error information indicating standalone mode operation.

2. **Logging**: Extensive logging has been added with the prefix "[STANDALONE MODE]" to clearly indicate when the server is operating with minimal dependencies.

3. **Config Manager**: The integration with config_manager is preserved to ensure the server can still access configuration values.

4. **Directory Creation**: The code still creates required directories based on configuration values.

5. **Server Instance**: The web server is still initialized, but returns standardized error responses from tools and resources.

## Troubleshooting

1. **Import Errors**: If you encounter import errors, check if there are additional files that need updating to handle missing components.

2. **Configuration Access**: Ensure the config_manager component is properly initialized before the MCP server component.

3. **Logging Configuration**: Make sure logging is properly configured to see the standalone mode messages.

4. **Mock Component Issues**: If mock components are not behaving as expected, check their implementation in `adapter.py`.
