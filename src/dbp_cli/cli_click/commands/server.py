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
# Implements the 'server' command group for managing the MCP server via the Click CLI.
# This allows users to start, stop, restart, and check the status of the MCP server
# directly from the command line, simplifying the workflow by avoiding manual server
# management in a separate terminal.
###############################################################################
# [Source file design principles]
# - Uses Click's command group structure for server management subcommands
# - Implements consistent interfaces for start, stop, restart and status operations
# - Provides clear feedback through standardized output formatting
# - Uses subprocess to start the MCP server in a background process
# - Maintains compatibility with the original CLI server command behavior
###############################################################################
# [Source file constraints]
# - Requires Python's subprocess module for process management
# - Server processes started in background mode need proper cleanup
# - PID tracking is used to manage server processes
# - Must align with Click framework patterns and best practices
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# codebase:src/dbp/mcp_server/server.py
# system:click
# system:requests
###############################################################################
# [GenAI tool change history]
# 2025-05-13T16:19:00Z : Fixed config_manager access via context by CodeAssistant
# * Updated all instances of ctx.config_manager to ctx.obj.config_manager
# * Fixed 'Context' object has no attribute 'config_manager' error
# * Corrected context attribute access pattern to match AppContext class design
# * Ensured consistent configuration access throughout the file
# 2025-05-13T01:39:15Z : Fixed import statements for proper module resolution by CodeAssistant
# * Changed relative imports (from ...cli_click.common) to absolute imports (from dbp_cli.cli_click.common)
# * Fixed ImportError: attempted relative import beyond top-level package
# 2025-05-12T20:57:05Z : Fixed restart_command implementation by CodeAssistant
# * Fixed error when directly calling start and stop commands
# * Improved server restart logic by properly checking server status first
# * Used direct function calls instead of problematic invoke/callback methods
# * Fixed parameter passing logic to avoid duplicate argument errors
# 2025-05-12T20:47:01Z : Fixed all progress indicator usages by CodeAssistant
# * Fixed "'ProgressIndicator' object is not callable" errors throughout the file
# * Refactored progress indicator usage in status, stop, restart and start commands
# * Implemented correct pattern using ctx.with_progress helper method
# * Ensured consistent approach for showing progress during long-running operations
###############################################################################

import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click
import requests

from dbp_cli.cli_click.common import catch_errors, get_output_adapter

# Set up logger
logger = logging.getLogger(__name__)


@click.group("server", help="Manage the MCP server")
@click.pass_context
def server_group(ctx: click.Context) -> None:
    """
    [Function intent]
    Create a command group for server management operations.
    
    [Design principles]
    Command grouping - organizes related server commands under a single namespace.
    Context sharing - passes context to all subcommands.
    
    [Implementation details]
    Creates a server command group and serves as the parent for all server subcommands.
    """
    # Group setup is handled by Click decorators
    pass


