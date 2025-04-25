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
# This file implements session management for the MCP server, providing a way to
# track client sessions and their negotiated capabilities across multiple API requests.
# It maintains session state information and provides methods for session lifecycle management.
###############################################################################
# [Source file design principles]
# - Immutable session identifiers for consistent reference
# - Thread-safe session operations
# - Effective session lifecycle management with automatic expiration
# - Clean separation of session state from protocol handling
# - Minimal memory footprint with efficient cleanup
###############################################################################
# [Source file constraints]
# - Must be thread-safe for concurrent access
# - Must handle session expiration gracefully
# - Should avoid storing large amounts of data in session objects
# - Should minimize locking contention for high-concurrency scenarios
###############################################################################
# [Dependencies]
# - codebase:src/dbp/mcp_server/mcp/negotiation.py
# - system:pydantic
# - system:uuid
# - system:time
###############################################################################
# [GenAI tool change history]
# 2025-04-25T19:22:00Z : Initial implementation of session management by CodeAssistant
# * Created MCPSession model for tracking client sessions
# * Implemented SessionManager for lifecycle management
# * Added methods for session creation, validation, and cleanup
###############################################################################

import time
import uuid
import threading
from typing import Dict, Any, Set, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .negotiation import validate_capabilities


class MCPSession(BaseModel):
    """
    [Class intent]
    Represents an active MCP client session with negotiated capabilities,
    providing a persistent identity for a client across multiple requests.
    
    [Design principles]
    - Immutable session ID ensures consistent reference
    - Maintains minimal state needed for capability enforcement
    - Tracks activity for session expiration
    
    [Implementation details]
    - Uses UUID for globally unique session identification
    - Stores capability information from negotiation
    - Records timestamps for session lifecycle management
    """
    id: str
    client_name: str
    client_version: str
    client_capabilities: Set[str]
    created_at: float
    last_activity: float
    auth_context: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create(cls, client_name: str, client_version: str, capabilities: Set[str],
               auth_context: Optional[Dict[str, Any]] = None) -> "MCPSession":
        """
        [Class method intent]
        Creates a new session with a unique ID and current timestamps.
        
        [Design principles]
        Factory method pattern for clean instantiation with defaults.
        
        [Implementation details]
        Generates a UUID v4 for the session ID and sets timestamps.
        
        Args:
            client_name: Identifier of the client application
            client_version: Version string of the client
            capabilities: Set of capability strings the client supports
            auth_context: Optional authentication context for the session
            
        Returns:
            A new MCPSession instance
        """
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            client_name=client_name,
            client_version=client_version,
            client_capabilities=capabilities,
            created_at=now,
            last_activity=now,
            auth_context=auth_context
        )
    
    def update_activity(self) -> None:
        """
        [Class method intent]
        Updates the last activity timestamp to the current time.
        
        [Design principles]
        Simple method for tracking session use.
        
        [Implementation details]
        Sets last_activity to current time.time().
        """
        self.last_activity = time.time()
    
    def has_capability(self, capability: str) -> bool:
        """
        [Class method intent]
        Checks if the client has a specific capability.
        
        [Design principles]
        Simple lookup for capability enforcement.
        
        [Implementation details]
        Direct set membership test.
        
        Args:
            capability: The capability string to check
            
        Returns:
            True if the client has the specified capability, False otherwise
        """
        return capability in self.client_capabilities
    
    def has_capabilities(self, capabilities: List[str]) -> bool:
        """
        [Class method intent]
        Checks if the client has all of the specified capabilities.
        
        [Design principles]
        Reuses validation logic from negotiation module.
        
        [Implementation details]
        Delegates to validate_capabilities function.
        
        Args:
            capabilities: List of capability strings to check
            
        Returns:
            True if the client has all specified capabilities, False otherwise
        """
        return validate_capabilities(list(self.client_capabilities), capabilities)
    
    def is_expired(self, max_idle_seconds: int) -> bool:
        """
        [Class method intent]
        Determines if this session has expired due to inactivity.
        
        [Design principles]
        Simple time-based expiration check.
        
        [Implementation details]
        Compares current time against last activity plus timeout.
        
        Args:
            max_idle_seconds: Maximum allowed idle time in seconds
            
        Returns:
            True if the session has expired, False otherwise
        """
        return time.time() - self.last_activity > max_idle_seconds
    
    def get_age_seconds(self) -> float:
        """
        [Class method intent]
        Gets the total age of this session in seconds.
        
        [Design principles]
        Simple accessor for diagnostic purposes.
        
        [Implementation details]
        Calculates difference between current time and creation time.
        
        Returns:
            Float representing session age in seconds
        """
        return time.time() - self.created_at
    
    def get_idle_seconds(self) -> float:
        """
        [Class method intent]
        Gets the idle time of this session in seconds.
        
        [Design principles]
        Simple accessor for monitoring and cleanup.
        
        [Implementation details]
        Calculates difference between current time and last activity time.
        
        Returns:
            Float representing session idle time in seconds
        """
        return time.time() - self.last_activity


