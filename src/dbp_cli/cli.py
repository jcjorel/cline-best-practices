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
# Implements the main CLI class for the Documentation-Based Programming CLI
# application. This class handles command-line argument parsing, initializes
# all necessary components, and delegates to appropriate command handlers.
###############################################################################
# [Source file design principles]
# - Acts as the main entry point for the CLI application.
# - Centralizes command registration and argument parsing.
# - Manages component dependencies (config, auth, API, output, progress).
# - Handles global error conditions and environment setup.
# - Provides consistent command-line interface across various commands.
# - Design Decision: Single Entry Point (2025-04-15)
#   * Rationale: Centralizes initialization and argument parsing, simplifying the interaction flow.
#   * Alternatives considered: Command-specific entry points (more complex, inconsistent), 
#     Library approach (less command-line friendly).
###############################################################################
# [Source file constraints]
# - Must maintain backward compatibility with command-line arguments.
# - Exit codes should follow standard conventions (0 success, non-zero failure).
# - All commands must be initialized with the same set of core services.
###############################################################################
# [Dependencies]
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
# 2025-04-17T14:35:00Z : Updated to use server ConfigurationManager by CodeAssistant
# * Changed from local CLI config manager to use the shared server ConfigurationManager
# * Improves configuration consistency by having a single source of truth
# * Fixed issue with missing configuration keys for MCP server components
# 2025-04-15T14:52:30Z : Added ServerCommandHandler to command registry by CodeAssistant
# * Integrated server management functionality into CLI.
# 2025-04-15T13:15:30Z : Initial creation of DocumentationProgrammingCLI by CodeAssistant
# * Implemented main CLI class with command registration and entry point.
###############################################################################

import argparse
import logging
import os
import sys
from importlib import metadata
from typing import Dict, List, Optional, Any

# Import core components
from dbp.config.config_manager import ConfigurationManager
from .auth import AuthenticationManager
from .api import MCPClientAPI
from .output import OutputFormatter
from .progress import ProgressIndicator
from .exceptions import CLIError, ConfigurationError, AuthenticationError

# Import command handlers
from .commands.base import BaseCommandHandler
# Import only the commands that directly align with MCP tools
from .commands.query import QueryCommandHandler
from .commands.commit import CommitCommandHandler
# Import system commands
from .commands.config import ConfigCommandHandler
from .commands.status import StatusCommandHandler
from .commands.server import ServerCommandHandler

# Set up logger
logger = logging.getLogger(__name__)

