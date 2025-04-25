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
# Provides streaming functionality for MCP tools and resources that need to return
# large amounts of data incrementally. Implements the streaming specification from
# the MCP protocol to allow progressive data delivery without requiring clients to
# wait for complete responses.
###############################################################################
# [Source file design principles]
# - Event-based streaming with standard JSON-RPC 2.0 message format
# - Support for both chunked and event-stream data formats
# - Thread-safe implementation for concurrent streaming
# - Clean separation of streaming protocol from data generation
# - Support for both tool and resource streaming
###############################################################################
# [Source file constraints]
# - Must maintain JSON-RPC 2.0 compatibility for each chunk
# - Should support variable chunk sizes
# - Must handle error conditions during streaming
# - Must support stream cancellation
# - Must be compatible with FastAPI's streaming response mechanisms
###############################################################################
# [Dependencies]
# system:asyncio
# system:pydantic
# system:typing
# system:logging
# codebase:src/dbp/mcp_server/mcp/error.py
# codebase:src/dbp/mcp_server/mcp/cancellation.py
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T22:43:10Z : Initial implementation of MCP streaming support by CodeAssistant
# * Created MCPStreamingResponse class
# * Added stream chunk data models
# * Implemented streaming protocol helpers
###############################################################################

import asyncio
import logging
import json
from enum import Enum
from typing import Dict, Any, Optional, AsyncGenerator, Callable, Union, List, AsyncIterator

from pydantic import BaseModel, Field

from .error import MCPError, MCPErrorCode
from .cancellation import MCPCancellationToken

logger = logging.getLogger(__name__)


class StreamFormat(Enum):
    """
    [Class intent]
    Defines the available streaming formats for MCP streaming responses.
    
    [Design principles]
    Enumeration for type-safe format selection.
    
    [Implementation details]
    Values correspond to MIME types or format identifiers.
    """
    JSON_CHUNKS = "json_chunks"  # JSON objects delimited by newlines
    EVENT_STREAM = "event_stream"  # Server-Sent Events format
    BINARY = "binary"  # Binary data with appropriate content type


class StreamChunk(BaseModel):
    """
    [Class intent]
    Represents a single chunk in a streaming response.
    
    [Design principles]
    - Consistent format for all stream chunks
    - Support for JSON-RPC 2.0 compatibility
    - Includes metadata for client processing
    
    [Implementation details]
    - Contains the chunk data and metadata
    - Supports sequence numbers for ordering
    - Includes flags for stream state (first/last chunk)
    """
    chunk_id: int
    data: Any
    is_first: bool = False
    is_last: bool = False
    metadata: Optional[Dict[str, Any]] = None


