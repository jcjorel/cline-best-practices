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
# Implements the CommitCommandHandler for the 'commit' CLI command, which exposes
# the commit message generation functionality of the MCP server's dbp_commit_message tool.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'commit' command.
# - Provides options to control commit message generation.
# - Displays formatted results including supporting metadata.
# - Offers ability to save generated messages to file.
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'dbp_commit_message' tool.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/mcp_tools_refactoring_plan/plan_overview.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T10:12:00Z : Initial creation of CommitCommandHandler by CodeAssistant
# * Implemented command handler for commit message generation
###############################################################################

import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseCommandHandler
from ..exceptions import CommandError, APIError

logger = logging.getLogger(__name__)

class CommitCommandHandler(BaseCommandHandler):
    """Handles the 'commit' command for generating commit messages."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add commit-specific arguments to the parser."""
        # Core parameters
        parser.add_argument(
            "--since",
            metavar="COMMIT",
            help="Base commit to compare against (defaults to HEAD~1)"
        )
        parser.add_argument(
            "--files",
            metavar="FILES",
            nargs="+",
            help="Specific files to include in the commit message"
        )
        
        # Format options
        parser.add_argument(
            "--format",
            choices=["conventional", "detailed", "simple"],
            default="conventional",
            help="Format style for the commit message (default: conventional)"
        )
        parser.add_argument(
            "--no-scope",
            action="store_true",
            help="Exclude scope information in conventional format"
        )
        parser.add_argument(
            "--max-length",
            type=int,
            metavar="CHARS",
            help="Maximum length for the subject line"
        )
        
        # Content options
        parser.add_argument(
            "--no-breaking-changes",
            action="store_true",
            help="Don't include breaking changes in the message"
        )
        parser.add_argument(
            "--no-tests",
            action="store_true",
            help="Don't include test changes in the message"
        )
        parser.add_argument(
            "--no-issues",
            action="store_true",
            help="Don't include issue references in the message"
        )
        
        # Output options
        parser.add_argument(
            "--save",
            metavar="FILE",
            help="Save the commit message to a file"
        )
        parser.add_argument(
            "--message-only",
            action="store_true",
            help="Output only the commit message, not the supporting metadata"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the commit command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Prepare parameters
            params = self._prepare_parameters(args)
            
            # Log the operation
            since_commit = params.get("since_commit", "HEAD~1")
            self.output.info(f"Generating commit message (since {since_commit})")
            
            # Execute the API call with progress indicator
            result = self.with_progress(
                "Generating commit message",
                self.mcp_client.generate_commit_message,
                **params
            )
            
            # Check for successful result
            if "commit_message" not in result:
                self.output.error("Failed to generate commit message")
                return 1
            
            # Save to file if requested
            if args.save:
                try:
                    save_path = Path(args.save).expanduser().resolve()
                    
                    # Create directory if it doesn't exist
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write commit message to file
                    with open(save_path, "w") as f:
                        f.write(result["commit_message"])
                    
                    self.output.success(f"Commit message saved to {save_path}")
                
                except Exception as e:
                    self.output.error(f"Failed to save commit message: {e}")
                    return 1
            
            # Output the result
            if args.message_only:
                # Only show the commit message
                self.output.print(result["commit_message"])
            else:
                # Show full result
                self.output.format_output(result)
            
            return 0
            
        except CommandError as e:
            self.output.error(str(e))
            return 1
        except Exception as e:
            return self.handle_api_error(e)
    
    def _prepare_parameters(self, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Prepare parameters for the API call based on command arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Dictionary of parameters for the API call
        """
        params = {}
        
        # Handle since commit
        if args.since:
            params["since_commit"] = args.since
        
        # Handle files
        if args.files:
            params["files"] = args.files
        
        # Format options
        params["format"] = args.format
        params["include_scope"] = not args.no_scope
        
        if args.max_length:
            params["max_length"] = args.max_length
        
        # Content options
        params["include_breaking_changes"] = not args.no_breaking_changes
        params["include_tests"] = not args.no_tests
        params["include_issues"] = not args.no_issues
        
        return params
