###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements streaming support for the MCP client, enabling handling of
# incremental data delivery from MCP servers according to the Model Context
# Protocol specification.
###############################################################################
# [Source file design principles]
# - Provides both synchronous and asynchronous streaming interfaces
# - Handles JSON-RPC 2.0 streaming format according to MCP specification
# - Supports proper error handling during streaming
# - Compatible with both streaming tools and resources
# - Enables incremental processing of streamed data
###############################################################################
# [Source file constraints]
# - Requires requests for HTTP streaming
# - Must handle partial JSON data and streaming errors
# - Should support cancellation during streaming
# - Should maintain backward compatibility with synchronous operations
###############################################################################
# [Dependencies]
# system:requests
# system:json
# system:typing
# system:logging
# system:threading
# codebase:src/dbp_cli/mcp/error.py
# codebase:src/dbp_cli/mcp/client.py
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:16:00Z : Initial implementation of MCP streaming support by CodeAssistant
# * Created MCPStreamingClient for handling streamed responses
# * Implemented streaming response processing
###############################################################################

import json
import logging
import threading
from typing import Dict, Any, Optional, Iterator, Generator, Callable, Union
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logging.getLogger(__name__).error(
        "The 'requests' library is required for MCPStreamingClient. "
        "Please install it (`pip install requests`)."
    )

from .error import MCPError, MCPErrorCode


@dataclass
class MCPStreamingResponse:
    """
    [Class intent]
    Represents a streaming response from an MCP server.
    Provides utility methods to access and process the stream.
    
    [Design principles]
    - Clean interface for consuming streaming data
    - Consistent error handling
    - Support for cancellation
    
    [Implementation details]
    - Wraps a requests Response object with streaming content
    - Provides methods to iterate over JSON-RPC chunks
    - Handles errors in the stream
    """
    
    response: requests.Response
    request_id: Optional[str] = None
    is_cancelled: bool = False
    
    def __post_init__(self):
        """Initialize the iterator for the streaming response."""
        self._iterator = self.response.iter_lines()
    
    def cancel(self):
        """
        [Function intent]
        Cancels the streaming response.
        
        [Design principles]
        - Simple cancellation mechanism
        
        [Implementation details]
        - Sets the is_cancelled flag
        - Closes the underlying response if possible
        """
        self.is_cancelled = True
        if hasattr(self.response, "close"):
            self.response.close()
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """
        [Function intent]
        Makes the streaming response iterable, yielding parsed JSON-RPC chunks.
        
        [Design principles]
        - Standard iterator protocol implementation
        - Handles JSON parsing and error checking
        
        [Implementation details]
        - Yields parsed JSON-RPC messages
        - Handles errors in the stream
        
        Returns:
            Iterator over parsed JSON-RPC messages
        
        Raises:
            MCPError: For protocol errors in the stream
        """
        return self.iter_chunks()
    
    def iter_chunks(self) -> Iterator[Dict[str, Any]]:
        """
        [Function intent]
        Iterates over JSON-RPC chunks in the streaming response.
        
        [Design principles]
        - Clean iterator over parsed chunks
        - Handles protocol and parsing errors
        - Supports cancellation
        
        [Implementation details]
        - Iterates over response lines
        - Parses each line as JSON-RPC message
        - Validates message structure
        - Handles errors in the stream
        
        Returns:
            Iterator over parsed JSON-RPC data chunks
            
        Raises:
            MCPError: For protocol errors in the stream
        """
        try:
            for line in self._iterator:
                if self.is_cancelled:
                    break
                
                if not line:
                    continue
                    
                # Parse the chunk as JSON
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as e:
                    raise MCPError(
                        MCPErrorCode.PARSE_ERROR, 
                        f"Failed to parse JSON chunk: {e}"
                    )
                
                # Check for valid JSON-RPC format
                if not isinstance(chunk, dict) or "jsonrpc" not in chunk:
                    raise MCPError(
                        MCPErrorCode.PARSE_ERROR, 
                        "Invalid JSON-RPC chunk format"
                    )
                    
                # Check for matching request ID if provided
                if self.request_id and chunk.get("id") != self.request_id:
                    raise MCPError(
                        MCPErrorCode.PARSE_ERROR, 
                        f"Mismatched request ID in chunk: {chunk.get('id')}"
                    )
                
                # Check for error in chunk
                if "error" in chunk:
                    error_obj = chunk["error"]
                    code = error_obj.get("code", MCPErrorCode.INTERNAL_ERROR.value)
                    message = error_obj.get("message", "Unknown error")
                    data = error_obj.get("data")
                    raise MCPError(code, message, data)
                
                # Extract result data
                if "result" not in chunk:
                    raise MCPError(
                        MCPErrorCode.PARSE_ERROR, 
                        "Missing 'result' field in chunk"
                    )
                
                yield chunk["result"]
                
        except MCPError:
            # Re-raise MCPError as is
            raise
        except Exception as e:
            # Wrap other exceptions in MCPError
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Error processing streaming response: {str(e)}"
            )
    
    def collect_all(self) -> Any:
        """
        [Function intent]
        Collects all chunks in the stream and returns them.
        
        [Design principles]
        - Convenience method for collecting entire stream
        - Handles chunked or aggregated response patterns
        
        [Implementation details]
        - Iterates through all chunks
        - For simple ordered chunks, returns a list of all chunks
        - For aggregating streams, returns the last chunk (which may contain all data)
        
        Returns:
            List of all chunks or final aggregated result
            
        Raises:
            MCPError: For errors during stream processing
        """
        chunks = list(self.iter_chunks())
        
        if not chunks:
            return None
            
        # If only one chunk, return it directly
        if len(chunks) == 1:
            return chunks[0]
            
        # Otherwise, return the list of chunks
        return chunks
    
    def process_stream(self, callback: Callable[[Any], None]) -> None:
        """
        [Function intent]
        Processes the stream with a callback function.
        
        [Design principles]
        - Callback-based stream processing
        - Simple streaming interface for consumers
        
        [Implementation details]
        - Iterates through chunks
        - Calls callback for each chunk
        - Handles errors during processing
        
        Args:
            callback: Function to call for each chunk
            
        Raises:
            MCPError: For errors during stream processing
        """
        try:
            for chunk in self.iter_chunks():
                callback(chunk)
        except Exception as e:
            if not isinstance(e, MCPError):
                raise MCPError(
                    MCPErrorCode.INTERNAL_ERROR,
                    f"Error in stream callback: {str(e)}"
                ) from e
            raise


