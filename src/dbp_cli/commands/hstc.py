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
# Implements the CLI command for HSTC operations, allowing users to update
# HSTC.md files and source code documentation from the command line.
###############################################################################
# [Source file design principles]
# - User-friendly CLI interface with clear options
# - Informative feedback and progress reporting
# - Direct integration with the HSTC component
# - Support for dry-run mode to preview changes
###############################################################################
# [Source file constraints]
# - Must follow DBP CLI command structure and conventions
# - Must handle large directory trees efficiently
# - Must provide clear feedback on operation results
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/base.py
# codebase:src/dbp/hstc/component.py
# system:argparse
# system:pathlib
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-07T16:19:21Z : Enhanced file preview in dry-run mode by CodeAssistant
# * Added display of complete updated file content in dry-run mode
# * Improved documentation for _display_file_preview method
# * Enhanced user feedback for better visibility of proposed changes
# 2025-05-07T12:55:14Z : Enhanced update-file command with direct console logging by CodeAssistant
# * Added direct stderr/stdout logging to ensure visibility regardless of logging configuration
# * Implemented file existence validation before processing
# * Added graceful interrupt handling to ensure clean termination
# * Enhanced error reporting with exception type information
# 2025-05-07T11:56:00Z : Initial implementation of HSTC CLI command by CodeAssistant
# * Created CLI command class with command-line options
# * Implemented execution logic for HSTC operations
# * Added formatting for operation results
###############################################################################

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from dbp_cli.commands.base import BaseCommandHandler
from dbp_cli.output import OutputFormatter
from dbp.hstc.component import HSTCComponent


