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
# Provides pytest fixtures and test utilities for the Click-based CLI tests.
# This file centralizes common testing functionality and fixtures that can be
# reused across multiple test modules.
###############################################################################
# [Source file design principles]
# - Centralization of test fixtures and utilities
# - Isolation of test dependencies from test cases
# - Mocking of external dependencies for unit testing
# - Consistent test environment setup and teardown
# - Cross-test reusability of common test setup
###############################################################################
# [Source file constraints]
# - Must not interfere with other pytest fixtures
# - Should avoid modifying real configuration/files
# - Test fixtures should be isolated from each other
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/main.py
# codebase:src/dbp_cli/cli_click/common.py
# system:pytest
# system:click.testing
###############################################################################
# [GenAI tool change history]
# 2025-05-13T12:18:00Z : Added AWS client factory mocking by CodeAssistant
# * Added mock_aws_client_factory fixture to provide mocked AWS credentials
# * Updated test_context to include AWS client factory support
# * Fixed AWS credential handling in tests
# 2025-05-12T15:37:16Z : Initial creation of test fixtures by CodeAssistant
# * Added fixtures for CLI runner, isolated context, and mocked services
# * Implemented test utility functions for CLI testing
###############################################################################

import os
import tempfile
import boto3
from typing import Dict, List, Optional, Any, Callable, Generator, Tuple
from unittest.mock import MagicMock, patch

import pytest
import click
from click.testing import CliRunner

from dbp.config.config_manager import ConfigurationManager
from dbp.api_providers.aws.client_factory import AWSClientFactory
from ...auth import AuthenticationManager
from ...api import MCPClientAPI
from ...output import OutputFormatter
from ...progress import ProgressIndicator
from ...exceptions import CLIError, ConfigurationError, AuthenticationError

