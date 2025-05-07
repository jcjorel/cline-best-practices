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
# Implements the HSTCManager class that coordinates the HSTC update process
# by orchestrating the scanner, source processor, and HSTC processor components.
# This manager provides a high-level API for updating HSTC.md files throughout
# a directory tree.
###############################################################################
# [Source file design principles]
# - Clean coordination of independent services
# - Clear error handling and aggregation
# - Consistent operation reporting
# - Progress tracking and status updates
###############################################################################
# [Source file constraints]
# - Must handle large directory trees efficiently
# - Must process directories in the correct order (leaves to root)
# - Must maintain consistent state across components
###############################################################################
# [Dependencies]
# codebase:src/dbp/hstc/scanner.py
# codebase:src/dbp/hstc/source_processor.py
# codebase:src/dbp/hstc/hstc_processor.py
# codebase:src/dbp/hstc/exceptions.py
# system:logging
# system:pathlib
# system:typing
# system:os
###############################################################################
# [GenAI tool change history]
# 2025-05-07T13:23:05Z : Removed threading from SourceProcessor delegation by CodeAssistant
# * Simplified code with direct synchronous invocation
# * Removed ThreadPoolExecutor dependency in manager
# * Enhanced error handling with better diagnostics
# * Added detailed debug logging for direct execution
# 2025-05-07T12:50:44Z : Added detailed progress logging in update_source_file by CodeAssistant
# * Added comprehensive file details logging for better diagnostics
# * Implemented timing statistics to identify performance bottlenecks
# * Enhanced error reporting with more contextual information
# * Added timestamp logging for debugging command stuck issues
# 2025-05-07T12:16:30Z : Implemented full HSTCManager functionality by CodeAssistant
# * Created manager class with component coordination
# * Implemented HSTC update orchestration
# * Added source file processing and reporting
# 2025-05-07T11:48:00Z : Initial placeholder implementation of HSTCManager by CodeAssistant
# * Created placeholder class with interface methods
# * Added basic logging and NotImplementedError responses
###############################################################################

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Set

from dbp.hstc.scanner import HSTCScanner
from dbp.hstc.source_processor import SourceCodeProcessor
from dbp.hstc.hstc_processor import HSTCFileProcessor
from dbp.hstc.exceptions import HSTCError, ScannerError, SourceProcessingError, HSTCProcessingError


