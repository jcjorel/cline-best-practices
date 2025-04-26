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
# Entry point for running the MCP server module directly. Parses command-line
# arguments, sets up logging, initializes components, and starts the server.
# This file is executed when the module is run with python -m dbp.mcp_server.
###############################################################################
# [Source file design principles]
# - Provides a clean entry point for the MCP server.
# - Processes command-line arguments for server configuration.
# - Sets up proper logging with configurable verbosity.
# - Initializes the server component and handles lifecycle.
# - Implements comprehensive error handling and detailed reporting.
# - Acts as a bridge between CLI and the actual MCP server implementation.
###############################################################################
# [Source file constraints]
# - Must work with the existing server implementation and component model.
# - Logging must be properly configured before server initialization.
# - Error handling must be detailed enough to diagnose startup issues.
# - Exit codes must be meaningful for the calling process.
###############################################################################
# [Dependencies]
# other:- src/dbp_cli/commands/server.py
# other:- src/dbp/mcp_server/component.py
# other:- src/dbp/mcp_server/server.py
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T15:21:00Z : Removed file-based startup signal mechanism by CodeAssistant
# * Removed all logic that creates and manages startup signal files
# * Server status is now detected solely through health API checks
# * Simplified server startup process to eliminate file-based coordination
# * Improved reliability by removing file operation dependencies
# 2025-04-25T15:15:00Z : Fixed missing keep_alive import causing startup failure by CodeAssistant
# * Added explicit import for keep_alive() function in main() method
# * Fixed UnboundLocalError during server startup
# * Ensured proper watchdog operation during initialization
# 2025-04-25T14:48:00Z : Modified watchdog behavior to disable after successful component initialization by CodeAssistant
# * Changed watchdog to stop after all components have started successfully
# * Removed the always-active watchdog behavior that was causing false triggers
# * Improved log message to clearly indicate watchdog is being disabled
# * Fixed the deadlock detection issue that occurred after all components started
# 2025-04-20T19:23:00Z : Fixed watchdog deadlock detection by CodeAssistant
# * Modified watchdog behavior to remain active during application lifetime
# * Removed code that was stopping watchdog after component initialization
# * Ensured watchdog can detect deadlocks in all operations including Alembic migrations 
# * Added detailed logging for watchdog status changes
# 2025-04-20T10:53:00Z : Moved watchdog implementation to dedicated core module by CodeAssistant
# * Extracted watchdog functionality to src/dbp/core/watchdog.py
# * Implemented watchdog with condition variables for better responsiveness
# * Updated imports in __main__.py to use the new watchdog module
# * Removed duplicate code to improve maintainability
# 2025-04-20T03:52:00Z : Fixed startup timeout parameter to use configuration values by CodeAssistant
# * Modified parse_arguments() to get default values from ConfigurationManager
# * Added strict exception handling for configuration access
# * Made default argument values consistent with system-wide configuration
# * Improved help text to show correct default values from configuration
###############################################################################

import argparse
import logging
import sys
import os
import time
import signal
import traceback
import inspect
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ..core.log_utils import setup_application_logging, get_formatted_logger, MillisecondFormatter
from ..core.watchdog import keep_alive, start_watchdog, stop_watchdog, setup_watchdog_for_exit_handler
from ..config.default_config import INITIALIZATION_DEFAULTS

# Global logger
logger = None

# Track the exit source
exit_source = None
exit_reason = None
exit_traceback = None

