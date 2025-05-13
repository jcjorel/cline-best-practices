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
# This file contains unit tests for the CLI integration of the HSTC Agno
# implementation. It tests the CLI command structure, options, and behavior.
###############################################################################
# [Source file design principles]
# - Test each CLI command in isolation
# - Verify option parsing and validation
# - Test both success and error handling paths
###############################################################################
# [Source file constraints]
# - Must use pytest fixtures from conftest.py
# - Should use Click's test utilities for CLI testing
###############################################################################
# [Dependencies]
# system:pytest
# system:click.testing
# codebase:src/dbp_cli/commands/hstc_agno/cli.py
# codebase:src/dbp_cli/commands/hstc_agno/tests/conftest.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T08:19:00Z : Initial implementation by CodeAssistant
# * Created unit tests for CLI integration
###############################################################################

import pytest
import os
from click.testing import CliRunner
from ..cli import hstc_agno, update, update_directory, status, view
from unittest.mock import patch, MagicMock


def test_hstc_agno_help():
    """
    [Function intent]
    Test the hstc_agno help command.
    
    [Design principles]
    Verifies that the command group provides useful help text.
    
    [Implementation details]
    Uses CliRunner to invoke the help command and checks the output.
    """
    runner = CliRunner()
    result = runner.invoke(hstc_agno, ["--help"])
    
    assert result.exit_code == 0
    assert "HSTC implementation with Agno framework" in result.output
    assert "update" in result.output
    assert "update-dir" in result.output
    assert "status" in result.output
    assert "view" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_update_command(mock_manager_cls, sample_python_file):
    """
    [Function intent]
    Test the update command.
    
    [Design principles]
    Verifies correct handling of the file update command with options.
    
    [Implementation details]
    Mocks the HSTCManager and tests command execution with different options.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        sample_python_file: Pytest fixture providing a sample Python file
    """
    # Create a mock manager
    mock_manager = MagicMock()
    mock_manager.process_file.return_value = {
        "file_path": sample_python_file,
        "documentation": {
            "file_type": "source_code",
            "language": "python",
            "definitions": [{"name": "test_function"}]
        },
        "validation": {"valid": True, "issues": []},
        "plan_path": "/tmp/test_plan"
    }
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test basic command
    result = runner.invoke(update, [sample_python_file])
    
    assert result.exit_code == 0
    assert "HSTC processing completed successfully" in result.output
    assert "Implementation plan generated" in result.output
    
    # Test with output option
    result = runner.invoke(update, [sample_python_file, "--output", "/tmp/output"])
    
    assert result.exit_code == 0
    mock_manager.process_file.assert_called_with(
        sample_python_file, 
        {"output": "/tmp/output", "recursive": False, "verbose": False}
    )
    
    # Test with recursive option
    result = runner.invoke(update, [sample_python_file, "--recursive"])
    
    assert result.exit_code == 0
    mock_manager.process_file.assert_called_with(
        sample_python_file, 
        {"output": None, "recursive": True, "verbose": False}
    )
    
    # Test with verbose option
    result = runner.invoke(update, [sample_python_file, "--verbose"])
    
    assert result.exit_code == 0
    mock_manager.process_file.assert_called_with(
        sample_python_file, 
        {"output": None, "recursive": False, "verbose": True}
    )
    assert "Documentation Summary" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_update_with_error(mock_manager_cls, sample_python_file):
    """
    [Function intent]
    Test the update command with an error.
    
    [Design principles]
    Verifies correct error handling and user feedback.
    
    [Implementation details]
    Simulates a processing error and checks the error output.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        sample_python_file: Pytest fixture providing a sample Python file
    """
    # Create a mock manager that returns an error
    mock_manager = MagicMock()
    mock_manager.process_file.return_value = {
        "error": "Test error",
        "file_path": sample_python_file,
        "traceback": "Traceback: Test traceback"
    }
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test basic error
    result = runner.invoke(update, [sample_python_file])
    
    assert result.exit_code == 0
    assert "Error: Test error" in result.output
    assert "Traceback" not in result.output
    
    # Test with verbose to show traceback
    result = runner.invoke(update, [sample_python_file, "--verbose"])
    
    assert result.exit_code == 0
    assert "Error: Test error" in result.output
    assert "Traceback" in result.output
    assert "Test traceback" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_update_directory_command(mock_manager_cls, temp_dir):
    """
    [Function intent]
    Test the update-dir command.
    
    [Design principles]
    Verifies correct handling of directory updates with various options.
    
    [Implementation details]
    Mocks the HSTCManager and tests command execution with different options.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        temp_dir: Pytest fixture providing a temporary directory
    """
    # Create a mock manager
    mock_manager = MagicMock()
    mock_manager.process_directory.return_value = {
        "directory": temp_dir,
        "files_processed": 2,
        "results": [
            {"file_path": "file1.py"},
            {"file_path": "file2.py"}
        ]
    }
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test basic command
    result = runner.invoke(update_directory, [temp_dir])
    
    assert result.exit_code == 0
    assert "Processed 2 files" in result.output
    assert "Successful: 2" in result.output
    
    # Test with options
    result = runner.invoke(update_directory, [
        temp_dir, 
        "--output", "/tmp/output",
        "--recursive",
        "--recursive-dir",
        "--pattern", "*.py",
        "--pattern", "*.js",
        "--verbose"
    ])
    
    assert result.exit_code == 0
    mock_manager.process_directory.assert_called_with(
        temp_dir, 
        {
            "output": "/tmp/output", 
            "recursive": True, 
            "recursive_dir": True, 
            "verbose": True,
            "file_patterns": ["*.py", "*.js"]
        }
    )


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_update_directory_with_failures(mock_manager_cls, temp_dir):
    """
    [Function intent]
    Test the update-dir command with some failed files.
    
    [Design principles]
    Verifies correct reporting of file processing failures.
    
    [Implementation details]
    Simulates some failures and checks the output.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        temp_dir: Pytest fixture providing a temporary directory
    """
    # Create a mock manager with some failures
    mock_manager = MagicMock()
    mock_manager.process_directory.return_value = {
        "directory": temp_dir,
        "files_processed": 4,
        "results": [
            {"file_path": "file1.py"},
            {"file_path": "file2.py"},
            {"file_path": "file3.py", "error": "Test error for file3"},
            {"file_path": "file4.py", "error": "Test error for file4"}
        ]
    }
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test with --verbose to see failures
    result = runner.invoke(update_directory, [temp_dir, "--verbose"])
    
    assert result.exit_code == 0
    assert "Processed 4 files" in result.output
    assert "Successful: 2" in result.output
    assert "Failed: 2" in result.output
    assert "Failed files:" in result.output
    assert "file3.py" in result.output
    assert "file4.py" in result.output
    assert "Test error for file3" in result.output
    assert "Test error for file4" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_status_command_file(mock_manager_cls, sample_python_file, mock_file_analyzer):
    """
    [Function intent]
    Test the status command for a file.
    
    [Design principles]
    Verifies correct analysis and display of file documentation status.
    
    [Implementation details]
    Mocks the file analyzer and tests different output formats.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        sample_python_file: Pytest fixture providing a sample Python file
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
    """
    # Create a mock manager with file analyzer
    mock_manager = MagicMock()
    mock_manager.file_analyzer = mock_file_analyzer
    
    mock_file_metadata = {
        "file_type": "source_code",
        "language": "python",
        "header_comment": "Test header",
        "definitions": [
            {"name": "test_function", "comments": "Test comment"},
            {"name": "undocumented_function"}
        ],
        "dependencies": [
            {"name": "os", "kind": "system"}
        ]
    }
    
    mock_file_analyzer.analyze_file.return_value = mock_file_metadata
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test basic status
    result = runner.invoke(status, [sample_python_file])
    
    assert result.exit_code == 0
    assert "File:" in result.output
    assert sample_python_file in result.output
    assert "Type: source_code" in result.output
    assert "Language: python" in result.output
    assert "Has header documentation" in result.output
    
    # Test verbose status
    result = runner.invoke(status, [sample_python_file, "--verbose"])
    
    assert result.exit_code == 0
    assert "Definitions:" in result.output
    assert "test_function" in result.output
    assert "Dependencies:" in result.output
    assert "os (system)" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_status_command_dir(mock_manager_cls, temp_dir):
    """
    [Function intent]
    Test the status command for a directory.
    
    [Design principles]
    Verifies correct handling of directory status requests.
    
    [Implementation details]
    Tests directory status message.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        temp_dir: Pytest fixture providing a temporary directory
    """
    # Create a mock manager
    mock_manager = MagicMock()
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test status on directory
    result = runner.invoke(status, [temp_dir])
    
    assert result.exit_code == 0
    assert "Directory:" in result.output
    assert temp_dir in result.output
    assert "Use 'hstc_agno update-dir'" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_view_command(mock_manager_cls, sample_python_file, mock_file_analyzer):
    """
    [Function intent]
    Test the view command with different output formats.
    
    [Design principles]
    Verifies correct display of documentation in various formats.
    
    [Implementation details]
    Tests text, JSON, and markdown output formats.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
        sample_python_file: Pytest fixture providing a sample Python file
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
    """
    # Create mock manager and mock responses
    mock_manager = MagicMock()
    mock_manager.file_analyzer = mock_file_analyzer
    
    mock_documentation = {
        "language": "python",
        "file_header": {
            "intent": "Test intent",
            "design_principles": "Test principles",
            "constraints": "Test constraints",
            "dependencies": [
                {"kind": "system", "dependency": "os"}
            ]
        },
        "definitions": [
            {
                "name": "test_function",
                "type": "function",
                "updated_comment": "Test function comment"
            }
        ]
    }
    
    mock_file_analyzer.analyze_file.return_value = {
        "file_type": "source_code",
        "language": "python"
    }
    
    mock_manager.generate_documentation.return_value = mock_documentation
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test text format (default)
    result = runner.invoke(view, [sample_python_file])
    
    assert result.exit_code == 0
    assert "HSTC Documentation for" in result.output
    assert "File Header:" in result.output
    assert "Intent: Test intent" in result.output
    assert "Design Principles: Test principles" in result.output
    assert "Definitions:" in result.output
    assert "test_function" in result.output
    
    # Test JSON format
    result = runner.invoke(view, [sample_python_file, "--output-format", "json"])
    
    assert result.exit_code == 0
    assert "\"language\": \"python\"" in result.output
    assert "\"intent\": \"Test intent\"" in result.output
    assert "\"name\": \"test_function\"" in result.output
    
    # Test markdown format
    result = runner.invoke(view, [sample_python_file, "--output-format", "markdown"])
    
    assert result.exit_code == 0
    assert "# HSTC Documentation for" in result.output
    assert "## File Header" in result.output
    assert "### Intent" in result.output
    assert "### Design Principles" in result.output
    assert "### Definitions" in result.output or "## Definitions" in result.output


