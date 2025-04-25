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
# Implements a watchdog mechanism to detect and handle system deadlocks.
# Provides functionality to monitor process activity and automatically
# terminate stuck processes to prevent system-wide failures.
###############################################################################
# [Source file design principles]
# - Thread-safe activity monitoring with configurable timeout threshold
# - Uses condition variables for efficient waiting instead of polling
# - Provides detailed process diagnostics to aid debugging of deadlocks
# - Automatic process termination with comprehensive exit information
# - Non-invasive monitoring that minimizes performance impact
###############################################################################
# [Source file constraints]
# - Must be thread-safe to handle concurrent access from multiple components
# - Diagnostic collection must not interfere with normal process operation
# - Must gracefully handle exceptions during diagnostic collection
# - Should capture sufficient debug information for post-mortem analysis
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T13:08:04Z : Fixed watchdog logging severity levels by CodeAssistant
# * Adjusted log levels to reserve CRITICAL only for actual watchdog triggers
# * Changed routine status checks from CRITICAL to INFO level
# * Changed thread information logging from CRITICAL to DEBUG level
# * Changed threshold exceeded notifications from CRITICAL to WARNING level
# * Maintained CRITICAL level for actual watchdog trigger diagnostics
# 2025-04-20T21:04:54Z : Enhanced watchdog to prioritize all thread stack traces on trigger by CodeAssistant
# * Modified diagnostic display to prominently show all thread stack traces first
# * Added clear section separators for better log readability
# * Ensured main thread trace is displayed first followed by other threads
# * Improved visibility of critical diagnostic information during deadlocks
# 2025-04-20T10:43:35Z : Created watchdog module with conditional variable mechanism by CodeAssistant
# * Implemented watchdog with condition variables instead of sleep-based polling
# * Added thread-safe keepalive mechanism with minimal overhead
# * Improved responsiveness to process activity updates
# * Simplified implementation following KISS principles
###############################################################################

import logging
import threading
import time
import os
import traceback
import sys
import inspect
from typing import Dict, Any, Optional, Callable

# Global logger
logger = logging.getLogger('dbp.core.watchdog')

# Watchdog mechanism globals
_condition = threading.Condition()
_last_keepalive_time = None
_watchdog_thread = None
_watchdog_timeout = 60  # Default timeout in seconds
_watchdog_active = False

def keep_alive():
    """
    [Function intent]
    Updates the last activity timestamp to prevent watchdog from terminating the process.
    
    [Implementation details]
    Updates the _last_keepalive_time variable with the current time and notifies
    the condition variable to wake up the watchdog thread immediately.
    
    [Design principles]
    Thread-safe timestamp updates with minimal delay.
    Immediate notification to watchdog through condition variable.
    """
    global _last_keepalive_time
    
    with _condition:
        _last_keepalive_time = time.time()
        _condition.notify_all()  # Wake up watchdog immediately
        
    if logger and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Process keepalive updated at {_last_keepalive_time}")