class DocumentationProgrammingCLI:
    """
    [Class intent]
    Main CLI application for Documentation-Based Programming that serves as the primary
    entry point for all command-line interactions with the system.
    
    [Implementation details]
    Manages the lifecycle of all core components (config, auth, API client, output, progress)
    and coordinates command registration and execution. Uses argparse for command-line
    argument parsing with a subcommand pattern for different operations.
    
    [Design principles]
    Command registry pattern - centralizes command handling in a registry.
    Dependency injection - core services are created and provided to commands.
    Progressive initialization - components are created only when needed.
    Consistent error handling - standardized approach for all error conditions.
    """
    
    def __init__(self):
        """Initialize the CLI application."""
        self.logger = logger
        
        # Set up core components (with lazy initialization)
        self.config_manager = None
        self.auth_manager = None
        self.mcp_client = None
        self.output_formatter = None
        self.progress_indicator = None
        
        # Command handlers (will be initialized on demand)
        self.command_handlers = {}
        
        # Parser (will be created during run)
        self.parser = None
        
    def _init_components(self, config_file: Optional[str] = None) -> None:
        """
        [Function intent]
        Initialize all core CLI components required for command execution.
        
        [Implementation details]
        Creates instances of fundamental components in a specific order:
        1. Configuration manager (loads settings from files/environment)
        2. Authentication manager (handles API keys and authentication)
        3. MCP client (for API communication)
        4. Output formatter (for displaying results)
        5. Progress indicator (for visual feedback during operations)
        
        [Design principles]
        Dependency chain - initializes components in correct dependency order.
        Lazy initialization - creates components only when needed.
        Configuration injection - allows overriding default configuration file.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.logger.debug("Initializing CLI components")
        
        # Create configuration manager
        self.config_manager = ConfigurationManager()
        if config_file:
            self.config_manager.load_from_file(config_file)
        
        # Create authentication manager
        self.auth_manager = AuthenticationManager(self.config_manager)
        
        # Create MCP client
        self.mcp_client = MCPClientAPI(self.auth_manager)
        
        # Create output formatter
        output_format = self.config_manager.get("cli.output_format", "text")
        use_color = self.config_manager.get("cli.color", True)
        self.output_formatter = OutputFormatter(default_format=output_format, use_color=use_color)
        
        # Create progress indicator
        self.progress_indicator = ProgressIndicator()
        
    def _init_command_handlers(self) -> None:
        """
        [Function intent]
        Create and register all command handler instances for the CLI.
        
        [Implementation details]
        Creates instances of all command handlers and registers them in a
        dictionary with command names as keys. Each handler is initialized
        with the core components (MCP client, output formatter, progress indicator).
        
        [Design principles]
        Command registry pattern - stores handlers in a central registry.
        Component injection - passes required dependencies to all handlers.
        Extensibility - easy to add new command handlers to the registry.
        """
        self.logger.debug("Initializing command handlers")
        
        # Register command handlers - only those that align with MCP tools or system commands
        self.command_handlers = {
            # Main MCP tool commands
            "query": QueryCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "commit": CommitCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            # System commands
            "config": ConfigCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "status": StatusCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "server": ServerCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        }
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        [Function intent]
        Create and configure the command-line argument parser for the CLI.
        
        [Implementation details]
        Creates the main parser with global options like version, config, verbosity.
        Sets up subparsers for each registered command.
        Delegates command-specific arguments to each command handler.
        
        [Design principles]
        Hierarchical parsing - main parser with command subparsers.
        Delegation - command handlers define their own arguments.
        Consistent interface - standard global options across all commands.
        Self-documentation - includes help text for all options and commands.
        
        Returns:
            Configured argparse.ArgumentParser ready to parse command-line arguments
        """
        self.logger.debug("Creating command-line parser")
        
        # Create main parser
        parser = argparse.ArgumentParser(
            description="Documentation-Based Programming CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Add version argument
        parser.add_argument(
            "--version",
            action="version",
            version=f"dbp-cli {self._get_version()}"
        )
        
        # Add global arguments
        parser.add_argument(
            "--config",
            metavar="FILE",
            help="Path to configuration file"
        )
        parser.add_argument(
            "--server",
            metavar="URL",
            help="MCP server URL"
        )
        parser.add_argument(
            "--api-key",
            metavar="KEY",
            help="API key for authentication"
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="Increase verbosity level"
        )
        parser.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="Suppress all non-error output"
        )
        parser.add_argument(
            "--output",
            "-o",
            choices=["text", "json", "markdown", "html"],
            help="Output format"
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="Disable colored output"
        )
        parser.add_argument(
            "--no-progress",
            action="store_true",
            help="Disable progress indicators"
        )
        
        # Create subparsers for commands
        subparsers = parser.add_subparsers(
            dest="command",
            help="Command to execute",
            title="Commands"
        )
        
        # Add command-specific subparsers
        for command_name, handler in self.command_handlers.items():
            command_parser = subparsers.add_parser(
                command_name,
                help=handler.__doc__.splitlines()[0] if handler.__doc__ else f"{command_name} command"
            )
            handler.add_arguments(command_parser)
        
        return parser
        
    def _get_version(self) -> str:
        """
        [Function intent]
        Determine the current version of the CLI application.
        
        [Implementation details]
        Attempts to retrieve version from package metadata using importlib.
        Falls back to a development version string if metadata is unavailable.
        
        [Design principles]
        Graceful degradation - provides reasonable default when metadata is missing.
        Single source of truth - uses package metadata for version information.
        
        Returns:
            Version string in semantic versioning format
        """
        try:
            # Try to get version from package metadata
            return metadata.version("dbp-cli")
        except Exception:
            # Fallback to development version
            return "0.1.0.dev"
            
    def _configure_logging(self, verbosity: int, quiet: bool) -> None:
        """
        [Function intent]
        Configure the Python logging system based on command-line options.
        
        [Implementation details]
        Sets log level based on verbosity flag count and quiet flag:
        - quiet=True → ERROR level only
        - verbosity=0 → WARNING level (default)
        - verbosity=1 → INFO level
        - verbosity≥2 → DEBUG level
        Uses the centralized application logging setup from log_utils.py for consistent formatting.
        Sets specific level for dbp_cli package loggers.
        
        [Design principles]
        Progressive verbosity - more verbose output with increasing verbosity level.
        Quiet override - quiet flag takes precedence over verbosity.
        Consistent formatting - standardized log format across all components.
        Reuses centralized logging utilities for system-wide consistency.
        
        Args:
            verbosity: Verbosity level (0=warning, 1=info, 2+=debug)
            quiet: Whether to suppress all non-error output
        """
        # Determine log level based on verbosity and quiet flags
        log_level_name = "WARNING"  # Default
        
        if quiet:
            log_level_name = "ERROR"
        elif verbosity == 1:
            log_level_name = "INFO"
        elif verbosity >= 2:
            log_level_name = "DEBUG"
            
        # Use the centralized application logging setup
        from dbp.core.log_utils import setup_application_logging
        setup_application_logging(log_level_name)
        
        # Set specific level for dbp_cli loggers
        logging.getLogger("dbp_cli").setLevel(getattr(logging, log_level_name))
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        [Function intent]
        Execute the CLI application with the provided arguments.
        
        [Implementation details]
        1. Initializes components if not already initialized
        2. Parses command-line arguments
        3. Configures logging based on verbosity
        4. Applies command-line overrides to configuration
        5. Initializes the MCP client for API access
        6. Executes the requested command or shows help
        7. Handles exceptions and returns appropriate exit codes
        
        [Design principles]
        Robust error handling - catches and reports all exceptions appropriately.
        Context preservation - maintains command context through execution flow.
        Lazy initialization - creates components only when needed.
        Command delegation - routes execution to appropriate command handler.
        Standard exit codes - returns 0 for success, non-zero for errors.
        
        Args:
            args: Command-line arguments (defaults to sys.argv[1:])
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            # Parse command-line arguments
            if self.parser is None:
                # Initialize components first (to ensure command handlers are available)
                self._init_components()
                self._init_command_handlers()
                self.parser = self._create_parser()
                
            # Parse arguments
            parsed_args = self.parser.parse_args(args)
            
            # Configure logging
            self._configure_logging(parsed_args.verbose, parsed_args.quiet)
            
            # Override configuration with command-line options
            if parsed_args.server:
                self.config_manager.set("mcp_server.url", parsed_args.server)
                
            if parsed_args.api_key:
                self.auth_manager.set_api_key(parsed_args.api_key, save=False)
                
            if parsed_args.output:
                self.output_formatter.set_format(parsed_args.output)
                
            if parsed_args.no_color:
                self.output_formatter.set_color_enabled(False)
            
            # Initialize MCP client (required for most commands)
            try:
                # Initialize API client (required for API calls)
                self.mcp_client.initialize()
            except ConfigurationError as e:
                # Don't fail if we're just running non-API commands like config or status
                if parsed_args.command not in ["config", "status", None]:
                    self.output_formatter.error(f"Configuration error: {e}")
                    return 2
            
            # Handle no command case
            if not parsed_args.command:
                self.parser.print_help()
                return 0
                
            # Execute the command
            handler = self.command_handlers.get(parsed_args.command)
            
            if handler:
                self.logger.info(f"Executing command: {parsed_args.command}")
                return handler.execute(parsed_args)
            else:
                self.output_formatter.error(f"Unknown command: {parsed_args.command}")
                return 1
                
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.logger.info("Operation cancelled by user")
            print("\nOperation cancelled by user", file=sys.stderr)
            return 130  # Convention for Ctrl+C
            
        except CLIError as e:
            # Handle known CLI errors
            self.output_formatter.error(str(e))
            return e.exit_code
            
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            self.output_formatter.error(f"Unexpected error: {e}")
            
            if self.logger.level <= logging.DEBUG:
                import traceback
                traceback.print_exc()
                
            return 1


def main() -> int:
    """
    [Function intent]
    Serve as the main entry point for the CLI application when executed as a script.
    
    [Implementation details]
    Creates an instance of the DocumentationProgrammingCLI class and calls its run method.
    Returns the exit code from the run method to the operating system.
    
    [Design principles]
    Minimal entry point - delegates all logic to the CLI class.
    Standard executable pattern - follows conventional CLI entry point pattern.
    Exit code propagation - passes CLI exit code back to the operating system.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    cli = DocumentationProgrammingCLI()
    return cli.run()
