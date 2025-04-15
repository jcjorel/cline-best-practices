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
# Implements the ServerCommandHandler for the 'server' CLI command, which allows
# users to start, stop, and manage the MCP server instance directly from the
# command line. This simplifies the workflow by avoiding the need to manually
# start the server in a separate terminal.
###############################################################################
# [Source file design principles]
# - Extends the BaseCommandHandler to implement the 'server' command.
# - Uses subprocess to start the MCP server in a background process.
# - Provides options to start, stop, restart, and check status of the server.
# - Supports customization of host, port, and other server parameters.
# - Maintains an easily discoverable interface for server management.
###############################################################################
# [Source file constraints]
# - Requires Python's subprocess module for process management.
# - Server processes started in background mode need proper cleanup.
# - PID tracking is used to manage server processes.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
# - src/dbp_cli/commands/base.py
# - src/dbp_cli/commands/status.py
# - src/dbp/mcp_server/server.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T14:50:00Z : Initial creation of ServerCommandHandler by CodeAssistant
# * Implemented command handler for MCP server management
# 2025-04-15T23:54:09Z : Fixed context manager issue in _check_status method by CodeAssistant
# * Changed incorrect usage of progress.start() with 'with' statement to using the with_progress helper method
###############################################################################

import argparse
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from .base import BaseCommandHandler
from ..exceptions import CommandError, ConnectionError

logger = logging.getLogger(__name__)