from ..common import Context
from ..main import cli, main


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    [Function intent]
    Provide a Click CLI runner for testing CLI commands.
    
    [Implementation details]
    Creates a Click test runner with isolated file system to prevent
    test cases from interfering with each other or the actual file system.
    
    [Design principles]
    Isolated testing - each test runs in its own environment.
    Clean test environment - tests don't affect each other.
    Reusable test fixture - shareable across test modules.
    
    Returns:
        A Click test runner with isolated file system
    """
    return CliRunner(mix_stderr=False, env={"DBP_CLI_TESTING": "true"})


@pytest.fixture
def mock_config_manager() -> MagicMock:
    """
    [Function intent]
    Provide a mocked configuration manager for testing.
    
    [Implementation details]
    Creates a mock ConfigurationManager with pre-configured default responses
    for common methods used during testing.
    
    [Design principles]
    Controlled test data - predictable configuration values.
    Isolated dependencies - no actual configuration files accessed.
    
    Returns:
        Mock ConfigurationManager for testing
    """
    mock = MagicMock(spec=ConfigurationManager)
    
    # Set up default config values
    config = MagicMock()
    config.cli = MagicMock()
    config.cli.output_format = "text"
    config.cli.color = True
    config.mcp_server = MagicMock()
    config.mcp_server.url = "http://localhost:8000"
    
    # Configure get_typed_config to return our mock config
    mock.get_typed_config.return_value = config
    
    return mock


@pytest.fixture
def mock_auth_manager() -> MagicMock:
    """
    [Function intent]
    Provide a mocked authentication manager for testing.
    
    [Implementation details]
    Creates a mock AuthenticationManager with pre-configured responses
    for authentication-related methods.
    
    [Design principles]
    Controlled test data - predictable authentication state.
    Isolation from actual authentication - no real credentials used.
    
    Returns:
        Mock AuthenticationManager for testing
    """
    mock = MagicMock(spec=AuthenticationManager)
    
    # Set up authentication state
    mock.is_authenticated.return_value = True
    mock.get_api_key.return_value = "test-api-key"
    
    return mock


@pytest.fixture
def mock_api_client() -> MagicMock:
    """
    [Function intent]
    Provide a mocked API client for testing.
    
    [Implementation details]
    Creates a mock MCPClientAPI with pre-configured responses
    for common API methods used during testing.
    
    [Design principles]
    Controlled test data - predictable API responses.
    Isolation from real API - no actual API calls made.
    
    Returns:
        Mock MCPClientAPI for testing
    """
    mock = MagicMock(spec=MCPClientAPI)
    
    # Set up API client state
    mock.is_initialized.return_value = True
    mock.get_status.return_value = {"status": "ok", "version": "1.0.0"}
    
    return mock


@pytest.fixture
def mock_output_formatter() -> MagicMock:
    """
    [Function intent]
    Provide a mocked output formatter for testing.
    
    [Implementation details]
    Creates a mock OutputFormatter that captures output during tests
    instead of printing to the console.
    
    [Design principles]
    Output capture - allows verifying command output.
    Format abstraction - supports multiple output formats.
    
    Returns:
        Mock OutputFormatter for testing
    """
    mock = MagicMock(spec=OutputFormatter)
    
    # Store printed output for verification
    mock.captured_output = []
    
    # Override print to capture output
    def mock_print(content):
        mock.captured_output.append(content)
    
    mock.print.side_effect = mock_print
    
    return mock


@pytest.fixture
def mock_progress_indicator() -> MagicMock:
    """
    [Function intent]
    Provide a mocked progress indicator for testing.
    
    [Implementation details]
    Creates a mock ProgressIndicator that doesn't display actual
    progress indicators during tests.
    
    [Design principles]
    Silent operation - no actual progress indicators shown.
    State tracking - allows verifying progress was used correctly.
    
    Returns:
        Mock ProgressIndicator for testing
    """
    mock = MagicMock(spec=ProgressIndicator)
    return mock


@pytest.fixture
def mock_aws_client_factory() -> MagicMock:
    """
    [Function intent]
    Provide a mocked AWS client factory for testing.
    
    [Implementation details]
    Creates a mock AWSClientFactory with pre-configured responses
    for session and client methods to provide proper AWS credentials.
    
    [Design principles]
    AWS credential isolation - prevents tests from using real AWS credentials.
    Controlled AWS resources - predictable AWS client behavior.
    
    Returns:
        Mock AWSClientFactory for testing
    """
    mock = MagicMock(spec=AWSClientFactory)
    
    # Create a mock boto3 session
    mock_session = MagicMock(spec=boto3.Session)
    
    # Configure mock session to return mock clients
    def get_mock_client(service_name, **kwargs):
        mock_client = MagicMock()
        # Configure service-specific client behavior
        if service_name == 'bedrock':
            # Mock bedrock client methods
            mock_client.converse = MagicMock(return_value={"result": "success"})
        return mock_client
    
    mock_session.client = MagicMock(side_effect=get_mock_client)
    
    # Configure get_session to return our mock session
    mock.get_session.return_value = mock_session
    
    # Configure get_client to return mock clients directly
    mock.get_client.side_effect = get_mock_client
    
    # Configure the singleton pattern for the mock
    mock.get_instance.return_value = mock
    
    # Mock the actual singleton instance
    with patch.object(AWSClientFactory, 'get_instance', return_value=mock):
        yield mock


@pytest.fixture
def test_context(
    mock_config_manager: MagicMock,
    mock_auth_manager: MagicMock,
    mock_api_client: MagicMock,
    mock_output_formatter: MagicMock,
    mock_progress_indicator: MagicMock,
    mock_aws_client_factory: MagicMock
) -> Context:
    """
    [Function intent]
    Provide a fully initialized Context object with mocked services for testing.
    
    [Implementation details]
    Creates a Context object and initializes it with all the mocked services,
    ready for use in unit tests.
    
    [Design principles]
    Complete test context - provides all services needed for testing.
    Controlled dependencies - all services are mocked.
    Reusable fixture - can be used across multiple test cases.
    
    Args:
        mock_config_manager: Mocked ConfigurationManager
        mock_auth_manager: Mocked AuthenticationManager
        mock_api_client: Mocked MCPClientAPI
        mock_output_formatter: Mocked OutputFormatter
        mock_progress_indicator: Mocked ProgressIndicator
        mock_aws_client_factory: Mocked AWSClientFactory
        
    Returns:
        Initialized Context with mocked services
    """
    ctx = Context()
    
    # Set mocked services
    ctx.config_manager = mock_config_manager
    ctx.auth_manager = mock_auth_manager
    ctx.api_client = mock_api_client
    ctx.output_formatter = mock_output_formatter
    ctx.progress_indicator = mock_progress_indicator
    ctx.aws_client_factory = mock_aws_client_factory
    
    # Set default flags
    ctx.debug = False
    ctx.verbose = 0
    ctx.quiet = False
    
    return ctx


@pytest.fixture
def cli_invoke() -> Callable:
    """
    [Function intent]
    Provide a helper function to invoke CLI commands with a test environment.
    
    [Implementation details]
    Creates a function that sets up a CLI test environment with mocked services,
    invokes a CLI command, and returns the result for verification.
    
    [Design principles]
    Testing convenience - simplifies CLI command testing.
    Consistent test setup - standardized environment for all command tests.
    Result capture - captures and returns command output and exit code.
    
    Returns:
        Function to invoke CLI commands in a test environment
    """
    def _invoke_cli(args: List[str], isolated: bool = True) -> click.testing.Result:
        """Invoke CLI with the given arguments in a test environment"""
        runner = CliRunner(mix_stderr=False)
        
        # Use isolated file system if requested
        if isolated:
            with runner.isolated_filesystem():
                return runner.invoke(cli, args, catch_exceptions=False)
        else:
            return runner.invoke(cli, args, catch_exceptions=False)
    
    return _invoke_cli


@pytest.fixture
def temp_config_file() -> Generator[str, None, None]:
    """
    [Function intent]
    Provide a temporary configuration file for testing.
    
    [Implementation details]
    Creates a temporary file with test configuration values that can be used
    as an input for the --config option during CLI testing.
    
    [Design principles]
    Temporary resources - automatically cleaned up after test.
    Isolated configuration - doesn't interfere with real config files.
    Realistic testing - tests CLI with actual file IO.
    
    Yields:
        Path to temporary configuration file
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w+') as f:
        f.write("""{
            "cli": {
                "output_format": "text",
                "color": true
            },
            "mcp_server": {
                "url": "http://localhost:8000"
            }
        }""")
        config_path = f.name
    
    yield config_path
    
    # Clean up
    try:
        os.unlink(config_path)
    except (OSError, IOError):
        pass


def assert_command_output(
    result: click.testing.Result, 
    expected_output: Optional[str] = None,
    expected_exit_code: int = 0,
    partial_match: bool = False
) -> None:
    """
    [Function intent]
    Assert that a CLI command produced the expected output and exit code.
    
    [Implementation details]
    Checks that the command result has the expected exit code and optionally
    that the output contains or matches the expected text.
    
    [Design principles]
    Test utility - simplifies command output verification.
    Flexible matching - supports exact and partial output matching.
    Clear failure messages - helpful error messages for test failures.
    
    Args:
        result: Click command result to check
        expected_output: Expected output text (or part of it if partial_match is True)
        expected_exit_code: Expected exit code (default: 0)
        partial_match: Whether to check for partial match instead of exact match
    """
    # Check exit code
    assert result.exit_code == expected_exit_code, \
        f"Expected exit code {expected_exit_code}, got {result.exit_code}\nOutput: {result.output}\nException: {result.exception}"
    
    # Check output if provided
    if expected_output is not None:
        if partial_match:
            assert expected_output in result.output, \
                f"Expected output to contain: {expected_output}\nActual output: {result.output}"
        else:
            assert result.output.strip() == expected_output.strip(), \
                f"Expected output: {expected_output}\nActual output: {result.output}"
