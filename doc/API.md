# MCP Server REST APIs

This document describes the REST API endpoints exposed by the Documentation-Based Programming MCP server.

## Design Decision: REST API as MCP Transport Layer

**Context**: The MCP server needs to expose its functionality through a standardized protocol.

**Decision**: Implement a minimal REST API layer that serves as a transport mechanism for the Model Context Protocol (MCP) rather than a comprehensive RESTful API.

**Rationale**: 
- The primary protocol for this system is the Model Context Protocol (MCP)
- The REST API serves only as a transport layer for MCP requests
- This approach simplifies client integration by leveraging standard HTTP 
- It maintains focus on the MCP protocol as the core interface

## Exposed REST API Endpoints

The MCP server exposes these specific REST API endpoints:

### Execute MCP Tool

**Endpoint**: `POST /mcp/tool/{tool_name}`

**Purpose**: Execute a specific MCP tool with provided parameters.

**Path Parameters**:
- `tool_name`: Name of the MCP tool to execute

**Request Body**: JSON object containing tool-specific parameters

**Response**: MCP response containing results or error information

**Example Request**:
```http
POST /mcp/tool/dbp_general_query HTTP/1.1
Content-Type: application/json

{
  "query": "What files implement the authentication system?",
  "responseFormat": "Detailed",
  "timeout": 30
}
```

**Example Response**:
```json
{
  "status": "success",
  "id": "req-12345",
  "result": {
    "files": [
      "src/auth/service.js",
      "src/auth/middleware.js"
    ],
    "details": "The authentication system is implemented across multiple files...",
    "suggestions": [
      "How do authentication and authorization interact?"
    ]
  }
}
```

### Access MCP Resource

**Endpoint**: `GET /mcp/resource/{resource_path:path}`

**Purpose**: Access a specific MCP resource.

**Path Parameters**:
- `resource_path`: Path to the MCP resource (e.g., `documentation/DESIGN.md`)

**Query Parameters**: Resource-specific parameters

**Response**: MCP response containing resource data or error information

**Example Request**:
```http
GET /mcp/resource/documentation/DESIGN.md HTTP/1.1
```

**Example Response**:
```json
{
  "status": "success",
  "id": "req-67890",
  "result": {
    "content": "# Documentation-Based Programming System Architecture\n\nThis document describes...",
    "format": "markdown",
    "lastModified": "2025-04-15T14:32:21Z"
  }
}
```

### Health Check

**Endpoint**: `GET /health`

**Purpose**: Verify the MCP server is running correctly.

**Response**: Basic health status information

**Example Request**:
```http
GET /health HTTP/1.1
```

**Example Response**:
```json
{
  "status": "healthy",
  "server": "DocumentationBasedProgramming",
  "version": "1.0.0",
  "uptime": "unknown"
}
```

## Error Handling

All endpoints use a standardized error response format:

```json
{
  "status": "error",
  "id": "req-12345",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "additionalInfo": "More specific error information"
    }
  }
}
```

Common HTTP status codes:
- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Tool or resource not found
- `500 Internal Server Error`: Server-side error

## Security Considerations

The REST API adheres to the security principles outlined in [SECURITY.md](SECURITY.md):

- **Default Localhost Binding**: By default, the API server binds only to 127.0.0.1 (localhost)
- **Authentication**: All endpoints support authentication through the MCP protocol's authentication mechanisms
- **Authorization**: Access controls for tools and resources follow the MCP specification
