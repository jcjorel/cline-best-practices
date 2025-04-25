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
# Implements MCP capability negotiation types and data models for client-server 
# capability declaration. These components allow MCP clients and servers to 
# explicitly declare and negotiate their supported features at the beginning of
# a session.
###############################################################################
# [Source file design principles]
# - Uses enumerations for type-safe capability declarations
# - Implements Pydantic models for request/response validation
# - Maintains strict protocol compliance with the MCP specification
# - Provides clear typing for IDE support and static analysis
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with server-side capability declarations
# - Should support all capabilities described in the MCP specification
# - Should be extensible for future capability additions
###############################################################################
# [Dependencies]
# system:enum
# system:pydantic
# system:typing
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:12:00Z : Initial implementation of MCP capability negotiation by CodeAssistant
# * Created capability type enumerations
# * Implemented negotiation request/response models
###############################################################################

from enum import Enum, auto
from typing import Dict, List, Any, Optional, Set, Union

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = object  # Type stub for type hints
    Field = lambda *args, **kwargs: None  # noqa: E731
    
    import logging
    logging.getLogger(__name__).error(
        "The 'pydantic' library is required for MCP capability negotiation. "
        "Please install it (`pip install pydantic`)."
    )


class ClientCapabilityType(str, Enum):
    """
    [Class intent]
    Defines the standard capability types that an MCP client can declare support for,
    as specified in the MCP protocol.
    
    [Design principles]
    - Uses string-based enum for easy JSON serialization
    - Includes all client capabilities from MCP specification
    - Allows for extension with custom capabilities
    
    [Implementation details]
    - Values match exactly the standardized capability names in the MCP spec
    """
    # Core capabilities from MCP specification
    SAMPLING = "sampling"
    NOTIFICATIONS = "notifications"
    PROGRESS_TRACKING = "progress_tracking"
    CANCELLATION = "cancellation"
    STREAMING = "streaming"
    
    # Extended capabilities
    SESSION_PERSISTENCE = "session_persistence"
    BATCH_REQUESTS = "batch_requests"
    AUTHENTICATION = "authentication"


class ServerCapabilityType(str, Enum):
    """
    [Class intent]
    Defines the standard capability types that an MCP server can declare support for,
    as specified in the MCP protocol.
    
    [Design principles]
    - Uses string-based enum for easy JSON serialization
    - Includes all server capabilities from MCP specification
    - Allows for extension with custom capabilities
    
    [Implementation details]
    - Values match exactly the standardized capability names in the MCP spec
    """
    # Core capabilities from MCP specification
    TOOLS = "tools"
    RESOURCES = "resources"
    SUBSCRIPTIONS = "subscriptions"
    PROMPTS = "prompts"
    STREAMING = "streaming"
    NOTIFICATIONS = "notifications"
    
    # Extended capabilities
    BATCH_OPERATIONS = "batch_operations"
    HISTORY = "history"
    METRICS = "metrics"


class CapabilityDetail(BaseModel):
    """
    [Class intent]
    Provides detailed information about a specific capability including
    version and parameter requirements.
    
    [Design principles]
    - Uses Pydantic for data validation and serialization
    - Follows MCP specification for capability metadata
    
    [Implementation details]
    - Includes standard fields from MCP specification
    - Allows for optional capability-specific parameters
    """
    name: str
    version: str = "1.0"
    description: str = ""
    parameters: Optional[Dict[str, Any]] = None


class NegotiationRequest(BaseModel):
    """
    [Class intent]
    Represents a client capability declaration request sent at session initialization
    to inform the server about supported capabilities.
    
    [Design principles]
    - Follows MCP specification for negotiation requests
    - Uses Pydantic for validation and serialization/deserialization
    
    [Implementation details]
    - Includes required client identification fields
    - Contains capability declarations with optional details
    - Supports protocol extensions
    """
    client_name: str
    client_version: str
    supported_capabilities: List[str]
    capability_details: Optional[Dict[str, CapabilityDetail]] = None
    extensions: Optional[Dict[str, Any]] = None


class NegotiationResponse(BaseModel):
    """
    [Class intent]
    Represents the server's capability declaration response that informs
    the client about supported features and available tools/resources.
    
    [Design principles]
    - Follows MCP specification for negotiation responses
    - Uses Pydantic for validation and serialization/deserialization
    
    [Implementation details]
    - Includes server identification
    - Lists all supported capabilities
    - Provides discovery information for tools and resources
    - Supports protocol extensions
    """
    server_name: str
    server_version: str
    supported_capabilities: List[str]
    available_tools: List[str] = Field(default_factory=list)
    available_resources: List[str] = Field(default_factory=list)
    capability_details: Optional[Dict[str, CapabilityDetail]] = None
    extensions: Optional[Dict[str, Any]] = None


def get_common_capabilities(client_capabilities: List[str], server_capabilities: List[str]) -> Set[str]:
    """
    [Function intent]
    Determines the intersection of capabilities supported by both client and server.
    
    [Design principles]
    - Simple utility function for capability intersection
    - Clear semantics for capability negotiation
    
    [Implementation details]
    - Uses set operations for clarity and efficiency
    
    Args:
        client_capabilities: List of capabilities supported by the client
        server_capabilities: List of capabilities supported by the server
        
    Returns:
        Set of capabilities supported by both client and server
    """
    return set(client_capabilities).intersection(set(server_capabilities))


def create_negotiation_request(
    client_name: str,
    client_version: str,
    capabilities: List[Union[str, ClientCapabilityType]],
    capability_details: Optional[Dict[str, CapabilityDetail]] = None,
    extensions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    [Function intent]
    Creates an MCP capability negotiation request following the specification.
    
    [Design principles]
    - Convenience function for creating properly structured requests
    - Handles enum conversion and validation
    
    [Implementation details]
    - Converts enum values to strings if needed
    - Creates a serializable dictionary
    
    Args:
        client_name: Identifying name of the client
        client_version: Client version string
        capabilities: List of capabilities supported by the client
        capability_details: Optional details for specific capabilities
        extensions: Optional extensions for future protocol versions
        
    Returns:
        A dictionary containing the negotiation request
    """
    # Convert any enum values to strings
    normalized_capabilities = [
        cap.value if isinstance(cap, ClientCapabilityType) else cap
        for cap in capabilities
    ]
    
    request = {
        "client_name": client_name,
        "client_version": client_version,
        "supported_capabilities": normalized_capabilities
    }
    
    if capability_details:
        request["capability_details"] = {
            name: detail.dict() if isinstance(detail, CapabilityDetail) else detail
            for name, detail in capability_details.items()
        }
        
    if extensions:
        request["extensions"] = extensions
    
    return request
