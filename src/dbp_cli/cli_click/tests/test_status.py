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
# Tests for the Click-based 'status' command implementation to ensure it correctly
# checks and displays system information, server connectivity, authentication status,
# and configuration settings.
###############################################################################
# [Source file design principles]
# - Verify status command functionality through unit tests
# - Use mocked dependencies to isolate command behavior
# - Test each subcommand and option combination
# - Verify error handling for different failure scenarios
# - Ensure troubleshooting guidance is presented correctly
###############################################################################
# [Source file constraints]
# - Must not make actual API calls during tests
# - Should not modify actual configuration files
# - Tests should run in isolation from other tests
# - Should verify compatibility with original status command
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/commands/status.py
# codebase:src/dbp_cli/cli_click/tests/conftest.py
# system:pytest
# system:unittest.mock
###############################################################################
# [GenAI tool change history]
# 2025-05-12T15:50:38Z : Initial creation of status command tests by CodeAssistant
# * Implemented tests for various status command options and behavior
# * Added tests for error handling and troubleshooting guidance
###############################################################################

import pytest
from unittest.mock import MagicMock, patch, call
import json
import platform
import sys
from datetime import datetime

from ..commands.status import status_command, _check_server, _check_auth, _show_settings, _show_system_info
from ...exceptions import ConnectionError, AuthenticationError, APIError


def test_status_command_all_checks(cli_invoke):
    """
    [Function intent]
    Test that the status command performs all checks when no specific options are provided.
    
    [Implementation details]
    Uses patched dependencies to verify that all check functions are called when
    no specific options are provided to the status command.
    
    [Design principles]
    Default behavior test - verifies that the command performs all checks by default.
    Integration test - verifies the command properly coordinates all the check functions.
    """
    with patch('src.dbp_cli.cli_click.commands.status._show_system_info') as mock_sys_info, \
         patch('src.dbp_cli.cli_click.commands.status._check_server', return_value=True) as mock_check_server, \
         patch('src.dbp_cli.cli_click.commands.status._check_auth', return_value=True) as mock_check_auth, \
         patch('src.dbp_cli.cli_click.commands.status._show_settings') as mock_show_settings:
        
        # Execute the command with no specific options
        result = cli_invoke(["status"])
        
        # Verify all check functions were called
        assert result.exit_code == 0
        mock_sys_info.assert_called_once()
        mock_check_server.assert_called_once()
        mock_check_auth.assert_called_once()
        mock_show_settings.assert_called_once()


def test_status_command_specific_checks(cli_invoke):
    """
    [Function intent]
    Test that the status command only performs the requested checks when specific options are provided.
    
    [Implementation details]
    Uses patched dependencies to verify that only the specifically requested check
    functions are called when options are provided to the status command.
    
    [Design principles]
    Option handling test - verifies the command respects specific check options.
    Selective execution - confirms only requested checks are performed.
    """
    with patch('src.dbp_cli.cli_click.commands.status._show_system_info') as mock_sys_info, \
         patch('src.dbp_cli.cli_click.commands.status._check_server', return_value=True) as mock_check_server, \
         patch('src.dbp_cli.cli_click.commands.status._check_auth', return_value=True) as mock_check_auth, \
         patch('src.dbp_cli.cli_click.commands.status._show_settings') as mock_show_settings:
        
        # Execute the command with only check-server option
        result = cli_invoke(["status", "--check-server"])
        
        # Verify only the server check was performed
        assert result.exit_code == 0
        mock_sys_info.assert_called_once()
        mock_check_server.assert_called_once()
        mock_check_auth.assert_not_called()
        mock_show_settings.assert_not_called()
        
        # Reset mocks for next test
        mock_sys_info.reset_mock()
        mock_check_server.reset_mock()
        
        # Execute the command with check-auth and show-settings options
        result = cli_invoke(["status", "--check-auth", "--show-settings"])
        
        # Verify only auth and settings checks were performed
        assert result.exit_code == 0
        mock_sys_info.assert_called_once()
        mock_check_server.assert_not_called()
        mock_check_auth.assert_called_once()
        mock_show_settings.assert_called_once()


def test_status_command_error_handling(cli_invoke):
    """
    [Function intent]
    Test that the status command correctly reports errors and returns appropriate exit codes.
    
    [Implementation details]
    Configures mocked check functions to return failure status and verifies that
    the command returns a non-zero exit code.
    
    [Design principles]
    Error handling test - verifies the command reports failures correctly.
    Exit code validation - confirms failures result in non-zero exit codes.
    """
    with patch('src.dbp_cli.cli_click.commands.status._show_system_info'), \
         patch('src.dbp_cli.cli_click.commands.status._check_server', return_value=False) as mock_check_server, \
         patch('src.dbp_cli.cli_click.commands.status._check_auth', return_value=True) as mock_check_auth, \
         patch('src.dbp_cli.cli_click.commands.status._show_settings'):
        
        # Execute the command
        result = cli_invoke(["status"])
        
        # Verify the command returns a non-zero exit code due to server check failure
        assert result.exit_code != 0


