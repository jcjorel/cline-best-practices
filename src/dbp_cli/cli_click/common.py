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
# Provides common utilities, context definitions, and decorators for the 
# Click-based CLI implementation. Centralizes shared functionality used across
# various commands and ensures consistent behavior throughout the CLI.
###############################################################################
# [Source file design principles]
# - Centralization of common functionality into reusable components
# - Decorator pattern for applying consistent options to commands
# - Context object pattern for sharing state between commands
# - Clean separation of concerns between CLI interface and business logic
# - Progressive enhancement of commands with additional functionality
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with existing CLI behavior
# - Should not directly depend on argparse-based CLI components
# - Context object must contain all required services for commands
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/api.py
# codebase:src/dbp_cli/auth.py
# codebase:src/dbp_cli/output.py
# codebase:src/dbp_cli/progress.py
# codebase:src/dbp_cli/exceptions.py
# system:click
###############################################################################
# [GenAI tool change history]
# 2025-05-13T13:53:30Z : Updated all CLI commands to use get_output_adapter() by CodeAssistant
# * Modified server.py, query.py, and commit.py to use centralized get_output_adapter() function 
# * Removed direct ctx.obj.output_formatter references in favor of adapter pattern
# * Ensured consistent error handling and output formatting across commands
# 2025-05-13T13:35:00Z : Fixed parameter compatibility in ClickContextOutputAdapter by CodeAssistant
# * Updated print method to convert 'nl' parameter to 'end' parameter for OutputFormatter compatibility
# * Added get_output_adapter() function to reuse adapters across commands
# * Fixed 'nl is an invalid keyword argument for print()' error in Bedrock CLI
# 2025-05-13T12:46:00Z : Added ClickContextOutputAdapter class for output formatting by CodeAssistant 
# * Created class to bridge Click context and output formatter interfaces
# * Implemented print, error, and warning methods for consistent output
# * Used adapter pattern to make Click and command handler interfaces compatible
# 2025-05-13T01:32:00Z : Fixed import statements for proper module resolution by CodeAssistant
# * Changed relative imports (..auth) to absolute imports (dbp_cli.auth)
# * Fixed ImportError: attempted relative import beyond top-level package
###############################################################################

import logging
import os
import sys
import functools
from importlib import metadata
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import click

# Import core service components
from dbp.config.config_manager import ConfigurationManager
from dbp.core.log_utils import setup_application_logging
from dbp_cli.auth import AuthenticationManager
from dbp_cli.api import MCPClientAPI
from dbp_cli.output import OutputFormatter
from dbp_cli.progress import ProgressIndicator
from dbp_cli.exceptions import CLIError, ConfigurationError, AuthenticationError, ConnectionError, APIError


