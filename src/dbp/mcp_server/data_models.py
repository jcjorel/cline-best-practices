###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
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
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:48:30Z : Initial creation of MCP data models by CodeAssistant
# * Defined MCPRequest, MCPResponse, and MCPError dataclasses.
###############################################################################

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union

logger = logging.getLogger(__name__)

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
