# Web Framework Transition Plan for MCP Server

## Overview

This document outlines the concrete plan for transitioning from the current placeholder web server implementation in the MCP Server component to a production-ready implementation using FastAPI and Uvicorn.

## Background

The current MCP Server implementation contains placeholder code for the HTTP server functionality, focusing on the MCP protocol implementation logic rather than specific web framework integration. As indicated in the design decision note in `src/dbp/mcp_server/server.py`, this approach was taken to separate MCP logic from web framework details during initial development.

## Transition Goals

1. Implement a concrete web server using industry-standard libraries
2. Maintain all existing MCP protocol functionality
3. Ensure compatibility with the Component lifecycle management
4. Support graceful shutdown and error handling
5. Preserve existing route logic and request/response handling

## Selected Technology Stack

- **FastAPI**: Modern, high-performance web framework based on standard Python type hints for request validation
- **Uvicorn**: ASGI server implementation for Python, providing fast HTTP server capabilities
- **Pydantic**: Already implicitly used by FastAPI for request/response validation

## Implementation Plan

### Phase 1: Dependencies and Configuration

1. Add FastAPI and Uvicorn as explicit dependencies in requirements.txt
2. Update configuration schema in `config_schema.py` to include web server specific settings:
   - Server worker count
   - Thread settings
   - CORS configuration
   - Response compression settings
   - HTTP timeouts

### Phase 2: MCPServer Class Updates

1. Replace the placeholder `_create_web_app()` method with concrete FastAPI implementation:
   ```python
   def _create_web_app(self):
       """Creates and configures the FastAPI application."""
       from fastapi import FastAPI
       
       self.logger.info("Creating FastAPI application...")
       app = FastAPI(
           title=self.name, 
           description=self.description, 
           version=self.version
       )
       
       # Setup CORS middleware if configured
       if self.config.get("enable_cors", False):
           from fastapi.middleware.cors import CORSMiddleware
           app.add_middleware(
               CORSMiddleware,
               allow_origins=self.config.get("cors_origins", ["*"]),
               allow_credentials=self.config.get("cors_allow_credentials", False),
               allow_methods=self.config.get("cors_methods", ["*"]),
               allow_headers=self.config.get("cors_headers", ["*"]),
           )
       
       self._setup_routes(app)
       return app
   ```

2. Implement concrete `_setup_routes()` method:
   ```python
   def _setup_routes(self, app):
       """Sets up FastAPI routes for MCP requests."""
       from fastapi import Request, Response, HTTPException
       import uuid
       
       @app.post("/mcp/tool/{tool_name}")
       async def handle_tool_request_http(tool_name: str, request: Request):
           # Parse incoming JSON request
           try:
               body = await request.json()
           except ValueError:
               raise HTTPException(status_code=400, detail="Invalid JSON")
               
           # Build MCPRequest object
           headers = dict(request.headers)
           request_id = body.get("id", str(uuid.uuid4()))
           
           mcp_request = MCPRequest(
               id=request_id,
               type="tool",
               target=tool_name,
               data=body.get("data", {}),
               headers=headers
           )
           
           # Process request through existing MCPServer methods
           mcp_response = self.handle_request(mcp_request)
           
           # Convert status to HTTP status code
           status_code = 200 if mcp_response.status == "success" else 500
           if mcp_response.error:
               # Map MCPError codes to HTTP status codes
               if mcp_response.error.code == "AUTHENTICATION_FAILED":
                   status_code = 401
               elif mcp_response.error.code == "AUTHORIZATION_FAILED":
                   status_code = 403
               elif mcp_response.error.code in ["RESOURCE_NOT_FOUND", "TOOL_NOT_FOUND"]:
                   status_code = 404
               elif mcp_response.error.code == "INVALID_PARAMETERS":
                   status_code = 400
                   
           # Return JSON response
           return Response(
               content=json.dumps(mcp_response.__dict__),
               media_type="application/json",
               status_code=status_code
           )
           
       @app.get("/mcp/resource/{resource_path:path}")
       async def handle_resource_request_http(resource_path: str, request: Request):
           # Similar implementation as above but for resource requests
           params = dict(request.query_params)
           headers = dict(request.headers)
           
           mcp_request = MCPRequest(
               id=params.get("id", str(uuid.uuid4())),
               type="resource",
               target=resource_path,
               data=params,
               headers=headers
           )
           
           mcp_response = self.handle_request(mcp_request)
           
           # Similar status code mapping logic
           status_code = 200 if mcp_response.status == "success" else 500
           if mcp_response.error:
               # Map error codes to status codes
               # Similar mapping as above
               
           return Response(
               content=json.dumps(mcp_response.__dict__),
               media_type="application/json",
               status_code=status_code
           )
           
       # Health check endpoint
       @app.get("/health")
       async def health_check():
           return {"status": "healthy", "server": self.name, "version": self.version}
   ```

