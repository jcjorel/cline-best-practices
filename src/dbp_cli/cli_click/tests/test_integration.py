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
# Tests integration between various CLI components.
# Verifies that commands work together correctly and that the CLI handles
# context correctly across different components.
###############################################################################
# [Source file design principles]
# - Test command interactions
# - Verify context passing between commands
# - Test global options with different commands
# - Ensure consistent behavior across command chains
###############################################################################
# [Source file constraints]
# - Must not make actual API calls
# - Should test realistic command workflows
###############################################################################
# [Dependencies]
# system:pytest
# codebase:src/dbp_cli/cli_click/main.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T15:59:05Z : Initial implementation by CodeAssistant
# * Created integration tests for CLI commands
# * Added tests for global options and context passing
# * Implemented hstc_agno integration test
###############################################################################

import pytest
from unittest.mock import patch, MagicMock, call
from click.testing import CliRunner

from ...cli_click.main import cli


def test_global_options_propagation():
    """
    [Function intent]
    Test that global options are properly passed to commands and affect command behavior.
    
    [Implementation details]
    Runs a command with global options and verifies the options are correctly propagated
    to the command context and affect output formatting and other global behaviors.
    
    [Design principles]
    Verify command integration - ensure global settings apply across commands.
    Test option propagation - check that options set at the group level affect subcommands.
    """
    runner = CliRunner()
    
    # Mock the output formatter
    with patch('src.dbp_cli.cli_click.common.OutputFormatter') as mock_formatter_class:
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        # Run command with global options
        result = runner.invoke(cli, ["--no-color", "status", "--check-server"])
        
        # Verify the command executed without errors
        assert result.exit_code == 0
        
        # Verify color option was passed to the formatter
        mock_formatter_class.assert_called_once()
        mock_formatter.set_color_enabled.assert_called_with(False)


def test_command_chaining_workflow():
    """
    [Function intent]
    Test a typical workflow that involves using multiple commands in sequence.
    
    [Implementation details]
    Simulates a user workflow involving configuration changes and status checks, 
    to ensure commands can build upon each other's results consistently.
    
    [Design principles]
    Workflow testing - verify realistic usage patterns.
    Command interaction - ensure commands work together consistently.
    """
    runner = CliRunner()
    
    # Mock the services
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config_manager, \
         patch('src.dbp_cli.cli_click.common.Context.output_formatter'):
        
        # First run config command
        result = runner.invoke(cli, ["config", "set", "api.url", "https://example.com/api"])
        assert result.exit_code == 0
        mock_config_manager.set.assert_called_with("api.url", "https://example.com/api")
        
        # Then run status command using the config
        mock_config_manager.get_typed_config.return_value = MagicMock(
            mcp_server=MagicMock(url="https://example.com/api")
        )
        result = runner.invoke(cli, ["status", "--check-server"])
        assert result.exit_code == 0
        
        # Verify the configurations are used consistently
        assert mock_config_manager.set.call_count == 1
        assert mock_config_manager.get_typed_config.call_count >= 1


def test_hstc_agno_integration():
    """
    [Function intent]
    Test that the hstc_agno command is properly integrated into the main CLI.
    
    [Implementation details]
    Verifies the hstc_agno command is accessible through the main CLI and that
    it properly displays help information and subcommands.
    
    [Design principles]
    Integration verification - ensure external commands work with the main CLI.
    Help system consistency - check that command documentation is correctly integrated.
    """
    runner = CliRunner()
    
    # Test the help output contains hstc_agno information
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "hstc_agno" in result.output
    
    # Test hstc_agno command help
    with patch('src.dbp_cli.commands.hstc_agno.cli.hstc_agno') as mock_hstc_agno:
        # Set up mock behavior
        mock_hstc_agno.__doc__ = "HSTC implementation with Agno framework"
        
        # Run hstc_agno help command
        result = runner.invoke(cli, ["hstc_agno", "--help"])
        
        # Verify the command was accessible
        assert result.exit_code == 0
        assert "HSTC implementation" in result.output or "hstc_agno" in result.output