class MCPStreamingResponse:
    """
    [Class intent]
    Handles the creation and management of streaming responses for MCP tools and resources.
    
    [Design principles]
    - Asynchronous streaming with background processing
    - Support for different streaming formats
    - Cancellation support
    - Error handling during streaming
    
    [Implementation details]
    - Uses AsyncGenerator for efficient streaming
    - Formats chunks according to specified format
    - Handles errors during stream processing
    """
    
    def __init__(
        self,
        format: StreamFormat = StreamFormat.JSON_CHUNKS,
        content_type: Optional[str] = None,
        chunk_size: int = 4096,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        [Class method intent]
        Initializes a new streaming response handler.
        
        [Design principles]
        - Configurable streaming format and settings
        - Default values for common use cases
        
        [Implementation details]
        - Sets up streaming configuration
        - Initializes counters and state
        
        Args:
            format: The streaming format to use
            content_type: Optional content type override
            chunk_size: Maximum size of each chunk in bytes
            logger_override: Optional logger instance
        """
        self.format = format
        self._chunk_size = chunk_size
        self._next_chunk_id = 0
        self._started = False
        self._completed = False
        self._error = None
        
        # Determine content type based on format if not specified
        self._content_type = content_type
        if not self._content_type:
            if format == StreamFormat.JSON_CHUNKS:
                self._content_type = "application/x-ndjson"
            elif format == StreamFormat.EVENT_STREAM:
                self._content_type = "text/event-stream"
            elif format == StreamFormat.BINARY:
                self._content_type = "application/octet-stream"
                
        self.logger = logger_override or logger.getChild(f"MCPStreamingResponse.{format.value}")
        
    @property
    def content_type(self) -> str:
        """Get the content type for the stream."""
        return self._content_type
    
    async def stream(
        self,
        generator: AsyncIterator[Any],
        request_id: Any,
        cancellation_token: Optional[MCPCancellationToken] = None
    ) -> AsyncGenerator[str, None]:
        """
        [Function intent]
        Streams data from an async generator, formatting according to the specified format.
        
        [Design principles]
        - Asynchronous processing for efficient streaming
        - Support for cancellation
        - Proper error handling
        
        [Implementation details]
        - Wraps generator output in appropriate format
        - Handles start/end of stream markers
        - Supports cancellation checks
        - Provides JSON-RPC 2.0 compatible output
        
        Args:
            generator: Async iterator producing the data to stream
            request_id: JSON-RPC request ID to include in each chunk
            cancellation_token: Optional token for checking cancellation
            
        Yields:
            Formatted chunks as strings according to the selected format
        """
        self._started = True
        self._next_chunk_id = 0
        
        try:
            # Yield starting marker for event_stream
            if self.format == StreamFormat.EVENT_STREAM:
                yield self._format_sse_message("start", {"status": "streaming_started"})
            
            # Stream first chunk with metadata
            first_chunk = await anext(generator, None)
            if first_chunk is not None:
                yield self._format_chunk(first_chunk, request_id, is_first=True)
                self._next_chunk_id += 1
            
            # Stream remaining chunks
            async for data in generator:
                # Check for cancellation
                if cancellation_token and cancellation_token.is_cancelled():
                    if self.format == StreamFormat.EVENT_STREAM:
                        yield self._format_sse_message(
                            "error", 
                            {"code": MCPErrorCode.CANCELLED.value, "message": "Stream cancelled"}
                        )
                    break
                
                yield self._format_chunk(data, request_id)
                self._next_chunk_id += 1
            
            # Yield final chunk to indicate completion
            yield self._format_chunk(None, request_id, is_last=True)
            
            # Yield ending marker for event_stream
            if self.format == StreamFormat.EVENT_STREAM:
                yield self._format_sse_message("end", {"status": "streaming_completed"})
                
            self._completed = True
            
        except Exception as e:
            self.logger.error(f"Error during streaming: {str(e)}", exc_info=True)
            self._error = e
            
            # Send error message in appropriate format
            if self.format == StreamFormat.EVENT_STREAM:
                error_data = {
                    "code": MCPErrorCode.INTERNAL_ERROR.value,
                    "message": f"Stream error: {str(e)}"
                }
                yield self._format_sse_message("error", error_data)
            else:
                error = MCPError(MCPErrorCode.INTERNAL_ERROR, f"Stream error: {str(e)}")
                error_json = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error.to_json_rpc()["error"]
                }
                yield json.dumps(error_json) + "\n"
    
    def _format_chunk(self, data: Any, request_id: Any, is_first: bool = False, is_last: bool = False) -> str:
        """
        [Function intent]
        Formats a data chunk according to the specified streaming format.
        
        [Design principles]
        - Format-specific encoding
        - Consistent structure across formats
        
        [Implementation details]
        - Creates JSON-RPC 2.0 compatible chunk for json_chunks
        - Creates SSE message for event_stream
        - Creates appropriate binary framing for binary format
        
        Args:
            data: The data to include in the chunk
            request_id: JSON-RPC request ID
            is_first: Whether this is the first chunk
            is_last: Whether this is the last chunk
            
        Returns:
            Formatted chunk as a string
        """
        if self.format == StreamFormat.JSON_CHUNKS:
            # For JSON chunks, create a JSON-RPC 2.0 response with chunk info
            chunk = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "chunk_id": self._next_chunk_id,
                    "is_first": is_first,
                    "is_last": is_last,
                    "data": data
                }
            }
            return json.dumps(chunk) + "\n"
            
        elif self.format == StreamFormat.EVENT_STREAM:
            # For SSE, create an event with the chunk data
            event_type = "chunk"
            if is_first:
                event_type = "start"
            elif is_last:
                event_type = "end"
                
            event_data = {
                "chunk_id": self._next_chunk_id,
                "data": data
            }
            
            return self._format_sse_message(event_type, event_data)
            
        elif self.format == StreamFormat.BINARY:
            # For binary, we'd need to implement appropriate framing
            # This is a placeholder; actual implementation would depend on binary format specs
            raise NotImplementedError("Binary streaming format not yet implemented")
            
        else:
            raise ValueError(f"Unsupported streaming format: {self.format}")
    
    def _format_sse_message(self, event: str, data: Any) -> str:
        """
        [Function intent]
        Formats a Server-Sent Events (SSE) message.
        
        [Design principles]
        - Follows SSE specification
        - JSON encoding for structured data
        
        [Implementation details]
        - Creates properly formatted SSE event
        - Adds event type and JSON data
        
        Args:
            event: The event type
            data: The data payload
            
        Returns:
            Formatted SSE message
        """
        json_data = json.dumps(data)
        return f"event: {event}\ndata: {json_data}\n\n"


async def create_streaming_generator(
    data_source: Union[List[Any], AsyncIterator[Any]],
    chunk_size: int = 1,
    delay: float = 0.0,
    cancellation_token: Optional[MCPCancellationToken] = None
) -> AsyncGenerator[Any, None]:
    """
    [Function intent]
    Creates an async generator from a data source for streaming.
    
    [Design principles]
    - Flexible data source support (lists or async iterators)
    - Configurable chunking and timing
    - Cancellation support
    
    [Implementation details]
    - Handles both list and async iterator data sources
    - Supports artificial delay for testing
    - Checks for cancellation between chunks
    
    Args:
        data_source: List of items or async iterator producing items
        chunk_size: Number of items to include in each chunk
        delay: Optional delay between chunks in seconds
        cancellation_token: Optional token for checking cancellation
        
    Yields:
        Data chunks according to the specified parameters
    """
    if isinstance(data_source, list):
        # Process a list source
        buffer = []
        for item in data_source:
            buffer.append(item)
            
            if len(buffer) >= chunk_size:
                # Check for cancellation
                if cancellation_token and cancellation_token.is_cancelled():
                    break
                    
                # Add optional delay
                if delay > 0:
                    await asyncio.sleep(delay)
                
                yield buffer.copy() if chunk_size > 1 else buffer[0]
                buffer.clear()
        
        # Yield any remaining items
        if buffer and not (cancellation_token and cancellation_token.is_cancelled()):
            if delay > 0:
                await asyncio.sleep(delay)
            yield buffer.copy() if chunk_size > 1 else buffer[0]
    else:
        # Process an async iterator source
        buffer = []
        async for item in data_source:
            buffer.append(item)
            
            if len(buffer) >= chunk_size:
                # Check for cancellation
                if cancellation_token and cancellation_token.is_cancelled():
                    break
                    
                # Add optional delay
                if delay > 0:
                    await asyncio.sleep(delay)
                
                yield buffer.copy() if chunk_size > 1 else buffer[0]
                buffer.clear()
        
        # Yield any remaining items
        if buffer and not (cancellation_token and cancellation_token.is_cancelled()):
            if delay > 0:
                await asyncio.sleep(delay)
            yield buffer.copy() if chunk_size > 1 else buffer[0]
