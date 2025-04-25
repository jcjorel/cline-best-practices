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
# This file implements the MCP capability negotiation protocol that allows clients and servers
# to explicitly declare and negotiate their supported features at the beginning of a session.
# It defines the data models and core logic for capability tracking and validation according
# to the MCP specification.
###############################################################################
# [Source file design principles]
# - Strict protocol compliance with the MCP specification for capability negotiation
# - Clear separation of client and server capability types
# - Extensibility to support future capability additions
# - Immutable data models for capability declarations
# - Comprehensive type hints for IDE support and static analysis
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with existing MCP clients
# - Must support all capabilities described in the MCP specification
# - Should avoid introducing dependencies beyond standard library and Pydantic
###############################################################################
# [Dependencies]
# - codebase:src/dbp/mcp_server/mcp/__init__.py
# - system:pydantic
###############################################################################
# [GenAI tool change history]
# 2025-04-25T19:20:00Z : Initial implementation of capability negotiation module by CodeAssistant
# * Created data models for capability negotiation
# * Implemented capability types as enumerations
# * Added request/response models for negotiation protocol
###############################################################################

from enum import Enum
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel, Field


class ServerCapabilityType(Enum):
    """
    [Class intent]
    Defines the standard capability types that an MCP server can support,
    as specified in the MCP protocol.
    
    [Design principles]
    Uses enum for type safety and standardization of capability names.
    
    [Implementation details]
    String values match the exact capability names in the MCP specification.
    """
    TOOLS = "tools"
    RESOURCES = "resources"
    SUBSCRIPTIONS = "subscriptions"
    PROMPTS = "prompts"
    STREAMING = "streaming"
    NOTIFICATIONS = "notifications"
    
    # Additional capabilities beyond core spec
    BATCH_OPERATIONS = "batch_operations"
    HISTORY = "history"
    METRICS = "metrics"


class ClientCapabilityType(Enum):
    """
    [Class intent]
    Defines the standard capability types that an MCP client can support,
    as specified in the MCP protocol.
    
    [Design principles]
    Uses enum for type safety and standardization of capability names.
    
    [Implementation details]
    String values match the exact capability names in the MCP specification.
    """
    SAMPLING = "sampling"
    NOTIFICATIONS = "notifications"
    PROGRESS_TRACKING = "progress_tracking"
    CANCELLATION = "cancellation"
    STREAMING = "streaming"
    
    # Additional capabilities beyond core spec
    BATCH_REQUESTS = "batch_requests"
    SESSION_RESUME = "session_resume"


class CapabilityDetail(BaseModel):
    """
    [Class intent]
    Provides detailed information about a specific capability including
    version and parameter requirements.
    
    [Design principles]
    Uses Pydantic for data validation and serialization.
    
    [Implementation details]
    Includes optional parameters field for capabilities that require configuration.
    """
    name: str
    version: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


class NegotiationRequest(BaseModel):
    """
    [Class intent]
    Represents a client capability declaration request sent at session initialization
    to inform the server about supported capabilities.
    
    [Design principles]
    Follows MCP specification for negotiation requests.
    Uses Pydantic for validation and serialization/deserialization.
    
    [Implementation details]
    Includes client identification and extensibility fields for future protocol versions.
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
    Follows MCP specification for negotiation responses.
    Uses Pydantic for validation and serialization/deserialization.
    
    [Implementation details]
    Includes full listing of available tools and resources for client discovery.
    """
    server_name: str
    server_version: str
    supported_capabilities: List[str]
    available_tools: List[str]
    available_resources: List[str]
    capability_details: Optional[Dict[str, CapabilityDetail]] = None
    extensions: Optional[Dict[str, Any]] = None


def validate_capabilities(claimed_capabilities: List[str], required_capabilities: List[str]) -> bool:
    """
    [Function intent]
    Validates that a set of claimed capabilities satisfies a set of required capabilities.
    
    [Design principles]
    Simple, deterministic validation with clear pass/fail result.
    
    [Implementation details]
    Performs set-based comparison for efficient validation.
    
    Args:
        claimed_capabilities: List of capability strings claimed by a client
        required_capabilities: List of capability strings required for an operation
        
    Returns:
        bool: True if all required capabilities are present in claimed capabilities
    """
    claimed_set = set(claimed_capabilities)
    required_set = set(required_capabilities)
    
    return required_set.issubset(claimed_set)


def get_common_capabilities(client_capabilities: List[str], server_capabilities: List[str]) -> Set[str]:
    """
    [Function intent]
    Determines the intersection of capabilities supported by both client and server.
    
    [Design principles]
    Uses set operations for clarity and efficiency.
    
    [Implementation details]
    Returns a set to ensure uniqueness of capability names.
    
    Args:
        client_capabilities: List of capabilities supported by the client
        server_capabilities: List of capabilities supported by the server
        
    Returns:
        Set[str]: Set of capabilities supported by both client and server
    """
    return set(client_capabilities).intersection(set(server_capabilities))


def get_capability_metadata(capability_type: str) -> Dict[str, Any]:
    """
    [Function intent]
    Retrieves metadata about a specific capability type.
    
    [Design principles]
    Centralizes capability metadata to ensure consistency.
    
    [Implementation details]
    Returns a dictionary with predefined metadata for known capabilities.
    
    Args:
        capability_type: String identifier of the capability
        
    Returns:
        Dict[str, Any]: Dictionary containing capability metadata
    """
    # Default metadata structure
    metadata = {
        "description": "Unknown capability",
        "version": "1.0",
        "required": False,
        "default_enabled": True
    }
    
    # Capability-specific metadata
    capability_metadata = {
        # Server capabilities
        "tools": {
            "description": "Ability to execute tools",
            "required": True
        },
        "resources": {
            "description": "Ability to access resources"
        },
        "subscriptions": {
            "description": "Support for event subscriptions",
            "default_enabled": False
        },
        "streaming": {
            "description": "Support for streaming responses",
            "default_enabled": False
        },
        
        # Client capabilities
        "sampling": {
            "description": "Support for tool sampling"
        },
        "notifications": {
            "description": "Support for receiving notifications"
        },
        "progress_tracking": {
            "description": "Support for tracking operation progress"
        },
        "cancellation": {
            "description": "Support for cancelling operations"
        }
    }
    
    # Update with specific metadata if available
    if capability_type in capability_metadata:
        metadata.update(capability_metadata[capability_type])
    
    return metadata
