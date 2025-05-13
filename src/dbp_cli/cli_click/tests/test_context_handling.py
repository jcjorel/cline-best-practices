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
# Tests the improved Click context handling mechanism, verifying that the 
# application's context (AppContext) is properly initialized and accessible
# through Click's native context object.
###############################################################################
# [Source file design principles]
# - Comprehensive validation of context initialization
# - Verify commands can access both Click context features and app services
# - Test context inheritance across command groups
# - Use pytest fixtures for clean test setup and teardown
# - Isolated test cases with clear assertions
###############################################################################
# [Source file constraints]
# - Must validate context without external dependencies like API calls
# - Tests should run quickly and not require a real server connection
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# codebase:src/dbp_cli/cli_click/main.py
# system:click
# system:pytest
###############################################################################
# [GenAI tool change history]
# 2025-05-13T00:46:00Z : Created context handling test file by CodeAssistant
# * Implemented tests for context initialization and access
# * Added tests for context inheritance
# * Added tests for command invocation with context
###############################################################################

import pytest
from unittest.mock import MagicMock
from click.testing import CliRunner

import click
from ..common import AppContext
from ..main import cli


def test_app_context_initialization():
    """
    [Function intent]
    Test that AppContext can be initialized properly with default values.
    
    [Design principles]
    Basic initialization test - verifies that object can be created.
    Default state verification - checks initial attribute values.
    
    [Implementation details]
    Creates a new AppContext instance and verifies its attributes
    are initialized to their expected default values.
    """
    app_ctx = AppContext()
    
    # Verify default attribute values
    assert app_ctx.config_manager is None
    assert app_ctx.auth_manager is None
    assert app_ctx.api_client is None
    assert app_ctx.output_formatter is None
    assert app_ctx.progress_indicator is None
    assert app_ctx.debug is False
    assert app_ctx.verbose == 0
    assert app_ctx.quiet is False


def test_cli_context_setup():
    """
    [Function intent]
    Test that the CLI properly initializes AppContext in Click's native context.
    
    [Design principles]
    CLI integration test - verifies context setup in actual commands.
    Command execution - validates the full command execution flow.
    
    [Implementation details]
    Uses CliRunner to invoke the CLI with a mock command, then
    verifies that AppContext is properly set up in Click's context.obj.
    """
    runner = CliRunner()
    
    # Create a test command that inspects the context object
    @cli.command('test_context')
    @click.pass_context
    def test_context_command(ctx):
        assert ctx.obj is not None
        assert isinstance(ctx.obj, AppContext)
        return 0
    
    # Run the command and check exit code
    result = runner.invoke(cli, ['test_context'])
    assert result.exit_code == 0


def test_context_service_access():
    """
    [Function intent]
    Test that commands can access application services through Click's context.
    
    [Design principles]
    Service access test - validates access pattern for application services.
    Mock services - use mocks to simulate service behavior.
    
    [Implementation details]
    Creates mock services, adds them to AppContext, and verifies
    a command can access and use these services via ctx.obj.
    """
    runner = CliRunner()
    
    # Mock services for testing
    mock_formatter = MagicMock()
    mock_formatter.print.return_value = None
    
    # Create a test command that uses app services
    @cli.command('test_services')
    @click.pass_context
    def test_services_command(ctx):
        # Add mock services to app context
        ctx.obj.output_formatter = mock_formatter
        
        # Use a service through context
        ctx.obj.output_formatter.print("test message")
        
        # Verify service was called correctly
        mock_formatter.print.assert_called_once_with("test message")
        return 0
    
    # Run the command
    result = runner.invoke(cli, ['test_services'])
    assert result.exit_code == 0


def test_click_context_features():
    """
    [Function intent]
    Test access to Click's native context features like parent context and command.
    
    [Design principles]
    Feature access test - validates access to Click-specific context features.
    Command hierarchy - tests context inheritance across command groups.
    
    [Implementation details]
    Creates a command group with nested commands and verifies
    they can access Click context features like parent and command.
    """
    runner = CliRunner()
    
    # Create a command group with a subcommand to test context inheritance
    @cli.group('parent_group')
    @click.pass_context
    def parent_group(ctx):
        # Store something in the context
        ctx.obj.test_value = "parent_value"
        pass
    
    @parent_group.command('child_command')
    @click.pass_context
    def child_command(ctx):
        # Check we can access parent context data
        assert ctx.parent is not None
        assert ctx.obj.test_value == "parent_value"
        # Check command access
        assert ctx.command.name == "child_command"
        return 0
    
    # Run the command and check exit code
    result = runner.invoke(cli, ['parent_group', 'child_command'])
    assert result.exit_code == 0


def test_context_command_invocation():
    """
    [Function intent]
    Test that commands can invoke other commands using Click's context invoke method.
    
    [Design principles]
    Command invocation test - validates commands can call other commands.
    Context sharing - tests context is properly shared between commands.
    
    [Implementation details]
    Creates two commands where one invokes the other, then verifies
    the invocation works correctly and context is maintained.
    """
    runner = CliRunner()
    result_container = {'called': False}
    
    @cli.command('target')
    @click.pass_context
    def target_command(ctx):
        result_container['called'] = True
        return 0
    
    @cli.command('invoker')
    @click.pass_context
    def invoker_command(ctx):
        # Invoke another command using Click's context
        return ctx.invoke(target_command)
    
    # Run the invoker command
    result = runner.invoke(cli, ['invoker'])
    assert result.exit_code == 0
    assert result_container['called'] is True
