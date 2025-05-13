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
# Implements the Click-based 'query' command for the CLI, which exposes the
# natural language query functionality of the MCP server's dbp_general_query tool.
###############################################################################
# [Source file design principles]
# - Uses Click decorators for command definition and argument parsing
# - Integrates with the Click-based CLI architecture
# - Maintains compatibility with the original query command behavior
# - Provides direct natural language access to the dbp_general_query MCP tool
# - Formats and displays results consistently
###############################################################################
# [Source file constraints]
# - Depends on the MCP server supporting the 'dbp_general_query' tool
# - Query handling ultimately depends on the server's ability to interpret queries
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# codebase:src/dbp_cli/exceptions.py
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T01:33:20Z : Fixed import statements for proper module resolution by CodeAssistant
# * Changed relative imports (from ...exceptions) to absolute imports (from dbp_cli.exceptions)
# * Fixed ImportError: attempted relative import beyond top-level package
# 2025-05-12T18:35:40Z : Fixed decorator order by CodeAssistant
# * Rearranged decorators to ensure @pass_context is applied first 
# * Fixed missing context parameter error
# 2025-05-12T15:41:38Z : Initial creation of Click-based query command by CodeAssistant
# * Implemented Click-based version of query command
# * Maintained compatibility with original command functionality
###############################################################################

import logging
from typing import List, Optional

import click

from ..common import api_command, catch_errors, get_output_adapter
from dbp_cli.exceptions import CommandError

logger = logging.getLogger(__name__)


@click.command(
    name="query",
    help="Execute a natural language query about the codebase and documentation",
    short_help="Execute a natural language query",
)
@click.argument("query_text", nargs=-1, required=True)
@click.option(
    "--budget",
    type=float,
    help="Maximum cost budget for LLM usage",
)
@click.option(
    "--timeout",
    type=int,
    help="Maximum execution time in milliseconds",
)
@click.pass_context
@api_command
@catch_errors
def query_command(
    ctx: click.Context,
    query_text: List[str],
    budget: Optional[float] = None,
    timeout: Optional[int] = None,
) -> int:
    """
    [Function intent]
    Execute a natural language query using the MCP server's dbp_general_query tool.
    
    [Implementation details]
    Combines query text into a single string, prepares query parameters including
    optional budget and timeout controls, executes the query using the MCP client,
    and displays the results. Shows a progress indicator during query execution.
    
    [Design principles]
    User-friendly interface - accepts natural language input.
    Resource control - allows limiting cost and execution time.
    Transparent processing - shows progress during execution.
    Error handling - captures and reports errors appropriately.
    
    Args:
        ctx: Click's context object with application context in obj attribute
        query_text: Natural language query text parts
        budget: Optional maximum cost budget for LLM usage
        timeout: Optional maximum execution time in milliseconds
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    try:
        # Combine query words into a single string
        combined_query = " ".join(query_text)
        
        # Prepare query data
        query_data = {
            "query": combined_query
        }
        
        # Add processing control parameters
        if budget is not None:
            query_data["max_cost_budget"] = budget
        
        if timeout is not None:
            query_data["max_execution_time_ms"] = timeout
        
        # Log the operation
        output.info(f"Processing query: {combined_query}")
        
        # Execute the query with progress indicator
        result = ctx.obj.with_progress(
            "Processing query",
            ctx.obj.api_client.call_tool,
            "dbp_general_query",
            query_data
        )
        
        # Display results
        output.format_output(result)
        
        return 0
        
    except CommandError as e:
        output.error(str(e))
        return 1
