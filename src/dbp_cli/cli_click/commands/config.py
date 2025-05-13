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
# Implements the Click-based 'config' command group for the CLI, which allows
# users to manage CLI configuration settings. This includes viewing, setting, and
# resetting configuration values for the DBP CLI application.
###############################################################################
# [Source file design principles]
# - Uses Click's command group structure for organizing subcommands
# - Provides operations for getting, setting, listing, and resetting configuration
# - Supports dot notation for accessing nested configuration values
# - Persists configuration changes to disk when needed
# - Maintains compatibility with original config command functionality
# - Validates configuration keys and values
###############################################################################
# [Source file constraints]
# - Depends on the ConfigurationManager from config.py
# - Configuration keys are case-sensitive
# - File writing depends on filesystem permissions
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# codebase:src/dbp_cli/config.py
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T13:31:00Z : Updated to use ClickContextOutputAdapter for output formatting by CodeAssistant
# * Replaced direct ctx.obj.output_formatter access with get_output_adapter utility
# * Modified _print_nested_dict to accept and use output adapter parameter
# * Improved error handling with consistent adapter usage
# 2025-05-13T01:36:00Z : Fixed import statements for proper module resolution by CodeAssistant
# * Changed relative imports (from ...exceptions) to absolute imports (from dbp_cli.exceptions)
# * Fixed ImportError: attempted relative import beyond top-level package
# 2025-05-13T00:58:00Z : Updated context handling by CodeAssistant
# * Changed from custom Context class to Click's native context
# * Updated to access application services via ctx.obj
# * Fixed duplicate click import
###############################################################################

import json
import logging
from typing import Any, Dict, Optional

import click

from ..common import catch_errors, get_output_adapter
from dbp_cli.exceptions import CommandError, ConfigurationError

logger = logging.getLogger(__name__)


@click.group(
    name="config",
    help="Manage CLI configuration settings",
    short_help="Manage CLI configuration",
)
@click.pass_context
def config_group(ctx: click.Context) -> None:
    """
    [Function intent]
    Serve as the main entry point for the config command group, which provides
    subcommands for managing CLI configuration settings.
    
    [Implementation details]
    Creates a command group that contains subcommands for getting, setting, listing,
    and resetting configuration values. The context object provides access to the
    configuration manager used by all subcommands.
    
    [Design principles]
    Command grouping - organizes related commands under a common namespace.
    Shared context - provides access to the configuration manager for all subcommands.
    """
    pass


@config_group.command("get")
@click.argument("key", required=True)
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text)",
)
@catch_errors
@click.pass_context
def config_get(ctx: click.Context, key: str, format: str) -> int:
    """
    [Function intent]
    Get a configuration value by key.
    
    [Implementation details]
    Retrieves a configuration value using the provided key, which may use dot
    notation for nested values. Displays the value in the specified format.
    
    [Design principles]
    Flexible output - supports different output formats.
    Nested access - supports dot notation for accessing nested configuration values.
    User-friendly output - formats output based on value type and user preference.
    
    Args:
        ctx: CLI context with access to services
        key: Configuration key (e.g., 'mcp_server.url')
        format: Output format ('text' or 'json')
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Get adapter for output formatting
        output = get_output_adapter(ctx)
        
        # Get the value
        value = ctx.obj.config_manager.get(key)
        
        if value is None:
            output.warning(f"No configuration value found for key '{key}'")
            return 1
        
        # Display the value
        if format == "json":
            output.format_output({key: value})
        else:
            if isinstance(value, dict):
                output.info(f"{key}:")
                for k, v in value.items():
                    output.info(f"  {k}: {v}")
            elif isinstance(value, list):
                output.info(f"{key}:")
                for i, v in enumerate(value):
                    output.info(f"  {i}: {v}")
            else:
                output.info(f"{key}: {value}")
        
        return 0
        
    except ConfigurationError as e:
        output = get_output_adapter(ctx)
        output.error(f"Configuration error: {e}")
        return 1


@config_group.command("set")
@click.argument("key", required=True)
@click.argument("value", required=True)
@click.option(
    "--save",
    is_flag=True,
    help="Save configuration changes to disk",
)
@catch_errors
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, save: bool) -> int:
    """
    [Function intent]
    Set a configuration value.
    
    [Implementation details]
    Sets a configuration value using the provided key and value. The value is
    parsed to determine its appropriate type (boolean, number, etc.). Changes
    can be persisted to disk with the --save flag.
    
    [Design principles]
    Value parsing - converts string values to appropriate types.
    Persistence control - allows saving changes to disk.
    Feedback - provides clear feedback about the operation result.
    
    Args:
        ctx: CLI context with access to services
        key: Configuration key (e.g., 'mcp_server.url')
        value: New value for the configuration key
        save: Whether to save changes to disk
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Get adapter for output formatting
        output = get_output_adapter(ctx)
        
        # Parse the value
        parsed_value = _parse_value(value)
        
        # Set the value
        ctx.obj.config_manager.set(key, parsed_value)
        
        # Save if requested
        if save:
            ctx.obj.config_manager.save_to_user_config()
            output.success(f"Configuration value for '{key}' set and saved to disk")
        else:
            output.success(f"Configuration value for '{key}' set (in memory only, use --save to persist)")
        
        return 0
        
    except ConfigurationError as e:
        output = get_output_adapter(ctx)
        output.error(f"Failed to set configuration: {e}")
        return 1


