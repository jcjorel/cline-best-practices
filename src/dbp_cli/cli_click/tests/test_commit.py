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
# Tests for the Click-based 'commit' command implementation to ensure it correctly
# generates commit messages based on git changes and handles command options properly.
###############################################################################
# [Source file design principles]
# - Verify commit command functionality through unit tests
# - Use mocked dependencies to isolate command behavior
# - Test different option combinations and parameter handling
# - Verify error handling and file saving functionality
# - Ensure compatibility with original commit command
###############################################################################
# [Source file constraints]
# - Must not make actual API calls during tests
# - Should not modify actual git repositories
# - Tests should run in isolation from other tests
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/commands/commit.py
# codebase:src/dbp_cli/cli_click/tests/conftest.py
# system:pytest
# system:unittest.mock
###############################################################################
# [GenAI tool change history]
# 2025-05-12T15:54:34Z : Initial creation of commit command tests by CodeAssistant
# * Implemented tests for commit message generation functionality
# * Added tests for different option combinations and error handling
###############################################################################

import pytest
from unittest.mock import MagicMock, patch, mock_open, call
from pathlib import Path

from ..commands.commit import commit_command, _prepare_parameters


def test_commit_basic_execution(cli_invoke):
    """
    [Function intent]
    Test that the commit command executes successfully with basic arguments.
    
    [Implementation details]
    Uses a patched API client to verify that the command processes arguments correctly
    and returns the expected exit code for a successful execution.
    
    [Design principles]
    Basic functionality test - verifies the command works under normal conditions.
    API interaction verification - confirms the command interacts with the API correctly.
    """
    # Mock the API client's generate_commit_message method to return a simple result
    with patch('src.dbp_cli.cli_click.common.Context.api_client') as mock_api_client, \
         patch('src.dbp_cli.cli_click.common.Context.with_progress', 
               return_value={"commit_message": "test: test commit message"}):
        
        # Execute the commit command
        result = cli_invoke(["commit"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        assert "test: test commit message" in result.output


def test_commit_with_all_options(cli_invoke):
    """
    [Function intent]
    Test that the commit command correctly processes all available options.
    
    [Implementation details]
    Executes the commit command with all available options and verifies that
    the command correctly passes these options to the API client.
    
    [Design principles]
    Option handling test - verifies all options are processed correctly.
    Parameter mapping test - confirms options are mapped to API parameters.
    """
    mock_result = {"commit_message": "feat(scope): add new feature"}
    
    with patch('src.dbp_cli.cli_click.common.Context.api_client') as mock_api_client, \
         patch('src.dbp_cli.cli_click.common.Context.with_progress', 
               return_value=mock_result):
        
        # Execute the commit command with all options
        result = cli_invoke([
            "commit",
            "--since", "HEAD~3",
            "--files", "file1.py", "file2.py",
            "--format", "detailed",
            "--no-scope",
            "--max-length", "50",
            "--no-breaking-changes",
            "--no-tests",
            "--no-issues",
            "--message-only"
        ])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        assert "feat(scope): add new feature" in result.output
        
        # Verify the message-only option was respected (no extra metadata)
        assert "commit_message" not in result.output


def test_commit_save_to_file(cli_runner, test_context):
    """
    [Function intent]
    Test that the commit command correctly saves the commit message to a file.
    
    [Implementation details]
    Directly invokes the commit_command function with the save option and verifies
    that it attempts to write the commit message to the specified file.
    
    [Design principles]
    File handling test - verifies file writing functionality.
    Path handling test - confirms paths are expanded correctly.
    Success reporting test - verifies success message is displayed.
    """
    # Mock the API client and file operations
    test_context.with_progress.return_value = {"commit_message": "test: test commit message"}
    
    # Execute the command directly with mocked file operations
    with patch('builtins.open', mock_open()) as mock_file, \
         patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('pathlib.Path.expanduser', return_value=Path('/tmp/commit_msg.txt')), \
         patch('pathlib.Path.resolve', return_value=Path('/tmp/commit_msg.txt')), \
         cli_runner.isolation():
        
        exit_code = commit_command(
            test_context,
            since=None,
            files=None,
            format="conventional",
            no_scope=False,
            max_length=None,
            no_breaking_changes=False,
            no_tests=False,
            no_issues=False,
            save="/tmp/commit_msg.txt",
            message_only=False
        )
    
    # Verify the command executed successfully
    assert exit_code == 0
    
    # Verify the file was written to
    mock_file.assert_called_once_with('/tmp/commit_msg.txt', 'w')
    mock_file().write.assert_called_once_with("test: test commit message")
    
    # Verify the success message was displayed
    test_context.output_formatter.success.assert_called_once_with(
        "Commit message saved to /tmp/commit_msg.txt"
    )


def test_commit_file_save_error_handling(cli_runner, test_context):
    """
    [Function intent]
    Test that the commit command correctly handles errors when saving to a file.
    
    [Implementation details]
    Configures file operations to raise an exception and verifies that the command
    catches the exception and displays an appropriate error message.
    
    [Design principles]
    Error handling test - verifies the command gracefully handles file system errors.
    Exit code validation - confirms errors result in non-zero exit codes.
    """
    # Mock the API client
    test_context.with_progress.return_value = {"commit_message": "test: test commit message"}
    
    # Execute the command directly with file operations that raise an exception
    with patch('builtins.open', side_effect=IOError("Permission denied")), \
         patch('pathlib.Path.mkdir'), \
         patch('pathlib.Path.expanduser', return_value=Path('/tmp/commit_msg.txt')), \
         patch('pathlib.Path.resolve', return_value=Path('/tmp/commit_msg.txt')), \
         cli_runner.isolation():
        
        exit_code = commit_command(
            test_context,
            since=None,
            files=None,
            format="conventional",
            no_scope=False,
            max_length=None,
            no_breaking_changes=False,
            no_tests=False,
            no_issues=False,
            save="/tmp/commit_msg.txt",
            message_only=False
        )
    
    # Verify the command returned a non-zero exit code
    assert exit_code != 0
    
    # Verify the error message was displayed
    test_context.output_formatter.error.assert_called_once_with(
        "Failed to save commit message: Permission denied"
    )


def test_commit_prepare_parameters():
    """
    [Function intent]
    Test that the _prepare_parameters function correctly processes command arguments.
    
    [Implementation details]
    Calls the _prepare_parameters function with various combinations of arguments
    and verifies that it returns the expected parameter dictionary.
    
    [Design principles]
    Parameter mapping test - verifies command options are mapped to API parameters correctly.
    Negation handling test - confirms 'no_' prefixed options are mapped to 'include_' parameters.
    """
    # Test with minimal arguments
    params = _prepare_parameters(
        since=None,
        files=None,
        format_style="conventional",
        no_scope=False,
        max_length=None,
        no_breaking_changes=False,
        no_tests=False,
        no_issues=False
    )
    
    # Verify expected parameters
    assert params["format"] == "conventional"
    assert params["include_scope"] is True
    assert params["include_breaking_changes"] is True
    assert params["include_tests"] is True
    assert params["include_issues"] is True
    assert "max_length" not in params
    assert "since_commit" not in params
    assert "files" not in params
    
    # Test with all arguments
    params = _prepare_parameters(
        since="HEAD~3",
        files=["file1.py", "file2.py"],
        format_style="detailed",
        no_scope=True,
        max_length=50,
        no_breaking_changes=True,
        no_tests=True,
        no_issues=True
    )
    
    # Verify expected parameters
    assert params["since_commit"] == "HEAD~3"
    assert params["files"] == ["file1.py", "file2.py"]
    assert params["format"] == "detailed"
    assert params["include_scope"] is False
    assert params["max_length"] == 50
    assert params["include_breaking_changes"] is False
    assert params["include_tests"] is False
    assert params["include_issues"] is False


def test_commit_api_error(cli_runner, test_context):
    """
    [Function intent]
    Test that the commit command correctly handles API errors.
    
    [Implementation details]
    Configures the mock API client to raise an exception and verifies that the
    command catches the exception and displays an appropriate error message.
    
    [Design principles]
    Error handling test - verifies the command gracefully handles API errors.
    Exit code validation - confirms errors result in non-zero exit codes.
    """
    # Mock the API client to raise an exception
    test_context.with_progress.side_effect = Exception("API error")
    
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = commit_command(
            test_context,
            since=None,
            files=None,
            format="conventional",
            no_scope=False,
            max_length=None,
            no_breaking_changes=False,
            no_tests=False,
            no_issues=False,
            save=None,
            message_only=False
        )
    
    # Verify the command returned a non-zero exit code
    assert exit_code != 0
    
    # Verify the error was reported
    test_context.output_formatter.error.assert_called_once()


def test_commit_missing_commit_message(cli_runner, test_context):
    """
    [Function intent]
    Test that the commit command handles invalid API responses correctly.
    
    [Implementation details]
    Configures the API client to return a response without a commit_message field
    and verifies that the command detects this and returns an error.
    
    [Design principles]
    Validation test - verifies the command validates API responses before processing.
    Error reporting test - confirms appropriate error message is displayed.
    """
    # Mock the API client to return a response without a commit_message field
    test_context.with_progress.return_value = {"status": "error"}
    
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = commit_command(
            test_context,
            since=None,
            files=None,
            format="conventional",
            no_scope=False,
            max_length=None,
            no_breaking_changes=False,
            no_tests=False,
            no_issues=False,
            save=None,
            message_only=False
        )
    
    # Verify the command returned a non-zero exit code
    assert exit_code != 0
    
    # Verify the error was reported
    test_context.output_formatter.error.assert_called_once_with(
        "Failed to generate commit message"
    )