class HSTCCommand(BaseCommandHandler):
    """
    [Class intent]
    Provides a command-line interface for HSTC operations, allowing users to
    update HSTC.md files and source code documentation from the command line.
    
    [Design principles]
    User-friendly interface with clear command structure.
    Informative feedback with appropriate detail level.
    Direct integration with the HSTC component for operations.
    
    [Implementation details]
    Uses the Command base class for consistent CLI structure.
    Creates and initializes an HSTCComponent instance.
    Formats and displays operation results.
    """
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        [Function intent]
        Configure the argument parser with HSTC command-specific arguments.
        
        [Design principles]
        Clear command structure with logical option grouping.
        Comprehensive help text for usability.
        
        [Implementation details]
        Creates subparsers for different HSTC operations.
        Sets up command-line arguments with appropriate types and defaults.
        
        Args:
            parser: The argparse parser for this command
        """
        # Create subcommands
        sub_subparsers = parser.add_subparsers(
            dest="hstc_command",
            help="HSTC operation to perform",
            required=True
        )
        
        # Register subcommands
        self._register_update_command(sub_subparsers)
        self._register_update_file_command(sub_subparsers)
        
    def _register_update_command(self, subparsers):
        """
        [Function intent]
        Registers the 'update' subcommand for updating HSTC.md files.
        
        [Design principles]
        Focused command for directory tree processing.
        Clear options for directory selection and dry-run mode.
        
        [Implementation details]
        Creates a subparser for the update command.
        Sets up command-line arguments with appropriate types and defaults.
        
        Args:
            subparsers: Subparser collection to add the command to
        """
        parser = subparsers.add_parser(
            "update",
            help="Update HSTC.md files in a directory tree",
            description="Scan for and update HSTC.md files in a directory tree"
        )
        
        # Add arguments
        parser.add_argument(
            "--directory", "-d",
            type=str,
            default=None,
            help="Directory to process (default: current directory)"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them"
        )
    
    def _register_update_file_command(self, subparsers):
        """
        [Function intent]
        Registers the 'update-file' subcommand for updating a single source file.
        
        [Design principles]
        Focused command for single file processing.
        Clear options for file selection and dry-run mode.
        
        [Implementation details]
        Creates a subparser for the update-file command.
        Sets up command-line arguments with appropriate types and defaults.
        
        Args:
            subparsers: Subparser collection to add the command to
        """
        parser = subparsers.add_parser(
            "update-file",
            help="Update documentation in a single source file",
            description="Update documentation in a single source file to match project standards"
        )
        
        # Add arguments
        parser.add_argument(
            "file",
            type=str,
            help="Path to the source file to update"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Executes the HSTC command with the provided arguments.
        
        [Design principles]
        Clean command execution with appropriate error handling.
        Consistent return codes for automation support.
        Informative output formatting for user feedback.
        
        [Implementation details]
        Creates and initializes an HSTCComponent instance.
        Dispatches to the appropriate handler based on the subcommand.
        Formats and displays results.
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        try:
            # Create and initialize component
            component = HSTCComponent()
            
            # Note: We're bypassing the component system here
            # by manually initializing the component
            component.logger = self.logger.getChild("hstc")
            component._manager = None
            component._initialized = True
            
            # Import here to avoid circular import
            from dbp.hstc.manager import HSTCManager
            component._manager = HSTCManager(logger=component.logger)
            
            # Dispatch to appropriate handler
            if args.hstc_command == "update":
                return self._execute_update(args, component)
            elif args.hstc_command == "update-file":
                return self._execute_update_file(args, component)
            else:
                self.output.error(f"Unknown HSTC command: {args.hstc_command}")
                return 1
                
        except Exception as e:
            self.output.error(f"Error executing HSTC command: {str(e)}")
            
            # Print stack trace if debug mode is enabled
            if hasattr(args, 'debug') and args.debug:
                import traceback
                print("\nStack trace:", file=sys.stderr)
                traceback.print_exc()
                
            return 1
    
    def _execute_update(self, args: argparse.Namespace, component: HSTCComponent) -> int:
        """
        [Function intent]
        Executes the 'update' subcommand to update HSTC.md files.
        
        [Design principles]
        Clear progress feedback.
        Detailed results reporting.
        
        [Implementation details]
        Calls the component's update_hstc method.
        Formats and displays results.
        
        Args:
            args: Command-line arguments
            component: HSTC component instance
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        # Get directory path
        directory_path = args.directory
        
        # Display operation information
        if args.dry_run:
            self.output.print(f"Previewing HSTC updates in {'current directory' if directory_path is None else directory_path}")
        else:
            self.output.print(f"Updating HSTC files in {'current directory' if directory_path is None else directory_path}")
        
        # Perform update
        result = component.update_hstc(
            directory_path=directory_path,
            dry_run=args.dry_run
        )
        
        # Check for error
        if result.get("status") == "error":
            self.output.error(result.get("message", "Unknown error"))
            return 1
            
        # Display summary
        self.output.print("")
        self.output.print("Update Summary:")
        self.output.print(f"  Directories scanned: {result.get('directories_scanned', 0)}")
        self.output.print(f"  Directories updated: {result.get('directories_updated', 0)}")
        self.output.print(f"  Directories with errors: {result.get('directories_with_errors', 0)}")
        
        # Display detailed results
        if args.dry_run:
            self._display_detailed_preview(result.get("results", []))
            
        # Display status
        if result.get("status") == "unchanged":
            self.output.print("\nNo directories needed updates.")
        elif result.get("directories_with_errors", 0) > 0:
            self.output.warning(f"\nUpdated with {result.get('directories_with_errors', 0)} errors.")
            return 1
        else:
            self.output.print("\nUpdate completed successfully.")
            
        return 0
    
    def _execute_update_file(self, args: argparse.Namespace, component: HSTCComponent) -> int:
        """
        [Function intent]
        Executes the 'update-file' subcommand to update a single source file.
        
        [Design principles]
        Clear progress feedback.
        Detailed results reporting.
        
        [Implementation details]
        Calls the component's update_source_file method.
        Formats and displays results.
        
        Args:
            args: Command-line arguments
            component: HSTC component instance
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        file_path = args.file
        
        # Initial user feedback
        if args.dry_run:
            self.output.print(f"Previewing documentation updates for {file_path}")
        else:
            self.output.print(f"Updating documentation in {file_path}")
        
        # Direct console output to ensure visibility regardless of logging configuration
        import sys
        print(f"[DEBUG] Processing file: {file_path}", file=sys.stderr)
        
        # Check file existence before attempting update
        import os
        if not os.path.exists(file_path):
            error_msg = f"ERROR: File does not exist: {file_path}"
            print(error_msg, file=sys.stderr)
            self.output.error(error_msg)
            return 1
            
        print(f"[DEBUG] File exists: {file_path} (size: {os.path.getsize(file_path)} bytes)", file=sys.stderr)
        sys.stderr.flush()
        sys.stdout.flush()
        
        # Set up graceful termination to ensure messages are flushed
        import signal
        original_handler = signal.getsignal(signal.SIGINT)
        
        def sigint_handler(sig, frame):
            print("\n[DEBUG] Received interrupt signal, attempting to terminate cleanly...", file=sys.stderr)
            sys.stderr.flush()
            sys.stdout.flush()
            # Restore original handler to allow a second Ctrl+C to force exit
            signal.signal(signal.SIGINT, original_handler)
            
        signal.signal(signal.SIGINT, sigint_handler)
        
        try:
            # Perform update with progress indicators
            print(f"[DEBUG] Starting update operation. Please wait...", file=sys.stderr)
            sys.stderr.flush()
            
            result = component.update_source_file(
                file_path=file_path,
                dry_run=args.dry_run
            )
            
            print(f"[DEBUG] Update operation completed with status: {result.get('status', 'unknown')}", file=sys.stderr)
            sys.stderr.flush()
        except Exception as e:
            print(f"[ERROR] Update operation failed: {str(e)}", file=sys.stderr)
            print(f"[ERROR] Exception type: {type(e).__name__}", file=sys.stderr)
            sys.stderr.flush()
            self.output.error(f"Failed to update file: {str(e)}")
            return 1
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_handler)
        
        # Check for error
        if result.get("status") == "error":
            self.output.error(result.get("message", "Unknown error"))
            return 1
        
        # Display summary of changes if available
        changes_summary = result.get("changes_summary", {})
        if changes_summary:
            self.output.print("\nChanges summary:")
            if changes_summary.get("file_header_updated"):
                self.output.print("  - Would update file header" if args.dry_run else "  - Updated file header")
            if changes_summary.get("functions_updated", 0) > 0:
                self.output.print(f"  - Would update {changes_summary.get('functions_updated')} functions" if args.dry_run else f"  - Updated {changes_summary.get('functions_updated')} functions")
            if changes_summary.get("classes_updated", 0) > 0:
                self.output.print(f"  - Would update {changes_summary.get('classes_updated')} classes" if args.dry_run else f"  - Updated {changes_summary.get('classes_updated')} classes")
            if changes_summary.get("methods_updated", 0) > 0:
                self.output.print(f"  - Would update {changes_summary.get('methods_updated')} methods" if args.dry_run else f"  - Updated {changes_summary.get('methods_updated')} methods")
        
        # Display result based on status
        if result.get("status") == "skipped":
            self.output.warning(result.get("message", "File skipped"))
        elif result.get("status") == "unchanged":
            self.output.print(result.get("message", "No changes needed"))
        elif result.get("status") == "preview" or (args.dry_run and "updated_content" in result):
            self._display_file_preview(result)
        elif result.get("status") == "updated":
            self.output.print(result.get("message", "File updated successfully"))
        else:
            self.output.print(result.get("message", "Operation completed with unknown status"))
            
        return 0
    
    def _display_detailed_preview(self, results: List[Dict[str, Any]]):
        """
        [Function intent]
        Displays detailed preview of directory updates in dry-run mode.
        
        [Design principles]
        Clear and concise preview information.
        
        [Implementation details]
        Formats and displays preview information for each directory.
        
        Args:
            results: List of update results
        """
        if not results:
            return
            
        self.output.print("\nUpdate Preview:")
        
        for result in results:
            dir_path = result.get("directory_path", "Unknown")
            status = result.get("status", "unknown")
            
            if status == "preview":
                self.output.print(f"  - {dir_path}: Would be updated")
            elif status == "unchanged":
                self.output.print(f"  - {dir_path}: No changes needed")
            elif status == "error":
                self.output.print(f"  - {dir_path}: Error: {result.get('message', 'Unknown error')}")
    
    def _display_file_preview(self, result: Dict[str, Any]):
        """
        [Function intent]
        Displays preview of file updates in dry-run mode, including the updated content.
        
        [Design principles]
        Clear and concise preview information.
        Complete updated content display for thorough review.
        
        [Implementation details]
        Formats and displays preview information for the file.
        Shows the full updated content if available.
        
        Args:
            result: Update result
        """
        file_path = result.get("file_path", "Unknown")
        self.output.print(f"\nPreview of changes for {file_path}:")
        
        # Display summary of changes if available
        changes_summary = result.get("changes_summary", {})
        if changes_summary:
            if changes_summary.get("file_header_updated"):
                self.output.print("  - Would update file header")
            if changes_summary.get("functions_updated", 0) > 0:
                self.output.print(f"  - Would update {changes_summary.get('functions_updated')} functions")
            if changes_summary.get("classes_updated", 0) > 0:
                self.output.print(f"  - Would update {changes_summary.get('classes_updated')} classes")
            if changes_summary.get("methods_updated", 0) > 0:
                self.output.print(f"  - Would update {changes_summary.get('methods_updated')} methods")
        
        # Display the updated content if available
        if "updated_content" in result:
            self.output.print("\nUpdated file content:")
            self.output.print("=" * 80)
            print(result["updated_content"])
            self.output.print("=" * 80)
