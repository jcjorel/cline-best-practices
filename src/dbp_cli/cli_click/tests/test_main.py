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
# Tests for the main CLI functionality of the Click-based CLI implementation.
# This file verifies the core CLI features like initialization, command execution,
# and error handling.
###############################################################################
# [Source file design principles]
# - Verify basic CLI functionality works as expected
# - Test global options and error handling
# - Ensure version command works correctly
# - Validate CLI structure and initialization
# - Focus on integration-level testing of CLI components
###############################################################################
# [Source file constraints]
# - Should not modify any real files or configuration
# - Must run in isolation from actual CLI environment
# - Tests should be independent and idempotent
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/main.py
# codebase:src/dbp_cli/cli_click/common.py
# codebase:src/dbp_cli/cli_click/tests/conftest.py
# system:pytest
# system:click.testing
###############################################################################
# [GenAI tool change history]
# 2025-05-12T15:38:45Z : Initial creation of main CLI tests by CodeAssistant
# * Added tests for CLI initialization, version command, and error handling
# * Implemented tests using pytest fixtures
###############################################################################

import pytest
from unittest.mock import patch, MagicMock
import click

from ..main import cli, main, version_command
from ..common import Context


def test_cli_basic_initialization(cli_runner):
    """
    [Function intent]
    Verify that the CLI can be initialized without errors.
    
    [Implementation details]
    Invokes the CLI with --help to ensure the basic command structure is working.
    
    [Design principles]
    Basic sanity check - ensures CLI can be executed without errors.
    Documentation verification - confirms help text is available.
    """
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Documentation-Based Programming CLI" in result.output
    assert "version" in result.output  # Verify version command is listed


def test_version_command(cli_runner, test_context):
    """
    [Function intent]
    Verify that the version command displays the correct version information.
    
    [Implementation details]
    Invokes the version command and checks that it outputs version information.
    
    [Design principles]
    Feature verification - ensures version command works correctly.
    Output validation - checks for expected output format.
    """
    # Mock get_version to return a fixed version
    test_context.get_version = lambda: "1.2.3"
    
    # Manually invoke the version command with our test context
    with cli_runner.isolation():
        version_command(test_context)
        
    # Verify output formatter was called with expected string
    test_context.output_formatter.print.assert_called_once_with("dbp-cli version 1.2.3")


def test_version_command_through_cli(cli_invoke):
    """
    [Function intent]
    Verify that the version command works correctly through the CLI interface.
    
    [Implementation details]
    Uses the CLI invoke fixture to execute the version command and verify output.
    
    [Design principles]
    Integration testing - tests command through the full CLI stack.
    End-to-end verification - confirms all components work together correctly.
    """
    with patch('src.dbp_cli.cli_click.common.Context.get_version', return_value="1.2.3"):
        result = cli_invoke(["version"])
        assert result.exit_code == 0
        assert "dbp-cli version 1.2.3" in result.output


def test_cli_unexpected_error_handling():
    """
    [Function intent]
    Verify that the CLI properly handles unexpected errors during execution.
    
    [Implementation details]
    Patches the Click group's main method to raise an exception, then verifies
    that the main function catches and handles the exception correctly.
    
    [Design principles]
    Error handling verification - ensures errors are handled gracefully.
    Exit code validation - confirms correct error code is returned.
    """
    with patch('click.Group.main', side_effect=RuntimeError("Test error")):
        exit_code = main(["version"])
        assert exit_code == 1  # Verify error exit code is returned


def test_cli_abort_handling():
    """
    [Function intent]
    Verify that the CLI properly handles user aborts (Ctrl+C).
    
    [Implementation details]
    Patches the Click group's main method to raise a Click Abort exception,
    then verifies that the main function catches and handles the exception correctly.
    
    [Design principles]
    User interrupt handling - ensures Ctrl+C is handled gracefully.
    Exit code validation - confirms conventional exit code 130 is returned.
    """
    with patch('click.Group.main', side_effect=click.Abort()):
        exit_code = main(["version"])
        assert exit_code == 130  # Convention for Ctrl+C


def test_cli_usage_error_handling():
    """
    [Function intent]
    Verify that the CLI properly handles command usage errors.
    
    [Implementation details]
    Patches the Click group's main method to raise a Usage Error exception,
    then verifies that the main function catches and handles the exception correctly.
    
    [Design principles]
    Usage error handling - ensures user errors are handled clearly.
    Exit code validation - confirms conventional exit code 2 is returned.
    """
    with patch('click.Group.main', side_effect=click.UsageError("Invalid usage")):
        exit_code = main(["version"])
        assert exit_code == 2  # Convention for usage errors
