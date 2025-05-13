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
# Tests the command suggestion functionality for the Click-based CLI. Validates that
# typing errors in command names result in helpful suggestions to the user instead
# of just generic error messages.
###############################################################################
# [Source file design principles]
# - Tests the get_command_suggestions function directly
# - Uses mock commands to ensure predictable test behavior
# - Validates command suggestion quality and relevance
# - Tests integration with error handling
# - Ensures user experience is improved for common typos
###############################################################################
# [Source file constraints]
# - Must not modify the CLI commands during testing
# - Must restore any temporary state changes
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/main.py
# system:pytest
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T01:43:00Z : Initial creation of command suggestion tests by CodeAssistant
# * Created test cases for get_command_suggestions function
# * Added test for integration with CLI error handling
# * Implemented mock runner for command suggestion testing
###############################################################################

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.dbp_cli.cli_click.main import cli, get_command_suggestions


class TestCommandSuggestions:
    """Test suite for the command suggestion functionality."""
    
    def test_get_command_suggestions(self):
        """
        [Function intent]
        Test that the get_command_suggestions function returns appropriate suggestions
        for similar commands.
        
        [Implementation details]
        Verifies that the function correctly identifies similar commands based on string
        similarity and returns them in order of relevance. Tests with various typos and
        misspellings to ensure robust behavior.
        
        [Design principles]
        Direct function testing - tests core functionality directly.
        Coverage of edge cases - tests various misspellings and similarities.
        """
        # Mock the cli.commands dictionary with some test commands
        test_commands = {
            'config': MagicMock(),
            'commit': MagicMock(),
            'query': MagicMock(),
            'server': MagicMock(),
            'version': MagicMock(),
        }
        
        # Test similar command suggestions
        with patch.object(cli, 'commands', test_commands):
            # Test a slightly misspelled command (1 character off)
            suggestions = get_command_suggestions('comfig')
            assert 'config' in suggestions
            assert suggestions[0] == 'config'  # Should be the first suggestion
            
            # Test a more significantly misspelled command
            suggestions = get_command_suggestions('querry')
            assert 'query' in suggestions
            
            # Test a completely different command (should not suggest anything relevant)
            suggestions = get_command_suggestions('xyz123')
            assert len(suggestions) == 0
            
            # Test a command with just one character different
            suggestions = get_command_suggestions('servir')
            assert 'server' in suggestions
            
    def test_subcommand_suggestions(self):
        """
        [Function intent]
        Test that suggestions work properly for subcommands.
        
        [Implementation details]
        Tests the suggestion mechanism for subcommands, ensuring that typos in
        subcommands are correctly detected and appropriate suggestions are made.
        
        [Design principles]
        Nested command testing - ensures hierarchical command handling works.
        """
        # Mock a cli structure with nested commands
        config_commands = {'list': MagicMock(), 'get': MagicMock(), 'set': MagicMock()}
        server_commands = {'start': MagicMock(), 'stop': MagicMock(), 'status': MagicMock()}
        
        config_mock = MagicMock()
        server_mock = MagicMock()
        
        # Add commands property to mock objects
        config_mock.commands = config_commands
        server_mock.commands = server_commands
        
        test_commands = {
            'config': config_mock,
            'server': server_mock,
        }
        
        with patch.object(cli, 'commands', test_commands):
            # Test subcommand suggestions
            suggestions = get_command_suggestions('config lst')
            assert 'config list' in suggestions
            
            suggestions = get_command_suggestions('server stat')
            assert 'server status' in suggestions or 'server start' in suggestions
    
    def test_cli_error_with_suggestion(self):
        """
        [Function intent]
        Test that CLI errors for unknown commands include appropriate suggestions.
        
        [Implementation details]
        Runs the CLI with a misspelled command and verifies that the error message
        includes a suggestion for the correct command.
        
        [Design principles]
        Integration testing - tests the suggestion mechanism within the CLI error handling.
        User experience focus - verifies the improved feedback mechanism.
        """
        runner = CliRunner()
        
        # Create a mock for the get_command_suggestions function
        with patch('src.dbp_cli.cli_click.main.get_command_suggestions') as mock_get_suggestions:
            # Set up the mock to return a suggestion
            mock_get_suggestions.return_value = ['config']
            
            # Run the CLI with a misspelled command
            result = runner.invoke(cli, ['onfig'])
            
            # Verify the error message includes the suggestion
            assert mock_get_suggestions.called
            assert mock_get_suggestions.call_args[0][0] == 'onfig'
            assert "Did you mean" in result.output
