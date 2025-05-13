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
# Tests the Click-based 'query' command implementation to ensure it correctly
# handles arguments, interacts with the API client, and formats results as expected.
###############################################################################
# [Source file design principles]
# - Verifies query command functionality through unit tests
# - Uses mocked dependencies to isolate command behavior
# - Checks different argument combinations and edge cases
# - Ensures API client interaction works correctly
# - Verifies error handling and exit codes
###############################################################################
# [Source file constraints]
# - Must not make actual API calls during tests
# - Should verify compatibility with original query command
# - Tests should run in isolation
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/commands/query.py
# codebase:src/dbp_cli/cli_click/tests/conftest.py
# system:pytest
# system:unittest.mock
###############################################################################
# [GenAI tool change history]
# 2025-05-12T15:42:47Z : Initial creation of query command tests by CodeAssistant
# * Implemented tests for basic query functionality
# * Added tests for argument handling and error conditions
###############################################################################

import pytest
from unittest.mock import MagicMock, patch, call

from ..commands.query import query_command


def test_query_basic_execution(cli_invoke):
    """
    [Function intent]
    Test that the query command executes successfully with basic arguments.
    
    [Implementation details]
    Uses a patched API client to verify the command processes arguments correctly
    and returns the expected exit code for a successful execution.
    
    [Design principles]
    Basic functionality test - verifies the command works under normal conditions.
    API interaction verification - confirms the command interacts with the API correctly.
    """
    # Mock the API client's call_tool method to return a simple result
    with patch('src.dbp_cli.cli_click.common.Context.with_progress', 
               return_value={"result": "Query executed successfully"}):
        # Execute the query command with a simple query
        result = cli_invoke(["query", "test", "query"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0


def test_query_with_budget(cli_runner, test_context):
    """
    [Function intent]
    Test that the query command correctly handles the --budget option.
    
    [Implementation details]
    Directly invokes the query_command function with a mocked context and
    verifies that the budget parameter is correctly included in the API request.
    
    [Design principles]
    Parameter validation - verifies option handling works correctly.
    API request validation - confirms parameters are passed to the API correctly.
    """
    # Set up mock API client
    test_context.api_client.call_tool.return_value = {"result": "Query with budget executed"}
    
    # Execute the command directly
    with cli_runner.isolation():
        query_command(test_context, ["test", "query"], budget=10.5, timeout=None)
    
    # Verify the API client was called with the correct budget parameter
    test_context.api_client.call_tool.assert_called_once()
    args, kwargs = test_context.api_client.call_tool.call_args
    assert args[0] == "dbp_general_query"
    assert args[1]["query"] == "test query"
    assert args[1]["max_cost_budget"] == 10.5


def test_query_with_timeout(cli_runner, test_context):
    """
    [Function intent]
    Test that the query command correctly handles the --timeout option.
    
    [Implementation details]
    Directly invokes the query_command function with a mocked context and
    verifies that the timeout parameter is correctly included in the API request.
    
    [Design principles]
    Parameter validation - verifies option handling works correctly.
    API request validation - confirms parameters are passed to the API correctly.
    """
    # Set up mock API client
    test_context.api_client.call_tool.return_value = {"result": "Query with timeout executed"}
    
    # Execute the command directly
    with cli_runner.isolation():
        query_command(test_context, ["test", "query"], budget=None, timeout=5000)
    
    # Verify the API client was called with the correct timeout parameter
    test_context.api_client.call_tool.assert_called_once()
    args, kwargs = test_context.api_client.call_tool.call_args
    assert args[0] == "dbp_general_query"
    assert args[1]["query"] == "test query"
    assert args[1]["max_execution_time_ms"] == 5000


def test_query_error_handling(cli_runner, test_context):
    """
    [Function intent]
    Test that the query command correctly handles API errors.
    
    [Implementation details]
    Configures the mock API client to raise an exception and verifies that
    the command handles the error properly, returning a non-zero exit code.
    
    [Design principles]
    Error handling validation - ensures errors are handled gracefully.
    Exit code verification - confirms errors result in appropriate exit codes.
    """
    # Set up mock API client to raise an exception
    test_context.api_client.call_tool.side_effect = Exception("API error")
    
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = query_command(test_context, ["test", "query"])
    
    # Verify the command returns a non-zero exit code
    assert exit_code != 0
    
    # Verify the error was reported
    test_context.output_formatter.error.assert_called_once()
