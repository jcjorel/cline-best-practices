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
# 2025-04-20T03:52:00Z : Fixed startup timeout parameter to use configuration values by CodeAssistant
# * Updated startup-timeout parameter to use timeout_seconds from configuration
# * Eliminated last hardcoded default value in argument parser
# * Ensured consistent default values across all CLI parameters
# 2025-04-20T03:48:00Z : Updated argument parser to use ConfigurationManager by CodeAssistant
# * Modified parse_arguments() to get default values from ConfigurationManager
# * Added strict exception handling for configuration access
# * Made default argument values consistent with system-wide configuration
# * Improved help text to show correct default values from configuration
# 2025-04-20T03:32:00Z : Enhanced process diagnostics for deadlock detection by CodeAssistant
# * Implemented deep stack inspection to better identify waiting conditions
# * Added detection and analysis of thread wait states
# * Added detailed local variable capture for waiting threads
# * Enhanced stack trace formatting with waiting condition markers
# 2025-04-18T14:01:00Z : Fixed truncated WARNING log level display by CodeAssistant
# * Imported get_formatted_logger and MillisecondFormatter from core.log_utils
# * Modified exit_handler to use get_formatted_logger instead of direct StreamHandler
# * Ensured proper width formatting for log level names in emergency logger
# 2025-04-18T11:45:00Z : Added watchdog mechanism for deadlock detection by CodeAssistant
# * Implemented keep_alive() that components must call to prevent timeout termination
# * Added watchdog thread that monitors for inactivity and terminates stuck processes
# * Added comprehensive process diagnostics for debugging deadlocks
# * Added watchdog-timeout command line parameter to configure the timeout value
# 2025-04-18T11:25:35Z : Added server exit handler with source tracking by CodeAssistant
# * Implemented exit_handler function to track process exit sources
# * Added signal handlers for SIGTERM, SIGINT, and other termination signals
# * Added traceback capture for detailed exit reason logging
# * Modified main() to use the exit handler for all termination cases
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
from ..config.default_config import INITIALIZATION_DEFAULTS

# Global logger
logger = None

# Track the exit source
exit_source = None
exit_reason = None
exit_traceback = None

# Watchdog mechanism globals
_last_keepalive_time = None
_watchdog_thread = None
_watchdog_timeout = 60  # Default timeout in seconds
_watchdog_active = False
_watchdog_lock = threading.Lock()

def keep_alive():
    """
    [Function intent]
    Updates the last activity timestamp to prevent watchdog from terminating the process.
    
    [Implementation details]
    Updates the global _last_keepalive_time variable with the current time.
    Components should call this periodically to indicate the process is not stuck.
    
    [Design principles]
    Simple interface for deadlock detection.
    Thread-safe timestamp updates.
    """
    global _last_keepalive_time, _watchdog_lock
    
    with _watchdog_lock:
        _last_keepalive_time = time.time()
        
    if logger and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Process keepalive updated at {_last_keepalive_time}")
        
def start_watchdog(timeout=60):
    """
    [Function intent]
    Starts a watchdog thread that monitors for process activity.
    
    [Implementation details]
    Creates a daemon thread that checks if keep_alive() has been called within
    the specified timeout period. If not, it logs detailed diagnostics and
    terminates the process.
    
    [Design principles]
    Automatic deadlock detection.
    Detailed diagnostic information for debugging.
    Graceful termination with exit handler integration.
    
    Args:
        timeout: Number of seconds to wait for activity before considering the process stuck
    """
    global _watchdog_thread, _watchdog_timeout, _watchdog_active, _last_keepalive_time
    
    if _watchdog_thread is not None:
        logger.warning("Watchdog already running, not starting another")
        return
    
    _watchdog_timeout = timeout
    _last_keepalive_time = time.time()
    _watchdog_active = True
    
    def watchdog_monitor():
        logger.info(f"Watchdog started with {timeout} second timeout")
        
        while _watchdog_active:
            time.sleep(min(5, timeout / 4))  # Check at reasonable intervals
            
            try:
                current_time = time.time()
                last_time = _last_keepalive_time
                
                if last_time is None:
                    continue
                    
                time_since_keepalive = current_time - last_time
                
                # If too much time has passed since last activity
                if time_since_keepalive > _watchdog_timeout:
                    # Get information about the current process state
                    process_info = get_process_diagnostics()
                    
                    logger.critical(f"WATCHDOG TRIGGERED: No activity for {time_since_keepalive:.1f} seconds (timeout: {_watchdog_timeout}s)")
                    logger.critical("Process appears to be stuck or deadlocked")
                    logger.critical(f"Last activity: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time))}")
                    
                    # Log process diagnostics
                    for key, value in process_info.items():
                        if isinstance(value, list):
                            logger.critical(f"{key}:")
                            for item in value:
                                logger.critical(f"  {item}")
                        else:
                            logger.critical(f"{key}: {value}")
                    
                    # Call exit handler with watchdog information
                    exit_handler(
                        reason=f"Watchdog triggered after {time_since_keepalive:.1f}s of inactivity",
                        source="Watchdog thread"
                    )
                    
                    # Allow a small delay for exit handler to log info
                    time.sleep(1)
                    
                    # Force terminate the process
                    os._exit(1)  # Use os._exit to ensure immediate exit
                    
            except Exception as e:
                if logger:
                    logger.error(f"Error in watchdog thread: {e}", exc_info=True)
                time.sleep(5)  # Sleep on error to prevent tight loop
    
    # Start watchdog thread
    _watchdog_thread = threading.Thread(target=watchdog_monitor, daemon=True, name="watchdog_monitor")
    _watchdog_thread.start()