class SessionManager:
    """
    [Class intent]
    Manages the lifecycle of MCP sessions, providing thread-safe creation,
    retrieval, and cleanup of session objects.
    
    [Design principles]
    - Thread-safe operations for concurrent environments
    - Automatic session expiration and cleanup
    - Centralized session management separate from server logic
    
    [Implementation details]
    - Uses RLock for thread safety
    - Maintains an in-memory dictionary of active sessions
    - Supports automatic and manual session cleanup
    """
    def __init__(self, session_timeout_seconds: int = 3600):
        """
        [Class method intent]
        Initializes a new SessionManager with the specified timeout.
        
        [Design principles]
        Simple initialization with reasonable defaults.
        
        [Implementation details]
        Creates empty session storage and lock.
        
        Args:
            session_timeout_seconds: Time in seconds after which inactive sessions expire
        """
        self._sessions: Dict[str, MCPSession] = {}
        self._lock = threading.RLock()
        self._session_timeout = session_timeout_seconds
    
    def create_session(self, client_name: str, client_version: str, 
                       capabilities: Set[str], 
                       auth_context: Optional[Dict[str, Any]] = None) -> MCPSession:
        """
        [Class method intent]
        Creates and stores a new session with the provided client information.
        
        [Design principles]
        Thread-safe session creation and storage.
        
        [Implementation details]
        Delegates creation to MCPSession.create and stores the result.
        
        Args:
            client_name: Identifier of the client application
            client_version: Version string of the client
            capabilities: Set of capabilities the client supports
            auth_context: Optional authentication context
            
        Returns:
            The newly created MCPSession
        """
        session = MCPSession.create(
            client_name=client_name,
            client_version=client_version,
            capabilities=capabilities,
            auth_context=auth_context
        )
        
        with self._lock:
            self._sessions[session.id] = session
            
        return session
    
    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """
        [Class method intent]
        Retrieves a session by its ID and updates its activity timestamp.
        
        [Design principles]
        Thread-safe session retrieval with activity tracking.
        
        [Implementation details]
        Looks up session by ID and updates last_activity if found.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            The requested MCPSession if found and not expired, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session:
                # Check if session is expired
                if session.is_expired(self._session_timeout):
                    # Remove expired session
                    del self._sessions[session_id]
                    return None
                
                # Update activity timestamp
                session.update_activity()
                
            return session
    
    def remove_session(self, session_id: str) -> bool:
        """
        [Class method intent]
        Explicitly removes a session by its ID.
        
        [Design principles]
        Thread-safe session removal for explicit termination.
        
        [Implementation details]
        Removes session from the dictionary if it exists.
        
        Args:
            session_id: Unique identifier for the session to remove
            
        Returns:
            True if session was found and removed, False otherwise
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
                
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        [Class method intent]
        Removes all expired sessions from the session store.
        
        [Design principles]
        Periodic maintenance operation for memory management.
        
        [Implementation details]
        Identifies and removes sessions that have exceeded the timeout.
        
        Returns:
            Number of expired sessions that were removed
        """
        expired_ids = []
        
        # Identify expired sessions
        with self._lock:
            for session_id, session in self._sessions.items():
                if session.is_expired(self._session_timeout):
                    expired_ids.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_ids:
                del self._sessions[session_id]
        
        return len(expired_ids)
    
    def get_session_count(self) -> int:
        """
        [Class method intent]
        Gets the current number of active sessions.
        
        [Design principles]
        Simple accessor for monitoring.
        
        [Implementation details]
        Returns the length of the sessions dictionary.
        
        Returns:
            Integer count of active sessions
        """
        with self._lock:
            return len(self._sessions)
    
    def get_all_sessions(self) -> List[MCPSession]:
        """
        [Class method intent]
        Gets a list of all active sessions for diagnostic purposes.
        
        [Design principles]
        Creates a copy to avoid concurrent modification issues.
        
        [Implementation details]
        Returns a list copy of all session values.
        
        Returns:
            List of all active MCPSession objects
        """
        with self._lock:
            return list(self._sessions.values())


def create_anonymous_session() -> MCPSession:
    """
    [Function intent]
    Creates a session with minimal capabilities for clients that don't support negotiation.
    
    [Design principles]
    Provides backward compatibility for older clients.
    
    [Implementation details]
    Creates a session with basic capabilities and anonymous identity.
    
    Returns:
        An MCPSession with minimal capabilities
    """
    return MCPSession.create(
        client_name="anonymous",
        client_version="unknown",
        capabilities={"basic"}
    )