class ServerCommandHandler(BaseCommandHandler):
    """
    [Class intent]
    Handles the 'server' command for managing the MCP server, enabling users to
    start, stop, restart, and check the status of the server directly from the CLI.
    
    [Implementation details]
    Manages server processes using Python's subprocess module, tracks server state
    using PID files, and provides various configuration options for server startup.
    Implements server management operations through subcommands (start, stop, restart, status)
    with appropriate options for each operation.
    
    [Design principles]
    Process isolation - runs server in separate background or foreground processes.
    Persistent state tracking - uses PID files to track server processes across CLI invocations.
    Environment verification - checks port availability and other system conditions.
    Clean resource management - ensures processes are properly terminated and resources released.
    """
    
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 6231
    PID_FILE = Path.home() / ".dbp" / "mcp_server.pid"
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        [Function intent]
        Configure the argument parser with options specific to MCP server management.
        
        [Implementation details]
        Creates a subparser for server actions (start, stop, restart, status) and
        configures each with appropriate options. Default values are defined as class
        constants for consistency.
        
        [Design principles]
        Command pattern - each action is a distinct subcommand with specific options.
        Consistent defaults - uses class constants to ensure consistent default values.
        User-friendly defaults - provides reasonable defaults for all parameters.
        
        Args:
            parser: The argparse parser to add arguments to
        """
        subparsers = parser.add_subparsers(dest="action", help="Server action")
        
        # Start command
        start_parser = subparsers.add_parser("start", help="Start the MCP server")
        start_parser.add_argument("--host", default=self.DEFAULT_HOST, help="Host address to bind to")
        start_parser.add_argument("--port", type=int, default=self.DEFAULT_PORT, help="Port to listen on")
        start_parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (blocking)")
        start_parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Logging level")
        
        # Stop command
        stop_parser = subparsers.add_parser("stop", help="Stop the MCP server")
        stop_parser.add_argument("--timeout", type=int, default=5, help="Timeout (seconds) when waiting for the server to stop")
        
        # Restart command
        restart_parser = subparsers.add_parser("restart", help="Restart the MCP server")
        restart_parser.add_argument("--host", default=self.DEFAULT_HOST, help="Host address to bind to")
        restart_parser.add_argument("--port", type=int, default=self.DEFAULT_PORT, help="Port to listen on")
        restart_parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (blocking)")
        restart_parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Logging level")
        restart_parser.add_argument("--timeout", type=int, default=5, help="Timeout (seconds) when waiting for the server to stop")
        
        # Status command
        subparsers.add_parser("status", help="Check MCP server status")
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Execute the appropriate server management action based on command arguments.
        
        [Implementation details]
        Dispatches to the appropriate method based on the action argument:
        - start: Start the MCP server
        - stop: Stop the MCP server
        - restart: Restart the MCP server
        - status: Check MCP server status
        Handles errors from all operations and provides appropriate exit codes.
        
        [Design principles]
        Command routing - uses the action argument to route to the appropriate handler method.
        Consistent error handling - catches and reports all exceptions in a user-friendly way.
        Standard exit codes - returns 0 for success, 1 for errors.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Default to status if no action specified
        if not args.action:
            self.output.error("No server action specified")
            self.output.info("Available actions: start, stop, restart, status")
            return 1
        
        try:
            if args.action == "start":
                return self._start_server(args)
            elif args.action == "stop":
                return self._stop_server(args)
            elif args.action == "restart":
                return self._restart_server(args)
            elif args.action == "status":
                return self._check_status(args)
            else:
                self.output.error(f"Unknown server action: {args.action}")
                return 1
        except Exception as e:
            self.output.error(f"Failed to {args.action} server: {e}")
            logger.exception(f"Server {args.action} error", exc_info=True)
            return 1
    
    def _start_server(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Start the MCP server as a background or foreground process.
        
        [Implementation details]
        Checks if the server is already running by examining the PID file.
        Verifies port availability before attempting to start the server.
        Starts the server either in foreground (blocking) or background mode based on args.
        In background mode, saves the PID for later management and verification.
        
        [Design principles]
        Resource validation - checks port availability before starting.
        Idempotent operation - handles already-running case gracefully.
        Process isolation - runs server in a separate process with proper input/output handling.
        
        Args:
            args: Command arguments containing host, port, foreground flag, and log level
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        # Check if already running
        pid = self._get_server_pid()
        if pid is not None:
            if self._is_process_running(pid):
                self.output.error(f"MCP server is already running (PID: {pid})")
                return 1
            else:
                # Stale PID file
                logger.debug(f"Removing stale PID file (PID: {pid} not found)")
                self._clear_pid_file()
        
        # Prepare directory for PID file
        self.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Check port availability
        if not self._is_port_available(args.host, args.port):
            self.output.error(f"Port {args.port} is already in use on {args.host}")
            return 1
        
        # Start the server
        self.output.info(f"Starting MCP server on {args.host}:{args.port}...")
        
        cmd = [
            sys.executable, "-m", "dbp.mcp_server",
            "--host", args.host,
            "--port", str(args.port),
            "--log-level", args.log_level
        ]
        
        try:
            if args.foreground:
                # Run in foreground (blocking)
                self.output.info("Running server in foreground (press Ctrl+C to stop)...")
                subprocess.run(cmd, check=True)
                return 0
            else:
                # Create log directory and files for server output
                logs_dir = Path.home() / ".dbp" / "logs"
                logs_dir.mkdir(parents=True, exist_ok=True)
                stdout_log = logs_dir / "mcp_server_stdout.log"
                stderr_log = logs_dir / "mcp_server_stderr.log"
                
                logger.debug(f"Starting server with command: {cmd}")
                logger.debug(f"Redirecting output to: {stdout_log} and {stderr_log}")
                
                # Run in background with output captured to log files
                with open(stdout_log, "a") as stdout_file, open(stderr_log, "a") as stderr_file:
                    # Add timestamp to logs
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    stdout_file.write(f"\n\n--- SERVER START ATTEMPT AT {timestamp} ---\n\n")
                    stderr_file.write(f"\n\n--- SERVER START ATTEMPT AT {timestamp} ---\n\n")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        start_new_session=True
                    )
                
                # Store PID for later management
                with open(self.PID_FILE, "w") as f:
                    f.write(str(process.pid))
                
                # Wait briefly and check if process is still running
                time.sleep(1)
                if process.poll() is not None:
                    # Server failed to start, read error logs
                    self.output.error(f"Server failed to start (exit code: {process.returncode})")
                    
                    # Try to read recent error logs
                    try:
                        with open(stderr_log, "r") as f:
                            # Read last 20 lines
                            lines = f.readlines()[-20:]
                            if lines:
                                self.output.error("Recent server error log:")
                                for line in lines:
                                    self.output.error(f"  {line.strip()}")
                    except Exception as e:
                        logger.error(f"Failed to read error log: {e}")
                    
                    self.output.info(f"Full server logs available at:")
                    self.output.info(f"  - Stdout: {stdout_log}")
                    self.output.info(f"  - Stderr: {stderr_log}")
                    return 1
                
                self.output.success(f"MCP server started (PID: {process.pid})")
                self.output.info(f"Server logs available at:")
                self.output.info(f"  - Stdout: {stdout_log}")
                self.output.info(f"  - Stderr: {stderr_log}")
                self.output.info("Use 'dbp server stop' to stop the server")
                return 0
        
        except subprocess.CalledProcessError as e:
            self.output.error(f"Failed to start server: {e}")
            return 1
    
    def _stop_server(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Stop a running MCP server gracefully or forcefully if needed.
        
        [Implementation details]
        Retrieves the server PID from the PID file and validates it's running.
        Sends SIGTERM to gracefully stop the server, with timeout monitoring.
        If graceful stop fails, sends SIGKILL for forced termination.
        Cleans up the PID file after successful termination.
        
        [Design principles]
        Progressive escalation - tries graceful termination first, then forced.
        Resource cleanup - removes PID file after server termination.
        Fail-safe operation - handles cases where process is already gone.
        
        Args:
            args: Command arguments containing timeout value
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        pid = self._get_server_pid()
        if pid is None:
            self.output.error("No running MCP server found")
            return 1
        
        if not self._is_process_running(pid):
            self.output.info(f"Removing stale PID file (PID: {pid} not found)")
            self._clear_pid_file()
            return 0
        
        # Send SIGTERM to gracefully stop the server
        self.output.info(f"Stopping MCP server (PID: {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to exit
            start_time = time.time()
            while self._is_process_running(pid):
                if time.time() - start_time > args.timeout:
                    self.output.warning(f"Timed out waiting for server to stop, sending SIGKILL...")
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Already gone
                    break
                time.sleep(0.1)
            
            # Clean up PID file
            self._clear_pid_file()
            
            self.output.success("MCP server stopped successfully")
            return 0
            
        except ProcessLookupError:
            self.output.info("Process not found, cleaning up PID file")
            self._clear_pid_file()
            return 0
        except PermissionError:
            self.output.error(f"Permission denied when trying to stop PID {pid}")
            return 1
    
    def _restart_server(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Restart the MCP server with potentially new configuration settings.
        
        [Implementation details]
        Stops any running instance of the server using _stop_server.
        Waits briefly to ensure complete shutdown and port release.
        Starts a new server instance with the provided arguments using _start_server.
        
        [Design principles]
        Composition - reuses _stop_server and _start_server methods.
        Safety delay - waits between stop and start to ensure clean restart.
        
        Args:
            args: Command arguments containing host, port, foreground flag, log level, and timeout
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        self.output.info("Restarting MCP server...")
        
        # Stop the server if it's running
        stop_args = argparse.Namespace()
        stop_args.timeout = args.timeout
        self._stop_server(stop_args)
        
        # Give it a moment to fully shut down
        time.sleep(1)
        
        # Start with new settings
        start_args = argparse.Namespace()
        start_args.host = args.host
        start_args.port = args.port
        start_args.foreground = args.foreground
        start_args.log_level = args.log_level
        return self._start_server(start_args)
    
    def _check_status(self, args: argparse.Namespace) -> int:
        """
        [Function intent]
        Check and display the current status of the MCP server.
        
        [Implementation details]
        Retrieves server URL from configuration and PID from the PID file.
        Checks if the server process is running and responsive to API requests.
        Displays detailed status information including PID, process state, and API connectivity.
        Provides guidance for starting the server if it's not running.
        
        [Design principles]
        Multi-level verification - checks both process existence and API responsiveness.
        Actionable feedback - includes commands to start server when not running.
        Informative output - shows complete status context including URL and PID.
        
        Args:
            args: Command arguments (not used in this method but required for interface consistency)
            
        Returns:
            Exit code (0 if server running and responsive, 1 otherwise)
        """
        # Get server URL from config
        server_url = self.mcp_client.config_manager.get("mcp_server.url")
        if not server_url:
            self.output.error("MCP server URL is not configured")
            return 1
        
        # Use the existing status command via the API client
        pid = self._get_server_pid()
        
        if pid is not None and self._is_process_running(pid):
            self.output.info(f"=== MCP Server Status ===")
            self.output.info(f"Server URL: {server_url}")
            self.output.info(f"PID: {pid}")
            self.output.info("Process: Running")
        else:
            if pid is not None:
                self.output.info("Cleaning up stale PID file")
                self._clear_pid_file()
            
            self.output.info(f"=== MCP Server Status ===")
            self.output.info(f"Server URL: {server_url}")
            self.output.error("Process: Not running")
            self.output.info("To start the server, run: dbp server start")
            return 1
            
        # Check if server is responsive
        try:
            self.output.info("Checking server connectivity...")
            result = self.with_progress(
                "Connecting to server",
                self.mcp_client.get_server_status
            )
            
            self.output.success("Server is responsive")
            
            if "version" in result:
                self.output.info(f"Version: {result['version']}")
            
            return 0
            
        except ConnectionError as e:
            self.output.error(f"Server is not responding: {e}")
            self.output.info("The process is running but not responding to API requests")
            self.output.info("You may need to restart the server: dbp server restart")
            return 1
        except Exception as e:
            self.output.error(f"Error checking server: {e}")
            return 1
    
    def _get_server_pid(self) -> Optional[int]:
        """
        [Function intent]
        Retrieve the process ID of a running MCP server from the PID file.
        
        [Implementation details]
        Checks if the PID file exists at the location specified by the class constant.
        Reads and parses the PID as an integer if the file exists.
        Returns None if the file doesn't exist or can't be read properly.
        Logs errors for troubleshooting but doesn't raise exceptions.
        
        [Design principles]
        Defensive coding - handles file not found and parsing errors gracefully.
        Diagnostic logging - logs errors but doesn't propagate them to calling code.
        
        Returns:
            The server process ID if available, None otherwise
        """
        try:
            if self.PID_FILE.exists():
                with open(self.PID_FILE, "r") as f:
                    return int(f.read().strip())
            return None
        except (ValueError, IOError):
            logger.error("Failed to read PID file", exc_info=True)
            return None
    
    def _clear_pid_file(self) -> None:
        """
        [Function intent]
        Delete the PID file to clean up after server shutdown.
        
        [Implementation details]
        Checks if the PID file exists before attempting deletion.
        Uses Path.unlink() to remove the file.
        Logs errors if deletion fails but doesn't raise exceptions.
        
        [Design principles]
        Idempotent operation - safe to call multiple times.
        Defensive coding - checks file existence before deletion.
        Diagnostic logging - logs errors but doesn't propagate them.
        
        Returns:
            None
        """
        try:
            if self.PID_FILE.exists():
                self.PID_FILE.unlink()
        except IOError:
            logger.error("Failed to delete PID file", exc_info=True)
    
    def _is_process_running(self, pid: int) -> bool:
        """
        [Function intent]
        Determine if a process with the given PID is currently running.
        
        [Implementation details]
        Uses os.kill with signal 0 to check process existence without sending an actual signal.
        Handles different error cases to determine process state:
        - ProcessLookupError: Process doesn't exist
        - PermissionError: Process exists but is owned by another user
        - No error: Process exists and is accessible
        
        [Design principles]
        Non-intrusive check - uses signal 0 to avoid affecting the running process.
        Cross-user awareness - correctly handles processes owned by different users.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if the process is running, False otherwise
        """
        try:
            # Sending signal 0 checks if process exists without affecting it
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # If we get permission error, the process exists but is owned by another user
            return True
    
    def _is_port_available(self, host: str, port: int) -> bool:
        """
        [Function intent]
        Determine if a specific network port is available for binding.
        
        [Implementation details]
        Attempts to create a socket and bind it to the specified host and port.
        Uses context manager to ensure socket is properly closed after checking.
        Success indicates the port is available, failure means it's in use.
        
        [Design principles]
        Resource management - uses context manager for automatic socket cleanup.
        Direct verification - tests actual binding rather than port scanning.
        
        Args:
            host: Host address to check
            port: Port number to check
            
        Returns:
            True if the port is available, False if it's in use
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except socket.error:
                return False
