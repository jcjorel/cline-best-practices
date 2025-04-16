# Phase 1: API Extension Plan

## Overview

This phase focuses on extending the `MCPClientAPI` class to support the new general query functionality. We need to add a method that communicates with the coordinator LLM through the `dbp_general_query` tool.

## File to Modify

`src/dbp_cli/api.py`

## Implementation Details

### 1. Add general_query Method

We will add a new method to the `MCPClientAPI` class that handles sending general queries to the server:

```python
def general_query(self, query_text: str, max_tokens: Optional[int] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    Calls the 'dbp_general_query' tool with a plain text query.
    
    Args:
        query_text: The plain text query to send to the coordinator LLM
        max_tokens: Optional maximum number of tokens for the response
        timeout: Optional timeout in seconds for the query processing
        
    Returns:
        Dictionary containing the query results
        
    Raises:
        ConnectionError: If connection to the server fails
        AuthenticationError: If the server returns an authentication error
        APIError: For server-side errors including LLM-specific issues
        ClientError: For unexpected client-side issues
        TimeoutError: If the request times out
    """
    tool_data = {"query": query_text}
    
    # Add optional parameters if provided
    if max_tokens is not None:
        tool_data["max_tokens"] = max_tokens
    if timeout is not None:
        tool_data["timeout"] = timeout
    
    self.logger.info(f"Sending general query: {query_text}")
    return self.call_tool("dbp_general_query", tool_data)
```

### 2. Enhanced Error Handling for LLM Issues

We should update `_make_request` to include handling for LLM-specific error codes that might be returned by the `dbp_general_query` tool. This requires adding new error mapping in the error handling section:

```python
# Add to existing error handling in _make_request
if code == "AUTHENTICATION_FAILED":
    raise AuthenticationError(message)
elif code == "AUTHORIZATION_FAILED":
    raise AuthorizationError(message)
elif code == "TOKEN_LIMIT_EXCEEDED":
    raise APIError(f"Token limit exceeded: {message}", code=code)
elif code == "LLM_PROCESSING_ERROR":
    raise APIError(f"LLM processing error: {message}", code=code)
elif code == "INVALID_QUERY":
    raise APIError(f"Invalid query: {message}", code=code)
else:
    raise APIError(message, code=code)
```

### 3. Implementation Considerations

1. **Parameter Validation**: The method will pass parameters directly to the server, allowing server-side validation and default values to be applied.

2. **Response Format**: The response from the server will be a dictionary with a structure determined by the LLM coordinator. The method will return this structure directly without modification.

3. **Timeout Handling**: We'll allow an optional timeout parameter, but rely on the existing timeout handling in `_make_request`.

4. **Documentation**: The method will be fully documented with docstrings following the same pattern as other methods in the class.

5. **Logging**: Appropriate logging statements will be added to facilitate debugging.

### 4. Testing Approach

While detailed testing will be covered in Phase 4, here are the key test scenarios for the API extension:

1. Basic query functionality with simple text
2. Query with max_tokens parameter
3. Query with timeout parameter
4. Query with both optional parameters
5. Error handling for various error scenarios:
   - Token limit exceeded
   - LLM processing error
   - Invalid query format
   - Network timeout
   - Server offline

## Implementation Plan

1. Add the `general_query` method to `MCPClientAPI`
2. Update error handling in `_make_request` if necessary
3. Verify integration with existing code
4. Add basic logging
5. Document the new method with comprehensive docstrings

After completing this phase, update the progress tracking in `plan_progress.md` before moving on to Phase 2.
