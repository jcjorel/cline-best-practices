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
# Implements the ConfigCommandHandler for the 'config' CLI command, which allows
# users to manage CLI configuration settings. This includes viewing, setting, and
# resetting configuration values for the DBP CLI application.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'config' command.
# - Provides operations for getting, setting, listing, and resetting configuration.
# - Supports dot notation for accessing nested configuration values.
# - Persists configuration changes to disk when needed.
# - Validates configuration keys and values.
###############################################################################
# [Source file constraints]
# - Depends on the ConfigurationManager from config.py.
# - Configuration keys are case-sensitive.
# - File writing depends on filesystem permissions.
###############################################################################
# [Dependencies]
# - src/dbp_cli/commands/base.py
# - src/dbp_cli/config.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T13:12:00Z : Initial creation of ConfigCommandHandler by CodeAssistant
# * Implemented command handler for managing CLI configuration.
###############################################################################

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from .base import BaseCommandHandler
from ..exceptions import CommandError, ConfigurationError

logger = logging.getLogger(__name__)

class ConfigCommandHandler(BaseCommandHandler):
    """Handles the 'config' command for managing CLI configuration."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add config-specific arguments to the parser."""
        # Required action argument
        parser.add_argument(
            "action",
            choices=["get", "set", "list", "reset"],
            help="Configuration action to perform"
        )
        
        # Optional key argument (required for get, set, reset)
        parser.add_argument(
            "key",
            nargs="?",
            help="Configuration key (e.g., 'mcp_server.url')"
        )
        
        # Optional value argument (required for set)
        parser.add_argument(
            "value",
            nargs="?",
            help="Configuration value (required for 'set')"
        )
        
        # Options
        parser.add_argument(
            "--save",
            action="store_true",
            help="Save configuration changes to disk"
        )
        
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)"
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the config command with the provided arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Handle different actions
            if args.action == "get":
                return self._get_config(args)
            elif args.action == "set":
                return self._set_config(args)
            elif args.action == "list":
                return self._list_config(args)
            elif args.action == "reset":
                return self._reset_config(args)
            else:
                # Should not happen because of choices in argparse
                self.output.error(f"Unknown action: {args.action}")
                return 1
        
        except CommandError as e:
            self.output.error(str(e))
            return 1
        except ConfigurationError as e:
            self.output.error(f"Configuration error: {e}")
            return 1
        except Exception as e:
            self.output.error(f"Error: {e}")
            return 1
    
    def _get_config(self, args: argparse.Namespace) -> int:
        """
        Get a configuration value.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        if not args.key:
            self.output.error("Key is required for 'get' action")
            return 1
        
        # Get the value
        value = self.mcp_client.config_manager.get(args.key)
        
        if value is None:
            self.output.warning(f"No configuration value found for key '{args.key}'")
            return 1
        
        # Display the value
        if args.format == "json":
            self.output.format_output({args.key: value})
        else:
            if isinstance(value, dict):
                self.output.info(f"{args.key}:")
                for k, v in value.items():
                    self.output.info(f"  {k}: {v}")
            elif isinstance(value, list):
                self.output.info(f"{args.key}:")
                for i, v in enumerate(value):
                    self.output.info(f"  {i}: {v}")
            else:
                self.output.info(f"{args.key}: {value}")
        
        return 0
    
    def _set_config(self, args: argparse.Namespace) -> int:
        """
        Set a configuration value.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        if not args.key:
            self.output.error("Key is required for 'set' action")
            return 1
        
        if args.value is None:
            self.output.error("Value is required for 'set' action")
            return 1
        
        # Parse the value (handle booleans, numbers, etc.)
        parsed_value = self._parse_value(args.value)
        
        try:
            # Set the value
            self.mcp_client.config_manager.set(args.key, parsed_value)
            
            # Save if requested
            if args.save:
                self.mcp_client.config_manager.save_to_user_config()
                self.output.success(f"Configuration value for '{args.key}' set and saved to disk")
            else:
                self.output.success(f"Configuration value for '{args.key}' set (in memory only, use --save to persist)")
            
            return 0
            
        except ConfigurationError as e:
            self.output.error(f"Failed to set configuration: {e}")
            return 1
    
    def _list_config(self, args: argparse.Namespace) -> int:
        """
        List configuration values.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Get the config dictionary
        config = self.mcp_client.config_manager.get_config_dict()
        
        # Display the configuration
        if args.format == "json":
            self.output.format_output(config)
        else:
            self._print_nested_dict(config)
        
        return 0
    
    def _reset_config(self, args: argparse.Namespace) -> int:
        """
        Reset configuration to default values.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            if args.key:
                # Reset specific key
                self.mcp_client.config_manager.reset(args.key)
                self.output.success(f"Configuration value for '{args.key}' reset to default")
            else:
                # Reset all configuration
                self.mcp_client.config_manager.reset()
                self.output.success("All configuration reset to defaults")
            
            # Save if requested
            if args.save:
                self.mcp_client.config_manager.save_to_user_config()
                self.output.success("Configuration changes saved to disk")
            else:
                self.output.info("Configuration reset in memory only (use --save to persist)")
            
            return 0
            
        except ConfigurationError as e:
            self.output.error(f"Failed to reset configuration: {e}")
            return 1
    
    def _print_nested_dict(self, data: Dict[str, Any], prefix: str = "") -> None:
        """
        Print a nested dictionary in a readable format.
        
        Args:
            data: Dictionary to print
            prefix: Key prefix for nested dictionaries
        """
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively print nested dictionaries
                self.output.info(f"{full_key}:")
                self._print_nested_dict(value, full_key)
            elif isinstance(value, list):
                # Print lists with indentation
                self.output.info(f"{full_key}: [")
                for item in value:
                    self.output.info(f"  {item}")
                self.output.info("]")
            else:
                # Print simple key-value pairs
                self.output.info(f"{full_key}: {value}")
    
    def _parse_value(self, value_str: str) -> Any:
        """
        Parse a string value into an appropriate Python type.
        
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
