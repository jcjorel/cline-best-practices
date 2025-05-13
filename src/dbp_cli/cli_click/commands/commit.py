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
# Implements the Click-based 'commit' CLI command, which exposes the commit
# message generation functionality of the MCP server's dbp_commit_message tool.
###############################################################################
# [Source file design principles]
# - Uses Click decorators for command definition and option handling
# - Maintains compatibility with original commit command behavior
# - Provides options to control commit message generation
# - Displays formatted results including supporting metadata
# - Offers ability to save generated messages to file
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'dbp_commit_message' tool
# - Must preserve exact functionality from the original command
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T01:38:00Z : Fixed import statements for proper module resolution by CodeAssistant
# * Changed relative imports (from ...exceptions) to absolute imports (from dbp_cli.exceptions)
# * Fixed ImportError: attempted relative import beyond top-level package
# 2025-05-12T18:36:13Z : Fixed decorator order by CodeAssistant
# * Rearranged decorators to ensure @pass_context is applied first
# * Fixed "commit_command() missing 1 required positional argument: 'ctx'" error
# 2025-05-12T15:52:59Z : Initial creation of Click-based commit command by CodeAssistant
# * Implemented commit command with all options and functionality
# * Maintained compatibility with original command behavior
###############################################################################

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import click

from ..common import catch_errors, api_command, get_output_adapter
from dbp_cli.exceptions import CommandError

logger = logging.getLogger(__name__)


@click.command(
    name="commit",
    help="Generate commit messages based on changes",
    short_help="Generate commit messages",
)
@click.option(
    "--since",
    metavar="COMMIT",
    help="Base commit to compare against (defaults to HEAD~1)",
)
@click.option(
    "--files",
    metavar="FILES",
    multiple=True,
    help="Specific files to include in the commit message",
)
@click.option(
    "--format",
    type=click.Choice(["conventional", "detailed", "simple"]),
    default="conventional",
    help="Format style for the commit message (default: conventional)",
)
@click.option(
    "--no-scope",
    is_flag=True,
    help="Exclude scope information in conventional format",
)
@click.option(
    "--max-length",
    type=int,
    metavar="CHARS",
    help="Maximum length for the subject line",
)
@click.option(
    "--no-breaking-changes",
    is_flag=True,
    help="Don't include breaking changes in the message",
)
@click.option(
    "--no-tests",
    is_flag=True,
    help="Don't include test changes in the message",
)
@click.option(
    "--no-issues",
    is_flag=True,
    help="Don't include issue references in the message",
)
@click.option(
    "--save",
    metavar="FILE",
    help="Save the commit message to a file",
)
@click.option(
    "--message-only",
    is_flag=True,
    help="Output only the commit message, not the supporting metadata",
)
@click.pass_context
@api_command
@catch_errors
def commit_command(
    ctx: click.Context,
    since: Optional[str],
    files: Optional[List[str]],
    format: str,
    no_scope: bool,
    max_length: Optional[int],
    no_breaking_changes: bool,
    no_tests: bool,
    no_issues: bool,
    save: Optional[str],
    message_only: bool,
) -> int:
    """
    [Function intent]
    Generate a commit message based on changes in a git repository.
    
    [Implementation details]
    Processes command options and prepares parameters for the API call.
    Calls the MCP server's dbp_commit_message tool to generate a commit message.
    Displays the result and optionally saves it to a file.
    
    [Design principles]
    User control - provides options to customize the commit message generation.
    Progressive output - shows progress during generation.
    Flexible formatting - supports different commit message formats.
    File persistence - allows saving the message to a file.
    
    Args:
        ctx: Click's context object with application context in obj attribute
        since: Base commit to compare against
        files: Specific files to include in the commit message
        format: Format style for the commit message
        no_scope: Whether to exclude scope information in conventional format
        max_length: Maximum length for the subject line
        no_breaking_changes: Whether to exclude breaking changes
        no_tests: Whether to exclude test changes
        no_issues: Whether to exclude issue references
        save: Path to save the commit message to
        message_only: Whether to output only the commit message
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    try:
        # Prepare parameters
        params = _prepare_parameters(since, files, format, no_scope, max_length,
                                    no_breaking_changes, no_tests, no_issues)
        
        # Log the operation
        since_commit = params.get("since_commit", "HEAD~1")
        output.info(f"Generating commit message (since {since_commit})")
        
        # Execute the API call with progress indicator
        result = ctx.obj.with_progress(
            "Generating commit message",
            ctx.obj.api_client.generate_commit_message,
            **params
        )
        
        # Check for successful result
        if "commit_message" not in result:
            output.error("Failed to generate commit message")
            return 1
        
        # Save to file if requested
        if save:
            try:
                save_path = Path(save).expanduser().resolve()
                
                # Create directory if it doesn't exist
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write commit message to file
                with open(save_path, "w") as f:
                    f.write(result["commit_message"])
                
                output.success(f"Commit message saved to {save_path}")
            
            except Exception as e:
                output.error(f"Failed to save commit message: {e}")
                return 1
        
        # Output the result
        if message_only:
            # Only show the commit message
            output.print(result["commit_message"])
        else:
            # Show full result
            output.format_output(result)
        
        return 0
        
    except CommandError as e:
        output.error(str(e))
        return 1


def _prepare_parameters(
    since: Optional[str],
    files: Optional[List[str]],
    format_style: str,
    no_scope: bool,
    max_length: Optional[int],
    no_breaking_changes: bool,
    no_tests: bool,
    no_issues: bool,
) -> Dict[str, Any]:
    """
    [Function intent]
    Prepare parameters for the API call based on command arguments.
    
    [Implementation details]
    Converts command options into a dictionary of parameters for the API call.
    Handles optional parameters and flag conversions (e.g., no_ prefixes to include_ parameters).
    
    [Design principles]
    Clean parameter mapping - converts CLI options to API parameters.
    Consistent conventions - handles negation prefixes predictably.
    
    Args:
        since: Base commit to compare against
        files: Specific files to include in the commit message
        format_style: Format style for the commit message
        no_scope: Whether to exclude scope information
        max_length: Maximum length for the subject line
        no_breaking_changes: Whether to exclude breaking changes
        no_tests: Whether to exclude test changes
        no_issues: Whether to exclude issue references
        
    Returns:
        Dictionary of parameters for the API call
    """
    params = {}
    
    # Handle since commit
    if since:
        params["since_commit"] = since
    
    # Handle files
    if files and len(files) > 0:
        params["files"] = list(files)
    
    # Format options
    params["format"] = format_style
    params["include_scope"] = not no_scope
    
    if max_length:
        params["max_length"] = max_length
    
    # Content options
    params["include_breaking_changes"] = not no_breaking_changes
    params["include_tests"] = not no_tests
    params["include_issues"] = not no_issues
    
    return params
