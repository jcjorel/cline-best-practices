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
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
###############################################################################
# [GenAI tool change history]
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
from .config import ConfigurationManager
from .auth import AuthenticationManager
from .api import MCPClientAPI
from .output import OutputFormatter
from .progress import ProgressIndicator
from .exceptions import CLIError, ConfigurationError, AuthenticationError

# Import command handlers
from .commands.base import BaseCommandHandler
from .commands.analyze import AnalyzeCommandHandler
from .commands.recommend import RecommendCommandHandler
from .commands.apply import ApplyCommandHandler
from .commands.relationships import RelationshipsCommandHandler
from .commands.config import ConfigCommandHandler
from .commands.status import StatusCommandHandler

# Set up logger
logger = logging.getLogger(__name__)

class DocumentationProgrammingCLI:
    """Main CLI application for Documentation-Based Programming."""
    
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
        Initialize core components.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.logger.debug("Initializing CLI components")
        
        # Create configuration manager
        self.config_manager = ConfigurationManager(config_file_override=config_file)
        
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
        """Initialize command handlers."""
        self.logger.debug("Initializing command handlers")
        
        # Register command handlers
        self.command_handlers = {
            "analyze": AnalyzeCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "recommend": RecommendCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "apply": ApplyCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "relationships": RelationshipsCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "config": ConfigCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "status": StatusCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        }
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create command-line argument parser.
        
        Returns:
            Configured argument parser
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
        Get the CLI version.
        
        Returns:
            Version string
        """
        try:
            # Try to get version from package metadata
            return metadata.version("dbp-cli")
        except Exception:
            # Fallback to development version
            return "0.1.0.dev"
            
    def _configure_logging(self, verbosity: int, quiet: bool) -> None:
        """
        Configure logging based on verbosity level.
        
        Args:
            verbosity: Verbosity level (0=warning, 1=info, 2+=debug)
            quiet: Whether to suppress all non-error output
        """
        log_level = logging.WARNING  # Default
        
        if quiet:
            log_level = logging.ERROR
        elif verbosity == 1:
            log_level = logging.INFO
        elif verbosity >= 2:
            log_level = logging.DEBUG
            
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format="%(levelname)s: %(message)s"
        )
        
        # Set level for our loggers
        logging.getLogger("dbp_cli").setLevel(log_level)
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI application.
        
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
    Main entry point function.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    cli = DocumentationProgrammingCLI()
    return cli.run()