@server_group.command("start", help="Start the MCP server")
@click.option("--host", default="localhost", help="Host address to bind to")
@click.option("--port", type=int, default=6231, help="Port to listen on")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (blocking)")
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
    help="Logging level",
)
@click.pass_context
@catch_errors
def start_command(ctx: click.Context, host: str, port: int, foreground: bool, log_level: str) -> None:
    """
    [Function intent]
    Start the MCP server as a background or foreground process.
    
    [Design principles]
    Resource validation - checks port availability before starting.
    Idempotent operation - handles already-running case gracefully.
    Process isolation - runs server in a separate process with proper IO handling.
    
    [Implementation details]
    Checks if server is already running by examining the PID file.
    Verifies port availability before attempting to start the server.
    Starts the server in either foreground or background mode based on options.
    In background mode, saves the PID for later management and monitoring.
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    # Check if already running
    pid = _get_server_pid(ctx)
    if pid is not None:
        if _is_process_running(pid):
            output.error(f"MCP server is already running (PID: {pid})")
            sys.exit(1)
        else:
            # Stale PID file
            logger.debug(f"Removing stale PID file (PID: {pid} not found)")
            _clear_pid_file(ctx)

    # Get required PID file path from configuration manager
    config = ctx.obj.config_manager.get_typed_config()
    pid_file_path = config.mcp_server.pid_file
    pid_file = Path(pid_file_path)
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    # Check port availability
    if not _is_port_available(host, port):
        output.error(f"Port {port} is already in use on {host}")
        sys.exit(1)

    # Start the server
    output.info(f"Starting MCP server on {host}:{port}...")

    cmd = [
        sys.executable, "-m", "dbp.mcp_server",
        "--host", host,
        "--port", str(port),
        "--log-level", log_level
    ]

    try:
        if foreground:
            # Run in foreground (blocking)
            output.info("Running server in foreground (press Ctrl+C to stop)...")
            subprocess.run(cmd, check=True)
            return
        else:
            # Get required log directory from configuration manager
            config = ctx.obj.config_manager.get_typed_config()
            logs_dir_path = config.mcp_server.logs_dir
            logs_dir = Path(logs_dir_path)
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
            with open(pid_file, "w") as f:
                f.write(str(process.pid))

            # Process is started, now wait for it to initialize
            output.info("Process started, waiting for server initialization...")

            # Get timeout from config
            config = ctx.obj.config_manager.get_typed_config()
            startup_timeout = config.initialization.timeout_seconds

            # Initial check if process is still running
            if process.poll() is not None:
                # Server failed to start, read error logs
                output.error(f"Server failed to start (exit code: {process.returncode})")
                # Show error logs
                _dump_server_error_logs(ctx, stderr_log)
                output.info(f"Full server logs available at:")
                output.info(f"  - Stdout: {stdout_log}")
                output.info(f"  - Stderr: {stderr_log}")
                output.info(f"  All logs directory: {logs_dir}")
                sys.exit(1)

            # Poll health API to detect server status
            output.info("Polling server health status...")

            # Get configuration and set up polling parameters
            server_url = f"http://{host}:{port}"
            poll_interval = 2  # Poll every 2 seconds

            # Get timeout from config
            health_check_timeout = config.initialization.timeout_seconds

            health_endpoint = f"{server_url}/health"
            output.info(f"Waiting up to {health_check_timeout}s for server initialization (polling every {poll_interval}s at {health_endpoint})...")

            # Initialize progress display
            last_step = None
            last_message = None

            # Define a function to poll the server health status
            def poll_health_status():
                nonlocal last_step, last_message
                start_time = time.time()
                while time.time() - start_time < health_check_timeout:
                    try:
                        # Check if the process is still running
                        if process.poll() is not None:
                            output.error(f"Server crashed during startup (exit code: {process.returncode})")
                            # Show complete logs for better debugging
                            _dump_server_error_logs(ctx, stderr_log)
                            output.info(f"Full server logs available at:")
                            output.info(f"  - Stdout: {stdout_log}")
                            output.info(f"  - Stderr: {stderr_log}")
                            sys.exit(1)

                        # Request health status
                        response = requests.get(health_endpoint, timeout=2)

                        # Parse the health data
                        if response.status_code == 200:
                            health_data = response.json()
                            status = health_data.get("status")

                            # Get initialization details
                            init_info = health_data.get("initialization", {})
                            current_step = init_info.get("current_step")
                            message = init_info.get("message")
                            error = init_info.get("error")

                            # Display progress updates only when they change
                            if current_step != last_step or message != last_message:
                                if error:
                                    output.error(f"Initialization failed: {error}")
                                    _dump_server_error_logs(ctx, stderr_log)
                                    sys.exit(1)
                                else:
                                    # Show progress info
                                    step_info = f"Step: {current_step}" if current_step else ""
                                    msg_info = f"- {message}" if message else ""
                                    output.info(f"Server status: {status} {step_info} {msg_info}")

                                # Update tracking variables
                                last_step = current_step
                                last_message = message

                            # Check if server is ready
                            if status == "healthy":
                                output.success("Server initialization completed successfully!")
                                output.info(f"Server is now ready to serve HTTP requests at {server_url}")
                                return True

                    except requests.RequestException:
                        # Connection errors are expected while the server is starting up
                        pass

                    # Wait before polling again
                    time.sleep(poll_interval)
                
                # Timeout reached
                output.error(f"Timeout waiting for server initialization after {health_check_timeout}s")
                output.warning("Server process is running but initialization did not complete")
                return False
            
            # Start polling with progress indicator
            ctx.obj.with_progress("Checking server health", poll_health_status)

            output.success(f"MCP server started (PID: {process.pid})")
            output.info(f"Server logs available at:")
            output.info(f"  - Stdout: {stdout_log}")
            output.info(f"  - Stderr: {stderr_log}")
            output.info("Use 'dbp-click server stop' to stop the server")
            
    except subprocess.CalledProcessError as e:
        output.error(f"Failed to start server: {e}")
        sys.exit(1)


@server_group.command("stop", help="Stop the MCP server")
@click.option("--timeout", type=int, default=5, help="Timeout (seconds) when waiting for the server to stop")
@click.pass_context
@catch_errors
def stop_command(ctx: click.Context, timeout: int) -> None:
    """
    [Function intent]
    Stop a running MCP server gracefully or forcefully if needed.
    
    [Design principles]
    Progressive escalation - tries graceful termination first, then forced.
    Resource cleanup - removes PID file after server termination.
    Fail-safe operation - handles cases where process is already gone.
    
    [Implementation details]
    Retrieves the server PID from the PID file and validates it's running.
    Sends SIGTERM to gracefully stop the server, with timeout monitoring.
    If graceful stop fails, sends SIGKILL for forced termination.
    Cleans up the PID file after successful termination.
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    pid = _get_server_pid(ctx)
    if pid is None:
        output.error("No running MCP server found")
        sys.exit(1)

    if not _is_process_running(pid):
        output.info(f"Removing stale PID file (PID: {pid} not found)")
        _clear_pid_file(ctx)
        return

    # Send SIGTERM to gracefully stop the server
    output.info(f"Stopping MCP server (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)

        # Define a function to wait for the process to exit
        def wait_for_exit():
            start_time = time.time()
            while _is_process_running(pid):
                if time.time() - start_time > timeout:
                    output.warning(f"Timed out waiting for server to stop, sending SIGKILL...")
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Already gone
                    break
                time.sleep(0.5)
        
        # Wait for process to exit with progress indicator
        ctx.obj.with_progress("Waiting for server to stop", wait_for_exit)

        # Clean up PID file
        _clear_pid_file(ctx)

        output.success("MCP server stopped successfully")

    except ProcessLookupError:
        output.info("Process not found, cleaning up PID file")
        _clear_pid_file(ctx)
    except PermissionError:
        output.error(f"Permission denied when trying to stop PID {pid}")
        sys.exit(1)


@server_group.command("restart", help="Restart the MCP server")
@click.option("--host", default="localhost", help="Host address to bind to")
@click.option("--port", type=int, default=6231, help="Port to listen on")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (blocking)")
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
    help="Logging level",
)
@click.option("--timeout", type=int, default=5, help="Timeout (seconds) when waiting for the server to stop")
@click.pass_context
@catch_errors
def restart_command(ctx: click.Context, host: str, port: int, foreground: bool, log_level: str, timeout: int) -> None:
    """
    [Function intent]
    Restart the MCP server with potentially new configuration settings.
    
    [Design principles]
    Composition - reuses stop and start command logic.
    Safety delay - waits between stop and start to ensure clean restart.
    Verification - checks that the server is responsive after restart.
    
    [Implementation details]
    Stops any running instance of the server.
    Waits to ensure complete shutdown and port release.
    Starts a new server instance with the provided arguments.
    Verifies successful restart by checking server responsiveness.
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    output.info("Restarting MCP server...")

    # Stop the server if it's running
    output.info("Stopping server...")
    
    pid = _get_server_pid(ctx)
    if pid is not None:
        if _is_process_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)

                # Define a function to wait for the process to exit
                def wait_for_exit():
                    start_time = time.time()
                    while _is_process_running(pid):
                        if time.time() - start_time > timeout:
                            output.warning(f"Timed out waiting for server to stop, sending SIGKILL...")
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass  # Already gone
                            break
                        time.sleep(0.5)
                
                # Wait for process to exit with progress indicator
                ctx.obj.with_progress("Waiting for server to stop", wait_for_exit)

                # Clean up PID file
                _clear_pid_file(ctx)
            except ProcessLookupError:
                output.info("Process not found, cleaning up PID file")
                _clear_pid_file(ctx)
            except PermissionError:
                output.error(f"Permission denied when trying to stop PID {pid}")
                sys.exit(1)
        else:
            output.info(f"Removing stale PID file (PID: {pid} not found)")
            _clear_pid_file(ctx)
    else:
        output.info("No running MCP server found")

    # Wait for port to be available
    output.info("Waiting for port release...")
    port_wait_time = timeout
    port_available = False
    
    # Define a function to wait for the port to be available
    def wait_for_port():
        nonlocal port_available
        start_time = time.time()
        while time.time() - start_time < port_wait_time:
            if _is_port_available(host, port):
                port_available = True
                break
            time.sleep(0.5)
    
    # Check port availability with progress indicator
    ctx.obj.with_progress("Waiting for port to become available", wait_for_port)

    if not port_available:
        output.error(f"Port {port} is still in use after server stop")
        output.info("You may need to manually free the port or use a different one")
        sys.exit(1)

    # Start with new settings - Do the same operations as in start_command
    output.info("Starting server with new settings...")
    
    # ----------- Begin replicating start_command functionality -----------
    # Check if already running (this is an extra check since we should have stopped the server already)
    pid = _get_server_pid(ctx)
    if pid is not None:
        if _is_process_running(pid):
            output.error(f"MCP server is already running (PID: {pid})")
            sys.exit(1)
        else:
            # Stale PID file
            logger.debug(f"Removing stale PID file (PID: {pid} not found)")
            _clear_pid_file(ctx)

    # Get required PID file path from configuration manager
    config = ctx.obj.config_manager.get_typed_config()
    pid_file_path = config.mcp_server.pid_file
    pid_file = Path(pid_file_path)
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    # We should have already checked port availability above, but let's verify again
    if not _is_port_available(host, port):
        output.error(f"Port {port} is still in use")
        output.info("You may need to manually free the port or use a different one")
        sys.exit(1)

    # Start the server - This replicates the code in start_command
    output.info(f"Starting MCP server on {host}:{port}...")

    cmd = [
        sys.executable, "-m", "dbp.mcp_server",
        "--host", host,
        "--port", str(port),
        "--log-level", log_level
    ]

    try:
        if foreground:
            # Run in foreground (blocking)
            output.info("Running server in foreground (press Ctrl+C to stop)...")
            subprocess.run(cmd, check=True)
            return
        else:
            # Get required log directory from configuration manager
            config = ctx.obj.config_manager.get_typed_config()
            logs_dir_path = config.mcp_server.logs_dir
            logs_dir = Path(logs_dir_path)
            logs_dir.mkdir(parents=True, exist_ok=True)
            stdout_log = logs_dir / "mcp_server_stdout.log"
            stderr_log = logs_dir / "mcp_server_stderr.log"

            logger.debug(f"Starting server with command: {cmd}")
            logger.debug(f"Redirecting output to: {stdout_log} and {stderr_log}")

            # Run in background with output captured to log files
            with open(stdout_log, "a") as stdout_file, open(stderr_log, "a") as stderr_file:
                # Add timestamp to logs
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                stdout_file.write(f"\n\n--- SERVER RESTART ATTEMPT AT {timestamp} ---\n\n")
                stderr_file.write(f"\n\n--- SERVER RESTART ATTEMPT AT {timestamp} ---\n\n")

                process = subprocess.Popen(
                    cmd,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=True
                )

            # Store PID for later management
            with open(pid_file, "w") as f:
                f.write(str(process.pid))

            output.success(f"MCP server restarted successfully (PID: {process.pid})")
            output.info(f"Server logs available at:")
            output.info(f"  - Stdout: {stdout_log}")
            output.info(f"  - Stderr: {stderr_log}")
    except subprocess.CalledProcessError as e:
        output.error(f"Failed to restart server: {e}")
        sys.exit(1)
    # ----------- End replicating start_command functionality -----------


@server_group.command("status", help="Check MCP server status")
@click.pass_context
@catch_errors
def status_command(ctx: click.Context) -> None:
    """
    [Function intent]
    Check and display the current status of the MCP server.
    
    [Design principles]
    Multi-level verification - checks both process existence and API responsiveness.
    Actionable feedback - includes commands to start server when not running.
    Informative output - shows complete status context including URL and PID.
    
    [Implementation details]
    Checks if the server process is running using the PID file.
    Constructs server URL from host and port configuration.
    Tests API connectivity by requesting the health endpoint.
    Displays detailed status information including PID and health details.
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    # Construct server URL from host and port configuration
    config = ctx.obj.config_manager.get_typed_config()
    host = config.mcp_server.host
    port = config.mcp_server.port
    server_url = f"http://{host}:{port}"

    # Check if the server process is running
    pid = _get_server_pid(ctx)

    if pid is not None and _is_process_running(pid):
        output.info(f"=== MCP Server Status ===")
        output.info(f"Server URL: {server_url}")
        output.info(f"PID: {pid}")
        output.info("Process: Running")
    else:
        if pid is not None:
            output.info("Cleaning up stale PID file")
            _clear_pid_file(ctx)

        output.info(f"=== MCP Server Status ===")
        output.info(f"Server URL: {server_url}")
        output.error("Process: Not running")
        output.info("To start the server, run: dbp-click server start")
        sys.exit(1)

    # Check if server is responsive by checking the health endpoint
    health_endpoint = f"{server_url}/health"
    output.info(f"Checking health endpoint: {health_endpoint}")
    
    try:
        response = ctx.obj.with_progress(
            "Connecting to server",
            requests.get,
            health_endpoint,
            timeout=5
        )
            
        if response.status_code == 200:
            result = response.json()
            output.success("Server is responsive")

            if "version" in result:
                output.info(f"Version: {result['version']}")

            # Pretty print the full health response JSON
            import json
            output.info("\nServer Health Response (JSON):")
            output.info(json.dumps(result, indent=2))
        else:
            output.error(f"Server returned error status code: {response.status_code}")
            output.info("The server is running but returned an error response")
            output.info("You may need to restart the server: dbp-click server restart")
            sys.exit(1)

    except requests.ConnectionError:
        output.error(f"Server is not responding")
        output.info("The process is running but not responding to API requests")
        output.info("You may need to restart the server: dbp-click server restart")
        sys.exit(1)
    except requests.Timeout:
        output.error(f"Server connection timed out")
        output.info("The process is running but health check timed out")
        output.info("You may need to restart the server: dbp-click server restart")
        sys.exit(1)
    except Exception as e:
        output.error(f"Error checking server: {e}")
        sys.exit(1)