class ClickContextOutputAdapter:
    """
    [Class intent]
    Adapts a Click Context to provide the output formatter interface expected by handlers
    and command implementations throughout the CLI codebase.
    
    [Design principles]
    - Adapter pattern for interface compatibility
    - Delegates calls to appropriate Click methods
    - Complete implementation covering all OutputFormatter methods
    - Common utility for Click-based CLI commands
    
    [Implementation details]
    - Wraps a Click context to provide full output formatter interface
    - Forwards output calls to appropriate Click echo functions
    - Supports different output formats and styling
    """
    
    def __init__(self, ctx: click.Context):
        """
        [Function intent]
        Initialize the adapter with a Click context.
        
        [Design principles]
        - Simple dependency injection
        - Clear initialization
        
        [Implementation details]
        - Stores reference to Click context for later use
        - Uses context's original output_formatter when available
        
        Args:
            ctx: Click context to adapt
        """
        self.ctx = ctx
        # Store reference to the original output formatter if available
        self.output_formatter = getattr(ctx.obj, 'output_formatter', None) if hasattr(ctx, 'obj') else None
    
    def print(self, message="", nl=True):
        """
        [Function intent]
        Print a message to the console.
        
        [Design principles]
        - Direct delegation to Click echo
        - Maintains parameter compatibility
        
        [Implementation details]
        - Uses original output formatter if available
        - Falls back to Click's echo function
        - Supports optional newline control
        - Converts nl parameter to end parameter for OutputFormatter compatibility
        
        Args:
            message: Message to print
            nl: Whether to include a newline
        """
        if self.output_formatter and hasattr(self.output_formatter, 'print'):
            # Convert nl parameter to end parameter for OutputFormatter
            end = "\n" if nl else ""
            self.output_formatter.print(message, end=end)
        else:
            click.echo(message, nl=nl)
    
    def error(self, message):
        """
        [Function intent]
        Print an error message to the console.
        
        [Design principles]
        - Consistent error formatting
        - Direct delegation to Click secho
        
        [Implementation details]
        - Uses original output formatter if available
        - Falls back to Click's secho with red color
        - Always prints to stderr
        
        Args:
            message: Error message to print
        """
        if self.output_formatter and hasattr(self.output_formatter, 'error'):
            self.output_formatter.error(message)
        else:
            click.secho(f"Error: {message}", fg="red", err=True)
    
    def warning(self, message):
        """
        [Function intent]
        Print a warning message to the console.
        
        [Design principles]
        - Consistent warning formatting
        - Direct delegation to Click secho
        
        [Implementation details]
        - Uses original output formatter if available
        - Falls back to Click's secho with yellow color
        
        Args:
            message: Warning message to print
        """
        if self.output_formatter and hasattr(self.output_formatter, 'warning'):
            self.output_formatter.warning(message)
        else:
            click.secho(f"Warning: {message}", fg="yellow")
            
    def info(self, message):
        """
        [Function intent]
        Print an informational message to the console.
        
        [Design principles]
        - Consistent information formatting
        - Direct delegation to Click echo
        
        [Implementation details]
        - Uses original output formatter if available
        - Falls back to Click's echo with default styling
        
        Args:
            message: Information message to print
        """
        if self.output_formatter and hasattr(self.output_formatter, 'info'):
            self.output_formatter.info(message)
        else:
            click.echo(message)
    
    def success(self, message):
        """
        [Function intent]
        Print a success message to the console.
        
        [Design principles]
        - Consistent success formatting
        - Direct delegation to Click secho
        
        [Implementation details]
        - Uses original output formatter if available
        - Falls back to Click's secho with green color
        
        Args:
            message: Success message to print
        """
        if self.output_formatter and hasattr(self.output_formatter, 'success'):
            self.output_formatter.success(message)
        else:
            click.secho(f"Success: {message}", fg="green")
    
    def format_output(self, data):
        """
        [Function intent]
        Format and print output data according to the selected format.
        
        [Design principles]
        - Flexible output formatting
        - Support for different data structures
        - Consistent presentation
        
        [Implementation details]
        - Uses original output formatter if available
        - Falls back to simple JSON formatting with Click
        
        Args:
            data: Data to format and print
        """
        if self.output_formatter and hasattr(self.output_formatter, 'format_output'):
            self.output_formatter.format_output(data)
        else:
            # Simple JSON fallback
            import json
            click.echo(json.dumps(data, indent=2))


def get_output_adapter(ctx: click.Context) -> ClickContextOutputAdapter:
    """
    [Function intent]
    Get or create an output adapter for a Click context.
    
    [Design principles]
    - Consistent output formatting across commands
    - Simplified access to output functionality
    - Graceful fallbacks for different contexts
    
    [Implementation details]
    - Creates a new ClickContextOutputAdapter if one doesn't exist
    - Stores the adapter in context.meta for reuse
    
    Args:
        ctx: Click context to get/create an adapter for
        
    Returns:
        ClickContextOutputAdapter: An output adapter for the context
    """
    # Check if we already have an adapter in context.meta
    if not hasattr(ctx, 'meta') or ctx.meta is None:
        ctx.meta = {}
        
    if 'output_adapter' not in ctx.meta:
        # Create a new adapter and store it
        ctx.meta['output_adapter'] = ClickContextOutputAdapter(ctx)
        
    return ctx.meta['output_adapter']

# Set up logger
logger = logging.getLogger(__name__)

# Type variables for better typing support
F = TypeVar('F', bound=Callable[..., Any])
CommandFunction = TypeVar('CommandFunction', bound=Callable[..., Any])

