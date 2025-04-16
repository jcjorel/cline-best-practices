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
# Implements the QueryCommandHandler for the 'query' CLI command, which exposes
# the natural language query functionality of the MCP server's dbp_general_query tool.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'query' command.
# - Provides direct natural language access to the dbp_general_query MCP tool.
# - Simplifies interaction by focusing only on natural language.
# - Formats and displays results consistently.
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'dbp_general_query' tool.
# - Query handling ultimately depends on the server's ability to interpret queries.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/mcp_tools_refactoring_plan/plan_overview.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T10:08:00Z : Initial creation of QueryCommandHandler by CodeAssistant
# * Implemented command handler for natural language queries
###############################################################################

import argparse
import logging
from typing import Dict, Any

from .base import BaseCommandHandler
from ..exceptions import CommandError, APIError

logger = logging.getLogger(__name__)

class QueryCommandHandler(BaseCommandHandler):
    """Handles the 'query' command for natural language queries about the codebase and documentation."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add query-specific arguments to the parser."""
        # Main query argument
        parser.add_argument(
            "query",
            nargs="+",
            help="Natural language query"
        )
        
        # Processing control
        parser.add_argument(
            "--budget",
            type=float,
            help="Maximum cost budget for LLM usage"
        )
        parser.add_argument(
            "--timeout",
            type=int,
            help="Maximum execution time in milliseconds"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the query command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Combine query words into a single string
            query_text = " ".join(args.query)
            
            # Prepare query data
            query_data = {
                "query": query_text
            }
            
            # Add processing control parameters
            if args.budget:
                query_data["max_cost_budget"] = args.budget
            
            if args.timeout:
                query_data["max_execution_time_ms"] = args.timeout
            
            # Log the operation
            self.output.info(f"Processing query: {query_text}")
            
            # Execute the query with progress indicator
            result = self.with_progress(
                "Processing query",
                self.mcp_client.call_tool,
                "dbp_general_query",
                query_data
            )
            
            # Display results
            self.output.format_output(result)
            
            return 0
            
        except CommandError as e:
            self.output.error(str(e))
            return 1
        except Exception as e:
            return self.handle_api_error(e)