def stop_watchdog():
    """
    [Function intent]
    Stops the watchdog monitoring thread.
    
    [Implementation details]
    Sets _watchdog_active to False to signal the watchdog thread to stop.
    
    [Design principles]
    Clean shutdown of monitoring resources.
    """
    global _watchdog_active
    _watchdog_active = False
    logger.debug("Watchdog deactivated")

def get_process_diagnostics():
    """
    [Function intent]
    Gathers detailed diagnostics about the current process state, with enhanced detection
    of deadlocks and waiting conditions for any type of blocking scenario.
    
    [Implementation details]
    Collects comprehensive information about threads, system resources, stack traces,
    thread states, waiting conditions, and potential deadlocks. Analyzes each thread's
    stack frames to identify functions that are likely blocking or waiting.
    
    [Design principles]
    - Comprehensive diagnostics for any type of deadlock identification
    - Deep stack inspection to locate waiting and blocked threads
    - Detailed local variable analysis in critical frames
    - Non-intrusive diagnostics that don't interfere with process state
    
    Returns:
        Dict with diagnostic information about the process state
    """
    diagnostics = {}
    
    # Get detailed thread information
    thread_info = []
    thread_map = {}  # Map thread IDs to thread objects
    
    for thread in threading.enumerate():
        thread_info.append(f"{thread.name} (id={thread.ident}, daemon={thread.daemon}, alive={thread.is_alive()})")
        thread_map[thread.ident] = thread
        
    diagnostics["Active Threads"] = thread_info
    
    # Get system resources
    try:
        import psutil
        process = psutil.Process()
        
        diagnostics["CPU Usage"] = f"{process.cpu_percent()}%"
        diagnostics["Memory Usage"] = f"{process.memory_info().rss / (1024*1024):.1f} MB"
        open_files_count = len(process.open_files())
        open_conns_count = len(process.connections())
        diagnostics["Open Files"] = open_files_count
        diagnostics["Open Connections"] = open_conns_count
        
        # Get more details about open files and connections that might be related to deadlocks
        if open_files_count > 0:
            open_files = process.open_files()
            file_details = [f"{f.path} (mode: {f.mode})" for f in open_files[:20]]  # Limit to 20 files
            if len(open_files) > 20:
                file_details.append(f"... and {len(open_files) - 20} more files")
            diagnostics["Open File Details"] = file_details
            
        if open_conns_count > 0:
            connections = process.connections()
            conn_details = []
            for conn in connections[:20]:  # Limit to 20 connections
                conn_details.append(f"{conn.laddr}→{conn.raddr if conn.raddr else 'N/A'} ({conn.status})")
            if len(connections) > 20:
                conn_details.append(f"... and {len(connections) - 20} more connections")
            diagnostics["Connection Details"] = conn_details
    except (ImportError, Exception) as e:
        diagnostics["Resource Info"] = f"Unable to get system resources: {str(e)}"
    
    # Enhanced thread stack trace collection with waiting condition detection
    try:
        import sys
        import inspect
        
        stack_traces = []
        frame_dict = sys._current_frames()
        waiting_threads = []
        blocking_threads = []
        main_thread_trace = None
        
        # Special keywords that suggest a thread might be waiting
        waiting_keywords = [
            'wait', 'acquire', 'lock', 'join', 'get', 'sleep', 
            'select', 'poll', 'recv', 'read', 'accept', '_waiters',
            'condition', 'event', 'queue', 'barrier', 'timeout'
        ]
        
        for thread_id, frame in frame_dict.items():
            thread_name = "Unknown"
            is_main_thread = False
            
            # Get the thread object if available
            thread_obj = thread_map.get(thread_id)
            if thread_obj:
                thread_name = thread_obj.name
                is_main_thread = thread_id == threading.main_thread().ident
            
            # Start building the stack trace
            stack_trace = []
            stack_trace.append(f"Thread {thread_name} (id: {thread_id}" + 
                              (", MAIN THREAD" if is_main_thread else "") + "):")
            
            # First pass to analyze if this thread is waiting or blocking
            is_waiting = False
            wait_info = {}
            
            # Walk frames to look for waiting indicators
            current_frame = frame
            while current_frame:
                frame_info = inspect.getframeinfo(current_frame)
                func_name = frame_info.function
                filename = frame_info.filename
                
                # Look for common waiting patterns in function names
                if any(keyword in func_name.lower() for keyword in waiting_keywords):
                    is_waiting = True
                    wait_info = {
                        'function': func_name,
                        'file': filename,
                        'line': frame_info.lineno,
                    }
                    
                    # Capture interesting local variables that might help diagnose the wait
                    wait_locals = {}
                    for var_name in ['timeout', 'block', 'blocking', 'queue', 'lock', 'condition',
                                    'event', 'self', 'obj', 'future', 'task', 'waiter']:
                        if var_name in current_frame.f_locals:
                            var_val = current_frame.f_locals[var_name]
                            # Get a safe string representation
                            try:
                                if hasattr(var_val, '__class__'):
                                    wait_locals[var_name] = f"{var_val.__class__.__name__}: {str(var_val)[:100]}"
                                else:
                                    wait_locals[var_name] = str(var_val)[:100]
                            except Exception:
                                wait_locals[var_name] = f"<error getting value>"
                    
                    if wait_locals:
                        wait_info['locals'] = wait_locals
                    
                    # Additional context for asyncio waits
                    if 'asyncio' in filename:
                        wait_info['type'] = 'asyncio'
                    
                    break
                
                current_frame = current_frame.f_back
            
            if is_waiting:
                waiting_threads.append({
                    'thread_id': thread_id,
                    'thread_name': thread_name,
                    'wait_info': wait_info
                })
            
            # Now extract the full stack trace with enhanced details
            frames = []
            current_frame = frame
            frame_index = 0
            
            while current_frame:
                frame_info = inspect.getframeinfo(current_frame)
                frames.append((frame_info, current_frame))
                current_frame = current_frame.f_back
                frame_index += 1
                
                # Prevent deep recursion in case of very deep stacks
                if frame_index > 100:  # Limit to reasonable depth
                    frames.append((None, None))  # Sentinel for truncation
                    break
            
            # Process frames (in reverse to show from oldest to newest call)
            for i, (frame_info, f_obj) in enumerate(reversed(frames)):
                if frame_info is None:  # Handle truncated stack
                    stack_trace.append("  ... frames truncated ...")
                    continue
                    
                # Basic frame information
                filename = frame_info.filename
                lineno = frame_info.lineno
                function = frame_info.function
                code_line = frame_info.code_context[0].strip() if frame_info.code_context else "<no source>"
                
                # Add special markers for interesting frames
                markers = []
                
                # Highlight waiting/blocking frames
                if any(keyword in function.lower() for keyword in waiting_keywords):
                    markers.append("WAITING")
                
                # Highlight potential deadlock-related modules
                for module in ['threading', 'multiprocessing', 'asyncio', 'queue', 'socket']:
                    if module in filename:
                        markers.append(module.upper())
                        break
                
                marker_str = f" [{', '.join(markers)}]" if markers else ""
                
                # Add the frame to the stack trace
                stack_trace.append(f"  Frame {i}: {filename}:{lineno} in {function}{marker_str}")
                stack_trace.append(f"    {code_line}")
                
                # For interesting frames (like ones that might be involved in waiting),
                # add more details about the local variables
                if markers or i < 3:  # Show details for waiting frames or top frames
                    if f_obj and f_obj.f_locals:
                        # Get key locals that might help diagnose issues
                        important_locals = {}
                        
                        # First look for variables with interesting names
                        for var_name, var_val in f_obj.f_locals.items():
                            if var_name.startswith('__'):
                                continue  # Skip internal vars
                                
                            if any(keyword in var_name.lower() for keyword in 
                                  ['lock', 'queue', 'event', 'condition', 'future', 'task', 'waiter', 
                                   'timeout', 'thread', 'connection']):
                                try:
                                    val_str = str(var_val)[:200]  # Limit string length
                                    important_locals[var_name] = val_str
                                except Exception:
                                    important_locals[var_name] = "<error getting value>"
                        
                        # Always include 'self' for method calls
                        if 'self' in f_obj.f_locals and len(important_locals) < 10:
                            try:
                                self_obj = f_obj.f_locals['self']
                                important_locals['self'] = f"{self_obj.__class__.__name__}"
                                
                                # For some common types, add more detail
                                if hasattr(self_obj, '__dict__'):
                                    for attr_name, attr_val in vars(self_obj).items():
                                        if len(important_locals) >= 15:
                                            break  # Limit the number of attributes
                                        if attr_name.startswith('_'):
                                            continue  # Skip private attributes
                                        try:
                                            important_locals[f"self.{attr_name}"] = str(attr_val)[:100]
                                        except Exception:
                                            pass
                            except Exception:
                                important_locals['self'] = "<error getting value>"
                        
                        # Add the locals to the stack trace if we found any
                        if important_locals:
                            stack_trace.append(f"    Local variables:")
                            for var_name, var_val in important_locals.items():
                                stack_trace.append(f"      {var_name} = {var_val}")
            
            # Save the trace
            full_trace = "\n".join(stack_trace)
            stack_traces.append(full_trace)
            
            # Keep track of main thread trace separately
            if is_main_thread:
                main_thread_trace = full_trace
        
        # Save all traces, but ensure main thread is first if present
        if main_thread_trace:
            # Remove main thread from the list if present
            stack_traces = [trace for trace in stack_traces if not trace.startswith(f"Thread MainThread")]
            # Add it to the beginning
            stack_traces.insert(0, main_thread_trace)
            
        diagnostics["Stack Traces"] = stack_traces
        
        # Add summary of waiting threads if any were found
        if waiting_threads:
            diagnostics["Waiting Threads Summary"] = [
                f"{w['thread_name']} (id: {w['thread_id']}) waiting in {w['wait_info'].get('function', 'unknown')}" 
                for w in waiting_threads
            ]
            
            # Detailed wait information
            wait_details = []
            for w in waiting_threads:
                info = w['wait_info']
                details = [f"Thread {w['thread_name']} (id: {w['thread_id']})"]
                details.append(f"  Function: {info.get('function', 'unknown')}")
                details.append(f"  File: {info.get('file', 'unknown')}:{info.get('line', '?')}")
                
                if 'locals' in info:
                    details.append("  Context variables:")
                    for name, value in info['locals'].items():
                        details.append(f"    {name} = {value}")
                        
                wait_details.append("\n".join(details))
                
            diagnostics["Detailed Wait Information"] = wait_details
            
    except Exception as e:
        error_trace = traceback.format_exc()
        diagnostics["Stack Traces"] = f"Unable to get enhanced stack traces: {str(e)}"
        diagnostics["Stack Trace Error"] = error_trace
    
    # Get information about other running processes that might be related
    try:
        import psutil
        
        # Get information about Python processes
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'python' in proc.name().lower():
                    if proc.pid != os.getpid():  # Skip our own process
                        cmd = ' '.join(proc.cmdline()) if proc.cmdline() else 'Unknown'
                        python_processes.append(f"PID {proc.pid}: {cmd}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        if python_processes:
            diagnostics["Related Python Processes"] = python_processes
    except Exception:
        # Not critical, just skip if unavailable
        pass
        
    return diagnostics

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
    
    # Start the watchdog with the specified timeout
    start_watchdog(timeout=watchdog_timeout)

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
    parser.add_argument('--startup-check', action='store_true',
                        help='Perform health check after starting to verify server is responsive')
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
    keep_alive()
    
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
            
            # Component initialization is complete, stop the watchdog
            # It has served its purpose of detecting deadlocks during initialization
            logger.info("Component initialization completed successfully, stopping watchdog")
            stop_watchdog()
                
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
                exit_handler(reason="Keyboard interrupt (SIGINT)", source="KeyboardInterrupt handler")
            except Exception as e:
                logger.critical(f"Failed during server execution: {e}", exc_info=True)
                exit_handler(reason="Failed during server execution", exception=e, source="MCP server execution")
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
