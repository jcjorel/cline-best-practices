# Phase 6: CLI Integration

This phase covers the implementation of the CLI command for HSTC updates, which allows users to trigger HSTC updates from the command line.

## Files to Implement

1. `src/dbp_cli/commands/hstc.py` - CLI command implementation for HSTC updates

## Implementation Details

### HSTC CLI Command Implementation

```python
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
# 2025-05-07T11:40:00Z : Initial implementation of HSTC CLI command by CodeAssistant
# * Created CLI command class with command-line options
# * Implemented execution logic for HSTC operations
# * Added formatting for operation results
###############################################################################

import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from dbp_cli.commands.base import Command
from dbp_cli.output import OutputFormatter
from dbp.hstc.component import HSTCComponent


class HSTCCommand(Command):
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
    
    @classmethod
    def register_subcommand(cls, subparsers):
        """
        [Function intent]
        Registers the HSTC command with the CLI subparser system.
        
        [Design principles]
        Clear command structure with logical option grouping.
        Comprehensive help text for usability.
        
        [Implementation details]
        Creates a subparser for the HSTC command.
        Adds subcommands for different operations.
        Sets up command-line arguments with appropriate types and defaults.
        
        Args:
            subparsers: Subparser collection to add the command to
        """
        parser = subparsers.add_parser(
            "hstc",
            help="HSTC (Hierarchical Semantic Tree Context) operations",
            description="Manage HSTC.md files and source code documentation"
        )
        
        # Create subcommands
        sub_subparsers = parser.add_subparsers(
            dest="hstc_command",
            help="HSTC operation to perform",
            required=True
        )
        
        # Register subcommands
        cls._register_update_command(sub_subparsers)
        cls._register_update_file_command(sub_subparsers)
        
        # Set handler
        parser.set_defaults(handler=cls)
        
    @classmethod
    def _register_update_command(cls, subparsers):
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
    
    @classmethod
    def _register_update_file_command(cls, subparsers):
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
                self.output_formatter.error(f"Unknown HSTC command: {args.hstc_command}")
                return 1
                
        except Exception as e:
            self.output_formatter.error(f"Error executing HSTC command: {str(e)}")
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
            self.output_formatter.print(f"Previewing HSTC updates in {'current directory' if directory_path is None else directory_path}")
        else:
            self.output_formatter.print(f"Updating HSTC files in {'current directory' if directory_path is None else directory_path}")
        
        # Perform update
        result = component.update_hstc(
            directory_path=directory_path,
            dry_run=args.dry_run
        )
        
        # Check for error
        if result.get("status") == "error":
            self.output_formatter.error(result.get("message", "Unknown error"))
            return 1
            
        # Display summary
        self.output_formatter.print("")
        self.output_formatter.print("Update Summary:")
        self.output_formatter.print(f"  Directories scanned: {result.get('directories_scanned', 0)}")
        self.output_formatter.print(f"  Directories updated: {result.get('directories_updated', 0)}")
        self.output_formatter.print(f"  Directories with errors: {result.get('directories_with_errors', 0)}")
        
        # Display detailed results
        if args.dry_run:
            self._display_detailed_preview(result.get("results", []))
            
        # Display status
        if result.get("status") == "unchanged":
            self.output_formatter.print("\nNo directories needed updates.")
        elif result.get("directories_with_errors", 0) > 0:
            self.output_formatter.warning(f"\nUpdated with {result.get('directories_with_errors', 0)} errors.")
            return 1
        else:
            self.output_formatter.print("\nUpdate completed successfully.")
            
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
        
        # Display operation information
        if args.dry_run:
            self.output_formatter.print(f"Previewing documentation updates for {file_path}")
        else:
            self.output_formatter.print(f"Updating documentation in {file_path}")
        
        # Perform update
        result = component.update_source_file(
            file_path=file_path,
            dry_run=args.dry_run
        )
        
        # Check for error
        if result.get("status") == "error":
            self.output_formatter.error(result.get("message", "Unknown error"))
            return 1
            
        # Display result based on status
        if result.get("status") == "skipped":
            self.output_formatter.warning(result.get("message", "File skipped"))
        elif result.get("status") == "unchanged":
            self.output_formatter.print(result.get("message", "No changes needed"))
        elif result.get("status") == "preview":
            self._display_file_preview(result)
        elif result.get("status") == "updated":
            self.output_formatter.print(result.get("message", "File updated successfully"))
            
            # Display summary of changes if available
            changes_summary = result.get("changes_summary", {})
            if changes_summary:
                self.output_formatter.print("\nChanges summary:")
                if changes_summary.get("file_header_updated"):
                    self.output_formatter.print("  - Updated file header")
                if changes_summary.get("functions_updated", 0) > 0:
                    self.output_formatter.print(f"  - Updated {changes_summary.get('functions_updated')} functions")
                if changes_summary.get("classes_updated", 0) > 0:
                    self.output_formatter.print(f"  - Updated {changes_summary.get('classes_updated')} classes")
                if changes_summary.get("methods_updated", 0) > 0:
                    self.output_formatter.print(f"  - Updated {changes_summary.get('methods_updated')} methods")
        else:
            self.output_formatter.print(result.get("message", "Operation completed with unknown status"))
            
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
            
        self.output_formatter.print("\nUpdate Preview:")
        
        for result in results:
            dir_path = result.get("directory_path", "Unknown")
            status = result.get("status", "unknown")
            
            if status == "preview":
                self.output_formatter.print(f"  - {dir_path}: Would be updated")
            elif status == "unchanged":
                self.output_formatter.print(f"  - {dir_path}: No changes needed")
            elif status == "error":
                self.output_formatter.print(f"  - {dir_path}: Error: {result.get('message', 'Unknown error')}")
    
    def _display_file_preview(self, result: Dict[str, Any]):
        """
        [Function intent]
        Displays preview of file updates in dry-run mode.
        
        [Design principles]
        Clear and concise preview information.
        
        [Implementation details]
        Formats and displays preview information for the file.
        
        Args:
            result: Update result
        """
        file_path = result.get("file_path", "Unknown")
        self.output_formatter.print(f"\nPreview of changes for {file_path}:")
        
        # Display summary of changes if available
        changes_summary = result.get("changes_summary", {})
        if changes_summary:
            if changes_summary.get("file_header_updated"):
                self.output_formatter.print("  - Would update file header")
            if changes_summary.get("functions_updated", 0) > 0:
                self.output_formatter.print(f"  - Would update {changes_summary.get('functions_updated')} functions")
            if changes_summary.get("classes_updated", 0) > 0:
                self.output_formatter.print(f"  - Would update {changes_summary.get('classes_updated')} classes")
            if changes_summary.get("methods_updated", 0) > 0:
                self.output_formatter.print(f"  - Would update {changes_summary.get('methods_updated')} methods")
```

