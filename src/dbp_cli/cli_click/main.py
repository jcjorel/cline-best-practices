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
# Defines the main Click command group and entry point for the Click-based CLI
# implementation. This file serves as the primary entry point for the CLI and
# handles command registration, initialization, and execution.
###############################################################################
# [Source file design principles]
# - Acts as the main entry point for the Click-based CLI application
# - Centralizes command registration and initialization
# - Defines the main command group and subcommands
# - Provides clean entry point with proper error handling
# - Separates CLI concerns from business logic
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with existing CLI behavior
# - Exit codes should follow standard conventions (0 success, non-zero failure)
# - Command execution must properly handle all error conditions
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T01:47:30Z : Fixed duplicate error messages for command suggestions by CodeAssistant
# * Fixed issue where "Usage error" appeared twice in the output
# * Improved error handling logic to avoid duplicated messages
# 2025-05-13T01:42:20Z : Added "Did you mean?" command suggestion feature by CodeAssistant
# * Added get_command_suggestions function to find similar commands
# * Enhanced error handling to show suggestions for mistyped commands
# * Improved user experience with helpful error messages
# 2025-05-12T21:05:07Z : Removed status command by CodeAssistant
# * Removed import for status_command
# * Removed status_command registration from cli command group
# * Removed obsolete status.py file
# 2025-05-12T17:20:50Z : Fixed decorator order by CodeAssistant
# * Rearranged decorators to ensure @pass_context is applied before @common_options
###############################################################################

import logging
import sys
from typing import Optional, List, Any, Dict, Set

import click
from difflib import get_close_matches

# Import common utilities and context
from .common import AppContext, common_options, catch_errors  # Using AppContext instead of Context

# Import commands
from .commands.query import query_command
from .commands.config import config_group
from .commands.commit import commit_command
from .commands.hstc_agno import hstc_agno_group
from .commands.server import server_group
from .commands.test import test_group

# Set up logger
logger = logging.getLogger(__name__)


@click.group(
    help="Documentation-Based Programming CLI",
    context_settings={
        "help_option_names": ["--help", "-h"],
        "auto_envvar_prefix": "DBP_CLI",
    }
)
@click.pass_context  # Using Click's native context decorator
@common_options
def cli(ctx: click.Context) -> None:
    """
    [Function intent]
    Serve as the main entry point for the Click-based CLI and initialize the context.
    
    [Implementation details]
    Creates the main command group that serves as the root for all subcommands.
    Initializes the AppContext object in the Click context's obj attribute.
    Applies common options to all commands through the common_options decorator.
    
    [Design principles]
    Centralized entry point - single starting point for all commands.
    Context initialization - sets up application context for use by all commands.
    Consistent options - applies common options to all commands.
    Native context usage - uses Click's context object properly.
    """
    # Initialize AppContext in Click's context if needed
    # The common_options decorator will handle the rest
    if not hasattr(ctx, 'obj') or ctx.obj is None:
        ctx.obj = AppContext()


# Register commands
cli.add_command(query_command)
cli.add_command(config_group)
cli.add_command(commit_command)
cli.add_command(hstc_agno_group)
cli.add_command(server_group)
cli.add_command(test_group)


@cli.command("version")
@click.pass_context
def version_command(ctx: click.Context) -> None:
    """
    [Function intent]
    Display version information about the CLI application.
    
    [Implementation details]
    Retrieves version information from package metadata and displays it.
    Provides a standalone command that doesn't require API initialization.
    
    [Design principles]
    Simple utility command - quick access to version information.
    Informational command - doesn't modify any state.
    """
    version = ctx.obj.get_version()
    if ctx.obj.output_formatter:
        ctx.obj.output_formatter.print(f"dbp-cli version {version}")


def main(args: Optional[List[str]] = None) -> int:
    """
    [Function intent]
    Execute the CLI application with the provided arguments and return an exit code.
    
    [Implementation details]
    Invokes the Click command group with the provided arguments or sys.argv if none.
    Catches and handles any exceptions that weren't caught by command handlers.
    Returns appropriate exit codes for different types of errors.
    
    [Design principles]
    Clean entry point - single function for executing the CLI.
    Robust error handling - catches and reports all exceptions appropriately.
    Standard exit codes - returns 0 for success, non-zero for errors.
    
    Args:
        args: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Let Click handle the context creation and passing
        return cli.main(args=args, standalone_mode=False) or 0
    except click.Abort:
        # Handle Ctrl+C gracefully
        logger.info("Operation cancelled by user")
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130  # Convention for Ctrl+C
    except click.UsageError as e:
        # Handle usage errors (invalid arguments, etc.)
        error_msg = str(e)
        
        # Check if this is a command not found error and suggest alternatives
        if "No such command" in error_msg:
            command = error_msg.split("'")[1] if "'" in error_msg else ""
            if command:
                suggestions = get_command_suggestions(command)
                if suggestions:
                    suggestion = suggestions[0]
                    # Only log the error once, don't print it
                    logger.error(f"Usage error: No such command '{command}'")
                    
                    # Print the suggestion to stderr
                    print(f"Usage error: No such command '{command}'.", file=sys.stderr)
                    print(f"Did you mean '{suggestion}'?", file=sys.stderr)
                    return 2
        
        # For other usage errors or when no suggestions are found
        logger.error(f"Usage error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except click.BadParameter as e:
        # Handle invalid parameter values
        logger.error(f"Bad parameter: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


def get_command_suggestions(command: str) -> List[str]:
    """
    [Function intent]
    Find similar command names for a given mistyped command.
    
    [Implementation details]
    Collects all available command names from the CLI command group and uses
    difflib's get_close_matches to find similar command names based on string similarity.
    
    [Design principles]
    User-friendly errors - helps users recover from common typos.
    Simple heuristic - uses standard library for string similarity without complex logic.
    
    Args:
        command: The mistyped command name
        
    Returns:
        List of command suggestions, sorted by similarity
    """
    # Get all available commands
    available_commands = set()
    for cmd_name in cli.commands.keys():
        available_commands.add(cmd_name)
        
    # Find commands that start with the given prefix (for subcommands)
    if ' ' in command:
        parts = command.split(' ')
        prefix = parts[0]
        if prefix in cli.commands:
            subcommand = cli.commands[prefix]
            if hasattr(subcommand, 'commands'):
                for subcmd_name in subcommand.commands.keys():
                    available_commands.add(f"{prefix} {subcmd_name}")
    
    # Get close matches
    return get_close_matches(command, list(available_commands), n=3, cutoff=0.6)


if __name__ == "__main__":
    sys.exit(main())
