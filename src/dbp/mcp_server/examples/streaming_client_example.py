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
# Provides a sample client implementation that demonstrates how to interact with
# streaming MCP tools. This serves as an example for client applications that need
# to consume streaming responses from MCP servers.
###############################################################################
# [Source file design principles]
# - Demonstrates MCP client patterns for streaming requests
# - Shows capability negotiation with streaming support
# - Includes examples for different stream formats (JSON chunks and SSE)
# - Implements proper error handling and timeout management
###############################################################################
# [Source file constraints]
# - For demonstration purposes only, not for production use
# - Requires running MCP server with streaming-capable tools
###############################################################################
# [Dependencies]
# system:aiohttp
# system:asyncio
# system:json
# system:logging
# codebase:src/dbp/mcp_server/examples/sample_streaming_tool.py
###############################################################################
# [GenAI tool change history]
# 2025-04-25T22:55:00Z : Initial implementation of streaming client example by CodeAssistant
# * Created basic client for testing streaming functionality
# * Added examples for both JSON chunks and SSE formats
# * Implemented session handling and capability negotiation
###############################################################################

import aiohttp
import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, AsyncIterable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MCPClient:
    """
    [Class intent]
    A simple MCP client implementation for testing streaming functionality.
    
    [Design principles]
    - Handles capability negotiation
    - Supports streaming requests
    - Maintains session state
    
    [Implementation details]
    - Uses aiohttp for async HTTP requests
    - Maintains session ID for capability-based requests
    - Supports JSON and SSE streaming formats
    """
    
    def __init__(self, server_url: str):
        """
        [Class method intent]
        Initializes the MCP client with the server URL.
        
        [Design principles]
        Simple initialization with minimal configuration.
        
        [Implementation details]
        Stores server URL and initializes empty session info.
        
        Args:
            server_url: The base URL of the MCP server
        """
        self.server_url = server_url
        self.session_id = None
        self.server_capabilities = []
        self.logger = logger.getChild('MCPClient')
        
    async def negotiate_capabilities(self, capabilities: List[str] = None):
        """
        [Function intent]
        Negotiates capabilities with the MCP server.
        
        [Design principles]
        Standard MCP capability negotiation.
        
        [Implementation details]
        Sends capability declaration request and stores session ID.
        
        Args:
            capabilities: List of capabilities the client supports
        
        Returns:
            Server capability information
        """
        if capabilities is None:
            capabilities = ["streaming", "progress_tracking", "cancellation"]
            
        async with aiohttp.ClientSession() as session:
            request_body = {
                "client_name": "StreamingTestClient",
                "client_version": "1.0",
                "supported_capabilities": capabilities
            }
            
            async with session.post(f"{self.server_url}/mcp/negotiate", json=request_body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Capability negotiation failed: {response.status} - {error_text}")
                    
                result = await response.json()
                self.session_id = response.headers.get("X-MCP-Session-ID")
                self.server_capabilities = result.get("supported_capabilities", [])
                
                self.logger.info(f"Capability negotiation successful. Session ID: {self.session_id}")
                self.logger.info(f"Server capabilities: {', '.join(self.server_capabilities)}")
                
                return result
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Calls an MCP tool in non-streaming mode.
        
        [Design principles]
        Standard JSON-RPC 2.0 tool request.
        
        [Implementation details]
        Sends tool execution request and returns full response.
        
        Args:
            tool_name: The name of the tool to call
            params: Parameters for the tool
            
        Returns:
            The complete tool response
        """
        if not self.session_id:
            await self.negotiate_capabilities()
            
        request_id = str(uuid.uuid4())
        request_body = {
            "jsonrpc": "2.0",
            "method": "executeTool",
            "params": params,
            "id": request_id
        }
        
        headers = {"X-MCP-Session-ID": self.session_id} if self.session_id else {}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/mcp/tool/{tool_name}", 
                json=request_body,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Tool call failed: {response.status} - {error_text}")
                    
                return await response.json()
    
    async def stream_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any],
        stream_format: str = "json_chunks",
        timeout: float = 30.0
    ) -> AsyncIterable[Dict[str, Any]]:
        """
        [Function intent]
        Calls an MCP tool in streaming mode and processes the streamed responses.
        
        [Design principles]
        - Stream processing with support for different formats
        - Proper error handling
        - Timeout management
        
        [Implementation details]
        - Adds streaming flag to parameters
        - Uses aiohttp's streaming response handling
        - Processes JSON chunks or SSE messages based on format
        
        Args:
            tool_name: The name of the tool to call
            params: Parameters for the tool
            stream_format: Format for streaming (json_chunks or event_stream)
            timeout: Request timeout in seconds
            
        Yields:
            Processed chunks from the stream
        """
        if not self.session_id:
            await self.negotiate_capabilities(["streaming", "progress_tracking", "cancellation"])
        
        # Ensure streaming is enabled in params
        streaming_params = params.copy()
        streaming_params["streaming"] = True
        streaming_params["stream_format"] = stream_format
        
        request_id = str(uuid.uuid4())
        request_body = {
            "jsonrpc": "2.0",
            "method": "executeTool",
            "params": streaming_params,
            "id": request_id
        }
        
        headers = {"X-MCP-Session-ID": self.session_id} if self.session_id else {}
        
        self.logger.info(f"Starting streaming request to tool '{tool_name}' with format '{stream_format}'")
        
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(
                    f"{self.server_url}/mcp/tool/{tool_name}", 
                    json=request_body,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"Streaming request failed: {response.status} - {error_text}")
                    
                    # Process stream based on format
                    if stream_format == "json_chunks":
                        async for chunk in self._process_json_chunks(response):
                            yield chunk
                    elif stream_format == "event_stream":
                        async for event in self._process_sse_stream(response):
                            yield event
                    else:
                        raise ValueError(f"Unsupported stream format: {stream_format}")
                        
        except asyncio.TimeoutError:
            self.logger.error(f"Streaming request timed out after {timeout} seconds")
            raise
            
        except Exception as e:
            self.logger.error(f"Error during streaming: {str(e)}")
            raise
    
    async def _process_json_chunks(self, response) -> AsyncIterable[Dict[str, Any]]:
        """
        [Function intent]
        Processes a JSON chunks stream from the server.
        
        [Design principles]
        - Line-by-line JSON parsing
        - Error handling for malformed JSON
        
        [Implementation details]
        - Splits response by lines
        - Parses each line as JSON
        - Extracts data from JSON-RPC result structure
        
        Args:
            response: The HTTP response with streaming content
            
        Yields:
            Parsed JSON objects from the stream
        """
        async for line in response.content:
            line_text = line.decode('utf-8').strip()
            if not line_text:
                continue
                
            try:
                chunk = json.loads(line_text)
                
                # Check for errors
                if "error" in chunk:
                    self.logger.error(f"Error in stream: {chunk['error']}")
                    yield {"error": chunk["error"]}
                    continue
                    
                # Extract result data
                if "result" in chunk and "data" in chunk["result"]:
                    yield {
                        "chunk_id": chunk["result"].get("chunk_id"),
                        "is_first": chunk["result"].get("is_first", False),
                        "is_last": chunk["result"].get("is_last", False),
                        "data": chunk["result"]["data"]
                    }
                else:
                    # Pass through any other valid chunk
                    yield chunk
                    
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse JSON: {line_text}")
            except Exception as e:
                self.logger.error(f"Error processing chunk: {str(e)}")
    
    async def _process_sse_stream(self, response) -> AsyncIterable[Dict[str, Any]]:
        """
        [Function intent]
        Processes a Server-Sent Events (SSE) stream from the server.
        
        [Design principles]
        - Standard SSE parsing
        - Event type-based processing
        
        [Implementation details]
        - Parses SSE format (event: type\ndata: {...})
        - Handles different event types (chunk, start, end, error)
        - Extracts JSON data from event data field
        
        Args:
            response: The HTTP response with streaming content
            
        Yields:
            Parsed events from the SSE stream
        """
        current_event = None
        current_data = []
        
        async for line in response.content:
            line_text = line.decode('utf-8').rstrip()
            
            if not line_text:
                # Empty line means end of event
                if current_event and current_data:
                    data_str = ''.join(current_data)
                    try:
                        data = json.loads(data_str)
                        
                        # Create event object based on event type
                        event_obj = {
                            "event": current_event,
                            "data": data
                        }
                        
                        if current_event == "error":
                            self.logger.error(f"Error event in SSE stream: {data}")
                        
                        yield event_obj
                        
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse SSE data: {data_str}")
                        
                    # Reset for next event
                    current_event = None
                    current_data = []
                continue
                
            # Parse SSE line
            if line_text.startswith("event:"):
                current_event = line_text[6:].strip()
            elif line_text.startswith("data:"):
                current_data.append(line_text[5:].strip())


async def run_streaming_example():
    """
    [Function intent]
    Runs an example of using the streaming capabilities.
    
    [Design principles]
    - Demonstrates end-to-end streaming with MCP
    - Shows both streaming formats
    
    [Implementation details]
    - Creates client and negotiates capabilities
    - Calls streaming tool with various parameters
    - Processes stream results in different formats
    """
    # Create client
    client = MCPClient("http://localhost:8000")
    
    try:
        # Negotiate capabilities
        await client.negotiate_capabilities(["streaming", "progress_tracking", "cancellation"])
        
        # Example 1: JSON chunks streaming
        logger.info("\n=== EXAMPLE 1: JSON Chunks Streaming ===\n")
        params = {
            "item_count": 5,
            "delay_seconds": 0.5,
            "streaming": True,
            "stream_format": "json_chunks"
        }
        
        item_count = 0
        async for chunk in client.stream_tool("sample_stream", params, "json_chunks"):
            if "data" in chunk:
                item_count += 1
                logger.info(f"Received chunk #{chunk['chunk_id']}: {chunk['data']}")
            elif "error" in chunk:
                logger.error(f"Stream error: {chunk['error']}")
        
        logger.info(f"JSON chunks streaming complete. Received {item_count} items.")
        
        # Example 2: SSE streaming
        logger.info("\n=== EXAMPLE 2: Server-Sent Events (SSE) Streaming ===\n")
        params = {
            "item_count": 5,
            "delay_seconds": 0.5,
            "streaming": True,
            "stream_format": "event_stream"
        }
        
        item_count = 0
        async for event in client.stream_tool("sample_stream", params, "event_stream"):
            event_type = event["event"]
            data = event["data"]
            
            if event_type == "start":
                logger.info(f"Stream started: {data}")
            elif event_type == "chunk":
                item_count += 1
                logger.info(f"Received SSE chunk #{data['chunk_id']}: {data['data']}")
            elif event_type == "end":
                logger.info(f"Stream ended: {data}")
            elif event_type == "error":
                logger.error(f"Stream error: {data}")
        
        logger.info(f"SSE streaming complete. Received {item_count} items.")
        
        # Example 3: Error handling in streaming
        logger.info("\n=== EXAMPLE 3: Error Handling in Streaming ===\n")
        params = {
            "item_count": 10,
            "delay_seconds": 0.5,
            "streaming": True,
            "fail_at_item": 3  # Simulate failure at item #3
        }
        
        try:
            item_count = 0
            async for chunk in client.stream_tool("sample_stream", params):
                if "data" in chunk:
                    item_count += 1
                    logger.info(f"Received chunk #{chunk['chunk_id']}: {chunk['data']}")
                elif "error" in chunk:
                    logger.error(f"Stream error: {chunk['error']}")
                    break
            
            logger.info(f"Error handling example complete. Received {item_count} items before error.")
        except Exception as e:
            logger.error(f"Error during streaming: {str(e)}")
        
    except Exception as e:
        logger.error(f"Example failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_streaming_example())