def test_show_system_info(cli_runner, test_context):
    """
    [Function intent]
    Test that the _show_system_info function displays the correct system information.
    
    [Implementation details]
    Directly invokes the _show_system_info function and verifies that it outputs
    the expected system information. Uses verbose flag to test detailed output.
    
    [Design principles]
    Direct function test - validates core function behavior in isolation.
    Verbose option test - verifies additional output with verbose flag.
    """
    # Execute the function directly
    with cli_runner.isolation():
        _show_system_info(test_context, verbose=False)
    
    # Verify basic system information was displayed
    assert test_context.output_formatter.info.call_count >= 3
    calls = [
        call("=== System Information ==="),
        call(f"Platform: {platform.platform()}"),
        call(f"Python: {sys.version.split()[0]}")
    ]
    test_context.output_formatter.info.assert_has_calls(calls, any_order=False)
    
    # Reset mocks for verbose test
    test_context.output_formatter.reset_mock()
    
    # Test with verbose flag
    with cli_runner.isolation():
        _show_system_info(test_context, verbose=True)
    
    # Verify detailed system information was displayed
    assert test_context.output_formatter.info.call_count > 3
    calls = [
        call("=== System Information ==="),
        call(f"Platform: {platform.platform()}"),
        call(f"Python: {sys.version.split()[0]}"),
        call(f"Working Directory: {pytest.helpers.any_instance_of(str)}")
    ]
    test_context.output_formatter.info.assert_has_calls(calls, any_order=False)


def test_check_server_success(cli_runner, test_context):
    """
    [Function intent]
    Test that the _check_server function correctly handles successful server connections.
    
    [Implementation details]
    Configures the mock API client to return a successful response and verifies
    that the function displays the appropriate success messages and returns True.
    
    [Design principles]
    Success path test - verifies correct handling of successful server checks.
    Version display test - confirms server version is displayed when available.
    """
    # Configure mock API client
    mock_response = {"version": "1.2.3", "status": "ok"}
    test_context.api_client.get_server_status.return_value = mock_response
    test_context.config_manager.get_typed_config.return_value = MagicMock(mcp_server=MagicMock(url="http://localhost:6231"))
    
    # Execute the function directly
    with cli_runner.isolation():
        result = _check_server(test_context, verbose=False)
    
    # Verify success result and output
    assert result is True
    assert test_context.output_formatter.success.call_count >= 1
    test_context.output_formatter.success.assert_any_call("Server is running (version 1.2.3)")
    
    # Test with verbose flag and details
    test_context.output_formatter.reset_mock()
    mock_response["details"] = {"feature1": "enabled", "feature2": "disabled"}
    
    with cli_runner.isolation():
        result = _check_server(test_context, verbose=True)
    
    # Verify detailed output
    assert result is True
    assert test_context.output_formatter.info.call_count > 3
    test_context.output_formatter.info.assert_any_call("Server Details:")


def test_check_server_connection_error(cli_runner, test_context):
    """
    [Function intent]
    Test that the _check_server function correctly handles server connection errors.
    
    [Implementation details]
    Configures the mock API client to raise a ConnectionError and verifies that
    the function displays appropriate error messages and troubleshooting guidance.
    
    [Design principles]
    Error path test - verifies graceful handling of connection failures.
    Troubleshooting test - confirms helpful guidance is provided for different error types.
    """
    # Configure mock API client to raise a ConnectionError
    test_context.api_client.get_server_status.side_effect = ConnectionError("Connection refused")
    test_context.config_manager.get_typed_config.return_value = MagicMock(mcp_server=MagicMock(url="http://localhost:6231"))
    
    # Execute the function directly
    with cli_runner.isolation():
        result = _check_server(test_context, verbose=False)
    
    # Verify failure result and error message
    assert result is False
    test_context.output_formatter.error.assert_called_once_with("Server connection failed: Connection refused")
    
    # Verify troubleshooting suggestions were provided
    assert test_context.output_formatter.info.call_count >= 5
    test_context.output_formatter.info.assert_any_call("\nTroubleshooting suggestions:")
    
    # Test with a different error type
    test_context.output_formatter.reset_mock()
    test_context.api_client.get_server_status.side_effect = ConnectionError("Timed out")
    
    with cli_runner.isolation():
        result = _check_server(test_context, verbose=False)
    
    # Verify different troubleshooting suggestions for timeout
    assert result is False
    assert test_context.output_formatter.info.call_count >= 3
    test_context.output_formatter.info.assert_any_call("\nTroubleshooting suggestions:")
    test_context.output_formatter.info.assert_any_call("1. The server might be overloaded or unresponsive")


