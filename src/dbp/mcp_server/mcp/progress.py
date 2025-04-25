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
# Provides progress reporting functionality for MCP tools that perform long-running 
# operations. Implements the progress reporting specification from the MCP protocol.
###############################################################################
# [Source file design principles]
# - Simple callback-based progress reporting
# - Adheres to MCP progress reporting specification
# - Thread-safe implementation
# - Consistent logging fallback when no callback provided
###############################################################################
# [Source file constraints]
# - Progress values must be between 0.0 and 1.0
# - Must be lightweight and not block execution
# - Should gracefully handle cases with no callback
###############################################################################
# [Dependencies]
# system:logging
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:47:37Z : Created during mcp_protocols.py refactoring by CodeAssistant
# * Extracted MCPProgressReporter class from mcp_protocols.py
###############################################################################

import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class MCPProgressReporter:
    """
    [Class intent]
    Provides standard progress reporting functionality for MCP tools.
    
    [Design principles]
    - Implements MCP progress reporting specification
    - Provides consistent interface for reporting progress
    
    [Implementation details]
    - Uses a callback mechanism for sending progress updates
    - Supports progress percentage and optional message
    """
    callback: Optional[Callable[[float, Optional[str]], None]] = None
    
    def report_progress(self, progress: float, message: Optional[str] = None) -> None:
        """
        [Function intent]
        Reports the progress of a long-running tool execution.
        
        [Design principles]
        - Provides real-time feedback for long-running operations
        - Follows MCP progress reporting specification
        
        [Implementation details]
        - Validates progress value between 0.0 and 1.0
        - Calls the callback if provided
        
        Args:
            progress: A float between 0.0 and 1.0 representing execution progress
            message: An optional status message describing current progress
        """
        if progress < 0.0 or progress > 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")
            
        if self.callback:
            self.callback(progress, message)
        else:
            logger.debug(f"Progress: {progress*100:.1f}% - {message or ''}")
