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
# Implements the ApplyCommandHandler for the 'apply' CLI command, which allows
# users to apply a recommendation to fix an inconsistency between code and 
# documentation. Supports both direct application and dry-run modes.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'apply' command.
# - Provides a dry-run option to preview changes without applying them.
# - Offers option to create backup files before applying changes.
# - Displays a summary of applied changes.
# - Supports validation to ensure recommendations exist.
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'apply_recommendation' tool.
# - Requires write access to files being modified.
# - Changes could potentially affect multiple files simultaneously.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:09:00Z : Initial creation of ApplyCommandHandler by CodeAssistant
# * Implemented command handler for applying recommendations.
###############################################################################

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseCommandHandler
from ..exceptions import CommandError, APIError

logger = logging.getLogger(__name__)

class ApplyCommandHandler(BaseCommandHandler):
    """Handles the 'apply' command for applying recommendations to fix inconsistencies."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add apply-specific arguments to the parser."""
        # Required recommendation ID
        parser.add_argument(
            "recommendation_id",
            help="ID of the recommendation to apply"
        )
        
        # Options
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without actually applying changes"
        )
        parser.add_argument(
            "--backup",
            action="store_true",
            help="Create backup files before applying changes"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Apply changes without interactive confirmation"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the apply command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Log what we're about to do
            mode = "dry run" if args.dry_run else "apply"
            backup = " with backup" if args.backup else ""
            force = " (forced)" if args.force else ""
            
            self.output.info(f"Preparing to {mode} recommendation '{args.recommendation_id}'{backup}{force}")
            
            # Execute the API call with progress indicator
            result = self.with_progress(
                f"{'Simulating' if args.dry_run else 'Applying'} recommendation",
                self.mcp_client.apply_recommendation,
                recommendation_id=args.recommendation_id,
                dry_run=args.dry_run,
                create_backup=args.backup,
                force=args.force
            )
            
            # Process the result
            return self._process_result(result, args)
        
        except CommandError as e:
            self.output.error(str(e))
            return 1
        except Exception as e:
            return self.handle_api_error(e)
    
    def _process_result(self, result: Dict[str, Any], args: argparse.Namespace) -> int:
        """
        Process the result of applying a recommendation.
        
        Args:
            result: Result from the API call
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Check if the operation was successful
        if not result.get("success", False):
            error = result.get("error", "Unknown error")
            self.output.error(f"Failed to {('simulate' if args.dry_run else 'apply')} recommendation: {error}")
            return 1
        
        # Handle dry run result
        if args.dry_run:
            self.output.info("Dry run completed successfully.")
            self._display_changes(result.get("changes", []))
            self.output.info("\nTo apply these changes, run the command without --dry-run")
            return 0
        
        # Handle actual application result
        if result.get("applied", False):
            self.output.success("Recommendation applied successfully.")
            self._display_changes(result.get("changes", []))
            
            # Show any created backup files
            if args.backup and "backup_files" in result:
                backup_files = result.get("backup_files", [])
                if backup_files:
                    self.output.info("\nBackup files created:")
                    for backup in backup_files:
                        self.output.info(f"  - {backup}")
            
            return 0
        else:
            self.output.warning("Recommendation was not applied. No changes made.")
            return 1
    
    def _display_changes(self, changes: List[Dict[str, Any]]) -> None:
        """
        Display the changes made by applying a recommendation.
        
        Args:
            changes: List of changes
        """
        if not changes:
            self.output.info("No changes were made.")
            return
        
        self.output.info(f"\nChanges ({len(changes)}):")
        
        for i, change in enumerate(changes, 1):
            file_path = change.get("file", "Unknown file")
            change_type = change.get("type", "Unknown")
            
            self.output.info(f"\n{i}. {change_type} in {file_path}:")
            
            # Display different information based on change type
            if change_type == "MODIFICATION":
                self._display_modification(change)
            elif change_type == "ADDITION":
                self._display_addition(change)
            elif change_type == "DELETION":
                self._display_deletion(change)
            elif change_type == "RENAME":
                self._display_rename(change)
            else:
                # Generic display for unknown change types
                if "description" in change:
                    self.output.info(f"   {change['description']}")
                else:
                    self.output.info("   (No details available)")
    
    def _display_modification(self, change: Dict[str, Any]) -> None:
        """Display modification change details."""
        if "line_info" in change:
            line_info = change["line_info"]
            start_line = line_info.get("start", "?")
            end_line = line_info.get("end", "?")
            self.output.info(f"   Modified lines {start_line}-{end_line}")
        
        # Show diff if available
        if "diff" in change:
            self.output.info("   Diff:")
            for line in change["diff"].split("\n"):
                if line.startswith("+"):
                    self.output.print(f"   {self.output.colors.get('green', '')}{line}{self.output.colors.get('reset', '')}")
                elif line.startswith("-"):
                    self.output.print(f"   {self.output.colors.get('red', '')}{line}{self.output.colors.get('reset', '')}")
                else:
                    self.output.print(f"   {line}")
    
    def _display_addition(self, change: Dict[str, Any]) -> None:
        """Display addition change details."""
        if "content" in change:
            self.output.info("   Added content:")
            for line in change["content"].split("\n")[:10]:  # Limit to 10 lines
                self.output.print(f"   + {line}")
            
            if len(change["content"].split("\n")) > 10:
                self.output.info("   ... (content truncated)")
        
        if "line_info" in change:
            line_info = change["line_info"]
            position = line_info.get("position", "?")
            self.output.info(f"   Added at line {position}")
    
    def _display_deletion(self, change: Dict[str, Any]) -> None:
        """Display deletion change details."""
        if "line_info" in change:
            line_info = change["line_info"]
            start_line = line_info.get("start", "?")
            end_line = line_info.get("end", "?")
            self.output.info(f"   Deleted lines {start_line}-{end_line}")
        
        if "deleted_content" in change:
            self.output.info("   Deleted content:")
            for line in change["deleted_content"].split("\n")[:5]:  # Limit to 5 lines
                self.output.print(f"   - {line}")
            
            if len(change["deleted_content"].split("\n")) > 5:
                self.output.info("   ... (content truncated)")
    
    def _display_rename(self, change: Dict[str, Any]) -> None:
        """Display rename change details."""
        old_path = change.get("old_path", "Unknown")
        new_path = change.get("new_path", "Unknown")
        self.output.info(f"   Renamed from: {old_path}")
        self.output.info(f"   Renamed to:   {new_path}")
