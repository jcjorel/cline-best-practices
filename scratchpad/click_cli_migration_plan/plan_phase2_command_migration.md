# Phase 2: Command Migration

## Overview

This phase involves converting each existing argparse-based command to a Click-based implementation. We'll migrate commands one by one, ensuring consistent behavior and functionality.

## Implementation Strategy

1. Start with simpler commands (query, status)
2. Progress to more complex commands
3. Save integration-heavy commands (like hstc_agno) for Phase 3

## Command Pattern Template

Each command will follow this standard pattern:

```python
# src/dbp_cli/cli_click/commands/command_name.py
import click
from ..main import cli
from ..common import handle_errors, with_progress

@cli.command('command-name')
# Command arguments and options
@handle_errors
@click.pass_context
def command_function(ctx, arg1, arg2, ...):
    """Command description."""
    # Get services from context
    mcp_client = ctx.obj["mcp_client"]
    output = ctx.obj["output_formatter"]
    progress = ctx.obj["progress_indicator"]
    
    # Command implementation
    
    return 0  # Success exit code
```

## Implementation Steps

### Step 1: Simple Command - Query

File: `src/dbp_cli/cli_click/commands/query.py`

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
# Implements the Click-based 'query' command for the CLI.
# This command provides natural language query capabilities using the MCP server.
###############################################################################
# [Source file design principles]
# - Mirror the behavior of the original QueryCommandHandler
# - Use Click decorators for argument parsing
# - Pass services via Click's context object
# - Provide consistent error handling and progress indication
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with the original command
# - Must handle arguments in the same way as the original command
###############################################################################
# [Dependencies]
# system:click
# codebase:src/dbp_cli/cli_click/main.py
# codebase:src/dbp_cli/cli_click/common.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:00:00Z : Initial implementation by CodeAssistant
# * Created Click-based query command
# * Implemented progress indication and error handling
###############################################################################

import click
from ..main import cli
from ..common import handle_errors, with_progress

@cli.command()
@click.argument("query", nargs=-1, required=True)
@click.option("--budget", type=float, help="Maximum cost budget for LLM usage")
@click.option("--timeout", type=int, help="Maximum execution time in milliseconds")
@handle_errors
@click.pass_context
def query(ctx, query, budget, timeout):
    """
    [Function intent]
    Process natural language queries about the codebase and documentation.
    
    [Design principles]
    Mirrors the behavior of the original QueryCommandHandler.
    Uses Click decorators for argument parsing.
    
    [Implementation details]
    Combines query words into a single string.
    Calls the MCP server's dbp_general_query tool.
    Shows progress during processing.
    
    Example:
    
        dbp query how does the configuration system work
        
        dbp query --budget 0.5 --timeout 10000 what is the authentication flow
    """
    # Get services from context
    mcp_client = ctx.obj["mcp_client"]
    output = ctx.obj["output_formatter"]
    progress = ctx.obj["progress_indicator"]
    
    # Combine query words into a single string
    query_text = " ".join(query)
    
    # Prepare query data
    query_data = {
        "query": query_text
    }
    
    # Add processing control parameters
    if budget:
        query_data["max_cost_budget"] = budget
    
    if timeout:
        query_data["max_execution_time_ms"] = timeout
    
    # Log the operation
    output.info(f"Processing query: {query_text}")
    
    # Execute the query with progress indication
    @with_progress("Processing query")
    def execute_query():
        return mcp_client.call_tool("dbp_general_query", query_data)
    
    result = execute_query()
    
    # Display results
    output.format_output(result)
    
    return 0
