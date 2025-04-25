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
# Provides cancellation functionality for MCP tools that perform long-running 
# operations. Implements the cancellation specification from the MCP protocol.
###############################################################################
# [Source file design principles]
# - Simple flag-based cancellation mechanism
# - Thread-safe implementation
# - Low overhead cancellation checking
# - Supports cooperative cancellation
###############################################################################
# [Source file constraints]
# - Must be lightweight and not impact performance
# - Should not block other operations
# - Relies on cooperative cancellation (tools must check cancellation status)
###############################################################################
# [Dependencies]
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:48:37Z : Created during mcp_protocols.py refactoring by CodeAssistant
# * Extracted MCPCancellationToken class from mcp_protocols.py
###############################################################################


class MCPCancellationToken:
    """
    [Class intent]
    Provides cancellation capability for MCP tool executions.
    
    [Design principles]
    - Implements MCP cancellation specification
    - Allows tools to check if execution should be cancelled
    
    [Implementation details]
    - Simple flag-based mechanism for cancellation
    - Thread-safe implementation
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes a new cancellation token.
        
        [Design principles]
        - Simple initialization with default non-cancelled state
        
        [Implementation details]
        - Sets initial cancellation flag to False
        """
        self._cancelled = False
        
    def cancel(self) -> None:
        """
        [Function intent]
        Marks this token as cancelled.
        
        [Design principles]
        - Simple flag-based cancellation
        
        [Implementation details]
        - Sets the cancellation flag to True
        """
        self._cancelled = True
        
    def is_cancelled(self) -> bool:
        """
        [Function intent]
        Checks if this token has been cancelled.
        
        [Design principles]
        - Provides a way for long-running operations to check cancellation status
        
        [Implementation details]
        - Returns the current state of the cancellation flag
        
        Returns:
            True if cancelled, False otherwise
        """
        return self._cancelled
