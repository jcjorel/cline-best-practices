# MCP Strict Compliance Implementation Plan

## Overview

This implementation plan outlines the specific steps required to modify the current MCP implementation to ensure strict compliance with the documented Anthropic MCP specification. The plan focuses on removing extensions and simplifying the streaming implementation to adhere only to features explicitly defined in the specification.

## Phase 1: Core Streaming Simplification

### 1. Simplify the Streaming Module
**File:** `src/dbp/mcp_server/mcp/streaming.py`

**Changes:**
- Remove `StreamFormat` enum entirely
- Replace `StreamChunk` model with a simpler model that matches JSON-RPC 2.0 structure
- Remove SSE-specific message formatting and content types
- Remove binary streaming support
- Simplify the `MCPStreamingResponse` class to focus only on basic JSON-RPC streaming

**Implementation:**

```python
# Modified MCPStreamingResponse without format options
class MCPStreamingResponse:
    """
    [Class intent]
    Handles the creation and management of streaming responses for MCP tools.
    
    [Design principles]
    - Asynchronous streaming with standard JSON-RPC 2.0 format
    - Error handling during streaming
    - Strict compliance with MCP specification
    
    [Implementation details]
    - Uses AsyncGenerator for efficient streaming
    - Each chunk is a complete JSON-RPC 2.0 response
    """
    
    def __init__(self, logger_override: Optional[logging.Logger] = None):
        self._next_chunk_id = 0
        self._started = False
        self._completed = False
        self._error = None
        self.logger = logger_override or logger.getChild("MCPStreamingResponse")
        
    async def stream(
        self,
        generator: AsyncIterator[Any],
        request_id: Any,
        cancellation_token: Optional[MCPCancellationToken] = None
    ) -> AsyncGenerator[str, None]:
        """
        [Function intent]
        Streams data from an async generator with standard JSON-RPC 2.0 format.
        
        [Design principles]
        - Simple JSON-RPC 2.0 compliant output for each chunk
        - Support for cancellation
        - Proper error handling
        
        [Implementation details]
        - Each chunk is a complete JSON-RPC 2.0 response
        - Supports cancellation checks
        
        Args:
            generator: Async iterator producing the data to stream
            request_id: JSON-RPC request ID to include in each chunk
            cancellation_token: Optional token for checking cancellation
            
        Yields:
            JSON-RPC 2.0 formatted chunks as strings
        """
        self._started = True
        
        try:
            # Stream all chunks
            async for data in generator:
                # Check for cancellation
                if cancellation_token and cancellation_token.is_cancelled():
                    break
                
                # Format as JSON-RPC 2.0 response
                chunk = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": data
                }
                yield json.dumps(chunk) + "\n"
                self._next_chunk_id += 1
                
            self._completed = True
            
        except Exception as e:
            self.logger.error(f"Error during streaming: {str(e)}", exc_info=True)
            self._error = e
            
            # Send error message
            error = MCPError(MCPErrorCode.INTERNAL_ERROR, f"Stream error: {str(e)}")
            error_json = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": error.to_json_rpc()["error"]
            }
            yield json.dumps(error_json) + "\n"
```

- Remove the `create_streaming_generator` function entirely

### 2. Update Streaming Tool Implementation
**File:** `src/dbp/mcp_server/mcp/streaming_tool.py`

**Changes:**
- Remove stream format parameters and references
- Simplify the `handle_streaming_request` method to use only basic JSON-RPC 2.0
- Update content type handling to use only application/x-ndjson

**Implementation:**