### Integration with CLI System

To make the command available in the CLI, we need to register it in the CLI's command registry. This is done by modifying the `src/dbp_cli/cli.py` file to import and register the HSTCCommand class:

```python
from dbp_cli.commands.hstc import HSTCCommand

# In the _register_commands method
self._register_command(HSTCCommand)
```

## CLI Command Usage

The HSTC CLI command provides two main operations:

1. **Update HSTC Files**:
   ```bash
   python -m dbp_cli hstc update [--directory DIR] [--dry-run]
   ```

   This command scans the specified directory (or current directory if not specified) for directories that need HSTC.md updates, and creates or updates the files.

2. **Update Source File Documentation**:
   ```bash
   python -m dbp_cli hstc update-file FILE [--dry-run]
   ```

   This command updates the documentation in a single source file to match the project standards.

For both commands, the `--dry-run` option allows previewing the changes without actually applying them.

## Integration Points

The CLI command is designed to integrate with:

1. **DBP CLI System**: The command follows the DBP CLI command structure and conventions.

2. **HSTC Component**: The command creates an instance of the HSTCComponent and uses it to perform operations.

3. **Output Formatting**: The command uses the OutputFormatter to display results in a user-friendly format.

## Implementation Steps

1. Implement `src/dbp_cli/commands/hstc.py` with the HSTCCommand class

2. Update `src/dbp_cli/cli.py` to register the command

3. Test the CLI commands with various scenarios