```

### Step 2: Config Command

File: `src/dbp_cli/cli_click/commands/config.py`

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
# Implements the Click-based 'config' command for the CLI.
# This command handles configuration management operations.
###############################################################################
# [Source file design principles]
# - Mirror the behavior of the original ConfigCommandHandler
# - Use Click decorators for argument parsing
# - Use Click subcommands for different configuration operations
# - Pass services via Click's context object
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with the original command
# - Must handle arguments in the same way as the original command
###############################################################################
# [Dependencies]
# system:click
# codebase:src/dbp_cli/cli_click/main.py
# codebase:src/dbp_cli/cli_click/common.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:00:00Z : Initial implementation by CodeAssistant
# * Created Click-based config command with subcommands
# * Implemented get, set, unset, and list operations
###############################################################################

import click
from ..main import cli
from ..common import handle_errors

@cli.group()
@click.pass_context
def config(ctx):
    """
    [Function intent]
    Manage configuration settings for the CLI.
    
    [Design principles]
    Uses Click group to organize configuration subcommands.
    
    [Implementation details]
    Provides subcommands for getting, setting, unsetting, and listing config values.
    
    Example:
    
        dbp config list
        
        dbp config set api.url https://example.com/api
    """
    pass

@config.command()
@click.argument("key")
@handle_errors
@click.pass_context
def get(ctx, key):
    """
    [Function intent]
    Get the value of a configuration key.
    
    [Design principles]
    Simple accessor for configuration values.
    
    [Implementation details]
    Retrieves a value from the configuration manager.
    Displays the value or an error if not found.
    """
    # Get services from context
    config_manager = ctx.obj["config_manager"]
    output = ctx.obj["output_formatter"]
    
    try:
        value = config_manager.get(key)
        if value is None:
            output.warning(f"Configuration key '{key}' not found")
            return 1
        else:
            output.info(f"{key}: {value}")
            return 0
    except Exception as e:
        output.error(f"Error getting configuration key '{key}': {e}")
        return 1

@config.command()
@click.argument("key")
@click.argument("value")
@handle_errors
@click.pass_context
def set(ctx, key, value):
    """
    [Function intent]
    Set the value of a configuration key.
    
    [Design principles]
    Simple modifier for configuration values.
    
    [Implementation details]
    Sets a value in the configuration manager.
    Saves the configuration and displays confirmation.
    """
    # Get services from context
    config_manager = ctx.obj["config_manager"]
    output = ctx.obj["output_formatter"]
    
    try:
        config_manager.set(key, value)
        config_manager.save()
        output.success(f"Configuration key '{key}' set to '{value}'")
        return 0
    except Exception as e:
        output.error(f"Error setting configuration key '{key}': {e}")
        return 1

@config.command()
@click.argument("key")
@handle_errors
@click.pass_context
def unset(ctx, key):
    """
    [Function intent]
    Remove a configuration key.
    
    [Design principles]
    Simple removal of configuration values.
    
    [Implementation details]
    Removes a key from the configuration manager.
    Saves the configuration and displays confirmation.
    """
    # Get services from context
    config_manager = ctx.obj["config_manager"]
    output = ctx.obj["output_formatter"]
    
    try:
        if config_manager.unset(key):
            config_manager.save()
            output.success(f"Configuration key '{key}' unset")
            return 0
        else:
            output.warning(f"Configuration key '{key}' not found")
            return 1
    except Exception as e:
        output.error(f"Error unsetting configuration key '{key}': {e}")
        return 1

@config.command()
@click.option("--section", "-s", help="Filter by section prefix")
@handle_errors
@click.pass_context
def list(ctx, section):
    """
    [Function intent]
    List all configuration keys and values.
    
    [Design principles]
    Provides visibility into the current configuration.
    
    [Implementation details]
    Retrieves all configuration key-value pairs.
    Optionally filters by section prefix.
    Displays values in a formatted table.
    """
    # Get services from context
    config_manager = ctx.obj["config_manager"]
    output = ctx.obj["output_formatter"]
    
    try:
        # Get all config items
        config_items = config_manager.get_all()
        
        # Filter by section if specified
        if section:
            config_items = {k: v for k, v in config_items.items() if k.startswith(f"{section}.")}
        
        # Display results
        if not config_items:
            if section:
                output.info(f"No configuration keys found in section '{section}'")
            else:
                output.info("No configuration keys found")
            return 0
        
        # Format output as a table
        output.info("Configuration:")
        for key, value in sorted(config_items.items()):
            output.info(f"  {key}: {value}")
            
        return 0
    except Exception as e:
        output.error(f"Error listing configuration: {e}")
        return 1
```

### Step 3: Status Command

