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
# Implements the MCPSession class for the Model Context Protocol (MCP) client.
# This class manages MCP sessions, including capability negotiation, shared context,
# and protocol versioning between the client and server.
###############################################################################
# [Source file design principles]
# - Centralized control point for MCP client-server session management
# - Handles capability negotiation following MCP specification
# - Maintains session state across multiple MCP operations
# - Provides consistent context for tools and resources
# - Enforces capability-based behavior modification
###############################################################################
# [Source file constraints]
# - Requires the base MCPClient for transport
# - Must properly handle capability negotiation and session initialization
# - Should maintain backward compatibility with servers lacking negotiation
# - Must respect declared server capabilities
###############################################################################
# [Dependencies]
# system:logging
# system:typing
# system:json
# codebase:src/dbp_cli/mcp/client.py
# codebase:src/dbp_cli/mcp/error.py
# codebase:src/dbp_cli/mcp/negotiation.py
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:14:00Z : Initial implementation of MCP session management by CodeAssistant
# * Created MCPSession class
# * Implemented capability negotiation
# * Added session state management
###############################################################################

import logging
from typing import Dict, Any, Optional, Set, List, Union

from .client import MCPClient
from .error import MCPError, MCPErrorCode
from .negotiation import (
    ClientCapabilityType, 
    ServerCapabilityType,
    NegotiationRequest, 
    NegotiationResponse,
    get_common_capabilities,
    create_negotiation_request
)


class MCPSession:
    """
    [Class intent]
    Manages an MCP communication session between client and server,
    handling capability negotiation, shared context, and session state.
    
    [Design principles]
    - Single point of control for session management
    - Tracks capabilities for appropriate feature usage
    - Maintains session state across operations
    
    [Implementation details]
    - Performs protocol handshake with capability exchange
    - Stores negotiated capabilities and session info
    - Provides capability-checking methods
    """
    
    MCP_VERSION = "1.0"
    CLIENT_NAME = "DBPCli-MCPClient"
    DEFAULT_CAPABILITIES = [
        ClientCapabilityType.CANCELLATION,
        ClientCapabilityType.PROGRESS_TRACKING,
        ClientCapabilityType.STREAMING
    ]
    
    def __init__(
        self, 
        client: MCPClient,
        client_version: str = "1.0",
        capabilities: Optional[List[Union[str, ClientCapabilityType]]] = None,
        skip_negotiation: bool = False,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        [Class method intent]
        Initializes a new MCP session and performs capability negotiation.
        
        [Design principles]
        - Automatic negotiation on initialization
        - Configurable client capabilities
        - Option to skip negotiation for backward compatibility
        
        [Implementation details]
        - Stores client and session state
        - Normalizes capability declarations
        - Performs negotiation unless skipped
        
        Args:
            client: The MCPClient instance for transport
            client_version: Version string for client identification
            capabilities: Optional list of supported capabilities (defaults to standard set)
            skip_negotiation: If True, skip capability negotiation
            logger_override: Optional logger instance
        """
        self.client = client
        self.client_version = client_version
        self.logger = logger_override or logging.getLogger(__name__)
        
        # Initialize session state
        self.server_name: Optional[str] = None
        self.server_version: Optional[str] = None
        self.server_capabilities: List[str] = []
        self.client_capabilities: List[str] = []
        self.common_capabilities: Set[str] = set()
        self.available_tools: List[str] = []
        self.available_resources: List[str] = []
        
        # Use default capabilities if none provided
        if capabilities is None:
            capabilities = self.DEFAULT_CAPABILITIES
            
        # Normalize client capabilities to strings
        self.client_capabilities = [
            cap.value if isinstance(cap, ClientCapabilityType) else cap
            for cap in capabilities
        ]
        
        # Perform initial capability negotiation
        self.session_active = False
        if not skip_negotiation:
            self.negotiate_capabilities()
            
    def negotiate_capabilities(self) -> NegotiationResponse:
        """
        [Function intent]
        Performs capability negotiation with the MCP server.
        
        [Design principles]
        - Follows MCP capability negotiation protocol
        - Handles negotiation errors gracefully
        - Updates session state based on response
        
        [Implementation details]
        - Creates a negotiation request with client capabilities
        - Sends request to server's negotiation endpoint
        - Updates session state with response data
        
        Returns:
            The server's negotiation response
            
        Raises:
            MCPError: If negotiation fails
        """
        try:
            # Create negotiation request
            request_data = create_negotiation_request(
                client_name=self.CLIENT_NAME,
                client_version=self.client_version,
                capabilities=self.client_capabilities
            )
            
            # Send negotiation request
            endpoint = "mcp/negotiate"
            self.logger.debug(f"Performing capability negotiation with {self.client.base_url}")
            response = self.client.send_request(
                method="POST",
                endpoint=endpoint,
                data=request_data
            )
            
            # Parse negotiation response
            neg_response = NegotiationResponse.parse_obj(response)
            
            # Update session state
            self.server_name = neg_response.server_name
            self.server_version = neg_response.server_version
            self.server_capabilities = neg_response.supported_capabilities
            self.available_tools = neg_response.available_tools
            self.available_resources = neg_response.available_resources
            self.common_capabilities = get_common_capabilities(
                self.client_capabilities, self.server_capabilities)
            
            self.session_active = True
            self.logger.debug(
                f"Negotiation successful with {self.server_name} v{self.server_version}. "
                f"Common capabilities: {', '.join(sorted(self.common_capabilities))}"
            )
            
            return neg_response
            
        except Exception as e:
            self.logger.error(f"Capability negotiation failed: {str(e)}")
            raise MCPError(
                MCPErrorCode.CAPABILITY_NEGOTIATION_ERROR,
                f"Failed to negotiate capabilities with server: {str(e)}"
            )
    
    def has_capability(self, capability: Union[str, ClientCapabilityType, ServerCapabilityType]) -> bool:
        """
        [Function intent]
        Checks if a specific capability is supported by both client and server.
        
        [Design principles]
        - Provides easy capability checking for feature usage
        - Handles both enum and string capability specifications
        
        [Implementation details]
        - Normalizes capability name to string
        - Checks against negotiated common capabilities
        
        Args:
            capability: The capability name to check
            
        Returns:
            True if the capability is supported, False otherwise
        """
        if isinstance(capability, (ClientCapabilityType, ServerCapabilityType)):
            capability = capability.value
            
        return capability in self.common_capabilities
    
    def is_active(self) -> bool:
        """
        [Function intent]
        Checks if the session is active with a successful negotiation.
        
        [Design principles]
        - Simple session state check
        - Allows conditional behavior based on session status
        
        [Implementation details]
        - Returns the session active flag
        
        Returns:
            True if the session is active, False otherwise
        """
        return self.session_active
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        [Function intent]
        Provides a summary of the current session state.
        
        [Design principles]
        - Centralized session information access
        - Complete session state representation
        
        [Implementation details]
        - Builds a dictionary with all session state information
        
        Returns:
            Dictionary with session state information
        """
        return {
            "active": self.session_active,
            "server": {
                "name": self.server_name,
                "version": self.server_version,
                "capabilities": self.server_capabilities
            },
            "client": {
                "name": self.CLIENT_NAME,
                "version": self.client_version,
                "capabilities": self.client_capabilities
            },
            "common_capabilities": list(self.common_capabilities),
            "available_tools": self.available_tools,
            "available_resources": self.available_resources
        }
