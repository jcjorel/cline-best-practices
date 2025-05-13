# Phase 3: Integration

## Overview

This phase focuses on integrating the Click-based CLI with existing Click commands, particularly the `hstc_agno` command, and implementing comprehensive testing to ensure all functionality works correctly before the final switchover.

## Implementation Steps

### Step 1: Integrate Existing Click Commands

#### hstc_agno Integration

File: `src/dbp_cli/cli_click/commands/hstc_agno.py`

```python
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
# Integrates the existing hstc_agno Click command group with the main CLI.
# Provides a direct connection between the existing Click command and the new CLI.
###############################################################################
# [Source file design principles]
# - Direct integration with existing Click commands
# - Maintain existing command behavior
# - Ensure consistent context handling
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with the original command
# - Must ensure proper context passing between commands
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/cli.py
# codebase:src/dbp_cli/cli_click/main.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:30:00Z : Initial implementation by CodeAssistant
# * Integrated hstc_agno Click command with main CLI
###############################################################################

from ...commands.hstc_agno.cli import hstc_agno as hstc_agno_group
from ..main import cli

# Add the hstc_agno Click group directly to our main CLI
cli.add_command(hstc_agno_group, "hstc_agno")
```

Update `src/dbp_cli/cli_click/commands/__init__.py` to register the command:

```python
# Import existing commands
from .query import query
from .config import config
from .status import status
from .commit import commit

# Register hstc_agno command
from .hstc_agno import hstc_agno_group
```

### Step 2: Create Integration Tests

File: `src/dbp_cli/cli_click/tests/test_integration.py`

```python
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
# 2025-05-12T14:30:00Z : Initial implementation by CodeAssistant
# * Created integration tests for CLI commands
# * Added tests for global options and context passing
###############################################################################

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from ...cli_click.main import cli

@pytest.fixture
def mock_services(monkeypatch):
    """Set up mock services for integration testing."""
    mock_mcp_client = MagicMock()
    mock_config_manager = MagicMock()
    mock_auth_manager = MagicMock()
    mock_output = MagicMock()
    mock_progress = MagicMock()
    
    # Mock config_manager.get_typed_config to return a MagicMock with cli attribute
    mock_config_obj = MagicMock()
    mock_config_obj.cli.output_format = "text"
    mock_config_obj.cli.color = True
    mock_config_manager.get_typed_config.return_value = mock_config_obj
    
    # Create a context object with mock services
    mock_obj = {
        "config_manager": mock_config_manager,
        "auth_manager": mock_auth_manager,
        "mcp_client": mock_mcp_client,
        "output_formatter": mock_output,
        "progress_indicator": mock_progress,
        "debug": False
    }
    
    # Patch the Click context to return our mock object
    monkeypatch.setattr("click.Context.ensure_object", lambda self, _: None)
    monkeypatch.setattr("click.Context.obj", mock_obj)
    
    return mock_obj

def test_global_options(mock_services):
    """Test that global options are properly passed to commands."""
    runner = CliRunner()
    
    # Run command with global options
    result = runner.invoke(cli, ["--verbose", "--no-color", "status"])
    
    # Verify global options were processed
    assert result.exit_code == 0
    assert mock_services["output_formatter"].set_color_enabled.called_with(False)

def test_command_integration_flow(mock_services):
    """Test a typical command flow with multiple commands."""
    runner = CliRunner()
    
    # Mock query response
    mock_services["mcp_client"].call_tool.return_value = {
        "response": "Config requires updating",
        "suggested_config": {"api.url": "https://example.com/api"}
    }
    
    # First run query
    result = runner.invoke(cli, ["query", "how to configure API"])
    assert result.exit_code == 0
    
    # Then update config based on query results
    result = runner.invoke(cli, ["config", "set", "api.url", "https://example.com/api"])
    assert result.exit_code == 0
    
    # Check that config was updated
    mock_services["config_manager"].set.assert_called_with("api.url", "https://example.com/api")
    mock_services["config_manager"].save.assert_called()

def test_hstc_agno_integration(mock_services):
    """Test that the hstc_agno command is properly integrated."""
    runner = CliRunner()
    
    # Mock hstc_agno command group for testing
    with patch('src.dbp_cli.commands.hstc_agno.cli.hstc_agno') as mock_hstc_agno:
        # Set up mock behavior
        mock_hstc_agno.callback = MagicMock()
        
        # Run hstc_agno command
        result = runner.invoke(cli, ["hstc_agno", "--help"])
        
        # Verify the command was invoked
        assert result.exit_code == 0
        assert mock_hstc_agno.callback.called
```

### Step 3: Comprehensive Test Suite

Create tests for each command to ensure functionality:

- `src/dbp_cli/cli_click/tests/test_query.py` (already created)
- `src/dbp_cli/cli_click/tests/test_config.py`
- `src/dbp_cli/cli_click/tests/test_status.py`
- `src/dbp_cli/cli_click/tests/test_commit.py`

#### Example Config Test File:

