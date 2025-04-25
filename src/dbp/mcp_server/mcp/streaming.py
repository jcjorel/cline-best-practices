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

import logging
import json
from typing import Dict, Any, Optional, AsyncGenerator, AsyncIterator

from .error import MCPError, MCPErrorCode
from .cancellation import MCPCancellationToken

logger = logging.getLogger(__name__)


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
        """
        [Class method intent]
        Initializes a new streaming response handler.
        
        [Design principles]
        - Simple initialization with minimal configuration
        
        [Implementation details]
        - Sets up basic streaming state
        
        Args:
            logger_override: Optional logger instance
        """
        self._next_chunk_id = 0
        self._started = False
        self._completed = False
        self._error = None
        self.logger = logger_override or logger.getChild("MCPStreamingResponse")
        self._content_type = "application/x-ndjson"
        
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
