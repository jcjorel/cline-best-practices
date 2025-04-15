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
# 2025-04-15T16:37:00Z : Created __main__.py file by CodeAssistant
# * Implemented entry point for MCP server module with detailed logging
###############################################################################

import argparse
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Configure logging to file for better diagnostics
def setup_logging(log_level: str, log_file: Optional[Path] = None) -> None:
    """
    Set up logging configuration with optional file output.

    Args:
        log_level: Logging level (debug, info, warning, error)
        log_file: Optional path to log file
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    
    if log_file:
        # Ensure directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, mode='a'))
    
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=handlers
    )
    
    # Set more verbose logging for specific modules during startup
    logging.getLogger('dbp.mcp_server').setLevel(numeric_level)
    logging.getLogger('dbp.core').setLevel(numeric_level)

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
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
    
    return parser.parse_args()

def main() -> int:
    """
    Main entry point for the MCP server.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    args = parse_arguments()
    
    # Set up logging with optional file output
    log_file = Path(args.log_file) if args.log_file else \
               Path.home() / '.dbp' / 'logs' / 'mcp_server.log'
    
    setup_logging(args.log_level, log_file)
    logger = logging.getLogger('dbp.mcp_server.__main__')
    
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
                    AnalyzeDocumentConsistencyTool, GenerateRecommendationsTool, 
                    ApplyRecommendationTool, GeneralQueryTool
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
        
        # Create and start the component
        logger.info("Initializing MCPServerComponent")
        try:
            component = MCPServerComponent()
            
            # Use proper component initialization pattern for consistency
            from ..core.registry import ComponentRegistry
            from ..core.component import InitializationContext
            from ..config.config_manager import ConfigurationManager
            from ..config.component import ConfigManagerComponent
            
            # Create the registry for component management
            registry = ComponentRegistry()
            
            # Get the ConfigurationManager singleton and initialize it
            config_manager = ConfigurationManager()
            config_manager.initialize()  # Initialize with default settings
            
            # Set MCP server config values
            config_manager.set("mcp_server.host", args.host)
            config_manager.set("mcp_server.port", args.port)
            config_manager.set("mcp_server.server_name", "dbp-mcp-server")
            config_manager.set("mcp_server.server_description", "MCP Server for DBP")
            config_manager.set("mcp_server.server_version", "1.0.0")
            config_manager.set("mcp_server.auth_enabled", False)
            
            # Register the config_manager component
            registry.register(ConfigManagerComponent(config_manager))
            
            # Create the initialization context with proper registry
            context = InitializationContext(
                logger=logger.getChild("component"),
                config=config_manager.as_dict(),
                component_registry=registry,
                resolver=None
            )
            
            # Initialize the component
            logger.info("Starting MCPServerComponent")
            component.initialize(context)
            
            # Run the server (this should block until server exit)
            logger.info("Starting MCP server...")
            component.start_server()  # Method is called start_server, not start
            
            # Keep the main thread alive
            logger.info("Server running. Press Ctrl+C to stop.")
            import signal
            
            def handle_signal(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                component.stop_server()
                component.shutdown()
                sys.exit(0)
                
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
            
            # Keep process alive
            while True:
                signal.pause()
                
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
