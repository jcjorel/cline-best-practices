###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements a command-line interface (CLI) for interacting with the
# ConfigurationManager. Allows users to get, set, list, and validate
# configuration parameters.
###############################################################################
# [Source file design principles]
# - Uses argparse for parsing command-line arguments and subcommands.
# - Provides distinct subcommands for different actions (get, set, list, validate).
# - Interacts with the ConfigurationManager singleton to perform actions.
# - Supports different output formats (JSON, YAML) for listing configuration.
# - Includes basic error handling and user feedback.
# - Design Decision: Argparse for CLI (2025-04-14)
#   * Rationale: Standard Python library for CLI parsing, well-documented, supports subcommands effectively.
#   * Alternatives considered: Click (more dependencies), Typer (Pydantic-based, potentially overkill for this).
###############################################################################
# [Source file constraints]
# - Depends on `config_manager.py` for the ConfigurationManager.
# - Requires `PyYAML` for YAML output format.
# - Assumes ConfigurationManager is initialized before CLI commands are run (in a typical application entry point).
###############################################################################
# [Reference documentation]
# - doc/CONFIGURATION.md
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_config_management.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:39:30Z : Initial creation of ConfigCLI class by CodeAssistant
# * Implemented CLI structure with get, set, list, validate subcommands.
###############################################################################

import argparse
import json
import yaml # Requires PyYAML
import sys
import logging
from typing import Dict, Any, Optional, List

# Assuming config_manager.py is accessible
try:
    from .config_manager import ConfigurationManager
except ImportError:
    # Allow running standalone for testing if needed
    from config_manager import ConfigurationManager

logger = logging.getLogger(__name__)

