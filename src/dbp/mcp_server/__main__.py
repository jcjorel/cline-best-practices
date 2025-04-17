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
# [Reference documentation]
# - src/dbp_cli/commands/server.py
# - src/dbp/mcp_server/component.py
# - src/dbp/mcp_server/server.py
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-17T17:17:45Z : Integrated with centralized application logging by CodeAssistant
# * Replaced local setup_logging with centralized setup_application_logging
# * Ensured consistent log formatting across all components
# 2025-04-17T17:05:00Z : Refactored to use centralized MillisecondFormatter by CodeAssistant
# * Updated to import MillisecondFormatter from core.log_utils
# * Removed duplicate formatter class definition to use shared implementation
# 2025-04-17T13:23:51Z : Fixed millisecond format in log timestamps by CodeAssistant
# * Added custom MillisecondFormatter class to display exactly 3 digits for milliseconds
# * Modified logging setup to use the custom formatter with all handlers
# * Fixed %f placeholder in logs that was displaying raw with 6 digits
# 2025-04-16T16:12:00Z : Added startup verification and restart functionality by CodeAssistant
# * Added support for creating startup signal file for reliable startup detection
# * Added health check capability with timeout for server verification
# * Improved error logging with rotating file handlers
# * Fixed code structure and indentation for better readability
###############################################################################

import argparse
import logging
import sys
import os
import time
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ..core.log_utils import setup_application_logging

def parse_arguments() -> argparse.Namespace:
    """
    [Function intent]
    Parse command-line arguments for the MCP server.
    
    [Implementation details]
    Sets up argument parser with options for host, port, logging, and startup verification.
    
    [Design principles]
    Provides sensible defaults while allowing customization.
    Includes options for startup verification to ensure server availability.
    """
    parser = argparse.ArgumentParser(description='MCP Server for Document-Based Programming')
    
    parser.add_argument('--host', type=str, default='localhost',
                        help='Host address to bind to')
    parser.add_argument('--port', type=int, default=6231,
                        help='Port number to listen on')
    parser.add_argument('--log-level', type=str, default='info',
                        choices=['debug', 'info', 'warning', 'error'],
                        help='Logging level')
    parser.add_argument('--log-file', type=str,
                        help='Path to log file')
    parser.add_argument('--startup-timeout', type=int, default=30,
                        help='Timeout in seconds to wait for server startup')
    parser.add_argument('--startup-check', action='store_true',
                        help='Perform health check after starting to verify server is responsive')
    
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
    args = parse_arguments()
    
    # Set up logging with optional file output
    log_file = Path(args.log_file) if args.log_file else \
               Path.home() / '.dbp' / 'logs' / 'mcp_server.log'
    
    # Use the centralized application logging setup
    setup_application_logging(args.log_level, log_file)
    logger = logging.getLogger('dbp.mcp_server.__main__')
    
    logger.info(f"Starting MCP server on {args.host}:{args.port}")
    logger.debug(f"Arguments: {args}")
    
    # Signal file to be used for startup indication
    startup_signal_file = Path.home() / '.dbp' / 'mcp_server_started'
    
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
                return 1
        except Exception as e:
            logger.critical(f"Error importing MCP server modules: {e}")
            logger.debug("Import error details:", exc_info=True)
            return 1
        
        # Use the LifecycleManager to handle component registration and initialization
        logger.info("Starting MCP server using LifecycleManager")
        try:
            from ..config.config_manager import ConfigurationManager
            from ..core.lifecycle import LifecycleManager
            
            # Create CLI args for the lifecycle manager
            cli_args = []
            
            # Set MCP server config values
            cli_args.append("--mcp-server.host=" + args.host)
            cli_args.append("--mcp-server.port=" + str(args.port))
            cli_args.append("--mcp-server.server-name=dbp-mcp-server")
            cli_args.append("--mcp-server.server-description=MCP Server for DBP")
            cli_args.append("--mcp-server.server-version=1.0.0")
            cli_args.append("--mcp-server.auth-enabled=false")
            
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
                    
                return 1
                
            logger.info("All components started successfully")
                
            # Access the MCP server component directly to start the server
            # (since LifecycleManager doesn't do that automatically)
            # Get the MCP server component from the system
            component = lifecycle.system.components.get("mcp_server")
            if not component:
                logger.critical("MCP server component not found in registry")
                return 1
            
            if not component.is_initialized:
                logger.critical("MCP server component was not properly initialized")
                return 1
            
            # Signal file to indicate successful startup
            try:
                with open(startup_signal_file, 'w') as f:
                    f.write(str(os.getpid()))
                logger.debug(f"Created startup signal file at {startup_signal_file}")
            except Exception as e:
                logger.warning(f"Failed to create startup signal file: {e}")

            # Perform health check if requested
            if args.startup_check:
                try:
                    import requests
                    from urllib.parse import urljoin
                    base_url = f"http://{args.host}:{args.port}"
                    
                    # Try to connect to the health endpoint
                    logger.info("Performing server health check...")
                    start_time = time.time()
                    while time.time() - start_time < args.startup_timeout:
                        try:
                            health_url = urljoin(base_url, "/health")
                            response = requests.get(health_url, timeout=2)
                            if response.status_code == 200:
                                logger.info("Server health check passed")
                                break
                        except Exception:
                            # Wait and retry
                            time.sleep(1)
                    else:
                        logger.warning("Server health check timed out, but continuing...")
                except Exception as e:
                    logger.warning(f"Health check setup failed: {e}")
            
            # Start the server (this should block until server exit)
            logger.info("Starting MCP server...")
            try:
                # Method is called start_server, not start
                component.start_server()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received.")
            except Exception as e:
                logger.critical(f"Failed during server execution: {e}", exc_info=True)
                return 1
            finally:
                # Clean up startup signal file
                if startup_signal_file.exists():
                    try:
                        startup_signal_file.unlink()
                        logger.debug("Removed startup signal file")
                    except Exception as e:
                        logger.warning(f"Failed to remove startup signal file: {e}")
                
                # Shutdown gracefully
                logger.info("Shutting down MCP server...")
                try:
                    lifecycle.shutdown()
                    logger.info("Lifecycle manager shutdown complete")
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
        
        except AttributeError as e:
            logger.critical(f"Method not found on component: {e}")
            logger.debug("This suggests the component API doesn't match what __main__.py expects", exc_info=True)
            return 1
        
        logger.info("MCP server shutting down normally")
        return 0
        
    except ImportError as e:
        logger.critical(f"Failed to import required modules: {e}")
        logger.debug(f"Import error details:", exc_info=True)
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
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
