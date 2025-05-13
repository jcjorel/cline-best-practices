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
# Contains tests for the server command group in the Click-based CLI implementation.
# Verifies the functionality of server management commands (start, stop, restart, status)
# while mocking the actual server processes and API calls to ensure tests are
# self-contained and predictable.
###############################################################################
# [Source file design principles]
# - Uses pytest fixtures to create a clean testing environment for each test
# - Employs CliRunner for testing Click commands with consistent inputs/outputs
# - Mocks system calls (subprocess, os.kill) and API requests to avoid actual server operations
# - Verifies each subcommand's behavior and options are correctly implemented
# - Ensures proper error handling for edge cases
###############################################################################
# [Source file constraints]
# - Mocks all calls to subprocess, socket, os.kill to avoid actual server operations
# - Avoids any actual network calls during tests
# - Relies on pytest fixtures to ensure test isolation
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/commands/server.py
# codebase:src/dbp_cli/cli_click/tests/conftest.py
# system:pytest
# system:click.testing
###############################################################################
# [GenAI tool change history]
# 2025-05-12T19:51:22Z : Created test file for server command by CodeAssistant
# * Implemented tests for all server subcommands
# * Created mocks for process management and API calls
# * Added tests for error handling and edge cases
###############################################################################

import os
import signal
import socket
import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, mock_open

import pytest
import requests
from click.testing import CliRunner

from ...cli_click.main import cli
from ...cli_click.commands.server import (
    server_group,
    _get_server_pid,
    _is_process_running,
    _is_port_available,
)


@pytest.fixture
def mock_config():
    """Fixture that sets up a mock configuration for server testing."""
    config = MagicMock()
    config.mcp_server.pid_file = "/tmp/mcp_server.pid"
    config.mcp_server.logs_dir = "/tmp/mcp_logs"
    config.mcp_server.host = "localhost"
    config.mcp_server.port = 6231
    config.initialization.timeout_seconds = 5
    return config


@pytest.fixture
def mock_context(mock_config):
    """Fixture that creates a mock context with necessary methods."""
    ctx = MagicMock()
    ctx.config_manager.get_typed_config.return_value = mock_config
    ctx.progress_indicator.return_value.__enter__.return_value = None
    ctx.progress_indicator.return_value.__exit__.return_value = None
    return ctx