File: `src/dbp_cli/cli_click/commands/status.py`

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
# Implements the Click-based 'status' command for the CLI.
# This command displays system status information.
###############################################################################
# [Source file design principles]
# - Mirror the behavior of the original StatusCommandHandler
# - Use Click decorators for argument parsing
# - Pass services via Click's context object
# - Provide detailed system status information
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with the original command
# - Must handle arguments in the same way as the original command
# - Should handle cases where some services may be unavailable
###############################################################################
# [Dependencies]
# system:click
# codebase:src/dbp_cli/cli_click/main.py
# codebase:src/dbp_cli/cli_click/common.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:00:00Z : Initial implementation by CodeAssistant
# * Created Click-based status command
# * Implemented system status reporting
###############################################################################

import click
import platform
import sys
from importlib import metadata
from ..main import cli
from ..common import handle_errors, with_progress

@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Display verbose status information")
@handle_errors
@click.pass_context
def status(ctx, verbose):
    """
    [Function intent]
    Display system status information.
    
    [Design principles]
    Provides visibility into the system configuration and status.
    
    [Implementation details]
    Shows version, environment, and services information.
    Optionally shows detailed information with the verbose flag.
    Handles cases where some services may be unavailable.
    
    Example:
    
        dbp status
        
        dbp status --verbose
    """
    # Get services from context
    config_manager = ctx.obj["config_manager"]
    auth_manager = ctx.obj["auth_manager"]
    mcp_client = ctx.obj["mcp_client"]
    output = ctx.obj["output_formatter"]
    
    # Basic information
    output.info("System Status:")
    
    # Version information
    try:
        version = metadata.version("dbp-cli")
    except Exception:
        version = "0.1.0.dev"
    
    output.info(f"  Version: {version}")
    output.info(f"  Python: {sys.version.split()[0]}")
    output.info(f"  Platform: {platform.platform()}")
    
    # Configuration information
    try:
        config_file = config_manager.get_config_file()
        output.info(f"  Config File: {config_file}")
    except Exception as e:
        output.warning(f"  Config: Unavailable ({e})")
    
    # Authentication information
    try:
        authenticated = auth_manager.is_authenticated()
        status_text = "Authenticated" if authenticated else "Not authenticated"
        output.info(f"  Authentication: {status_text}")
    except Exception as e:
        output.warning(f"  Authentication: Unavailable ({e})")
    
    # MCP Server information
    try:
        server_url = mcp_client.get_server_url()
        output.info(f"  MCP Server: {server_url}")
    except Exception as e:
        output.warning(f"  MCP Server: Unavailable ({e})")
    
    # Display verbose information if requested
    if verbose:
        output.info("\nDetailed Information:")
        
        # Config details
        try:
            config = config_manager.get_all()
            output.info("  Configuration:")
            for key, value in sorted(config.items()):
                if "api_key" in key.lower() or "token" in key.lower():
                    value = "********"
                output.info(f"    {key}: {value}")
        except Exception as e:
            output.warning(f"  Configuration Details: Unavailable ({e})")
            
        # Check MCP server connection
        try:
            @with_progress("Checking MCP server connection")
            def check_server():
                return mcp_client.get_status()
            
            server_status = check_server()
            output.info("  MCP Server Status:")
            output.info(f"    Status: {server_status.get('status', 'Unknown')}")
            output.info(f"    Version: {server_status.get('version', 'Unknown')}")
            
            # Server tools
            tools = server_status.get('tools', [])
            output.info(f"    Available Tools: {len(tools)}")
            if tools:
                for tool in tools:
                    output.info(f"      - {tool}")
        except Exception as e:
            output.warning(f"  MCP Server Connection: Failed ({e})")
    
    return 0