@patch("src.dbp_cli.commands.hstc_agno.cli.HSTCManager")
def test_cache_commands(mock_manager_cls):
    """
    [Function intent]
    Test the cache management commands.
    
    [Design principles]
    Verifies correct handling of cache operations.
    
    [Implementation details]
    Tests clear-cache, save-cache, and load-cache commands.
    
    Args:
        mock_manager_cls: Mocked HSTCManager class
    """
    # Create a mock manager
    mock_manager = MagicMock()
    mock_manager_cls.return_value = mock_manager
    
    runner = CliRunner()
    
    # Test clear-cache
    result = runner.invoke(hstc_agno, ["clear-cache"])
    
    assert result.exit_code == 0
    assert "Cache cleared successfully" in result.output
    mock_manager.clear_cache.assert_called_once()
    
    # Test save-cache
    result = runner.invoke(hstc_agno, ["save-cache", "test_cache.json"])
    
    assert result.exit_code == 0
    assert "Cache saved to" in result.output
    mock_manager.save_cache.assert_called_once_with("test_cache.json")
    
    # Test load-cache (success)
    mock_manager.load_cache.return_value = True
    result = runner.invoke(hstc_agno, ["load-cache", "test_cache.json"])
    
    assert result.exit_code == 0
    assert "Cache loaded from" in result.output
    mock_manager.load_cache.assert_called_with("test_cache.json")
    
    # Test load-cache (failure)
    mock_manager.load_cache.return_value = False
    result = runner.invoke(hstc_agno, ["load-cache", "nonexistent_cache.json"])
    
    assert result.exit_code == 0
    assert "Error: Failed to load cache" in result.output