3. Update the `_run_server()` method to use Uvicorn:
   ```python
   def _run_server(self):
       """Runs the FastAPI server using Uvicorn."""
       import uvicorn
       
       self.logger.debug("Server thread started.")
       
       config = uvicorn.Config(
           app=self._app,
           host=self.host,
           port=self.port,
           log_level="warning",
           loop="asyncio",
           workers=self.config.get("workers", 1),
           timeout_keep_alive=self.config.get("keep_alive", 5),
           timeout_graceful_shutdown=self.config.get("graceful_shutdown_timeout", 10)
       )
       
       self._server = uvicorn.Server(config)
       
       try:
           # Start server, blocks until self._server.should_exit is set
           self._server.run()
       except Exception as e:
           self.logger.critical(f"Web server failed to run: {e}", exc_info=True)
       finally:
           self._is_running = False
           self.logger.info("Web server process stopped.")
   ```

4. Update the `stop()` method to gracefully shut down Uvicorn:
   ```python
   def stop(self):
       """Stops the MCP server."""
       if not self._is_running:
           self.logger.warning(f"MCP Server '{self.name}' is not running.")
           return

       self.logger.info(f"Stopping MCP server '{self.name}'...")
       self._stop_event.set()
       
       # Signal Uvicorn to shut down gracefully
       if hasattr(self, '_server') and self._server:
           self.logger.debug("Sending shutdown signal to Uvicorn...")
           self._server.should_exit = True
           
       # The rest of the method remains the same
   ```

### Phase 3: Request/Response Schema Enhancements

1. Create Pydantic models for request validation:
   ```python
   from pydantic import BaseModel, Field
   from typing import Dict, Any, Optional

   class MCPToolRequest(BaseModel):
       id: Optional[str] = None
       data: Dict[str, Any] = Field(default_factory=dict)
       
   class MCPResourceRequest(BaseModel):
       id: Optional[str] = None
       # Additional query parameters handled automatically by FastAPI
   ```

2. Update route handlers to use Pydantic models:
   ```python
   @app.post("/mcp/tool/{tool_name}")
   async def handle_tool_request_http(tool_name: str, request: MCPToolRequest):
       # Now using validated Pydantic model instead of raw JSON
       # Adjust implementation accordingly
   ```

### Phase 4: Testing and Verification

1. Create unit tests for FastAPI routes using TestClient
2. Create integration tests for end-to-end MCP request flow
3. Verify error handling and status code mapping
4. Performance testing with concurrent requests
5. Graceful shutdown verification

## Migration Strategy

The migration will be performed in a separate feature branch with the following steps:

1. Implement changes in phases 1-3
2. Run automated tests (phase 4)
3. Create a PR for review
4. After approval, merge to main branch

## Default Configuration

```python
DEFAULT_MCP_SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 6231,
    "server_name": "dbp-mcp-server",
    "server_description": "MCP Server for Documentation-Based Programming",
    "server_version": "1.0.0",
    "workers": 1,
    "enable_cors": False,
    "cors_origins": ["*"],
    "cors_methods": ["*"],
    "cors_headers": ["*"],
    "keep_alive": 5,
    "graceful_shutdown_timeout": 10,
}
```

## Backward Compatibility

This implementation maintains full backward compatibility with the current MCP protocol. The transition affects only the HTTP server implementation, not the MCP protocol handling logic.