def exit_handler(signum=None, frame=None, reason=None, source=None, exception=None):
    """
    [Function intent]
    Handles server exit events with detailed tracking of exit source and reason.
    
    [Implementation details]
    Captures detailed information about what part of the application requested server exit,
    including stack trace information. Records the exit source, reason, and traceback
    for improved diagnostics and troubleshooting.
    
    [Design principles]
    Comprehensive exit tracking regardless of termination source.
    Centralized exit handling for both signal-based and programmatic exits.
    
    Args:
        signum: Signal number if triggered by a signal handler
        frame: Current stack frame if triggered by a signal handler
        reason: Explicit reason for exit
        source: Component or function that triggered the exit
        exception: Exception that caused the exit, if any
    """
    global logger, exit_source, exit_reason, exit_traceback
    
    if not logger:
        # Ensure we have a logger even if called before setup
        # Use get_formatted_logger to ensure proper formatting with consistent width for level names
        logger = get_formatted_logger('dbp.mcp_server.exit_handler', logging.INFO)
    
    # Determine exit source
    if source is None:
        # If source not provided, try to determine from call stack
        caller_info = []
        
        if frame is not None:
            # We got a stack frame from signal handler
            frame_info = inspect.getframeinfo(frame)
            caller_info.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
        else:
            # Walk up the call stack to find information
            caller_frame = inspect.currentframe().f_back
            depth = 0
            max_depth = 5  # Limit the stack trace depth
            
            while caller_frame and depth < max_depth:
                frame_info = inspect.getframeinfo(caller_frame)
                module_name = caller_frame.f_globals.get('__name__', 'unknown')
                caller_info.append(f"{module_name}.{frame_info.function} at {frame_info.filename}:{frame_info.lineno}")
                caller_frame = caller_frame.f_back
                depth += 1
                
        source = " -> ".join(caller_info) if caller_info else "unknown"
    
    # Determine exit reason
    if reason is None:
        if signum is not None:
            try:
                signal_name = signal.Signals(signum).name
                reason = f"Signal received: {signal_name} ({signum})"
            except (ValueError, AttributeError):
                reason = f"Signal received: {signum}"
        elif exception is not None:
            reason = f"Exception: {type(exception).__name__}: {str(exception)}"
        else:
            reason = "Unknown reason"
    
    # Capture detailed traceback information
    if exit_traceback is None:  # Only capture the first traceback if multiple calls
        if exception is not None:
            exit_traceback = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
        else:
            exit_traceback = ''.join(traceback.format_stack())
    
    # Store exit information globally
    exit_source = source
    exit_reason = reason
    
    # Log the exit information
    logger.warning(f"Server exit detected")
    logger.warning(f"Exit source: {exit_source}")
    logger.warning(f"Exit reason: {exit_reason}")
    
    if exit_traceback:
        logger.debug(f"Exit traceback:\n{exit_traceback}")
    
    # For signal handlers, we need to re-raise the signal after logging
    if signum is not None:
        # Restore default signal handler to avoid infinite recursion
        signal.signal(signum, signal.SIG_DFL)
        # Re-raise the signal against the process
        os.kill(os.getpid(), signum)

