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
# Defines the base command handler abstract class that all CLI command handlers
# must inherit from. Provides common functionality and a standard interface for
# command execution.
###############################################################################
# [Source file design principles]
# - Uses abstract base class to enforce interface.
# - Provides common helper methods for all command handlers.
# - Simplifies command implementation by standardizing parameters and dependencies.
# - Takes dependencies via constructor for better testability.
# - Design Decision: Abstract Base Class (2025-04-15)
#   * Rationale: Enforces consistent interface across all command handlers.
#   * Alternatives considered: Function-based commands (less enforced structure), 
#     class-based without ABC (less explicit contract).
###############################################################################
# [Source file constraints]
# - Requires Python 3.8+ for TypedDict usage.
# - Command execution must return an integer exit code.
# - Must have explicit error handling within execute().
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:04:40Z : Initial creation of BaseCommandHandler by CodeAssistant
# * Implemented abstract base class with execute method and helper methods.
###############################################################################

import argparse
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..api import MCPClientAPI
from ..output import OutputFormatter
from ..progress import ProgressIndicator
from ..exceptions import CLIError, AuthenticationError, ConnectionError, APIError

logger = logging.getLogger(__name__)

class BaseCommandHandler(ABC):
    """
    Abstract base class for all CLI command handlers.
    Each command handler processes a specific CLI command.
    """
    
    def __init__(
        self, 
        mcp_client: MCPClientAPI, 
        output_formatter: OutputFormatter,
        progress_indicator: ProgressIndicator
    ):
        """
        Initializes a command handler with necessary dependencies.
        
        Args:
            mcp_client: Client for interacting with the MCP server API
            output_formatter: Formatter for command output
            progress_indicator: Progress indicator for long-running operations
        """
        self.mcp_client = mcp_client
        self.output = output_formatter
        self.progress = progress_indicator
        self.logger = logger.getChild(self.__class__.__name__)
        
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """
        Executes the command with the provided arguments.
        
        Args:
            args: Command-line arguments from argparse
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        pass
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Adds command-specific arguments to the parser.
        Override this method to define command-specific arguments.
        
        Args:
            parser: The argparse parser for this command
        """
        pass
    
    def with_progress(self, message: str, func, *args, **kwargs):
        """
        Executes a function with progress indicator.
        
        Args:
            message: Message to display during execution
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function execution
        """
        try:
            self.progress.start(message)
            return func(*args, **kwargs)
        finally:
            self.progress.stop()
            
    def handle_api_error(self, error: Exception) -> int:
        """
        Handles API-related errors and returns appropriate exit code.
        
        Args:
            error: The exception to handle
            
        Returns:
            Exit code corresponding to the error type
        """
        if isinstance(error, AuthenticationError):
            self.output.error(f"Authentication error: {error}")
            return 3
        elif isinstance(error, ConnectionError):
            self.output.error(f"Connection error: {error}")
            return 4
        elif isinstance(error, APIError):
            self.output.error(f"API error: {error}")
            return 5
        else:
            self.output.error(f"Unexpected error: {error}")
            return 1