```

### Step 4: Commit Command

File: `src/dbp_cli/cli_click/commands/commit.py`

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
# Implements the Click-based 'commit' command for the CLI.
# This command handles commit message generation and git integration.
###############################################################################
# [Source file design principles]
# - Mirror the behavior of the original CommitCommandHandler
# - Use Click decorators for argument parsing
# - Pass services via Click's context object
# - Provide consistent error handling and progress indication
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with the original command
# - Must handle arguments in the same way as the original command
# - Should properly handle Git integration
###############################################################################
# [Dependencies]
# system:click
# system:subprocess
# codebase:src/dbp_cli/cli_click/main.py
# codebase:src/dbp_cli/cli_click/common.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:00:00Z : Initial implementation by CodeAssistant
# * Created Click-based commit command
# * Implemented commit message generation with options
###############################################################################

import click
import os
import subprocess
from typing import List, Dict, Any, Optional
from ..main import cli
from ..common import handle_errors, with_progress

@cli.command()
@click.option("--files", "-f", multiple=True, help="Specific files to include in commit")
@click.option("--message", "-m", help="User-provided commit message")
@click.option("--all", "-a", is_flag=True, help="Include all changed files")
@click.option("--execute", "-e", is_flag=True, help="Execute git commit with the generated message")
@click.option("--template", "-t", help="Commit message template to use")
@handle_errors
@click.pass_context
def commit(ctx, files, message, all, execute, template):
    """
    [Function intent]
    Generate commit messages and optionally execute git commit.
    
    [Design principles]
    Leverages MCP server for intelligent commit message generation.
    Integrates with git for a streamlined workflow.
    
    [Implementation details]
    Collects git diff information for staged changes.
    Calls the MCP server to generate a commit message.
    Optionally executes git commit with the generated message.
    
    Example:
    
        dbp commit
        
        dbp commit --files path/to/file.py --message "Feature implementation"
        
        dbp commit --all --execute
    """
    # Get services from context
    mcp_client = ctx.obj["mcp_client"]
    output = ctx.obj["output_formatter"]
    progress = ctx.obj["progress_indicator"]
    
    # Check for git repository
    if not _is_git_repository():
        output.error("Not a git repository")
        return 1
    
    # Determine which files to include
    if not files and not all:
        # Default to staged files
        diff_files = _get_staged_files()
        if not diff_files:
            output.error("No staged files found. Use --files to specify files or --all to include all changes.")
            return 1
    elif all:
        # Include all changed files
        diff_files = _get_all_changed_files()
        if not diff_files:
            output.error("No changed files found.")
            return 1
    else:
        # Use specified files
        diff_files = list(files)
        if not _verify_files_exist(diff_files):
            output.error("One or more specified files do not exist.")
            return 1
    
    # Get diff content for the files
    diff_content = _get_diff_content(diff_files)
    if not diff_content:
        output.error("No changes found in the specified files.")
        return 1
    
    # Prepare commit message generation request
    request_data = {
        "diff_content": diff_content,
        "files": diff_files,
    }
    
    if message:
        request_data["user_message"] = message
        
    if template:
        request_data["template"] = template
    
    # Generate commit message
    @with_progress("Generating commit message")
    def generate_message():
        return mcp_client.call_tool("generate_commit_message", request_data)
    
    result = generate_message()
    
    # Extract commit message from result
    commit_message = result.get("commit_message")
    if not commit_message:
        output.error("Failed to generate commit message.")
        return 1
    
    # Display generated commit message
    output.info("\nGenerated Commit Message:")
    output.info(commit_message)
    
    # Execute git commit if requested
    if execute:
        try:
            # Add files if needed
            if all:
                subprocess.run(["git", "add", "--all"], check=True, capture_output=True, text=True)
            elif files:
                subprocess.run(["git", "add"] + list(files), check=True, capture_output=True, text=True)
            
            # Execute commit
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True, capture_output=True, text=True
            )
            
            output.success("\nCommit executed successfully:")
            output.info(result.stdout)
        except subprocess.CalledProcessError as e:
            output.error(f"\nFailed to execute git commit: {e}")
            output.error(e.stderr)
            return 1
    
    return 0

def _is_git_repository() -> bool:
    """Check if the current directory is a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True, capture_output=True, text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def _get_staged_files() -> List[str]:
    """Get list of staged files in the git repository."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--name-only"],
            check=True, capture_output=True, text=True
        )
        return [file for file in result.stdout.splitlines() if file.strip()]
    except subprocess.CalledProcessError:
        return []

def _get_all_changed_files() -> List[str]:
    """Get list of all changed files in the git repository."""
    try:
        # Get staged files
        staged = subprocess.run(
            ["git", "diff", "--staged", "--name-only"],
            check=True, capture_output=True, text=True
        ).stdout.splitlines()
        
        # Get unstaged but tracked files
        unstaged = subprocess.run(
            ["git", "diff", "--name-only"],
            check=True, capture_output=True, text=True
        ).stdout.splitlines()
        
        # Get untracked files
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            check=True, capture_output=True, text=True
        ).stdout.splitlines()
        
        # Combine all files
        all_files = set()
        for file_list in [staged, unstaged, untracked]:
            all_files.update([file for file in file_list if file.strip()])
            
        return list(all_files)
    except subprocess.CalledProcessError:
        return []

def _verify_files_exist(files: List[str]) -> bool:
    """Verify that all specified files exist."""
    return all(os.path.exists(file) for file in files)

def _get_diff_content(files: List[str]) -> str:
    """Get git diff content for the specified files."""
    try:
        # Try to get diff for specific files
        result = subprocess.run(
            ["git", "diff", "HEAD", "--"] + files,
            check=True, capture_output=True, text=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""
```