def setup_exit_handlers(watchdog_timeout=60):
    """
    [Function intent]
    Sets up signal handlers to track all possible exit sources and starts the watchdog.
    
    [Implementation details]
    Registers the exit_handler function for various termination signals
    to ensure all exits are properly tracked and logged.
    Also starts the watchdog thread to detect deadlocked processes.
    
    [Design principles]
    Comprehensive signal handling for improved diagnostics.
    Proactive deadlock detection with automatic recovery.
    
    Args:
        watchdog_timeout: Seconds to wait for keep_alive before considering process stuck
    """
    # Register for standard termination signals
    for sig in [signal.SIGTERM, signal.SIGINT]:
        try:
            signal.signal(sig, exit_handler)
            logger.debug(f"Registered exit handler for signal {sig}")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not register handler for signal {sig}: {e}")
    
    # Register for other signals if available on this platform
    platform_signals = []
    
    # Common Unix signals
    for sig_name in ['SIGHUP', 'SIGQUIT', 'SIGABRT', 'SIGUSR1', 'SIGUSR2']:
        if hasattr(signal, sig_name):
            sig = getattr(signal, sig_name)
            platform_signals.append(sig)
    
    for sig in platform_signals:
        try:
            signal.signal(sig, exit_handler)
            logger.debug(f"Registered exit handler for platform signal {sig}")
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not register handler for signal {sig}: {e}")
    
    # Register with sys.excepthook to catch unhandled exceptions
    original_excepthook = sys.excepthook
    
    def exception_exit_handler(exc_type, exc_value, exc_traceback):
        exit_handler(reason=f"Unhandled exception: {exc_type.__name__}", 
                    exception=exc_value)
        # Call the original excepthook
        original_excepthook(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_exit_handler
    logger.debug("Registered exit handler for unhandled exceptions")
    
    # Register with atexit to catch normal process termination
    import atexit
    atexit.register(lambda: exit_handler(reason="Process exit via atexit", 
                                        source="Python interpreter shutdown"))
    logger.debug("Registered exit handler for normal process termination")
    
    # Start the watchdog with the specified timeout and our exit handler
    setup_watchdog_for_exit_handler(timeout=watchdog_timeout, exit_handler_func=exit_handler)

def parse_arguments() -> argparse.Namespace:
    """
    [Function intent]
    Parse command-line arguments for the MCP server.
    
    [Implementation details]
    Sets up argument parser with options for host, port, logging, startup verification,
    and watchdog functionality for deadlock detection. Gets default values from
    ConfigurationManager to ensure consistency with system configuration.
    
    [Design principles]
    Requires ConfigurationManager for default values to ensure configuration consistency.
    Provides consistent command line interface for server settings.
    Throws exception if configuration values cannot be retrieved.
    
    Raises:
        RuntimeError: If default values cannot be retrieved from ConfigurationManager
    """
    # Get default values from ConfigurationManager - throw if unavailable
    try:
        from ..config.config_manager import ConfigurationManager
        config_mgr = ConfigurationManager()
        
        # Initialize ConfigurationManager if not already initialized
        if not config_mgr.initialized_flag:
            config_mgr.initialize()
            
        typed_config = config_mgr.get_typed_config()
        
        # Get default values from configuration
        watchdog_timeout = typed_config.initialization.watchdog_timeout
        server_host = typed_config.mcp_server.host
        server_port = typed_config.mcp_server.port
        
    except Exception as e:
        error_msg = f"Failed to get default values from ConfigurationManager: {str(e)}"
        # If logger is initialized, log the error
        if 'logger' in globals() and logger is not None:
            logger.critical(error_msg)
        # Always raise the exception
        raise RuntimeError(error_msg) from e
    
    parser = argparse.ArgumentParser(description='MCP Server for Document-Based Programming')
    
    parser.add_argument('--host', type=str, default=server_host,
                        help=f'Host address to bind to (default: {server_host})')
    parser.add_argument('--port', type=int, default=server_port,
                        help=f'Port number to listen on (default: {server_port})')
    parser.add_argument('--log-level', type=str, default='info',
                        choices=['debug', 'info', 'warning', 'error'],
                        help='Logging level')
    parser.add_argument('--log-file', type=str,
                        help='Path to log file')
    parser.add_argument('--startup-timeout', type=int, default=typed_config.initialization.timeout_seconds,
                        help=f'Timeout in seconds to wait for server startup (default: {typed_config.initialization.timeout_seconds})')
    parser.add_argument('--watchdog-timeout', type=int, default=watchdog_timeout,
                        help=f'Watchdog timeout in seconds (default: {watchdog_timeout})')
    
    return parser.parse_args()

def main() -> int:
    """
    [Function intent]
    Main entry point for the MCP server.
    
    [Implementation details]
    Orchestrates the server startup sequence: parses arguments, sets up logging,
    initializes components via LifecycleManager, and starts the server.
    Creates a startup signal file for external process coordination.
    Optionally performs health checks to verify server responsiveness.
    
    [Design principles]
    Progressive initialization with detailed error reporting at each step.
    Coordinated startup signaling for external monitoring.
    Graceful shutdown with proper resource cleanup.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    global logger
    args = parse_arguments()
    
    # Set up logging with optional file output
    log_file = Path(args.log_file) if args.log_file else \
               Path.home() / '.dbp' / 'logs' / 'mcp_server.log'
    
    # Use the centralized application logging setup
    setup_application_logging(args.log_level, log_file)
    logger = logging.getLogger('dbp.mcp_server.__main__')
    
    # Get watchdog timeout from configuration if available
    watchdog_timeout = args.watchdog_timeout
    
    try:
        # Try to get timeout from ConfigurationManager if it's already instantiated
        from ..config.config_manager import ConfigurationManager
        config_mgr = ConfigurationManager()
        if hasattr(config_mgr, '_config') and config_mgr._config:
            typed_config = config_mgr.get_typed_config()
            if typed_config and typed_config.initialization and typed_config.initialization.watchdog_timeout:
                # Use timeout from configuration if available
                watchdog_timeout = typed_config.initialization.watchdog_timeout
                logger.debug(f"Using watchdog timeout from configuration: {watchdog_timeout}s")
    except Exception as e:
        # Fall back to command line argument if configuration is not available
        logger.debug(f"Could not get watchdog timeout from configuration, using CLI argument: {e}")
    
    # Set up exit handlers and watchdog as early as possible
    setup_exit_handlers(watchdog_timeout=watchdog_timeout)
    
    # Record initial keepalive
    from ..core.watchdog import keep_alive
    keep_alive()
    
    logger.info(f"Starting MCP server on {args.host}:{args.port}")
    logger.debug(f"Arguments: {args}")
    
    try:
        # Import here to avoid circular imports
        from .component import MCPServerComponent
        
        # Log import status and available components
        logger.debug("Successfully imported MCPServerComponent")
        
        # Log environment information
        env_info = {
            "Python version": sys.version,
            "Working directory": os.getcwd(),
            "Module path": __file__,
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", "")
        }
        logger.debug(f"Environment: {env_info}")
        
        # Import system dependencies to check for errors
        try:
            import fastapi
            import uvicorn
            logger.debug(f"FastAPI version: {fastapi.__version__}")
            logger.debug(f"Uvicorn available: {uvicorn.__name__}")
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            exit_handler(reason="Missing dependency", exception=e)
            return 1
            
        # Try importing module files to check for potential issues
        logger.info("Checking component dependencies and imports...")
        
        # Check for required modules that might be missing
        try:
            import fastapi
            import uvicorn
            logger.info(f"FastAPI version: {fastapi.__version__}")
            logger.info(f"Uvicorn available: {uvicorn.__name__}")
        except ImportError as e:
            logger.critical(f"Required dependency missing: {e}")
            logger.info("Please install missing dependencies with: pip install fastapi uvicorn")
            exit_handler(reason="Required dependency missing", exception=e)
            return 1
        
        # Check if tool and resource modules exist
        try:
            try:
                from .tools import (
                    GeneralQueryTool, CommitMessageTool
                )
                logger.debug("Successfully imported tool classes")
            except ImportError as e:
                logger.critical(f"Failed to import tool classes: {e}")
                logger.info("MCP server tools may not be fully implemented yet")
                exit_handler(reason="Failed to import tool classes", exception=e)
                return 1
                
            try:
                from .resources import (
                    DocumentationResource, CodeMetadataResource, 
                    InconsistencyResource, RecommendationResource
                )
                logger.debug("Successfully imported resource classes")
            except ImportError as e:
                logger.critical(f"Failed to import resource classes: {e}")
                logger.info("MCP server resources may not be fully implemented yet")
                exit_handler(reason="Failed to import resource classes", exception=e)
                return 1
        except Exception as e:
            logger.critical(f"Error importing MCP server modules: {e}")
            logger.debug("Import error details:", exc_info=True)
            exit_handler(reason="Error importing MCP server modules", exception=e)
            return 1
        
        # Use the LifecycleManager to handle component registration and initialization
        logger.info("Starting MCP server using LifecycleManager")
        try:
            from ..config.config_manager import ConfigurationManager
            from ..core.lifecycle import LifecycleManager
            
            # Create CLI args for the lifecycle manager
            cli_args = []
            
            
            # Create and initialize the lifecycle manager
            lifecycle = LifecycleManager(cli_args)
            
            # Start all components (which will register MCPServerComponent)
            if not lifecycle.start():
                logger.critical("Failed to start components")
                
                # Collect detailed component diagnostic information
                failed_components = []
                try:
                    for name, component in lifecycle.system.components.items():
                        if not component.is_initialized:
                            debug_info = component.get_debug_info() if hasattr(component, 'get_debug_info') else {}
                            failed_components.append({
                                'name': name, 
                                'info': debug_info
                            })
                            
                            # Get detailed error information if available
                            if hasattr(component, 'get_error_details'):
                                error_details = component.get_error_details()
                                if error_details:
                                    logger.critical(f"Component '{name}' failure details:")
                                    for key, value in error_details.items():
                                        logger.critical(f"  {key}: {value}")
                except Exception as debug_err:
                    logger.error(f"Error collecting diagnostic information: {debug_err}")
                    
                if failed_components:
                    logger.critical(f"Components that failed to initialize: {[c['name'] for c in failed_components]}")
                    
                exit_handler(reason="Failed to start components", source="LifecycleManager.start()")
                return 1
                
            logger.info("All components started successfully")

            # Component initialization is complete
            logger.info("Component initialization completed successfully")

            # Disable the watchdog now that all components have started successfully
            from ..core.watchdog import stop_watchdog
            stop_watchdog()
            logger.info("Watchdog disabled after successful component initialization")
                
            # Access the MCP server component directly to start the server
            # (since LifecycleManager doesn't do that automatically)
            # Get the MCP server component from the system
            component = lifecycle.system.components.get("mcp_server")
            if not component:
                logger.critical("MCP server component not found in registry")
                exit_handler(reason="MCP server component not found", source="Component registry lookup")
                return 1
            
            if not component.is_initialized:
                logger.critical("MCP server component was not properly initialized")
                exit_handler(reason="MCP server component not initialized", source="Component initialization check")
                return 1
            
            
            # Wait for the server to exit (this should block until server exit)
            logger.info("Starting MCP server...")
            try:
                component.wait_for_server_exit()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received.")
                exit_handler(reason="Keyboard interrupt (SIGINT)", source="KeyboardInterrupt handler")
            except Exception as e:
                logger.critical(f"Failed during server execution: {e}", exc_info=True)
                exit_handler(reason="Failed during server execution", exception=e, source="MCP server execution")
                return 1
            finally:
                # Shutdown gracefully
                logger.info("Shutting down MCP server...")
                try:
                    # Re-enable watchdog for shutdown process to detect potential deadlocks
                    from ..core.watchdog import start_watchdog, keep_alive
                    watchdog_timeout = args.watchdog_timeout
                    start_watchdog(timeout=watchdog_timeout, exit_handler=exit_handler)
                    logger.info(f"Watchdog reactivated with {watchdog_timeout}s timeout for shutdown process")
                    keep_alive()  # Initialize keepalive for shutdown
                    
                    # Perform shutdown
                    lifecycle.shutdown()
                    logger.info("Lifecycle manager shutdown complete")
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
                    exit_handler(reason="Error during shutdown", exception=e, source="lifecycle.shutdown()")
        
        except AttributeError as e:
            logger.critical(f"Method not found on component: {e}")
            logger.debug("This suggests the component API doesn't match what __main__.py expects", exc_info=True)
            exit_handler(reason="Method not found on component", exception=e)
            return 1
        
        logger.info("MCP server shutting down normally")
        # Log the exit source and reason if available
        if exit_source and exit_reason:
            logger.info(f"Server exit triggered by: {exit_source}")
            logger.info(f"Server exit reason: {exit_reason}")
        else:
            # If we got here without exit_source being set, it's a normal exit
            exit_handler(reason="Normal server shutdown", source="main() completion")
            
        return 0
        
    except ImportError as e:
        logger.critical(f"Failed to import required modules: {e}")
        logger.debug(f"Import error details:", exc_info=True)
        exit_handler(reason="Failed to import required modules", exception=e)
        return 1
    except Exception as e:
        logger.critical(f"Failed to start MCP server: {e}")
        
        # Log detailed exception information
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.critical("Detailed exception information:")
        
        tb_formatted = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in tb_formatted:
            logger.critical(line.rstrip())
            
        # Log variables that might be useful for debugging
        frame = traceback.extract_tb(exc_traceback)[-1]
        logger.critical(f"Error location: {frame.filename}:{frame.lineno} in {frame.name}")
        
        exit_handler(reason="Failed to start MCP server", exception=e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