class AppContext:
    """
    [Class intent]
    Represents the application context containing common services and state
    required by command implementations. Stored in Click's context obj attribute.
    
    [Implementation details]
    Holds instances of core services like configuration, authentication, API client,
    output formatting, and progress indication. Provides convenience methods for
    accessing configuration values and handling errors.
    
    [Design principles]
    Dependency injection container - centralizes service creation and access.
    Progressive initialization - services are created only when needed.
    Consistent error handling - standardized approach for all error conditions.
    Immutable after initialization - prevents unexpected state changes.
    """
    def __init__(self):
        """
        [Function intent]
        Initialize an empty application context object that will be populated during CLI startup.
        
        [Implementation details]
        Sets all service attributes to None initially. Services will be initialized
        by the CLI's setup function before commands are executed.
        
        [Design principles]
        Two-phase initialization - separates object creation from service initialization.
        Explicit state - clearly shows which services have been initialized.
        """
        # Core services (initialized during CLI startup)
        self.config_manager: Optional[ConfigurationManager] = None
        self.auth_manager: Optional[AuthenticationManager] = None
        self.api_client: Optional[MCPClientAPI] = None
        self.output_formatter: Optional[OutputFormatter] = None
        self.progress_indicator: Optional[ProgressIndicator] = None
        
        # Logging and configuration
        self.debug: bool = False
        self.verbose: int = 0
        self.quiet: bool = False
        
        # Initialize logger
        self.logger = logger.getChild('Context')

    def init_services(
        self,
        config_file: Optional[str] = None,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        output_format: Optional[str] = None,
        color_enabled: bool = True,
        progress_enabled: bool = True
    ) -> None:
        """
        [Function intent]
        Initialize all core services required for command execution.
        
        [Implementation details]
        Creates instances of required services in the correct dependency order:
        1. Configuration manager (loads settings from files/environment)
        2. Authentication manager (handles API keys and authentication)
        3. API client (for server communication)
        4. Output formatter (for displaying results)
        5. Progress indicator (for visual feedback)
        Applies command-line overrides to the default configuration.
        
        [Design principles]
        Dependency chain - initializes components in correct dependency order.
        Configuration overrides - allows command-line options to take precedence.
        Service composition - connects all services into a coherent system.
        
        Args:
            config_file: Optional path to configuration file
            server_url: Optional server URL override
            api_key: Optional API key override
            output_format: Optional output format override
            color_enabled: Whether colored output is enabled
            progress_enabled: Whether progress indicators are enabled
        """
        self.logger.debug("Initializing context services")
        
        # Create configuration manager
        self.config_manager = ConfigurationManager()
        if config_file and os.path.exists(config_file):
            self.config_manager.load_from_file(config_file)
        
        # Apply server URL override if provided
        if server_url:
            config = self.config_manager.get_typed_config()
            config.mcp_server.url = server_url
        
        # Create authentication manager
        self.auth_manager = AuthenticationManager(self.config_manager)
        
        # Apply API key override if provided
        if api_key:
            self.auth_manager.set_api_key(api_key, save=False)
        
        # Create API client
        self.api_client = MCPClientAPI(self.auth_manager)
        
        # Create output formatter
        config = self.config_manager.get_typed_config()
        default_format = output_format or config.cli.output_format
        self.output_formatter = OutputFormatter(default_format=default_format, use_color=color_enabled)
        
        # Create progress indicator
        self.progress_indicator = ProgressIndicator() if progress_enabled else None
    
    def init_api_client(self) -> None:
        """
        [Function intent]
        Initialize the API client for server communication.
        
        [Implementation details]
        Attempts to initialize the API client by connecting to the server.
        Handles common initialization errors, but allows non-API commands
        to run even if API initialization fails.
        
        [Design principles]
        Graceful degradation - allows partial functionality without API.
        Explicit initialization - clearly shows when API is available.
        Error handling - captures and reports initialization issues.
        """
        if self.api_client:
            try:
                self.api_client.initialize()
                self.logger.debug("API client initialized successfully")
            except ConfigurationError as e:
                self.logger.warning(f"API client initialization failed: {e}")
                # API initialization failures are handled at the command level
    
    def configure_logging(self) -> None:
        """
        [Function intent]
        Configure the Python logging system based on verbosity settings.
        
        [Implementation details]
        Sets log level based on verbosity flag count and quiet flag:
        - quiet=True → ERROR level only
        - verbose=0 → WARNING level (default)
        - verbose=1 → INFO level
        - verbose≥2 → DEBUG level
        Uses the centralized application logging setup from log_utils.py.
        
        [Design principles]
        Progressive verbosity - more verbose output with increasing verbosity.
        Quiet override - quiet flag takes precedence over verbosity.
        Consistent formatting - standardized log format across components.
        """
        # Determine log level based on verbosity and quiet flags
        log_level_name = "WARNING"  # Default
        
        if self.quiet:
            log_level_name = "ERROR"
        elif self.verbose == 1:
            log_level_name = "INFO"
        elif self.verbose >= 2:
            log_level_name = "DEBUG"
        
        # Use the centralized application logging setup
        setup_application_logging(log_level_name)
        
        # Set specific level for dbp_cli loggers
        logging.getLogger("dbp_cli").setLevel(getattr(logging, log_level_name))
    
    def with_progress(self, message: str, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        [Function intent]
        Execute a function while displaying a progress indicator, then return the result.
        
        [Implementation details]
        Starts the progress indicator with the provided message, executes the function
        with the given arguments, ensures the progress indicator is stopped when complete
        (even if an exception occurs), then returns the function's result.
        
        [Design principles]
        Resource management - uses try/finally to ensure progress indicator cleanup.
        Functional transparency - preserves and returns the original function result.
        
        Args:
            message: Message to display during execution
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function execution
        """
        if not self.progress_indicator:
            return func(*args, **kwargs)
            
        try:
            self.progress_indicator.start(message)
            result = func(*args, **kwargs)
            return result
        finally:
            if self.progress_indicator:
                self.progress_indicator.stop()
    
    def handle_error(self, error: Exception) -> int:
        """
        [Function intent]
        Classify and handle errors with appropriate user feedback and exit codes.
        
        [Implementation details]
        Checks the error type against known error classes and provides specific
        error messages and exit codes based on the error type.
        Maps error types to standardized exit codes:
        - Authentication errors: 3
        - Connection errors: 4
        - API errors: 5
        - Configuration errors: 2
        - CLI errors: Use the exit code from the error
        - Other errors: 1
        
        [Design principles]
        Standardized error handling - consistent error reporting and exit codes.
        Error classification - differentiates between different error types.
        User-friendly feedback - displays useful error messages for troubleshooting.
        
        Args:
            error: The exception to handle
            
        Returns:
            Exit code corresponding to the error type
        """
        if not self.output_formatter:
            print(f"Error: {error}", file=sys.stderr)
            return 1
            
        if isinstance(error, AuthenticationError):
            self.output_formatter.error(f"Authentication error: {error}")
            return 3
        elif isinstance(error, ConnectionError):
            self.output_formatter.error(f"Connection error: {error}")
            return 4
        elif isinstance(error, APIError):
            self.output_formatter.error(f"API error: {error}")
            return 5
        elif isinstance(error, ConfigurationError):
            self.output_formatter.error(f"Configuration error: {error}")
            return 2
        elif isinstance(error, CLIError):
            self.output_formatter.error(str(error))
            return getattr(error, 'exit_code', 1)
        elif isinstance(error, click.Abort):
            self.output_formatter.error("Operation aborted by user")
            return 130  # Convention for Ctrl+C
        else:
            self.output_formatter.error(f"Unexpected error: {error}")
            
            # Print stack trace if in debug mode
            if self.debug:
                import traceback
                print("\nStack trace:", file=sys.stderr)
                traceback.print_exc()
                
            return 1
    
    def get_version(self) -> str:
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


# No custom pass_context decorator - use click.pass_context directly instead

def common_options(function: F) -> F:
    """
    [Function intent]
    Apply common CLI options to a Click command function.
    
    [Implementation details]
    Creates a decorator that adds standard global options like:
    - --config for configuration file path
    - --verbose/-v for verbosity level
    - --quiet/-q for suppressing non-error output
    - --debug for enabling debug mode
    - --output/-o for output format
    - --no-color for disabling colored output
    - --no-progress for disabling progress indicators
    Initializes the AppContext object and stores it in Click's context.obj.
    
    [Design principles]
    Decorator pattern - attaches common options to command functions.
    Composition - decorators are applied in a specific order for correct behavior.
    DRY principle - avoids repeating option definitions across commands.
    
    Args:
        function: Click command function to decorate
        
    Returns:
        Decorated function with common options
    """
    @click.option(
        '--config',
        metavar='FILE',
        help='Path to configuration file'
    )
    @click.option(
        '--server',
        metavar='URL',
        help='MCP server URL'
    )
    @click.option(
        '--api-key',
        metavar='KEY',
        help='API key for authentication'
    )
    @click.option(
        '--verbose', '-v',
        count=True,
        help='Increase verbosity level'
    )
    @click.option(
        '--quiet', '-q',
        is_flag=True,
        help='Suppress all non-error output'
    )
    @click.option(
        '--output', '-o',
        type=click.Choice(['text', 'json', 'markdown', 'html']),
        help='Output format'
    )
    @click.option(
        '--no-color',
        is_flag=True,
        help='Disable colored output'
    )
    @click.option(
        '--no-progress',
        is_flag=True,
        help='Disable progress indicators'
    )
    @click.option(
        '--debug',
        is_flag=True,
        help='Enable debug mode with stack traces on errors'
    )
    @functools.wraps(function)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        # IMPORTANT: ctx is Click's native context object
        # Our application services are accessible via ctx.obj (AppContext)
        # Extract and remove common options from kwargs
        config = kwargs.pop('config', None)
        server = kwargs.pop('server', None)
        api_key = kwargs.pop('api_key', None)
        verbose = kwargs.pop('verbose', 0)
        quiet = kwargs.pop('quiet', False)
        output = kwargs.pop('output', None)
        no_color = kwargs.pop('no_color', False)
        no_progress = kwargs.pop('no_progress', False)
        debug = kwargs.pop('debug', False)
        
        # Initialize app context if needed
        if not hasattr(ctx, 'obj') or ctx.obj is None:
            ctx.obj = AppContext()
            
        # Update app context with option values
        ctx.obj.verbose = verbose
        ctx.obj.quiet = quiet
        ctx.obj.debug = debug
        
        # Initialize services if not already initialized
        if not ctx.obj.config_manager:
            ctx.obj.init_services(
                config_file=config,
                server_url=server,
                api_key=api_key,
                output_format=output,
                color_enabled=not no_color,
                progress_enabled=not no_progress
            )
            
            # Configure logging based on verbosity
            ctx.obj.configure_logging()
        
        # Call the original function with the updated context
        return function(ctx, *args, **kwargs)
    
    return cast(F, wrapper)

def api_command(function: CommandFunction) -> CommandFunction:
    """
    [Function intent]
    Mark a command as requiring API access and ensure API client is initialized.
    
    [Implementation details]
    Creates a decorator that initializes the API client before executing the command.
    Catches API initialization errors and handles them appropriately.
    
    [Design principles]
    Decorator pattern - separates API initialization from command logic.
    Fail-fast - immediately reports API-related errors.
    Composition - can be combined with other command decorators.
    
    Args:
        function: Click command function to decorate
        
    Returns:
        Decorated function with API initialization
    """
    @functools.wraps(function)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        # Initialize the API client if not already initialized
        if ctx.obj.api_client and not ctx.obj.api_client._initialized:
            try:
                ctx.obj.api_client.init_api_client()
            except ConfigurationError as e:
                ctx.obj.output_formatter.error(f"Configuration error: {e}")
                return 2
                
        # Call the original function
        return function(ctx, *args, **kwargs)
    
    return cast(CommandFunction, wrapper)

def catch_errors(function: CommandFunction) -> CommandFunction:
    """
    [Function intent]
    Catch and handle errors during command execution.
    
    [Implementation details]
    Creates a decorator that wraps command execution in a try-except block.
    Catches and handles common error types with appropriate messages and exit codes.
    
    [Design principles]
    Decorator pattern - separates error handling from command logic.
    Centralized error handling - ensures consistent handling across commands.
    Composition - can be combined with other command decorators.
    
    Args:
        function: Click command function to decorate
        
    Returns:
        Decorated function with error handling
    """
    @functools.wraps(function)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        try:
            return function(ctx, *args, **kwargs)
        except Exception as e:
            return ctx.obj.handle_error(e)
    
    return cast(CommandFunction, wrapper)