# Helper functions (similar to the original implementation but adapted for Click context)

def _dump_server_error_logs(ctx: click.Context, stderr_log_path: Path) -> None:
    """
    [Function intent]
    Extract and display all logs from the server's stderr log file since the start marker.
    
    [Design principles]
    Complete context - shows all logs since server start without truncation.
    Actionable feedback - provides detailed error information for troubleshooting.
    
    [Implementation details]
    Reads the specified log file and formats messages according to their severity.
    Displays all log messages since the last server start for comprehensive context.
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    try:
        if not stderr_log_path.exists():
            output.warning(f"Server log file does not exist: {stderr_log_path}")
            return

        with open(stderr_log_path, "r") as f:
            lines = f.readlines()
            if not lines:
                output.warning("Server log file is empty")
                return

            # Find the last server start marker
            start_marker_prefix = "--- SERVER START ATTEMPT AT "
            start_marker_index = -1

            for i, line in enumerate(reversed(lines)):
                if start_marker_prefix in line:
                    start_marker_index = len(lines) - i - 1
                    break

            # If no start marker found, show all logs
            if start_marker_index == -1:
                output.info("No server start marker found, showing all logs:")
                log_lines = lines
            else:
                # Get all logs since the last server start
                log_lines = lines[start_marker_index:]
                start_time = log_lines[0].strip().replace(start_marker_prefix, "").replace("---", "").strip()
                output.info(f"Server logs since start attempt at {start_time}:")

            # Display all logs with proper formatting
            output.info("Complete server error log:")
            for line in log_lines:
                line = line.strip()
                if "ERROR" in line or "CRITICAL" in line:
                    output.error(f"  {line}")
                elif "WARNING" in line:
                    output.warning(f"  {line}")
                else:
                    output.info(f"  {line}")

    except Exception as e:
        output.error(f"Failed to read error log: {e}")


def _get_server_pid(ctx: click.Context) -> Optional[int]:
    """
    [Function intent]
    Retrieve the process ID of a running MCP server from the PID file.
    
    [Design principles]
    Defensive coding - handles file not found and parsing errors gracefully.
    Configuration-driven - uses configured paths instead of hardcoded values.
    
    [Implementation details]
    Gets PID file path from configuration manager.
    Reads and parses the PID as an integer if the file exists.
    Returns None if the file doesn't exist or can't be read properly.
    """
    config = ctx.obj.config_manager.get_typed_config()
    pid_file_path = config.mcp_server.pid_file

    try:
        pid_file = Path(pid_file_path)
        if pid_file.exists():
            with open(pid_file, "r") as f:
                return int(f.read().strip())
        return None
    except (ValueError, IOError):
        logger.error("Failed to read PID file", exc_info=True)
        return None


def _clear_pid_file(ctx: click.Context) -> None:
    """
    [Function intent]
    Delete the PID file to clean up after server shutdown.
    
    [Design principles]
    Idempotent operation - safe to call multiple times.
    Defensive coding - checks file existence before deletion.
    
    [Implementation details]
    Gets PID file path from configuration manager.
    Checks if the PID file exists before attempting deletion.
    Logs errors if deletion fails but doesn't raise exceptions.
    """
    config = ctx.obj.config_manager.get_typed_config()
    pid_file_path = config.mcp_server.pid_file

    try:
        pid_file = Path(pid_file_path)
        if pid_file.exists():
            pid_file.unlink()
    except IOError:
        logger.error("Failed to delete PID file", exc_info=True)


def _is_process_running(pid: int) -> bool:
    """
    [Function intent]
    Determine if a process with the given PID is currently running.
    
    [Design principles]
    Non-intrusive check - uses signal 0 to avoid affecting the running process.
    Cross-user awareness - correctly handles processes owned by different users.
    
    [Implementation details]
    Uses os.kill with signal 0 to check process existence without sending an actual signal.
    Returns True if the process exists and is accessible or owned by another user.
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


def _is_port_available(host: str, port: int) -> bool:
    """
    [Function intent]
    Determine if a specific network port is available for binding.
    
    [Design principles]
    Resource management - uses context manager for automatic socket cleanup.
    Direct verification - tests actual binding rather than port scanning.
    
    [Implementation details]
    Attempts to create a socket and bind it to the specified host and port.
    Sets SO_REUSEADDR to handle ports in TIME_WAIT state.
    Success indicates the port is available, failure means it's in use.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Set SO_REUSEADDR to allow reusing local addresses in TIME_WAIT state
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except socket.error:
            logger.debug(f"Port {port} is in use")
            return False