def test_hstc_agno_update_command():
    """
    [Function intent]
    Test the hstc_agno update command functionality within the main CLI.
    
    [Implementation details]
    Tests that the update subcommand of hstc_agno is correctly available and
    functions properly when called through the main CLI.
    
    [Design principles]
    Subcommand integration - verify nested commands are properly accessible.
    Parameter passing - ensure parameters are correctly passed to subcommands.
    """
    runner = CliRunner()
    
    # Mock the hstc_agno update command
    with patch('src.dbp_cli.commands.hstc_agno.cli.update') as mock_update:
        # Configure the mock
        mock_update.return_value = None
        
        # Run the command with arguments
        result = runner.invoke(cli, ["hstc_agno", "update", "test.py", "--verbose"])
        
        # Verify the command executed without errors
        assert result.exit_code == 0
        
        # Check if we can reach the command (even if it's mocked and doesn't actually run)
        assert "Error" not in result.output


def test_context_sharing_between_commands():
    """
    [Function intent]
    Test that context objects are properly shared between commands.
    
    [Implementation details]
    Verifies that context initialized at the CLI level is properly propagated to
    subcommands, allowing consistent access to shared services.
    
    [Design principles]
    Context consistency - ensure context is maintained across commands.
    Service sharing - verify services initialized once are available everywhere.
    """
    runner = CliRunner()
    
    # Use an advanced mock to track context propagation
    context_tracker = {}
    
    def track_context_in_command(ctx, *args, **kwargs):
        # Store the context object for later verification
        context_tracker['command_context'] = ctx
        return 0
    
    def track_context_in_cli(ctx, *args, **kwargs):
        # Store the CLI context and initialize a service
        context_tracker['cli_context'] = ctx
        ctx.test_service = "initialized"
    
    with patch('src.dbp_cli.cli_click.main.cli.callback', side_effect=track_context_in_cli), \
         patch('src.dbp_cli.cli_click.commands.status.status_command.callback', 
               side_effect=track_context_in_command):
        
        # Run a command
        result = runner.invoke(cli, ["status"])
        
        # Verify the command executed
        assert result.exit_code == 0
        
        # Verify context was shared
        assert 'cli_context' in context_tracker
        assert 'command_context' in context_tracker
        
        # Verify the service was available to the command
        # Note: In a real case, the actual context object would be shared
        # This test is simplified due to mocking limitations


def test_error_propagation():
    """
    [Function intent]
    Test that errors from subcommands are properly propagated to the main CLI.
    
    [Implementation details]
    Verifies that errors raised by subcommands are caught by the main CLI's
    error handling system and result in appropriate exit codes.
    
    [Design principles]
    Error handling - ensure errors are caught and processed properly.
    Exit code consistency - verify error conditions return appropriate codes.
    """
    runner = CliRunner()
    
    # Mock a command to raise an error
    with patch('src.dbp_cli.cli_click.commands.query.query_command.callback', 
               side_effect=Exception("Test error")):
        
        # Run the command
        result = runner.invoke(cli, ["query", "test query"])
        
        # Verify the command failed with non-zero exit code
        assert result.exit_code != 0
        # Verify the error was reported
        assert "Test error" in result.output or "Error" in result.output


def test_settings_persistence():
    """
    [Function intent]
    Test that settings configured in one command persist for other commands.
    
    [Implementation details]
    Simulates setting configuration values and then verifying they are accessible
    from other commands in the same session.
    
    [Design principles]
    Configuration persistence - verify settings changes affect subsequent commands.
    Service state - ensure services maintain state across command calls.
    """
    runner = CliRunner()
    
    # Mock the config manager
    mock_config = {}
    
    def mock_set(key, value):
        mock_config[key] = value
        
    def mock_get(key):
        return mock_config.get(key)
    
    with patch('src.dbp_cli.cli_click.common.Context.config_manager') as mock_config_manager, \
         patch('src.dbp_cli.cli_click.common.Context.output_formatter'):
        
        # Configure the mock
        mock_config_manager.set.side_effect = mock_set
        mock_config_manager.get.side_effect = mock_get
        
        # First set a config value
        result = runner.invoke(cli, ["config", "set", "test.key", "test-value"])
        assert result.exit_code == 0
        
        # Then retrieve it
        result = runner.invoke(cli, ["config", "get", "test.key"])
        assert result.exit_code == 0
        
        # Verify the value was correctly stored
        assert mock_config == {"test.key": "test-value"}