@config_group.command("list")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text)",
)
@catch_errors
@click.pass_context
def config_list(ctx: click.Context, format: str) -> int:
    """
    [Function intent]
    List all configuration values.
    
    [Implementation details]
    Retrieves the complete configuration dictionary and displays it in the
    specified format (text or JSON).
    
    [Design principles]
    Comprehensive view - shows all configuration values.
    Flexible output - supports different output formats.
    Structured display - formats nested structures for readability.
    
    Args:
        ctx: CLI context with access to services
        format: Output format ('text' or 'json')
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Get adapter for output formatting
        output = get_output_adapter(ctx)
        
        # Get the config dictionary
        config = ctx.obj.config_manager.get_config_dict()
        
        # Display the configuration
        if format == "json":
            output.format_output(config)
        else:
            _print_nested_dict(ctx, config, output)
        
        return 0
        
    except ConfigurationError as e:
        output = get_output_adapter(ctx)
        output.error(f"Failed to list configuration: {e}")
        return 1


@config_group.command("reset")
@click.argument("key", required=False)
@click.option(
    "--save",
    is_flag=True,
    help="Save configuration changes to disk",
)
@catch_errors
@click.pass_context
def config_reset(ctx: click.Context, key: Optional[str], save: bool) -> int:
    """
    [Function intent]
    Reset configuration values to defaults.
    
    [Implementation details]
    Resets all configuration or a specific key to default values. Changes can be
    persisted to disk with the --save flag.
    
    [Design principles]
    Selective reset - allows resetting specific keys or all configuration.
    Persistence control - allows saving changes to disk.
    Feedback - provides clear feedback about the operation result.
    
    Args:
        ctx: CLI context with access to services
        key: Optional configuration key to reset
        save: Whether to save changes to disk
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Get adapter for output formatting
        output = get_output_adapter(ctx)
        
        if key:
            # Reset specific key
            ctx.obj.config_manager.reset(key)
            output.success(f"Configuration value for '{key}' reset to default")
        else:
            # Reset all configuration
            ctx.obj.config_manager.reset()
            output.success("All configuration reset to defaults")
        
        # Save if requested
        if save:
            ctx.obj.config_manager.save_to_user_config()
            output.success("Configuration changes saved to disk")
        else:
            output.info("Configuration reset in memory only (use --save to persist)")
        
        return 0
        
    except ConfigurationError as e:
        output = get_output_adapter(ctx)
        output.error(f"Failed to reset configuration: {e}")
        return 1


def _print_nested_dict(ctx: click.Context, data: Dict[str, Any], output=None, prefix: str = "") -> None:
    """
    [Function intent]
    Print a nested dictionary in a readable format.
    
    [Implementation details]
    Recursively traverses a nested dictionary structure and prints each key-value
    pair in a readable format, with proper indentation and formatting for nested
    structures.
    
    [Design principles]
    Recursive traversal - handles arbitrary nesting levels.
    Readable format - uses indentation and formatting for clarity.
    
    Args:
        ctx: CLI context with access to services
        data: Dictionary to print
        output: Output adapter to use for printing (if None, one will be created)
        prefix: Key prefix for nested dictionaries
    """
    # If no output adapter was provided, get one
    if output is None:
        output = get_output_adapter(ctx)
        
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursively print nested dictionaries
            output.info(f"{full_key}:")
            _print_nested_dict(ctx, value, output, full_key)
        elif isinstance(value, list):
            # Print lists with indentation
            output.info(f"{full_key}: [")
            for item in value:
                output.info(f"  {item}")
            output.info("]")
        else:
            # Print simple key-value pairs
            output.info(f"{full_key}: {value}")


def _parse_value(value_str: str) -> Any:
    """
    [Function intent]
    Parse a string value into an appropriate Python type.
    
    [Implementation details]
    Attempts to parse the string value into an appropriate Python type,
    trying boolean, null, JSON, integer, and float before defaulting to string.
    
    [Design principles]
    Type inference - determines appropriate type from string representation.
    Progressive parsing - tries different types in order of specificity.
    
    Args:
        value_str: String value to parse
        
    Returns:
        Parsed value (bool, int, float, or string)
    """
    # Handle boolean values
    if value_str.lower() in ("true", "yes", "1", "on"):
        return True
    if value_str.lower() in ("false", "no", "0", "off"):
        return False
    
    # Handle null/None
    if value_str.lower() in ("null", "none"):
        return None
    
    # Try to parse as JSON
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        pass
    
    # Try to parse as integer
    try:
        return int(value_str)
    except ValueError:
        pass
    
    # Try to parse as float
    try:
        return float(value_str)
    except ValueError:
        pass
    
    # Default to string
    return value_str