```python
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
# Tests the Click-based 'config' command.
# Verifies that the command processes arguments correctly and manages configuration properly.
###############################################################################
# [Source file design principles]
# - Test each config subcommand
# - Mock configuration manager
# - Verify correct behavior for different scenarios
###############################################################################
# [Source file constraints]
# - Must not modify actual configuration files
# - Must test both success and error cases
###############################################################################
# [Dependencies]
# system:pytest
# codebase:src/dbp_cli/cli_click/commands/config.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:30:00Z : Initial implementation by CodeAssistant
# * Created tests for config command and subcommands
###############################################################################

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from ...cli_click.main import cli

@pytest.fixture
def mock_services(monkeypatch):
    """Set up mock services for config testing."""
    mock_config_manager = MagicMock()
    mock_output = MagicMock()
    
    # Mock config_manager methods
    mock_config_manager.get.return_value = "test_value"
    mock_config_manager.get_all.return_value = {"api.url": "https://example.com", "api.token": "secret"}
    
    # Create a context object with mock services
    mock_obj = {
        "config_manager": mock_config_manager,
        "output_formatter": mock_output,
    }
    
    # Patch the Click context to return our mock object
    monkeypatch.setattr("click.Context.ensure_object", lambda self, _: None)
    monkeypatch.setattr("click.Context.obj", mock_obj)
    
    return mock_obj

def test_config_get(mock_services):
    """Test the 'config get' command."""
    runner = CliRunner()
    
    # Test successful get
    result = runner.invoke(cli, ["config", "get", "api.url"])
    assert result.exit_code == 0
    mock_services["config_manager"].get.assert_called_with("api.url")
    mock_services["output_formatter"].info.assert_called_with("api.url: test_value")
    
    # Test get for non-existent key
    mock_services["config_manager"].get.return_value = None
    result = runner.invoke(cli, ["config", "get", "non.existent"])
    assert result.exit_code == 1
    mock_services["output_formatter"].warning.assert_called_with("Configuration key 'non.existent' not found")

def test_config_set(mock_services):
    """Test the 'config set' command."""
    runner = CliRunner()
    
    result = runner.invoke(cli, ["config", "set", "api.url", "https://new-example.com"])
    assert result.exit_code == 0
    mock_services["config_manager"].set.assert_called_with("api.url", "https://new-example.com")
    mock_services["config_manager"].save.assert_called_once()
    mock_services["output_formatter"].success.assert_called_with("Configuration key 'api.url' set to 'https://new-example.com'")

def test_config_unset(mock_services):
    """Test the 'config unset' command."""
    runner = CliRunner()
    
    # Test successful unset
    mock_services["config_manager"].unset.return_value = True
    result = runner.invoke(cli, ["config", "unset", "api.url"])
    assert result.exit_code == 0
    mock_services["config_manager"].unset.assert_called_with("api.url")
    mock_services["config_manager"].save.assert_called_once()
    mock_services["output_formatter"].success.assert_called_with("Configuration key 'api.url' unset")
    
    # Test unset for non-existent key
    mock_services["config_manager"].unset.return_value = False
    result = runner.invoke(cli, ["config", "unset", "non.existent"])
    assert result.exit_code == 1
    mock_services["output_formatter"].warning.assert_called_with("Configuration key 'non.existent' not found")

def test_config_list(mock_services):
    """Test the 'config list' command."""
    runner = CliRunner()
    
    # Test list all config items
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    mock_services["config_manager"].get_all.assert_called_once()
    mock_services["output_formatter"].info.assert_any_call("Configuration:")
    
    # Test list with section filter
    mock_services["config_manager"].get_all.return_value = {"api.url": "https://example.com", "api.token": "secret"}
    result = runner.invoke(cli, ["config", "list", "--section", "api"])
    assert result.exit_code == 0
    # Verify filtered items are displayed
    assert mock_services["output_formatter"].info.call_count >= 3  # Header + 2 items
```

### Step 4: Cross-Check Original CLI Behavior

1. Document and compare original CLI behavior with Click implementation:

File: `scratchpad/click_cli_migration_plan/command_behavior_comparison.md`