```python
async def handle_streaming_request(
    self,
    request: Dict[str, Any],
    session: Optional[Any] = None
) -> AsyncGenerator[str, None]:
    """
    [Function intent]
    Handles a JSON-RPC request for this tool with streaming response.
    
    [Design principles]
    - Standard JSON-RPC 2.0 protocol
    - Handles validation and error formatting
    
    [Implementation details]
    - Validates request format and parameters
    - Sets up cancellation and progress tracking
    - Calls execute_streaming and streams results
    - Handles errors during streaming
    
    Args:
        request: A dictionary containing the JSON-RPC request
        session: Optional session object from capability negotiation
        
    Yields:
        Formatted JSON-RPC 2.0 responses as strings
    """
    # Default response ID in case request is malformed
    request_id = None
    
    try:
        # Validate JSON-RPC request
        if not isinstance(request, dict):
            raise MCPError(MCPErrorCode.INVALID_REQUEST, "Request must be a JSON object")
            
        # Check JSON-RPC version
        if request.get("jsonrpc") != "2.0":
            raise MCPError(MCPErrorCode.INVALID_REQUEST, "Invalid JSON-RPC version, must be 2.0")
            
        # Get request ID
        request_id = request.get("id")
        
        # Validate method
        method = request.get("method")
        if not method:
            raise MCPError(MCPErrorCode.INVALID_REQUEST, "Method is required")
            
        if method != "executeTool":
            raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Method '{method}' not found")
            
        # Get parameters
        params = request.get("params", {})
        if not isinstance(params, dict):
            raise MCPError(MCPErrorCode.INVALID_PARAMS, "Params must be an object")
            
        # Set up cancellation and progress reporting based on session capabilities
        cancellation_token = None
        progress_reporter = None
        
        # Create objects only if we don't have a session or if session has the capability
        if session is None or session.has_capability("cancellation"):
            cancellation_token = MCPCancellationToken()
            
        if session is None or session.has_capability("progress_tracking"):
            progress_reporter = MCPProgressReporter()
        
        # Extract auth context if provided
        auth_context = params.get("auth_context")
        
        # Validate parameters against schema
        try:
            input_model = self.input_schema.parse_obj(params)
        except Exception as e:
            raise MCPError(MCPErrorCode.INVALID_PARAMS, f"Invalid parameters: {str(e)}")
        
        # Create streaming response handler
        response_handler = MCPStreamingResponse()
        
        # Execute the streaming tool
        try:
            generator = self.execute_streaming(
                input_model,
                cancellation_token=cancellation_token,
                progress_reporter=progress_reporter,
                auth_context=auth_context
            )
            
            # Stream results through response handler
            async for chunk in response_handler.stream(generator, request_id, cancellation_token):
                yield chunk
                
        except MCPError as e:
            # Tool raised an MCP error
            self.logger.error(f"MCP error in streaming tool {self.name}: {str(e)}")
            error_response = e.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            yield f"{error_response}\n"
            
        except Exception as e:
            # Unexpected error during execution
            self.logger.error(f"Error executing streaming tool {self.name}: {str(e)}", exc_info=True)
            error = MCPError(
                MCPErrorCode.TOOL_EXECUTION_ERROR, 
                f"Tool execution error: {str(e)}"
            )
            error_response = error.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            yield f"{error_response}\n"
            
    except MCPError as e:
        # JSON-RPC protocol error
        self.logger.error(f"Protocol error in streaming tool {self.name}: {str(e)}")
        error_response = e.to_json_rpc()
        error_response["jsonrpc"] = "2.0"
        error_response["id"] = request_id
        yield f"{error_response}\n"
        
    except Exception as e:
        # Unexpected error during request handling
        self.logger.error(f"Internal error in streaming tool {self.name}: {str(e)}", exc_info=True)
        error = MCPError(
            MCPErrorCode.INTERNAL_ERROR,
            f"Internal error: {str(e)}"
        )
        error_response = error.to_json_rpc()
        error_response["jsonrpc"] = "2.0"
        error_response["id"] = request_id
        yield f"{error_response}\n"
```

- Remove stream format parameter from `MCPStreamingTool.execute_streaming` method

### 3. Update MCPStreamingTool Class