class ConfigCLI:
    """Command-line interface for managing DBP configuration."""

    def __init__(self, config_manager: ConfigurationManager = None):
        """
        Initializes the ConfigCLI.

        Args:
            config_manager: An instance of ConfigurationManager. If None,
                            the singleton instance will be retrieved.
        """
        self.config_manager = config_manager or ConfigurationManager()
        if not isinstance(self.config_manager, ConfigurationManager):
             raise TypeError("config_manager must be an instance of ConfigurationManager")
        # Ensure config is initialized if not already (e.g., when run standalone)
        if not self.config_manager.initialized_flag:
             logger.warning("ConfigurationManager not initialized. Attempting initialization.")
             try:
                 # Initialize with None for args, assuming defaults/files/env are primary sources for CLI use
                 self.config_manager.initialize(args=None)
             except Exception as e:
                 print(f"Error: Failed to initialize configuration: {e}", file=sys.stderr)
                 # Allow CLI to potentially still run if defaults are sufficient,
                 # but log the failure.
                 logger.error("CLI proceeding with potentially uninitialized config due to error.", exc_info=True)


    def run(self, args: Optional[List[str]] = None):
        """
        Runs the configuration CLI.

        Args:
            args: List of command-line arguments (defaults to sys.argv[1:]).

        Returns:
            Exit code (0 for success, 1 for error).
        """
        parser = self._create_parser()
        # Use provided args or sys.argv[1:]
        parsed_args = parser.parse_args(args if args is not None else sys.argv[1:])

        if not hasattr(parsed_args, 'func'):
            parser.print_help()
            return 1 # Indicate error or no command given

        # Execute the function associated with the subcommand
        try:
            return parsed_args.func(parsed_args)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            logger.error("Error executing CLI command.", exc_info=True)
            return 1

    def _create_parser(self) -> argparse.ArgumentParser:
        """Creates the main argument parser and subparsers for commands."""
        parser = argparse.ArgumentParser(
            description='Manage Documentation-Based Programming (DBP) configuration.',
            prog='dbp-config' # Example program name
        )
        subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

        # --- Get Command ---
        get_parser = subparsers.add_parser('get', help='Get a specific configuration value by key.')
        get_parser.add_argument('key', help='Configuration key in dot notation (e.g., database.type).')
        get_parser.set_defaults(func=self._handle_get)

        # --- Set Command ---
        set_parser = subparsers.add_parser('set', help='Set a configuration value (runtime only, not persistent).')
        set_parser.add_argument('key', help='Configuration key in dot notation.')
        set_parser.add_argument('value', help='The value to set.')
        set_parser.set_defaults(func=self._handle_set)

        # --- List Command ---
        list_parser = subparsers.add_parser('list', help='List all or part of the configuration.')
        list_parser.add_argument(
            '--format', choices=['json', 'yaml'], default='yaml',
            help='Output format (default: yaml).'
        )
        list_parser.add_argument(
            '--prefix', help='Only list keys starting with this prefix (e.g., database).'
        )
        list_parser.set_defaults(func=self._handle_list)

        # --- Validate Command ---
        validate_parser = subparsers.add_parser('validate', help='Validate the current configuration against the schema.')
        validate_parser.set_defaults(func=self._handle_validate)

        return parser

    def _handle_get(self, args: argparse.Namespace) -> int:
        """Handles the 'get' command."""
        value = self.config_manager.get(args.key)
        if value is None:
            print(f"Error: Configuration key not found: '{args.key}'", file=sys.stderr)
            return 1
        # Print simple values directly, complex values as JSON for clarity
        if isinstance(value, (str, int, float, bool)):
            print(value)
        else:
            try:
                print(json.dumps(value, indent=2))
            except TypeError:
                # Fallback for non-serializable objects (shouldn't happen with Pydantic)
                print(repr(value))
        return 0

    def _handle_set(self, args: argparse.Namespace) -> int:
        """Handles the 'set' command."""
        # Attempt to convert value before setting
        converted_value = self.config_manager._convert_value(args.value)
        success = self.config_manager.set(args.key, converted_value)
        if not success:
            print(f"Error: Failed to set configuration value for key '{args.key}'. Check logs for validation errors.", file=sys.stderr)
            return 1
        print(f"Configuration value set successfully (runtime only): {args.key} = {converted_value!r}")
        return 0

    def _handle_list(self, args: argparse.Namespace) -> int:
        """Handles the 'list' command."""
        config_dict = self.config_manager.as_dict()

        # Filter by prefix if provided
        if args.prefix:
            filtered_dict = self._filter_dict_by_prefix(config_dict, args.prefix)
            if not filtered_dict:
                 print(f"No configuration keys found matching prefix: '{args.prefix}'", file=sys.stderr)
                 return 1
            config_dict = filtered_dict


        # Output in requested format
        try:
            if args.format == 'json':
                print(json.dumps(config_dict, indent=2))
            else: # Default is yaml
                print(yaml.dump(config_dict, default_flow_style=False, sort_keys=False))
            return 0
        except Exception as e:
            print(f"Error formatting output: {e}", file=sys.stderr)
            return 1

    def _filter_dict_by_prefix(self, data: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Filters a nested dictionary to include only items under the given prefix."""
        prefix_parts = prefix.split('.')
        current_level = data
        try:
            for part in prefix_parts:
                if isinstance(current_level, dict):
                    current_level = current_level[part]
                else:
                    # If intermediate path is not a dict, prefix doesn't fully match
                    return {}
            # If we successfully navigated, return the structure starting from the prefix
            # Need to reconstruct the path back
            result = {}
            d = result
            for i, part in enumerate(prefix_parts):
                 if i < len(prefix_parts) - 1:
                     d[part] = {}
                     d = d[part]
                 else:
                     d[part] = current_level
            return result

        except (KeyError, TypeError):
            # Prefix not found or invalid structure
            return {}


    def _handle_validate(self, args: argparse.Namespace) -> int:
        """Handles the 'validate' command."""
        print("Validating current configuration...")
        errors = self.config_manager.validate()

        if not errors:
            print("Configuration is valid.")
            return 0
        else:
            print("Configuration validation failed with the following errors:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

# Main execution block for standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    cli = ConfigCLI()
    exit_code = cli.run()
    sys.exit(exit_code)