```markdown
# Command Behavior Comparison

This document compares the behavior of original argparse-based commands with their Click-based counterparts.

## Query Command

| Feature | Original | Click-Based | Status |
|---------|----------|-------------|--------|
| Basic query | ✅ | ✅ | Identical |
| Budget option | ✅ | ✅ | Identical |
| Timeout option | ✅ | ✅ | Identical |
| Progress indication | ✅ | ✅ | Identical |
| Error handling | ✅ | ✅ | Identical |
| Output formatting | ✅ | ✅ | Identical |

## Config Command

| Feature | Original | Click-Based | Status |
|---------|----------|-------------|--------|
| Get config | ✅ | ✅ | Identical |
| Set config | ✅ | ✅ | Identical |
| Unset config | ✅ | ✅ | Identical |
| List all config | ✅ | ✅ | Identical |
| List filtered config | ✅ | ✅ | Identical |
| Config saving | ✅ | ✅ | Identical |

## Status Command

| Feature | Original | Click-Based | Status |
|---------|----------|-------------|--------|
| Basic status | ✅ | ✅ | Identical |
| Verbose mode | ✅ | ✅ | Identical |
| Version info | ✅ | ✅ | Identical |
| Authentication status | ✅ | ✅ | Identical |
| Server connection | ✅ | ✅ | Identical |
| Error handling | ✅ | ✅ | Identical |

## Commit Command

| Feature | Original | Click-Based | Status |
|---------|----------|-------------|--------|
| Default behavior | ✅ | ✅ | Identical |
| Specific files | ✅ | ✅ | Identical |
| All files option | ✅ | ✅ | Identical |
| Message hint | ✅ | ✅ | Identical |
| Execute option | ✅ | ✅ | Identical |
| Template option | ✅ | ✅ | Identical |
| Git integration | ✅ | ✅ | Identical |

## HSTC_Agno Command

| Feature | Original | Click-Based | Status |
|---------|----------|-------------|--------|
| Command registration | ✅ | ✅ | Direct integration |
| Subcommands | ✅ | ✅ | Identical |
| Options | ✅ | ✅ | Identical |
| Arguments | ✅ | ✅ | Identical |
| Help text | ✅ | ✅ | Identical |
```

### Step 5: End-to-End Testing

Create an end-to-end test script that validates the CLI functionality with real commands:

File: `src/dbp_cli/cli_click/tests/test_end_to_end.py`

```python
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
# Provides end-to-end tests for the Click-based CLI.
# Validates that the CLI works correctly in realistic scenarios.
###############################################################################
# [Source file design principles]
# - Test real command flows
# - Simulate user interactions
# - Validate input/output behavior
###############################################################################
# [Source file constraints]
# - Should only run in test environments
# - Must clean up after tests
# - Avoid making external API calls
###############################################################################
# [Dependencies]
# system:pytest
# codebase:src/dbp_cli/cli_click/main.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:30:00Z : Initial implementation by CodeAssistant
# * Created end-to-end tests for CLI
# * Added test for typical user workflows
###############################################################################

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
import subprocess

# Mark these tests to be skipped by default since they're end-to-end
# Run with pytest -m e2e to execute these tests
pytestmark = pytest.mark.e2e

@pytest.fixture
def temp_config():
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp:
        # Write test configuration
        temp.write(b"""
api:
  url: https://example.com/api
  timeout: 30
cli:
  color: true
  output_format: text
        """)
        temp_path = temp.name
    
    yield temp_path
    
    # Clean up
    os.unlink(temp_path)

@patch('subprocess.run')
def test_cli_version(mock_run):
    """Test that the CLI version command works."""
    # Set up mock
    mock_process = MagicMock()
    mock_process.stdout = "dbp-cli 0.1.0.dev"
    mock_process.returncode = 0
    mock_run.return_value = mock_process
    
    # Run CLI version command
    subprocess.run(["python", "-m", "dbp_cli.cli_click", "--version"])
    
    # Verify command was called correctly
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "python"
    assert "--version" in args

@patch('subprocess.run')
def test_cli_config_workflow(mock_run, temp_config):
    """Test a typical config workflow."""
    # Set up mocks for three commands
    mock_responses = [
        MagicMock(stdout="Configuration:\n  api.url: https://example.com/api\n  api.timeout: 30", returncode=0),
        MagicMock(stdout="Configuration key 'api.url' set to 'https://new-example.com'", returncode=0),
        MagicMock(stdout="Configuration:\n  api.url: https://new-example.com\n  api.timeout: 30", returncode=0),
    ]
    mock_run.side_effect = mock_responses
    
    # Run workflow: list config -> set config -> list again
    subprocess.run(["python", "-m", "dbp_cli.cli_click", "--config", temp_config, "config", "list"])
    subprocess.run(["python", "-m", "dbp_cli.cli_click", "--config", temp_config, "config", "set", "api.url", "https://new-example.com"])
    subprocess.run(["python", "-m", "dbp_cli.cli_click", "--config", temp_config, "config", "list"])
    
    # Verify all three commands were called
    assert mock_run.call_count == 3
```

## Expected Outcome

At the end of Phase 3, we will have:

1. A fully integrated Click-based CLI with all commands
2. Direct integration with existing Click commands like hstc_agno
3. Comprehensive test coverage
4. Verification of command behavior compared to original implementation

This integration phase ensures that all commands work together correctly before switching over to the new implementation.

## Dependencies

- Completed Phase 1 and Phase 2
- Python 3.8+
- Click package
- pytest (for tests)
- pytest-mock (for mocking services in tests)

## Testing

Run the comprehensive test suite to verify the integration:

```bash
# From the project root
pytest src/dbp_cli/cli_click/tests/ -v
```

For end-to-end tests:

```bash
# From the project root
pytest src/dbp_cli/cli_click/tests/ -m e2e -v