```python
class MCPStreamingTool(MCPTool):
    """
    [Class intent]
    Abstract base class for MCP tools that support streaming responses.
    Extends the standard MCPTool class with streaming capabilities.
    
    [Design principles]
    - Maintains compatibility with base MCPTool interface
    - Adds streaming-specific methods
    - Follows strict MCP specification compliance
    
    [Implementation details]
    - Uses asyncio for non-blocking streaming
    - Maintains JSON-RPC 2.0 compatibility for each chunk
    """
    
    def __init__(self, name: str, description: str, logger_override: Optional[logging.Logger] = None):
        """
        [Class method intent]
        Initializes a streaming-capable MCP tool.
        
        [Design principles]
        - Extends MCPTool initialization
        - Maintains backward compatibility
        
        [Implementation details]
        - Calls parent constructor with same parameters
        
        Args:
            name: The unique identifier name for this tool
            description: A human-readable description of the tool's purpose
            logger_override: Optional logger instance
        """
        super().__init__(name, description, logger_override)
        self._supports_streaming = True
        
    @property
    def supports_streaming(self) -> bool:
        """Whether this tool supports streaming responses."""
        return self._supports_streaming
    
    @abc.abstractmethod
    async def execute_streaming(
        self,
        data: BaseModel,
        cancellation_token: Optional[MCPCancellationToken] = None,
        progress_reporter: Optional[MCPProgressReporter] = None,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Any, None]:
        """
        [Function intent]
        Executes the tool's logic and returns an async generator for streaming results.
        This is the core method that streaming tools must implement.
        
        [Design principles]
        - Similar interface to execute() but returns an async generator
        - Supports cancellation and progress reporting
        - Abstract method to be implemented by concrete tool classes
        
        [Implementation details]
        - Must be implemented by concrete streaming tool classes
        - Should yield data that can be serialized to JSON
        - Should check cancellation between chunks
        
        Args:
            data: A Pydantic model containing the validated input parameters
            cancellation_token: Optional token to check for cancellation
            progress_reporter: Optional reporter to update progress
            auth_context: Optional authentication context
            
        Yields:
            Data chunks for streaming to the client
            
        Raises:
            MCPError: For tool-specific execution errors
            Exception: Other exceptions will be converted to MCPError
        """
        pass
```

### 4. Update Module Exports
**File:** `src/dbp/mcp_server/mcp/__init__.py`

**Changes:**
- Remove StreamFormat export
- Update other exports to match simplified implementation

```python
# Re-export all MCP protocol classes for external use
from .error import MCPErrorCode, MCPError
from .progress import MCPProgressReporter
from .cancellation import MCPCancellationToken
from .tool import MCPTool
from .resource import MCPResource
from .streaming import MCPStreamingResponse
from .streaming_tool import MCPStreamingTool, StreamingResponse

__all__ = [
    'MCPErrorCode',
    'MCPError',
    'MCPProgressReporter',
    'MCPCancellationToken',
    'MCPTool',
    'MCPResource',
    'MCPStreamingResponse',
    'MCPStreamingTool',
    'StreamingResponse'
]
```

## Phase 2: Update Example Implementation

### 1. Update Example Streaming Tool
**File:** `src/dbp/mcp_server/examples/sample_streaming_tool.py`

**Changes:**
- Remove stream format parameter from execute_streaming method
- Remove format-specific handling
- Update model to reflect simplified implementation

### 2. Update Example Client
**File:** `src/dbp/mcp_server/examples/streaming_client_example.py`

**Changes:**
- Remove stream format selection options
- Update client to handle only basic JSON-RPC streaming

## Phase 3: Testing Strategy

1. **Unit Testing**
   - Update existing unit tests for the simplified streaming implementation
   - Remove tests for format-specific behavior
   - Add tests to verify JSON-RPC 2.0 compatibility

2. **Integration Testing**
   - Test tool execution with and without streaming
   - Verify streaming chunks are valid JSON-RPC 2.0 messages
   - Test error handling during streaming

3. **Compatibility Testing**
   - Ensure the simplified streaming works with existing tools
   - Verify that tools using the old API can be updated easily

## Phase 4: Backward Compatibility Notes

The proposed changes will break backward compatibility for any code that:
1. Uses specific streaming formats (EVENT_STREAM, BINARY)
2. Relies on enhanced chunk metadata
3. Expects specific SSE event types

To manage this:

1. **Documentation**: Clearly document the changes as compliance-driven
2. **Version Bump**: Increase the major version number to signal breaking changes
3. **Migration Guide**: Provide guidance for updating code that used the extended features

## Implementation Timeline

1. **Phase 1 (Core Changes)**: 2-3 days
   - Update streaming modules
   - Update tool implementation
   - Update module exports

2. **Phase 2 (Examples)**: 1 day
   - Update sample tool
   - Update client example

3. **Phase 3 (Testing)**: 2 days
   - Adapt/create unit tests
   - Run integration tests
   - Fix any issues discovered

4. **Phase 4 (Documentation)**: 1 day
   - Update API documentation
   - Create migration guide

**Total Estimated Time**: 6-7 days

## Conclusion

This plan provides a comprehensive approach to simplifying the MCP streaming implementation to strictly adhere to the documented MCP specification. The resulting implementation will support basic streaming while removing extensions that go beyond the specification, ensuring full compliance at the cost of reduced functionality.
