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
# Implements the AnalyzeCommandHandler for the 'analyze' CLI command, which allows
# users to analyze consistency between code files and documentation files.
# Handles both individual file analysis and directory-based bulk analysis.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'analyze' command.
# - Provides options for filtering by severity and type.
# - Supports both individual file and directory-based analysis.
# - Offers sorting and output customization options.
# - Uses progress indicators for long-running operations.
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'analyze_document_consistency' tool.
# - Files to analyze must be accessible from the CLI client's file system.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:05:20Z : Initial creation of AnalyzeCommandHandler by CodeAssistant
# * Implemented command handler for analyzing document consistency.
###############################################################################

import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .base import BaseCommandHandler
from ..exceptions import CommandError, APIError

logger = logging.getLogger(__name__)

class AnalyzeCommandHandler(BaseCommandHandler):
    """Handles the 'analyze' command for checking consistency between code and documentation."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add analyze-specific arguments to the parser."""
        # Individual file arguments
        parser.add_argument(
            "code_file", 
            nargs="?", 
            help="Path to code file to analyze"
        )
        parser.add_argument(
            "doc_file", 
            nargs="?", 
            help="Path to documentation file to analyze"
        )
        
        # Directory-based analysis
        parser.add_argument(
            "--code-dir", 
            help="Directory containing code files"
        )
        parser.add_argument(
            "--doc-dir", 
            help="Directory containing documentation files"
        )
        
        # Filter options
        parser.add_argument(
            "--severity", 
            choices=["high", "medium", "low", "all"],
            default="all",
            help="Filter inconsistencies by severity (default: all)"
        )
        parser.add_argument(
            "--type", 
            help="Filter by inconsistency type"
        )
        
        # Output options
        parser.add_argument(
            "--summary-only", 
            action="store_true", 
            help="Show only summary, not individual inconsistencies"
        )
        parser.add_argument(
            "--sort-by", 
            choices=["severity", "file", "type"],
            default="severity",
            help="Sort results by this field (default: severity)"
        )
        
    def _validate_file_paths(self, code_path: Optional[str], doc_path: Optional[str]) -> Tuple[Path, Path]:
        """
        Validates that both file paths exist and are readable.
        
        Args:
            code_path: Path to code file
            doc_path: Path to documentation file
            
        Returns:
            Tuple of validated Path objects for code and documentation file
            
        Raises:
            CommandError: If either file doesn't exist or is not accessible
        """
        if not code_path:
            raise CommandError("No code file specified")
        if not doc_path:
            raise CommandError("No documentation file specified")
            
        code_file = Path(code_path).expanduser().resolve()
        doc_file = Path(doc_path).expanduser().resolve()
        
        if not code_file.exists():
            raise CommandError(f"Code file does not exist: {code_path}")
        if not doc_file.exists():
            raise CommandError(f"Documentation file does not exist: {doc_path}")
            
        if not code_file.is_file():
            raise CommandError(f"Code path is not a file: {code_path}")
        if not doc_file.is_file():
            raise CommandError(f"Documentation path is not a file: {doc_path}")
            
        if not os.access(code_file, os.R_OK):
            raise CommandError(f"No permission to read code file: {code_path}")
        if not os.access(doc_file, os.R_OK):
            raise CommandError(f"No permission to read documentation file: {doc_path}")
            
        return code_file, doc_file
    
    def _find_matching_files(self, code_dir: Path, doc_dir: Path) -> List[Tuple[Path, Path]]:
        """
        Finds matching code and documentation files in the given directories.
        
        Args:
            code_dir: Directory containing code files
            doc_dir: Directory containing documentation files
            
        Returns:
            List of tuples containing matching (code_file, doc_file) paths
        """
        # This is a basic implementation that can be expanded later
        # It currently matches files with the same name but different extensions
        matches = []
        
        if not code_dir.is_dir() or not doc_dir.is_dir():
            return matches
            
        # Get all code files
        code_files = list(code_dir.glob("**/*.*"))
        
        # Get potential documentation files
        doc_extensions = [".md", ".rst", ".txt", ".docx", ".html"]
        doc_files = []
        for ext in doc_extensions:
            doc_files.extend(doc_dir.glob(f"**/*{ext}"))
            
        # Find matches based on name (without extension)
        for code_file in code_files:
            code_stem = code_file.stem.lower()
            
            for doc_file in doc_files:
                doc_stem = doc_file.stem.lower()
                
                # Check for exact match
                if code_stem == doc_stem:
                    matches.append((code_file, doc_file))
                    
                # Check for prefix match (e.g., user.py and USER_MODEL.md)
                elif (code_stem.startswith(doc_stem) or doc_stem.startswith(code_stem)):
                    matches.append((code_file, doc_file))
                    
        return matches
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the analyze command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Check if we're doing individual file analysis or directory-based analysis
            if args.code_file and args.doc_file:
                # Individual file analysis
                return self._analyze_individual_files(args)
            elif args.code_dir and args.doc_dir:
                # Directory-based analysis
                return self._analyze_directories(args)
            else:
                # Invalid combination of arguments
                self.output.error("Please provide either both individual files (code_file doc_file) or both directories (--code-dir --doc-dir)")
                return 1
                
        except CommandError as e:
            self.output.error(str(e))
            return 1
        except Exception as e:
            return self.handle_api_error(e)
            
    def _analyze_individual_files(self, args: argparse.Namespace) -> int:
        """
        Analyze consistency between a single code file and documentation file.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Validate file paths
            code_file, doc_file = self._validate_file_paths(args.code_file, args.doc_file)
            
            # Log the analysis
            self.logger.info(f"Analyzing consistency between {code_file} and {doc_file}")
            self.output.info(f"Analyzing consistency between {code_file} and {doc_file}")
            
            # Execute the analysis with progress indicator
            result = self.with_progress(
                "Analyzing consistency", 
                self.mcp_client.analyze_consistency,
                str(code_file),
                str(doc_file)
            )
            
            # Apply filters if specified
            if args.severity != "all":
                result = self._filter_by_severity(result, args.severity)
                
            if args.type:
                result = self._filter_by_type(result, args.type)
                
            # Sort results if needed
            if args.sort_by and "inconsistencies" in result:
                result["inconsistencies"] = sorted(
                    result["inconsistencies"],
                    key=lambda x: x.get(args.sort_by, "")
                )
                
            # Remove details if summary only
            if args.summary_only and "inconsistencies" in result:
                del result["inconsistencies"]
                
            # Display results
            self.output.format_output(result)
            
            # Check summary for exit code
            exit_code = 0
            if "summary" in result and result["summary"].get("total_inconsistencies", 0) > 0:
                # Return non-zero exit code if inconsistencies were found
                # This allows for shell scripting based on results
                exit_code = 50  # Using 50 as a specific code for "inconsistencies found"
                
            return exit_code
            
        except APIError as e:
            # Re-raise for the generic handler
            raise e
        except Exception as e:
            self.logger.error(f"Error during file analysis: {e}", exc_info=True)
            raise CommandError(f"Analysis failed: {e}")
            
    def _analyze_directories(self, args: argparse.Namespace) -> int:
        """
        Analyze consistency between code and documentation directories.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            code_dir = Path(args.code_dir).expanduser().resolve()
            doc_dir = Path(args.doc_dir).expanduser().resolve()
            
            if not code_dir.is_dir():
                raise CommandError(f"Code directory does not exist: {args.code_dir}")
            if not doc_dir.is_dir():
                raise CommandError(f"Documentation directory does not exist: {args.doc_dir}")
                
            # Find matching files
            self.progress.start("Finding matching files")
            try:
                matches = self._find_matching_files(code_dir, doc_dir)
            finally:
                self.progress.stop()
                
            if not matches:
                self.output.warning("No matching code and documentation files found")
                return 0
                
            # Log what we found
            self.output.info(f"Found {len(matches)} matching file pairs")
            
            # Initialize counters for summary
            total_inconsistencies = 0
            by_severity = {"high": 0, "medium": 0, "low": 0}
            by_type = {}
            
            # Analyze each pair
            for code_file, doc_file in matches:
                try:
                    # Log the analysis
                    self.output.info(f"Analyzing {code_file.relative_to(code_dir)} with {doc_file.relative_to(doc_dir)}")
                    
                    # Execute the analysis with progress indicator
                    result = self.with_progress(
                        f"Analyzing {code_file.name}", 
                        self.mcp_client.analyze_consistency,
                        str(code_file),
                        str(doc_file)
                    )
                    
                    # Apply filters if specified
                    if args.severity != "all":
                        result = self._filter_by_severity(result, args.severity)
                        
                    if args.type:
                        result = self._filter_by_type(result, args.type)
                        
                    # Update counters
                    if "summary" in result:
                        total_inconsistencies += result["summary"].get("total_inconsistencies", 0)
                        
                        if "by_severity" in result["summary"]:
                            for sev, count in result["summary"]["by_severity"].items():
                                by_severity[sev] = by_severity.get(sev, 0) + count
                                
                        if "by_type" in result["summary"]:
                            for typ, count in result["summary"]["by_type"].items():
                                by_type[typ] = by_type.get(typ, 0) + count
                                
                    # Display results if not summary only
                    if not args.summary_only:
                        self.output.format_output(result)
                        
                except Exception as e:
                    self.output.warning(f"Error analyzing {code_file} with {doc_file}: {e}")
                    
            # Display final summary
            summary = {
                "summary": {
                    "total_inconsistencies": total_inconsistencies,
                    "total_files_analyzed": len(matches),
                    "by_severity": by_severity,
                    "by_type": by_type
                }
            }
            
            self.output.info("Analysis complete")
            self.output.format_output(summary)
            
            # Return non-zero exit code if inconsistencies were found
            return 50 if total_inconsistencies > 0 else 0
            
        except APIError as e:
            # Re-raise for the generic handler
            raise e
        except Exception as e:
            self.logger.error(f"Error during directory analysis: {e}", exc_info=True)
            raise CommandError(f"Directory analysis failed: {e}")
            
    def _filter_by_severity(self, result: Dict[str, Any], severity: str) -> Dict[str, Any]:
        """
        Filter results by severity.
        
        Args:
            result: The analysis result
            severity: Severity level to filter by
            
        Returns:
            Filtered results
        """
        if "inconsistencies" not in result:
            return result
            
        filtered = [i for i in result["inconsistencies"] if i.get("severity") == severity]
        
        # Update summary
        if "summary" in result:
            result["summary"]["filtered_total"] = len(filtered)
            result["summary"]["filtered_by"] = f"severity={severity}"
            
        # Replace with filtered list
        result["inconsistencies"] = filtered
        return result
        
    def _filter_by_type(self, result: Dict[str, Any], inconsistency_type: str) -> Dict[str, Any]:
        """
        Filter results by inconsistency type.
        
        Args:
            result: The analysis result
            inconsistency_type: Type to filter by
            
        Returns:
            Filtered results
        """
        if "inconsistencies" not in result:
            return result
            
        filtered = [i for i in result["inconsistencies"] if i.get("inconsistency_type") == inconsistency_type]
        
        # Update summary
        if "summary" in result:
            # If we already have a filtered total, calculate the new one
            if "filtered_total" in result["summary"]:
                result["summary"]["filtered_total"] = len(filtered)
                result["summary"]["filtered_by"] = result["summary"].get("filtered_by", "") + f", type={inconsistency_type}"
            else:
                result["summary"]["filtered_total"] = len(filtered)
                result["summary"]["filtered_by"] = f"type={inconsistency_type}"
                
        # Replace with filtered list
        result["inconsistencies"] = filtered
        return result