def start_watchdog(timeout: int = 60, exit_handler: Optional[Callable] = None):
    """
    [Function intent]
    Starts a watchdog thread that monitors for process activity.
    
    [Implementation details]
    Creates a daemon thread that waits for keepalive signals using condition variables.
    If no keepalive is received within the timeout period, collects diagnostic information
    and terminates the process.
    
    [Design principles]
    Efficient waiting using condition variables instead of sleep-based polling.
    Immediate response to keepalive updates.
    Comprehensive diagnostics for debugging deadlocks.
    
    Args:
        timeout: Number of seconds to wait for activity before considering the process stuck
        exit_handler: Function to call when watchdog is triggered
    """
    global _watchdog_thread, _watchdog_timeout, _watchdog_active, _last_keepalive_time
    
    if _watchdog_thread is not None:
        logger.warning("Watchdog already running, not starting another")
        return
    
    _watchdog_timeout = timeout
    _last_keepalive_time = time.time()
    _watchdog_active = True
    
    # Log diagnostic information about watchdog setup
    logger.info(f"WATCHDOG SETUP: Initializing watchdog with {timeout}s timeout")
    logger.info(f"WATCHDOG SETUP: Initial timestamp: {_last_keepalive_time}")
    
    def watchdog_monitor():
        logger.info(f"WATCHDOG THREAD STARTED: with {timeout} second timeout")
        
        # Log thread information for debugging
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        logger.debug(f"WATCHDOG THREAD INFO: id={thread_id}, name={thread_name}, is_daemon={threading.current_thread().daemon}")
        
        # Loop counter for logging
        loop_counter = 0
        
        while _watchdog_active:
            loop_counter += 1
            logger.debug(f"WATCHDOG LOOP {loop_counter}: Waiting for activity")
            
            # Efficiently wait using condition variable with timeout
            current_time = time.time()
            last_time = _last_keepalive_time
            
            # Calculate how long to wait
            if last_time is None:
                wait_time = _watchdog_timeout
            else:
                wait_time = max(0, last_time + _watchdog_timeout - current_time)
            
            # Wait for notification or timeout
            with _condition:
                # Wait returns False if timeout occurred, True if notified
                notified = _condition.wait(wait_time)
            
            try:
                current_time = time.time()
                last_time = _last_keepalive_time
                
                if last_time is None:
                    logger.warning("WATCHDOG LOOP: _last_keepalive_time is None, skipping check")
                    continue
                    
                time_since_keepalive = current_time - last_time
                logger.info(f"WATCHDOG CHECK: Time since last keepalive: {time_since_keepalive:.1f}s (threshold: {_watchdog_timeout}s)")
                
                # If too much time has passed since last activity
                if time_since_keepalive > _watchdog_timeout:
                    logger.warning("WATCHDOG THRESHOLD EXCEEDED: Preparing to take action")
                    # Get information about the current process state
                    process_info = get_process_diagnostics()
                    
                    logger.critical(f"WATCHDOG TRIGGERED: No activity for {time_since_keepalive:.1f} seconds (timeout: {_watchdog_timeout}s)")
                    logger.critical("Process appears to be stuck or deadlocked")
                    logger.critical(f"Last activity: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time))}")
                    
                    # Log process diagnostics - prioritize stack traces first
                    logger.critical("============= WATCHDOG TRIGGERED: ALL THREAD STACK TRACES =============")
                    
                    # First display all stack traces
                    if "Stack Traces" in process_info:
                        stack_traces = process_info["Stack Traces"]
                        for trace in stack_traces:
                            logger.critical(trace)
                            logger.critical("---------------------------------------------------")
                        
                        # Remove from process_info to avoid duplication
                        del process_info["Stack Traces"]
                    
                    # Then log other diagnostic information
                    logger.critical("============= ADDITIONAL DIAGNOSTIC INFORMATION =============")
                    for key, value in process_info.items():
                        if isinstance(value, list):
                            logger.critical(f"{key}:")
                            for item in value:
                                logger.critical(f"  {item}")
                        else:
                            logger.critical(f"{key}: {value}")
                    
                    # Call exit handler with watchdog information
                    if exit_handler:
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
                # Brief sleep to prevent tight loop on continuous errors
                time.sleep(1)
    
    # Start watchdog thread
    _watchdog_thread = threading.Thread(target=watchdog_monitor, daemon=True, name="watchdog_monitor")
    _watchdog_thread.start()

def stop_watchdog():
    """
    [Function intent]
    Stops the watchdog monitoring thread.
    
    [Implementation details]
    Sets _watchdog_active to False and notifies the condition variable to 
    wake up the watchdog thread for clean termination.
    
    [Design principles]
    Clean shutdown of monitoring resources.
    Immediate notification for quick termination.
    """
    global _watchdog_active
    
    with _condition:
        _watchdog_active = False
        _condition.notify_all()
    
    logger.debug("Watchdog deactivated")

def get_process_diagnostics() -> Dict[str, Any]:
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
        stack_traces = []
        frame_dict = sys._current_frames()
        waiting_threads = []
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

def is_watchdog_active() -> bool:
    """
    [Function intent]
    Checks if the watchdog is currently active.
    
    [Implementation details]
    Returns the current state of the _watchdog_active flag.
    
    [Design principles]
    Simple status check for conditional logic.
    
    Returns:
        bool: True if watchdog is active, False otherwise
    """
    return _watchdog_active

def get_last_keepalive_time() -> Optional[float]:
    """
    [Function intent]
    Returns the timestamp of the last keepalive signal.
    
    [Implementation details]
    Returns the global _last_keepalive_time variable.
    
    [Design principles]
    Provides diagnostic access to internal state.
    
    Returns:
        float: Unix timestamp of last keepalive, or None if not yet set
    """
    return _last_keepalive_time

def setup_watchdog_for_exit_handler(timeout: int, exit_handler_func: Callable):
    """
    [Function intent]
    Configures and starts the watchdog with integration to an exit handler.
    
    [Implementation details]
    Wrapper function that starts the watchdog with the provided exit handler function.
    
    [Design principles]
    Simplified integration with exit handling mechanisms.
    Standard interface for system-wide usage.
    
    Args:
        timeout: Seconds to wait for activity before triggering watchdog
        exit_handler_func: Function to call when watchdog is triggered
    """
    start_watchdog(timeout=timeout, exit_handler=exit_handler_func)