class TestServerCommand:
    """Test suite for the server command and its subcommands."""

    def test_server_group_command_structure(self):
        """Test that the server command group has the expected structure."""
        runner = CliRunner()
        result = runner.invoke(cli, ["server", "--help"])
        assert result.exit_code == 0
        # Verify all subcommands are listed
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("subprocess.Popen")
    @patch("os.kill")
    @patch("requests.get")
    def test_server_start_command(
        self,
        mock_requests_get,
        mock_kill,
        mock_popen,
        mock_file,
        mock_mkdir,
        mock_path_exists,
        mock_context,
    ):
        """Test server start command with mocked dependencies."""
        # Setup mocks
        mock_path_exists.return_value = False  # PID file doesn't exist
        mock_popen.return_value.pid = 12345
        mock_popen.return_value.poll.return_value = None  # Process is running

        # Mock socket to simulate port availability
        with patch("socket.socket") as mock_socket:
            mock_socket.return_value.__enter__.return_value.bind.return_value = None
            
            # Mock requests.get to simulate server becoming ready
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "version": "1.0.0",
                "initialization": {
                    "current_step": "complete",
                    "message": "Server ready",
                }
            }
            mock_requests_get.return_value = mock_response

            # Run test with context object
            with patch("src.dbp_cli.cli_click.commands.server._get_server_pid", return_value=None):
                with patch("src.dbp_cli.cli_click.commands.server._is_port_available", return_value=True):
                    runner = CliRunner()
                    result = runner.invoke(
                        cli, ["server", "start", "--host", "localhost", "--port", "8080"]
                    )
                    
                    # Verify output contains expected messages
                    assert result.exit_code == 0
                    assert "Starting MCP server" in result.output
                    # Verify process was started
                    mock_popen.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.kill")
    def test_server_stop_command(
        self, mock_kill, mock_file, mock_path_exists, mock_context
    ):
        """Test server stop command with mocked dependencies."""
        # Setup mock to return PID
        mock_path_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "12345"

        # Mock checking if process is running
        with patch("src.dbp_cli.cli_click.commands.server._get_server_pid", return_value=12345):
            with patch("src.dbp_cli.cli_click.commands.server._is_process_running", return_value=True):
                with patch("pathlib.Path.unlink") as mock_unlink:
                    runner = CliRunner()
                    result = runner.invoke(cli, ["server", "stop"])

                    # Verify output contains expected messages
                    assert result.exit_code == 0
                    assert "Stopping MCP server" in result.output
                    # Verify kill was called
                    mock_kill.assert_called_once_with(12345, signal.SIGTERM)
                    # Verify PID file was removed
                    mock_unlink.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.kill")
    @patch("subprocess.Popen")
    @patch("requests.get")
    def test_server_restart_command(
        self,
        mock_requests_get,
        mock_popen,
        mock_kill,
        mock_file,
        mock_path_exists,
        mock_context,
    ):
        """Test server restart command with mocked dependencies."""
        # Setup mocks
        mock_path_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "12345"
        mock_popen.return_value.pid = 12346
        mock_popen.return_value.poll.return_value = None

        # Mock response for health check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
        }
        mock_requests_get.return_value = mock_response

        # Run test
        with patch("src.dbp_cli.cli_click.commands.server._get_server_pid", return_value=12345):
            with patch("src.dbp_cli.cli_click.commands.server._is_process_running", return_value=True):
                with patch("src.dbp_cli.cli_click.commands.server._is_port_available", return_value=True):
                    with patch("pathlib.Path.unlink"):
                        with patch("pathlib.Path.mkdir"):
                            runner = CliRunner()
                            result = runner.invoke(
                                cli, ["server", "restart", "--host", "localhost", "--port", "8080"]
                            )

                            # Verify output
                            assert result.exit_code == 0
                            assert "Restarting MCP server" in result.output
                            # Verify kill was called to stop the existing process
                            mock_kill.assert_called_with(12345, signal.SIGTERM)
                            # Verify new process was started
                            assert mock_popen.called

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("requests.get")
    def test_server_status_command_running(
        self, mock_requests_get, mock_file, mock_path_exists, mock_context
    ):
        """Test server status command when server is running and responsive."""
        # Setup mocks
        mock_path_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "12345"

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "initialization": {
                "current_step": "complete",
                "message": "Server ready",
            }
        }
        mock_requests_get.return_value = mock_response

        # Run test
        with patch("src.dbp_cli.cli_click.commands.server._get_server_pid", return_value=12345):
            with patch("src.dbp_cli.cli_click.commands.server._is_process_running", return_value=True):
                runner = CliRunner()
                result = runner.invoke(cli, ["server", "status"])

                # Verify output
                assert result.exit_code == 0
                assert "Server is responsive" in result.output
                assert "Version: 1.0.0" in result.output

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("requests.get")
    def test_server_status_command_not_running(
        self, mock_requests_get, mock_file, mock_path_exists, mock_context
    ):
        """Test server status command when server is not running."""
        # Setup mocks
        mock_path_exists.return_value = False
        
        # Run test
        with patch("src.dbp_cli.cli_click.commands.server._get_server_pid", return_value=None):
            runner = CliRunner()
            result = runner.invoke(cli, ["server", "status"])

            # Verify output
            assert result.exit_code == 1  # Non-zero exit code
            assert "Process: Not running" in result.output
            assert "To start the server, run:" in result.output

    @patch("pathlib.Path.exists")
    def test_get_server_pid(self, mock_path_exists, mock_context):
        """Test _get_server_pid function."""
        # When PID file exists
        mock_path_exists.return_value = True
        with patch("builtins.open", mock_open(read_data="12345")):
            pid = _get_server_pid(mock_context)
            assert pid == 12345

        # When PID file doesn't exist
        mock_path_exists.return_value = False
        pid = _get_server_pid(mock_context)
        assert pid is None

    @patch("os.kill")
    def test_is_process_running(self, mock_kill):
        """Test _is_process_running function."""
        # Process is running
        mock_kill.side_effect = None
        assert _is_process_running(12345) is True

        # Process is not running
        mock_kill.side_effect = ProcessLookupError()
        assert _is_process_running(12345) is False

        # Process exists but permission denied
        mock_kill.side_effect = PermissionError()
        assert _is_process_running(12345) is True

    @patch("socket.socket")
    def test_is_port_available(self, mock_socket):
        """Test _is_port_available function."""
        # Port is available
        mock_socket.return_value.__enter__.return_value.bind.side_effect = None
        assert _is_port_available("localhost", 8080) is True

        # Port is in use
        mock_socket.return_value.__enter__.return_value.bind.side_effect = socket.error()
        assert _is_port_available("localhost", 8080) is False
