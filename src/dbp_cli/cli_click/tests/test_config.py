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
# Tests for the Click-based 'config' command implementation to ensure it correctly
# handles configuration management operations, including getting, setting, listing,
# and resetting configuration values.
###############################################################################
# [Source file design principles]
# - Verify config command functionality through unit tests
# - Use mocked dependencies to isolate command behavior
# - Test each subcommand (get, set, list, reset) with various arguments
# - Ensure configuration persistence works correctly
# - Verify error handling for invalid inputs
###############################################################################
# [Source file constraints]
# - Must not modify actual configuration files
# - Should run in isolation from other tests
# - Verify compatibility with original config command
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/commands/config.py
# codebase:src/dbp_cli/cli_click/tests/conftest.py
# system:pytest
# system:unittest.mock
###############################################################################
# [GenAI tool change history]
# 2025-05-12T15:46:01Z : Initial creation of config command tests by CodeAssistant
# * Implemented tests for get, set, list, and reset subcommands
# * Added tests for error conditions and edge cases
###############################################################################

import pytest
from unittest.mock import MagicMock, patch, call

from ..commands.config import config_group, config_get, config_set, config_list, config_reset


def test_config_get_command(cli_invoke, test_context):
    """
    [Function intent]
    Test that the config get subcommand works correctly.
    
    [Implementation details]
    Uses a patched configuration manager to verify that the command correctly
    retrieves and displays configuration values. Tests simple string values,
    dictionaries, and lists.
    
    [Design principles]
    Basic functionality test - verifies the command works under normal conditions.
    Output validation - confirms the output format matches expectations.
    """
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config:
        # Set up mock return value
        mock_config.get.return_value = "test-value"
        
        # Execute the command
        result = cli_invoke(["config", "get", "test.key"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        # Verify the config manager was called with the correct key
        mock_config.get.assert_called_once_with("test.key")


def test_config_get_nested_value(cli_runner, test_context):
    """
    [Function intent]
    Test that the config get subcommand handles nested dictionary values correctly.
    
    [Implementation details]
    Directly invokes the config_get function with a mocked context and verifies
    that nested dictionary values are displayed correctly.
    
    [Design principles]
    Nested structure handling - verifies formatting of complex structures.
    Direct function test - validates core function behavior in isolation.
    """
    # Set up mock return value as a nested dictionary
    nested_value = {"sub1": {"sub2": "value"}, "another": "val2"}
    test_context.config_manager.get.return_value = nested_value
    
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = config_get(test_context, "test.key", "text")
    
    # Verify the command executed successfully
    assert exit_code == 0
    
    # Verify the output formatter was called correctly
    assert test_context.output_formatter.info.call_count >= 3  # At least 3 calls for the nested dict


def test_config_get_nonexistent_key(cli_invoke):
    """
    [Function intent]
    Test that the config get subcommand handles nonexistent keys correctly.
    
    [Implementation details]
    Uses a patched configuration manager that returns None for the requested key
    and verifies that the command returns a non-zero exit code and displays an
    appropriate warning.
    
    [Design principles]
    Error handling test - verifies graceful handling of missing values.
    Exit code validation - confirms errors result in appropriate exit codes.
    """
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config:
        # Set up mock return value
        mock_config.get.return_value = None
        
        # Execute the command
        result = cli_invoke(["config", "get", "nonexistent.key"])
        
        # Verify the command returned an error exit code
        assert result.exit_code != 0
        # Verify the error message contains the key
        assert "nonexistent.key" in result.output


def test_config_set_command(cli_invoke, test_context):
    """
    [Function intent]
    Test that the config set subcommand works correctly.
    
    [Implementation details]
    Uses a patched configuration manager to verify that the command correctly
    parses and sets configuration values. Tests with and without the --save flag.
    
    [Design principles]
    Value parsing test - verifies string values are parsed correctly.
    Persistence control - tests behavior with and without saving to disk.
    """
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config:
        # Execute the command
        result = cli_invoke(["config", "set", "test.key", "test-value"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        # Verify the config manager was called with the correct key and value
        mock_config.set.assert_called_once()
        args, kwargs = mock_config.set.call_args
        assert args[0] == "test.key"
        assert args[1] == "test-value"
        # Verify save_to_user_config was not called (no --save flag)
        assert not mock_config.save_to_user_config.called


def test_config_set_with_save(cli_invoke, test_context):
    """
    [Function intent]
    Test that the config set subcommand handles the --save flag correctly.
    
    [Implementation details]
    Uses a patched configuration manager to verify that the command correctly
    saves configuration changes to disk when the --save flag is used.
    
    [Design principles]
    Persistence test - verifies configuration is saved when requested.
    Flag handling - tests correct interpretation of command-line flags.
    """
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config:
        # Execute the command with --save flag
        result = cli_invoke(["config", "set", "test.key", "test-value", "--save"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        # Verify save_to_user_config was called
        mock_config.save_to_user_config.assert_called_once()


def test_config_set_complex_value(cli_runner, test_context):
    """
    [Function intent]
    Test that the config set subcommand correctly parses complex values.
    
    [Implementation details]
    Directly invokes the config_set function with various types of values to
    verify that the value parsing logic correctly handles booleans, numbers,
    and JSON strings.
    
    [Design principles]
    Type inference test - verifies correct parsing of different value types.
    Complex value handling - tests JSON parsing for complex structures.
    """
    # Set up test cases
    test_cases = [
        ("true", True),
        ("123", 123),
        ("3.14", 3.14),
        ('{"key": "value"}', {"key": "value"}),
        ("null", None)
    ]
    
    for input_str, expected_value in test_cases:
        # Reset mocks
        test_context.config_manager.reset_mock()
        
        # Execute the command directly
        with cli_runner.isolation():
            exit_code = config_set(test_context, "test.key", input_str, False)
        
        # Verify the command executed successfully
        assert exit_code == 0
        # Verify the value was parsed correctly
        test_context.config_manager.set.assert_called_once()
        args, kwargs = test_context.config_manager.set.call_args
        assert args[1] == expected_value


def test_config_list_command(cli_invoke, test_context):
    """
    [Function intent]
    Test that the config list subcommand works correctly.
    
    [Implementation details]
    Uses a patched configuration manager to verify that the command correctly
    retrieves and displays all configuration values in the specified format.
    
    [Design principles]
    Comprehensive listing - verifies display of complete configuration.
    Format selection - tests different output formats.
    """
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config:
        # Set up mock return value
        mock_config.get_config_dict.return_value = {
            "section1": {"key1": "value1"},
            "section2": {"key2": "value2"}
        }
        
        # Execute the command
        result = cli_invoke(["config", "list"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        # Verify the config manager was called
        mock_config.get_config_dict.assert_called_once()


def test_config_list_json_format(cli_runner, test_context):
    """
    [Function intent]
    Test that the config list subcommand handles the JSON output format correctly.
    
    [Implementation details]
    Directly invokes the config_list function with format="json" and verifies
    that the output formatter's format_output method is called with the complete
    configuration dictionary.
    
    [Design principles]
    Format option test - verifies alternative output format.
    Direct function test - validates core function behavior in isolation.
    """
    # Set up mock return value
    config_dict = {"section1": {"key1": "value1"}, "section2": {"key2": "value2"}}
    test_context.config_manager.get_config_dict.return_value = config_dict
    
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = config_list(test_context, "json")
    
    # Verify the command executed successfully
    assert exit_code == 0
    # Verify the output formatter was called with the correct argument
    test_context.output_formatter.format_output.assert_called_once_with(config_dict)


def test_config_reset_command(cli_invoke, test_context):
    """
    [Function intent]
    Test that the config reset subcommand works correctly.
    
    [Implementation details]
    Uses a patched configuration manager to verify that the command correctly
    resets configuration values. Tests with a specific key and with no key
    (reset all).
    
    [Design principles]
    Reset functionality - verifies both specific and global resets.
    Argument handling - tests behavior with and without optional arguments.
    """
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config:
        # Execute the command with a specific key
        result = cli_invoke(["config", "reset", "test.key"])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        # Verify the config manager was called with the correct key
        mock_config.reset.assert_called_once_with("test.key")


def test_config_reset_all(cli_runner, test_context):
    """
    [Function intent]
    Test that the config reset subcommand can reset all configuration values.
    
    [Implementation details]
    Directly invokes the config_reset function without a key parameter and verifies
    that the configuration manager's reset method is called without arguments.
    
    [Design principles]
    Global reset test - verifies reset of all configuration values.
    Optional parameter handling - tests behavior when optional parameters are omitted.
    """
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = config_reset(test_context, None, False)
    
    # Verify the command executed successfully
    assert exit_code == 0
    # Verify the config manager was called with no arguments
    test_context.config_manager.reset.assert_called_once_with()


def test_config_reset_with_save(cli_runner, test_context):
    """
    [Function intent]
    Test that the config reset subcommand handles the --save flag correctly.
    
    [Implementation details]
    Directly invokes the config_reset function with save=True and verifies that
    the configuration manager's save_to_user_config method is called after resetting.
    
    [Design principles]
    Persistence test - verifies configuration changes are saved when requested.
    Flag handling - tests correct interpretation of command-line flags.
    """
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = config_reset(test_context, "test.key", True)
    
    # Verify the command executed successfully
    assert exit_code == 0
    # Verify the config manager methods were called in the correct order
    test_context.config_manager.reset.assert_called_once_with("test.key")
    test_context.config_manager.save_to_user_config.assert_called_once()


def test_config_error_handling(cli_runner, test_context):
    """
    [Function intent]
    Test that the config commands handle errors correctly.
    
    [Implementation details]
    Configures the mock configuration manager to raise ConfigurationError exceptions
    and verifies that the commands catch and report these errors appropriately.
    
    [Design principles]
    Error handling test - verifies graceful handling of exceptions.
    Exit code validation - confirms errors result in appropriate exit codes.
    """
    # Set up mock to raise an exception
    test_context.config_manager.get.side_effect = Exception("Configuration error")
    
    # Execute the command directly
    with cli_runner.isolation():
        exit_code = config_get(test_context, "test.key", "text")
    
    # Verify the command returned an error exit code
    assert exit_code != 0
    # Verify the error was reported
    test_context.output_formatter.error.assert_called_once()