class HSTCManager:
    """
    [Class intent]
    Orchestrates the HSTC update process by coordinating the scanner, source processor,
    and HSTC processor components. Provides a high-level API for updating HSTC.md files
    throughout a directory tree.
    
    [Design principles]
    Clean separation of concerns with delegation to specialized services.
    Coordinated workflow with proper ordering of operations.
    Consistent operation reporting with detailed status information.
    Continues processing on non-critical errors to maximize update coverage.
    
    [Implementation details]
    Uses HSTCScanner to identify directories needing updates.
    Uses SourceCodeProcessor to update source file documentation.
    Uses HSTCFileProcessor to create or update HSTC.md files.
    Follows bottom-up processing order to maintain hierarchical consistency.
    """
    
    def __init__(self, logger=None, 
                source_processor_model_id="anthropic.claude-3-7-sonnet-20250219-v1:0",
                hstc_processor_model_id="amazon.nova-lite-v1"):
        """
        [Function intent]
        Initializes the HSTC manager with the necessary components and configuration.
        
        [Design principles]
        Clean initialization with configurable LLM model IDs.
        Delegation to specialized service components.
        
        [Implementation details]
        Creates scanner, source processor, and HSTC processor instances.
        Configures logging with proper child hierarchy.
        
        Args:
            logger: Optional logger instance, creates new logger if None
            source_processor_model_id: LLM model ID for source file processing
            hstc_processor_model_id: LLM model ID for HSTC file processing
        """
        self.logger = logger or logging.getLogger("dbp.hstc.manager")
        
        # Create component instances
        self._scanner = HSTCScanner(logger=self.logger.getChild("scanner"))
        self._source_processor = SourceCodeProcessor(
            logger=self.logger.getChild("source_processor"),
            llm_model_id=source_processor_model_id
        )
        self._hstc_processor = HSTCFileProcessor(
            logger=self.logger.getChild("hstc_processor"),
            llm_model_id=hstc_processor_model_id
        )
    
    def update_source_file(self, file_path: Union[str, Path], dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Updates a source file's documentation to match project standards.
        
        [Design principles]
        Simple delegation to the source processor.
        Clean error handling and reporting.
        
        [Implementation details]
        Delegates to the source processor to update the file.
        Adds consistent operation metadata to the result.
        
        Args:
            file_path: Path to the source file
            dry_run: If True, return changes without applying them
            
        Returns:
            dict: Result of the operation with status and details
            
        Raises:
            SourceProcessingError: If processing fails
        """
        # Direct console output for debugging
        import sys
        print(f"[MANAGER:DEBUG] update_source_file called with file_path={file_path}, dry_run={dry_run}", file=sys.stderr)
        sys.stderr.flush()
        
        self.logger.info(f"Starting update of source file: {file_path} (dry_run={dry_run})")
        
        # Convert to Path object if string for consistent handling
        if isinstance(file_path, str):
            file_path = Path(file_path)
            print(f"[MANAGER:DEBUG] Converted string path to Path object: {file_path}", file=sys.stderr)
            sys.stderr.flush()
        
        # Check source processor availability
        if self._source_processor is None:
            error_msg = "Source processor is not initialized"
            print(f"[MANAGER:ERROR] {error_msg}", file=sys.stderr)
            sys.stderr.flush()
            self.logger.error(error_msg)
            raise SourceProcessingError(error_msg)
        else:
            print(f"[MANAGER:DEBUG] Source processor is available", file=sys.stderr)
            sys.stderr.flush()
            
        # Log detailed information about the file
        print(f"[MANAGER:DEBUG] File details - exists: {file_path.exists()}, "
              f"is_file: {file_path.is_file() if file_path.exists() else 'N/A'}, "
              f"suffix: {file_path.suffix}, "
              f"size: {file_path.stat().st_size if file_path.exists() and file_path.is_file() else 'N/A'} bytes", 
              file=sys.stderr)
        sys.stderr.flush()
        
        self.logger.info(f"File details - exists: {file_path.exists()}, "
                        f"is_file: {file_path.is_file() if file_path.exists() else 'N/A'}, "
                        f"suffix: {file_path.suffix}, "
                        f"size: {file_path.stat().st_size if file_path.exists() and file_path.is_file() else 'N/A'} bytes")
        
        start_time = __import__('time').time()
        print(f"[MANAGER:DEBUG] Will delegate to SourceCodeProcessor at {__import__('time').strftime('%H:%M:%S')}", file=sys.stderr)
        sys.stderr.flush()
        self.logger.info(f"Delegating to SourceCodeProcessor at {__import__('time').strftime('%H:%M:%S')}")
        
        try:
            # Direct invocation without threading
            print(f"[MANAGER:DEBUG] Starting direct invocation of source processor", file=sys.stderr)
            sys.stderr.flush()
            
            # Call the source processor directly - no threading
            result = self._source_processor.update_source_file(file_path, dry_run)
            
            elapsed_time = __import__('time').time() - start_time
            print(f"[MANAGER:DEBUG] SourceProcessor completed in {elapsed_time:.2f} seconds", file=sys.stderr)
            sys.stderr.flush()
            self.logger.info(f"Source processor completed in {elapsed_time:.2f} seconds with status: {result.get('status', 'unknown')}")
            
            result['operation'] = 'update_source_file'
            print(f"[MANAGER:DEBUG] Operation completed successfully", file=sys.stderr)
            sys.stderr.flush()
            return result
            
        except Exception as e:
            elapsed_time = __import__('time').time() - start_time
            print(f"[MANAGER:ERROR] Failed to update source file after {elapsed_time:.2f} seconds: {str(e)}", file=sys.stderr)
            print(f"[MANAGER:ERROR] Error type: {type(e).__name__}, Error details: {str(e)}", file=sys.stderr)
            sys.stderr.flush()
            self.logger.error(f"Failed to update source file after {elapsed_time:.2f} seconds: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}, Error details: {str(e)}")
            raise
    
    def update_hstc(self, directory_path: Optional[Union[str, Path]] = None, 
                   dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Updates HSTC.md files for a directory tree, starting from the specified directory.
        
        [Design principles]
        Coordinated workflow with proper ordering of operations.
        Continues processing on non-critical errors to maximize update coverage.
        Detailed status reporting with aggregated results.
        
        [Implementation details]
        Uses the scanner to identify directories needing updates.
        Processes directories in bottom-up order (leaves to root).
        Updates HSTC.md files in each directory.
        Collects results for reporting.
        
        Args:
            directory_path: Root directory to update (defaults to project root)
            dry_run: If True, show changes without applying them
            
        Returns:
            dict: Summary of update operations with detailed results
        """
        # Set default directory if not provided
        if directory_path is None:
            directory_path = Path.cwd()
        elif isinstance(directory_path, str):
            directory_path = Path(directory_path)
            
        self.logger.info(f"Updating HSTC files in {directory_path} (dry_run={dry_run})")
        
        try:
            # Scan for directories needing updates
            self.logger.info("Scanning for directories needing updates")
            scan_results = self._scanner.scan_for_updates(directory_path)
            
            # Extract directories to update
            dirs_to_update = []
            
            # Directories with HSTC_REQUIRES_UPDATE.md
            dirs_with_update_required = scan_results.get("dirs_with_update_required", [])
            if dirs_with_update_required:
                self.logger.info(f"Found {len(dirs_with_update_required)} directories with update markers")
                dirs_to_update.extend(dirs_with_update_required)
            
            # Directories without HSTC.md
            dirs_without_hstc = scan_results.get("dirs_without_hstc", [])
            if dirs_without_hstc:
                self.logger.info(f"Found {len(dirs_without_hstc)} directories without HSTC.md")
                dirs_to_update.extend(dirs_without_hstc)
            
            # Directories with forced updates
            dirs_with_force_update = scan_results.get("dirs_with_force_update", [])
            if dirs_with_force_update:
                self.logger.info(f"Found {len(dirs_with_force_update)} directories requiring forced updates")
                dirs_to_update.extend(dirs_with_force_update)
            
            # Get unique directories
            dirs_to_update = list(set(dirs_to_update))
            
            # Check if any directories need updates
            if not dirs_to_update:
                self.logger.info("No directories need HSTC updates")
                return {
                    "operation": "update_hstc",
                    "status": "unchanged",
                    "message": "No directories need HSTC updates",
                    "directories_scanned": scan_results.get("total_dirs", 0),
                    "directories_updated": 0,
                    "results": [],
                    "dry_run": dry_run
                }
            
            # Get update order (bottom-up)
            update_order = scan_results.get("update_order", [])
            if not update_order:
                update_order = self._scanner.get_update_order(dirs_to_update)
                
            self.logger.info(f"Processing {len(update_order)} directories in bottom-up order")
            
            # Process each directory
            results = []
            success_count = 0
            error_count = 0
            
            for directory in update_order:
                try:
                    self.logger.info(f"Processing directory: {directory}")
                    
                    # Update HSTC.md file
                    result = self._hstc_processor.update_hstc_file(directory, dry_run)
                    
                    # Add result to list
                    results.append(result)
                    
                    # Update counts
                    if result["status"] in ["updated", "preview"]:
                        success_count += 1
                    elif result["status"] == "error":
                        error_count += 1
                        
                except Exception as e:
                    error_msg = f"Error updating HSTC.md for {directory}: {str(e)}"
                    self.logger.error(error_msg)
                    
                    # Add error result
                    results.append({
                        "status": "error",
                        "message": error_msg,
                        "directory_path": str(directory),
                        "dry_run": dry_run
                    })
                    
                    error_count += 1
            
            # Return summary results
            return {
                "operation": "update_hstc",
                "status": "completed",
                "message": f"Processed {len(update_order)} directories, {success_count} updated, {error_count} errors",
                "directories_scanned": scan_results.get("total_dirs", 0),
                "directories_updated": success_count,
                "directories_with_errors": error_count,
                "results": results,
                "dry_run": dry_run
            }
                
        except Exception as e:
            error_msg = f"Error updating HSTC files: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "operation": "update_hstc",
                "status": "error",
                "message": error_msg,
                "dry_run": dry_run
            }
    
    def query_hstc(self, query: str) -> Dict[str, Any]:
        """
        [Function intent]
        Queries HSTC files based on the provided query string. This is a placeholder
        for future functionality.
        
        [Design principles]
        Simple placeholder for future query functionality.
        
        [Implementation details]
        Currently raises NotImplementedError as this is for future implementation.
        
        Args:
            query: Query string
            
        Returns:
            dict: Query results
            
        Raises:
            NotImplementedError: As this is a placeholder for future functionality
        """
        self.logger.info(f"HSTC query: {query}")
        raise NotImplementedError("HSTC querying is not yet implemented")
