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
# Implements the RecommendCommandHandler for the 'recommend' CLI command, which allows
# users to get recommendations for fixing inconsistencies between code and documentation.
# Users can filter recommendations by inconsistency ID, file path, or severity level.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'recommend' command.
# - Allows filtering recommendations by inconsistency ID, file, or severity.
# - Controls the number of recommendations with a limit option.
# - Provides options to show code and documentation snippets in recommendations.
# - Uses progress indicators for potentially long-running operations.
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'generate_recommendations' tool.
# - Requires valid inconsistency IDs or file paths to generate recommendations.
# - Code and documentation snippets may be lengthy, affecting output formatting.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:07:30Z : Initial creation of RecommendCommandHandler by CodeAssistant
# * Implemented command handler for generating recommendations.
###############################################################################

import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import BaseCommandHandler
from ..exceptions import CommandError, APIError

logger = logging.getLogger(__name__)

class RecommendCommandHandler(BaseCommandHandler):
    """Handles the 'recommend' command for generating recommendations to fix inconsistencies."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add recommend-specific arguments to the parser."""
        # Filter options (mutually exclusive)
        filter_group = parser.add_mutually_exclusive_group()
        filter_group.add_argument(
            "--inconsistency-id", 
            metavar="ID",
            help="Inconsistency ID to generate recommendations for"
        )
        filter_group.add_argument(
            "--file", 
            help="Path to file to generate recommendations for"
        )
        filter_group.add_argument(
            "--latest",
            action="store_true",
            help="Get recommendations for the most recent inconsistency analysis"
        )
        
        # Additional filter options
        parser.add_argument(
            "--severity", 
            choices=["high", "medium", "low", "all"],
            default="all",
            help="Filter recommendations by severity (default: all)"
        )
        
        # Output options
        parser.add_argument(
            "--limit", 
            type=int, 
            default=10,
            help="Maximum number of recommendations to show (default: 10)"
        )
        parser.add_argument(
            "--show-code", 
            action="store_true", 
            help="Show code snippets in recommendations"
        )
        parser.add_argument(
            "--show-doc", 
            action="store_true", 
            help="Show documentation snippets in recommendations"
        )
        parser.add_argument(
            "--show-all-snippets",
            action="store_true",
            help="Show both code and documentation snippets"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the recommend command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Prepare parameters for the API call
            params = self._prepare_parameters(args)
            
            # Generate recommendations
            self.output.info(f"Generating recommendations for {self._get_filter_description(args)}")
            
            # Execute the API call with progress indicator
            result = self.with_progress(
                "Generating recommendations", 
                self.mcp_client.generate_recommendations,
                **params
            )
            
            # Check if any recommendations were found
            total_recommendations = len(result.get("recommendations", []))
            
            if total_recommendations == 0:
                self.output.info("No recommendations found.")
                return 0
            
            # Ensure we have a summary section
            if "summary" not in result:
                result["summary"] = {"total": total_recommendations}
                
            # Display results
            self.output.format_output(result)
            
            # Show a helpful message about applying recommendations
            if total_recommendations > 0:
                self.output.info(
                    f"\nTo apply a recommendation, use:\n"
                    f"  dbp apply <recommendation_id>\n"
                    f"For example:\n"
                    f"  dbp apply {result['recommendations'][0]['id']} --dry-run"
                )
            
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
        # Initialize parameters
        params = {
            "limit": args.limit,
        }
        
        # Process filter options
        inconsistency_ids = []
        
        if args.inconsistency_id:
            # Single inconsistency ID
            inconsistency_ids = [args.inconsistency_id]
            params["inconsistency_ids"] = inconsistency_ids
        elif args.file:
            # File path
            file_path = Path(args.file).expanduser().resolve()
            if not file_path.exists():
                raise CommandError(f"File does not exist: {args.file}")
            
            params["file_path"] = str(file_path)
        elif args.latest:
            # Latest inconsistencies
            params["latest"] = True
        
        # Add severity filter if not "all"
        if args.severity != "all":
            params["severity"] = args.severity
        
        # Add snippet options
        show_code = args.show_code or args.show_all_snippets
        show_doc = args.show_doc or args.show_all_snippets
        
        if show_code:
            params["show_code_snippets"] = True
        
        if show_doc:
            params["show_doc_snippets"] = True
        
        return params
    
    def _get_filter_description(self, args: argparse.Namespace) -> str:
        """
        Get a human-readable description of the filter options.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Description string
        """
        if args.inconsistency_id:
            return f"inconsistency '{args.inconsistency_id}'"
        elif args.file:
            return f"file '{args.file}'"
        elif args.latest:
            return "latest analysis"
        else:
            return "all inconsistencies"
