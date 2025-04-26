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
# Main entry point for the MCP server. This file is responsible for initializing
# the MCP server component and waiting for the server to exit.
###############################################################################
# [Source file design principles]
# - Simple entry point for the MCP server
# - Handles command-line arguments
# - Initializes the MCP server component
# - Waits for the server to exit
# - Provides clean shutdown handling
###############################################################################
# [Source file constraints]
# - Must initialize the MCP server component
# - Must wait for the server to exit
# - Must handle clean shutdown
###############################################################################
# [Dependencies]
# codebase:- src/dbp/core/system.py
# codebase:- src/dbp/mcp_server/component.py
# system:- argparse
# system:- logging
# system:- signal
# system:- sys
###############################################################################
# [GenAI tool change history]
# 2025-04-27T00:08:00Z : Created sample implementation for __main__.py by CodeAssistant
# * Updated to use wait_for_server_exit() instead of start_server()
# * Added signal handling for clean shutdown
# * Added command-line argument parsing
###############################################################################

import argparse
import logging
import signal
import sys
from typing import Optional

# Import system and component
from ..core.system import System
from .component import MCPServerComponent

logger = logging.getLogger(__name__)

def parse_args():
    """
    [Function intent]
    Parse command-line arguments for the MCP server.
    
    [Design principles]
    - Simple argument parsing
    - Provides help and version information
    
    [Implementation details]
    - Uses argparse for argument parsing
    - Provides help and version information
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--log-level", help="Log level", default="INFO")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    return parser.parse_args()

def setup_logging(log_level: str):
    """
    [Function intent]
    Set up logging for the MCP server.
    
    [Design principles]
    - Simple logging setup
    - Configurable log level
    
    [Implementation details]
    - Sets up logging with the specified log level
    - Configures log format
    
    Args:
        log_level: Log level to use
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def setup_signal_handlers(system: System):
    """
    [Function intent]
    Set up signal handlers for clean shutdown.
    
    [Design principles]
    - Clean shutdown handling
    - Handles common signals
    
    [Implementation details]
    - Sets up signal handlers for SIGINT and SIGTERM
    - Calls system.shutdown() when a signal is received
    
    Args:
        system: System instance
    """
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        system.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """
    [Function intent]
    Main entry point for the MCP server.
    
    [Design principles]
    - Simple entry point
    - Handles initialization and shutdown
    
    [Implementation details]
    - Parses command-line arguments
    - Sets up logging
    - Initializes the system
    - Initializes the MCP server component
    - Waits for the server to exit
    - Handles clean shutdown
    
    Returns:
        int: Exit code
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Initialize the system
    system = System()
    
    # Set up signal handlers
    setup_signal_handlers(system)
    
    try:
        # Initialize the system
        system.initialize(config_file=args.config)
        
        # Get the MCP server component
        mcp_server = system.get_component("mcp_server")
        if not mcp_server:
            logger.error("MCP server component not found")
            return 1
        
        # Wait for the server to exit
        # This replaces the previous call to mcp_server.start_server()
        mcp_server.wait_for_server_exit()
        
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        system.shutdown()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        system.shutdown()
        return 1

if __name__ == "__main__":
    sys.exit(main())
