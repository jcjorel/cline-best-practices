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
# Defines the core data structures (using dataclasses) for the Model Context
# Protocol (MCP) server integration. This includes representations for MCP
# requests, responses, and error objects, aligning with MCP specifications.
###############################################################################
# [Source file design principles]
# - Uses standard Python dataclasses for data representation.
# - Defines structures closely matching the expected MCP message formats.
# - Includes type hints for clarity.
# - Provides a clear structure for handling errors within the MCP framework.
###############################################################################
# [Source file constraints]
# - Requires Python 3.7+ for dataclasses.
# - Assumes adherence to the basic principles of the Model Context Protocol.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:56:00Z : Fixed Pydantic v2 compatibility issues by CodeAssistant
# * Replaced deprecated @root_validator with @model_validator
# * Updated schema_extra to json_schema_extra
# * Fixed class reference order issue
# 2025-04-15T19:32:00Z : Added FastAPI Pydantic models for request/response validation by CodeAssistant
# * Created Pydantic models MCPToolRequest and MCPResourceRequest for FastAPI
# * Added FastAPI response models and helper functions
# 2025-04-15T10:48:30Z : Initial creation of MCP data models by CodeAssistant
# * Defined MCPRequest, MCPResponse, and MCPError dataclasses.
###############################################################################

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union, Type
from pydantic import BaseModel, Field, validator, model_validator
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# FastAPI Pydantic Models for Request Validation
class MCPToolRequest(BaseModel):
    """Pydantic model for validating MCP tool requests in FastAPI."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), 
                              description="Unique request identifier, auto-generated if not provided")
    data: Dict[str, Any] = Field(default_factory=dict, 
                                 description="Payload containing parameters for the tool")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "req-123456",
                "data": {
                    "param1": "value1",
                    "param2": 42
                }
            }
        }

class MCPResourceRequest(BaseModel):
    """Pydantic model for validating MCP resource requests in FastAPI."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), 
                              description="Unique request identifier, auto-generated if not provided")
    # Additional query parameters are handled by FastAPI directly

    class Config:
        json_schema_extra = {
            "example": {
                "id": "req-123456"
            }
        }

# FastAPI Pydantic Models for Response Validation
class MCPErrorModel(BaseModel):
    """Pydantic model for MCP error details in responses."""
    code: str = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "TOOL_NOT_FOUND",
                "message": "The requested tool 'analyze_data' was not found.",
                "data": {"available_tools": ["tool1", "tool2"]}
            }
        }

class MCPResponseModel(BaseModel):
    """Base Pydantic model for MCP responses."""
    id: str = Field(..., description="Request identifier that this response corresponds to")
    status: str = Field(..., description="Response status ('success' or 'error')")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Result payload (for success status)")
    error: Optional[MCPErrorModel] = Field(default=None, description="Error details (for error status)")

    @model_validator(mode='after')
    def validate_status_fields(self):
        """Validate that the appropriate fields are present for the given status."""
        if self.status == "success" and self.error is not None:
            logger.warning(f"MCPResponse has status 'success' but also contains an error object.")
        if self.status == "error" and self.error is None:
            logger.warning(f"MCPResponse has status 'error' but is missing the error object.")
        
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "id": "req-123456",
                "status": "success",
                "result": {
                    "output": "Analysis completed successfully",
                    "details": {"duration_ms": 320}
                },
                "error": None
            }
        }


@dataclass
class MCPError:
    """Represents an error structure within an MCP response."""
    code: str # Standardized error code (e.g., "INVALID_REQUEST", "TOOL_NOT_FOUND")
    message: str # Human-readable error message
    data: Optional[Dict[str, Any]] = None # Optional additional error details

@dataclass
class MCPRequest:
    """
    Represents an incoming request to the MCP server.
    This structure might be populated by the web framework handling the HTTP request.
    """
    id: str # Unique request identifier (usually provided by the client)
    type: str # Type of request, typically "tool" or "resource"
    target: str # The name of the tool or the URI of the resource being targeted
    data: Dict[str, Any] = field(default_factory=dict) # Payload containing parameters for tools or resources
    headers: Dict[str, str] = field(default_factory=dict) # Request headers (e.g., for authentication)
    # Add other potential MCP fields if needed, like 'metadata'

@dataclass
class MCPResponse:
    """Represents a response sent back by the MCP server."""
    id: str # Corresponds to the MCPRequest id
    status: str # "success" or "error"
    result: Optional[Dict[str, Any]] = None # Payload containing the result (for success status)
    error: Optional[MCPError] = None # Error details (for error status)
    # Add other potential MCP fields if needed, like 'metadata'

    def __post_init__(self):
        # Basic validation
        if self.status == "success" and self.error is not None:
            logger.warning(f"MCPResponse (ID: {self.id}) has status 'success' but also contains an error object.")
        if self.status == "error" and self.error is None:
            logger.warning(f"MCPResponse (ID: {self.id}) has status 'error' but is missing the error object.")
            # Optionally create a default error
            # self.error = MCPError(code="INTERNAL_ERROR", message="Unknown error occurred.", data=None)
        if self.status == "success" and self.result is None:
             # Result can sometimes be legitimately null/empty for success, maybe just debug log
             logger.debug(f"MCPResponse (ID: {self.id}) has status 'success' but result is None.")


# Helper functions for FastAPI integration
def create_mcp_request_from_tool(tool_request: MCPToolRequest, tool_name: str, headers: Dict[str, str]) -> MCPRequest:
    """Convert a FastAPI tool request to an internal MCPRequest."""
    return MCPRequest(
        id=tool_request.id,
        type="tool",
        target=tool_name,
        data=tool_request.data,
        headers=headers
    )

def create_mcp_request_from_resource(resource_request: MCPResourceRequest, resource_uri: str, 
                                    query_params: Dict[str, str], headers: Dict[str, str]) -> MCPRequest:
    """Convert a FastAPI resource request to an internal MCPRequest."""
    return MCPRequest(
        id=resource_request.id,
        type="resource",
        target=resource_uri,
        data=query_params,
        headers=headers
    )

def mcp_response_to_model(response: MCPResponse) -> MCPResponseModel:
    """Convert an internal MCPResponse to a Pydantic response model."""
    error_model = None
    if response.error:
        error_model = MCPErrorModel(
            code=response.error.code,
            message=response.error.message,
            data=response.error.data
        )
    
    return MCPResponseModel(
        id=response.id,
        status=response.status,
        result=response.result,
        error=error_model
    )

def get_http_status_for_mcp_error(error_code: str) -> int:
    """Map MCP error codes to appropriate HTTP status codes."""
    status_map = {
        "AUTHENTICATION_FAILED": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_FAILED": status.HTTP_403_FORBIDDEN,
        "TOOL_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_REQUEST": status.HTTP_400_BAD_REQUEST,
        "INVALID_PARAMETERS": status.HTTP_400_BAD_REQUEST,
        "EXECUTION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR
    }
    return status_map.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
