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
# Provides an adapter class to integrate Click-based command groups with the main
# CLI framework. This adapter allows Click command groups to be used within the
# DocumentationProgrammingCLI architecture.
###############################################################################
# [Source file design principles]
# - Adapter pattern to bridge incompatible interfaces
# - Clean separation between Click and argparse frameworks
# - Transparent delegation to the Click command group
# - Preserves the existing CLI architecture while enabling integration of Click commands
###############################################################################
# [Source file constraints]
# - Must implement the BaseCommandHandler interface
# - Should handle all Click group functionality correctly
# - Must maintain compatibility with the CLI's error handling mechanism
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T09:00:00Z : Enhanced Click subcommand handling by CodeAssistant
# * Fixed subcommand discovery and execution
# * Improved Click context handling with proper execution
# * Added better argument extraction from sys.argv
# 2025-05-12T06:56:11Z : Created ClickGroupAdapter to fix CLI integration by CodeAssistant
# * Implemented adapter to bridge Click command groups with the CLI framework
# * Fixed AttributeError and UnboundLocalError in the main CLI
###############################################################################

import argparse
import logging
import sys
from typing import Any, Callable

from .base import BaseCommandHandler
from ..api import MCPClientAPI
from ..output import OutputFormatter
from ..progress import ProgressIndicator

logger = logging.getLogger(__name__)

class ClickGroupAdapter(BaseCommandHandler):
    """
    [Class intent]
    Adapter that wraps a Click command group to make it compatible with the
    DocumentationProgrammingCLI architecture by implementing the BaseCommandHandler
    interface.
    
    [Implementation details]
    Implements the BaseCommandHandler interface while delegating the actual
    command execution to the wrapped Click command group. Instead of using
    argparse directly, it passes the command line arguments to the Click
    command group.
    
    [Design principles]
    Adapter pattern - wraps an existing Click command group without modifying it.
    Interface compliance - implements the required BaseCommandHandler interface.
    Delegation - forwards the execution to the Click command group.
    """
    
    def __init__(
        self, 
        click_group: Callable,
        mcp_client: MCPClientAPI, 
        output_formatter: OutputFormatter,
        progress_indicator: ProgressIndicator
    ):
        """
        [Function intent]
        Initialize the adapter with a Click command group and the standard
        BaseCommandHandler dependencies.
        
        [Implementation details]
        Stores the Click command group and initializes the base class with the
        standard dependencies required by all command handlers.
        
        [Design principles]
        Dependency injection - receives all required components via constructor.
        Composition over inheritance - contains the Click group as a delegate.
        
        Args:
            click_group: The Click command group function to wrap
            mcp_client: Client for interacting with the MCP server API
            output_formatter: Formatter for command output
            progress_indicator: Progress indicator for long-running operations
        """
        super().__init__(mcp_client, output_formatter, progress_indicator)
        self.click_group = click_group
        self.__doc__ = click_group.__doc__  # Copy the docstring from the Click group
        
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        [Function intent]
        Add a placeholder argument to indicate that the command is handled by Click.
        
        [Implementation details]
        This method is required by the BaseCommandHandler interface but doesn't
        need to add any arguments since the Click command group handles its own
        argument parsing.
        
        [Design principles]
        Interface compliance - implements the required method from BaseCommandHandler.
        Minimal implementation - avoids interfering with Click's argument parsing.
        
        Args:
            parser: The argparse parser for this command
        """
        # No need to add arguments for Click commands
        # They handle their own argument parsing
        pass
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Execute the wrapped Click command group with the provided arguments.
        
        [Implementation details]
        Extracts the original command line arguments from sys.argv and passes them
        to the Click command group for execution. Handles any exceptions that might
        occur during execution.
        
        [Design principles]
        Delegation - forwards execution to the Click command group.
        Error handling - catches and handles exceptions properly.
        
        Args:
            args: Command-line arguments from argparse
            
        Returns:
            Exit code from the Click command execution
        """
        try:
            # Extract the command from sys.argv and execute the Click group
            # Get the original command line arguments
            if hasattr(args, 'subcommand') and args.subcommand:
                # If we have a subcommand, use it
                cli_args = [args.command, args.subcommand]
            else:
                # Otherwise just use the command
                cli_args = [args.command]
                
            # Add any additional arguments from sys.argv that follow the command
            cmd_index = sys.argv.index(args.command)
            if cmd_index < len(sys.argv) - 1:
                cli_args.extend(sys.argv[cmd_index + 1:])
            
            # Log the arguments being passed to Click
            self.logger.debug(f"Executing Click group with arguments: {cli_args}")
            
            # Import Click context to properly invoke the command group
            import click
            ctx = click.Context(self.click_group)
            
            # Execute the Click command group
            with ctx:
                result = self.click_group.main(args=cli_args[1:], prog_name=cli_args[0], standalone_mode=False)
                return result or 0
        except Exception as e:
            # Handle exceptions from the Click command group
            self.logger.error(f"Error executing Click command group: {e}", exc_info=True)
            self.output.error(f"Error executing '{args.command}': {str(e)}")
            return 1