class MCPStreamingClient:
    """
    [Class intent]
    Client for handling streaming responses from MCP servers.
    Provides specialized functionality for executing streaming tools and
    accessing streaming resources.
    
    [Design principles]
    - Builds on the base MCPClient transport
    - Supports both tool and resource streaming
    - Provides consistent streaming interface
    
    [Implementation details]
    - Creates and manages streaming responses
    - Supports both iterator and callback patterns
    - Handles cancellation and error processing
    """
    
    def __init__(self, client):
        """
        [Class method intent]
        Initializes a new streaming client.
        
        [Design principles]
        - Simple initialization with base client
        
        [Implementation details]
        - Stores reference to the base client
        - Creates logger instance
        
        Args:
            client: The base MCPClient instance
        """
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        if not HAS_REQUESTS:
            raise ImportError("The 'requests' library is required for MCPStreamingClient.")
            
    def execute_streaming_tool(
        self,
        tool_name: str, 
        params: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> MCPStreamingResponse:
        """
        [Function intent]
        Executes an MCP tool with streaming response.
        
        [Design principles]
        - Follows MCP specification for streaming tool execution
        - Provides streaming response object for consumption
        
        [Implementation details]
        - Prepares JSON-RPC request for the tool
        - Sets up streaming HTTP request
        - Returns streaming response object
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            request_id: Optional request ID
            
        Returns:
            Streaming response object
            
        Raises:
            MCPError: For errors setting up the streaming request
        """
        endpoint = f"mcp/tools/{tool_name}/stream"
        
        try:
            # Prepare JSON-RPC request
            response = self.client.call_json_rpc(
                method="executeTool",
                endpoint=endpoint,
                params=params,
                request_id=request_id,
                stream=True  # This returns raw response
            )
            
            return MCPStreamingResponse(response, request_id)
            
        except Exception as e:
            if isinstance(e, MCPError):
                raise e
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Error setting up streaming tool execution: {str(e)}"
            )
        
    def get_streaming_resource(
        self,
        resource_uri: str, 
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> MCPStreamingResponse:
        """
        [Function intent]
        Access an MCP resource with streaming response.
        
        [Design principles]
        - Follows MCP specification for streaming resource access
        - Provides streaming response object for consumption
        
        [Implementation details]
        - Prepares JSON-RPC request for the resource
        - Sets up streaming HTTP request
        - Returns streaming response object
        
        Args:
            resource_uri: URI of the resource to access
            params: Optional parameters for the resource
            request_id: Optional request ID
            
        Returns:
            Streaming response object
            
        Raises:
            MCPError: For errors setting up the streaming request
        """
        endpoint = f"mcp/resources/{resource_uri}/stream"
        
        try:
            # Prepare JSON-RPC request
            response = self.client.call_json_rpc(
                method="getResource",
                endpoint=endpoint,
                params=params or {},
                request_id=request_id,
                stream=True  # This returns raw response
            )
            
            return MCPStreamingResponse(response, request_id)
            
        except Exception as e:
            if isinstance(e, MCPError):
                raise e
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Error setting up streaming resource access: {str(e)}"
            )
    
    def stream_with_callback(
        self, 
        streaming_response: MCPStreamingResponse,
        callback: Callable[[Any], None],
        cancel_event: Optional[threading.Event] = None
    ) -> None:
        """
        [Function intent]
        Process a streaming response with a callback function,
        optionally supporting cancellation.
        
        [Design principles]
        - Simple callback-based streaming interface
        - Support for cancellation
        - Consistent error handling
        
        [Implementation details]
        - Processes streaming response in a loop
        - Calls callback for each chunk
        - Checks for cancellation between chunks
        
        Args:
            streaming_response: The streaming response object
            callback: Function to call for each chunk
            cancel_event: Optional threading.Event for cancellation
            
        Raises:
            MCPError: For errors during stream processing
        """
        try:
            for chunk in streaming_response.iter_chunks():
                if cancel_event and cancel_event.is_set():
                    streaming_response.cancel()
                    break
                    
                callback(chunk)
                
        except Exception as e:
            if not isinstance(e, MCPError):
                raise MCPError(
                    MCPErrorCode.INTERNAL_ERROR,
                    f"Error processing streaming response: {str(e)}"
                ) from e
            raise
