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
    [Class intent]
    Abstract base class for all CLI command handlers, providing the foundation
    for implementing specific command operations in a consistent way.
    
    [Implementation details]
    Defines the core command handler interface with abstract execute() method
    that command implementations must override. Provides helper methods for
    common operations like progress indication and error handling that are 
    shared across all command handlers.
    
    [Design principles]
    Interface standardization - enforces consistent behavior across all command handlers.
    Abstract base class pattern - defines a clear contract for subclasses.
    Shared utility methods - centralizes common functionality to avoid duplication.
    Error classification - provides standardized error handling with specific exit codes.
    """
    
    def __init__(
        self, 
        mcp_client: MCPClientAPI, 
        output_formatter: OutputFormatter,
        progress_indicator: ProgressIndicator
    ):
        """
        [Function intent]
        Initialize a command handler with all required dependencies for command execution.
        
        [Implementation details]
        Sets up instance variables for API client access, output formatting, and progress indication.
        Creates a child logger specific to the concrete command handler class for proper log hierarchy.
        
        [Design principles]
        Dependency injection - receives all dependencies through constructor for testability.
        Consistent naming - uses descriptive instance variable names matching parameter names.
        Hierarchical logging - creates a child logger for each command handler instance.
        
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
        [Function intent]
        Execute the command with the provided arguments and return an exit code.
        
        [Implementation details]
        This is an abstract method that must be implemented by concrete command handlers.
        Each implementation should process the command-specific arguments and perform
        the operations required by that command.
        
        [Design principles]
        Command pattern - each command handler implements specific command logic.
        Standard exit codes - 0 for success, non-zero for different error types.
        Clear contract - enforces consistent interface across all command handlers.
        
        Args:
            args: Command-line arguments from argparse
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        pass
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        [Function intent]
        Configure the argument parser with command-specific arguments.
        
        [Implementation details]
        Default implementation is empty. Subclasses should override this method
        to add their specific command-line arguments to the provided parser.
        
        [Design principles]
        Template method pattern - default implementation that can be overridden.
        Consistent interface - all command handlers use the same method signature.
        
        Args:
            parser: The argparse parser for this command
        """
        pass
    
    def with_progress(self, message: str, func, *args, **kwargs):
        """
        [Function intent]
        Execute a function while displaying a progress indicator, then return the result.
        
        [Implementation details]
        Starts the progress indicator with the provided message, executes the function
        with the given arguments, ensures the progress indicator is stopped when complete
        (even if an exception occurs), then returns the function's result.
        
        [Design principles]
        Resource management - uses try/finally to ensure progress indicator cleanup.
        Functional transparency - preserves and returns the original function result.
        Reusable utility - centralizes progress indication logic for all command handlers.
        
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
        [Function intent]
        Classify and handle API-related errors with appropriate user feedback and exit codes.
        
        [Implementation details]
        Checks the error type against known API error classes and provides specific
        error messages and exit codes based on the type of error encountered.
        Maps error types to standardized exit codes:
        - Authentication errors: 3
        - Connection errors: 4
        - API errors: 5
        - Other errors: 1
        
        [Design principles]
        Standardized error handling - consistent error reporting and exit codes.
        Error classification - differentiates between different API error types.
        User-friendly feedback - displays useful error messages for troubleshooting.
        
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