### Step 5: Command Registration

Update the commands `__init__.py` to register all commands:

File: `src/dbp_cli/cli_click/commands/__init__.py`

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
# Registers all Click commands with the main CLI group.
# This file serves as the central point for command registration.
###############################################################################
# [Source file design principles]
# - Centralize command registration
# - Import only what's necessary
# - Support dynamic command discovery
###############################################################################
# [Source file constraints]
# - Must ensure all commands are registered with the main CLI group
# - Must avoid circular imports
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/main.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:00:00Z : Added initial command registrations by CodeAssistant
# * Registered query, config, status, and commit commands
###############################################################################

# Import all commands to register them with the main CLI group
from .query import query
from .config import config
from .status import status
from .commit import commit

# Additional commands will be imported here as they are implemented
```

### Step 6: Testing Command Migration

Create tests for each migrated command to verify they work as expected:

File: `src/dbp_cli/cli_click/tests/test_query.py`

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
# Tests the Click-based 'query' command.
# Verifies that the command processes arguments correctly and calls the API properly.
###############################################################################
# [Source file design principles]
# - Test command behavior
# - Mock external dependencies
# - Verify API calls
# - Check error handling
###############################################################################
# [Source file constraints]
# - Must not make actual API calls
# - Must verify compatibility with the original command
###############################################################################
# [Dependencies]
# system:pytest
# codebase:src/dbp_cli/cli_click/commands/query.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T14:00:00Z : Initial implementation by CodeAssistant
# * Created tests for query command
# * Added tests for various argument combinations
###############################################################################

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from ...cli_click.main import cli

@pytest.fixture
def mock_services(monkeypatch):
    """Set up mock services for testing."""
    mock_mcp_client = MagicMock()
    mock_output = MagicMock()
    mock_progress = MagicMock()
    
    # Mock call_tool to return a test response
    mock_mcp_client.call_tool.return_value = {"response": "Test response"}
    
    # Create a context object with mock services
    mock_obj = {
        "mcp_client": mock_mcp_client,
        "output_formatter": mock_output,
        "progress_indicator": mock_progress,
        "debug": False
    }
    
    # Patch the Click context to return our mock object
    monkeypatch.setattr("click.Context.ensure_object", lambda self, _: None)
    monkeypatch.setattr("click.Context.obj", mock_obj)
    
    return mock_obj

def test_query_basic(mock_services):
    """Test basic query command execution."""
    runner = CliRunner()
    
    # Run command
    result = runner.invoke(cli, ["query", "test", "question"])
    
    # Check result
    assert result.exit_code == 0
    
    # Verify API was called with correct arguments
    mock_services["mcp_client"].call_tool.assert_called_once_with(
        "dbp_general_query", 
        {"query": "test question"}
    )
    
    # Verify output was displayed
    mock_services["output_formatter"].format_output.assert_called_once_with(
        {"response": "Test response"}
    )

def test_query_with_options(mock_services):
    """Test query command with budget and timeout options."""
    runner = CliRunner()
    
    # Run command with options
    result = runner.invoke(cli, ["query", "--budget", "0.5", "--timeout", "10000", "test", "question"])
    
    # Check result
    assert result.exit_code == 0