def test_check_auth(cli_runner, test_context):
    """
    [Function intent]
    Test that the _check_auth function correctly checks authentication status.
    
    [Implementation details]
    Configures the mock auth manager with different authentication states and
    verifies that the function displays appropriate messages and returns correct results.
    
    [Design principles]
    Authentication status test - verifies both authenticated and unauthenticated states.
    Verbose mode test - confirms additional authentication testing in verbose mode.
    """
    # Configure mock auth manager - authenticated
    test_context.auth_manager.is_authenticated.return_value = True
    
    # Execute the function directly
    with cli_runner.isolation():
        result = _check_auth(test_context, verbose=False)
    
    # Verify success result and message
    assert result is True
    test_context.output_formatter.success.assert_called_once_with("API key is configured")
    
    # Test unauthenticated state
    test_context.output_formatter.reset_mock()
    test_context.auth_manager.is_authenticated.return_value = False
    
    with cli_runner.isolation():
        result = _check_auth(test_context, verbose=False)
    
    # Verify failure result and guidance
    assert result is False
    test_context.output_formatter.error.assert_called_once_with("No API key configured")
    assert test_context.output_formatter.info.call_count >= 1
    
    # Test verbose mode with authentication test
    test_context.output_formatter.reset_mock()
    test_context.auth_manager.is_authenticated.return_value = True
    
    with cli_runner.isolation():
        result = _check_auth(test_context, verbose=True)
    
    # Verify authentication test was performed
    assert result is True
    test_context.output_formatter.info.assert_any_call("Testing authentication...")
    test_context.api_client.get_server_status.assert_called_once()
    test_context.output_formatter.success.assert_any_call("Authentication successful")


def test_check_auth_error(cli_runner, test_context):
    """
    [Function intent]
    Test that the _check_auth function correctly handles authentication errors.
    
    [Implementation details]
    Configures the mock API client to raise an AuthenticationError during the
    authentication test and verifies that the function displays the appropriate
    error message and returns False.
    
    [Design principles]
    Error path test - verifies graceful handling of authentication failures.
    Verbose mode error test - confirms verbose mode error handling.
    """
    # Configure mock auth manager and API client
    test_context.auth_manager.is_authenticated.return_value = True
    test_context.api_client.get_server_status.side_effect = AuthenticationError("Invalid API key")
    
    # Execute the function directly with verbose mode
    with cli_runner.isolation():
        result = _check_auth(test_context, verbose=True)
    
    # Verify failure result and error message
    assert result is False
    test_context.output_formatter.error.assert_called_once_with("Authentication failed: Invalid API key")


def test_show_settings(cli_runner, test_context):
    """
    [Function intent]
    Test that the _show_settings function correctly displays configuration settings.
    
    [Implementation details]
    Configures the mock configuration manager with test settings and verifies
    that the function displays the settings correctly in both normal and verbose modes.
    
    [Design principles]
    Settings display test - verifies key settings are displayed.
    Verbose mode test - confirms additional settings shown in verbose mode.
    Security test - verifies sensitive values like API keys are masked.
    """
    # Configure mock config manager
    mock_config = MagicMock()
    mock_config.mcp_server.url = "http://localhost:6231"
    mock_config.mcp_server.timeout = 30
    mock_config.cli.output_format = "text"
    mock_config.cli.color = True
    mock_config.cli.progress_bar = True
    mock_config.dict.return_value = {
        "mcp_server": {
            "url": "http://localhost:6231",
            "timeout": 30,
            "api_key": "secret-key"
        },
        "cli": {
            "output_format": "text",
            "color": True,
            "progress_bar": True
        }
    }
    
    test_context.config_manager.get_typed_config.return_value = mock_config
    test_context.auth_manager.is_authenticated.return_value = True
    
    # Execute the function directly
    with cli_runner.isolation():
        _show_settings(test_context, verbose=False)
    
    # Verify key settings were displayed
    assert test_context.output_formatter.info.call_count >= 6
    test_context.output_formatter.info.assert_any_call("=== Current Settings ===")
    test_context.output_formatter.info.assert_any_call("Server URL: http://localhost:6231")
    test_context.output_formatter.info.assert_any_call("Request Timeout: 30s")
    test_context.output_formatter.info.assert_any_call("API Key: Configured")
    
    # Test verbose mode
    test_context.output_formatter.reset_mock()
    
    with cli_runner.isolation():
        _show_settings(test_context, verbose=True)
    
    # Verify all settings were displayed and API key was masked
    assert test_context.output_formatter.info.call_count > 6
    test_context.output_formatter.info.assert_any_call("\nAll Settings:")
    # The API key should be masked
    test_context.output_formatter.info.assert_any_call("  mcp_server.api_key: ***")
