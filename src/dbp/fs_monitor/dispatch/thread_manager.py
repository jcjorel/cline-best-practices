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
# This file implements a thread manager for the file system monitor component.
# It provides a mechanism to manage worker threads for efficient event dispatching,
# supporting task prioritization and graceful shutdown handling.
###############################################################################
# [Source file design principles]
# - Efficient thread utilization
# - Support for task prioritization
# - Graceful shutdown handling
# - Thread-safe operations
# - Minimal resource utilization during idle periods
###############################################################################
# [Source file constraints]
# - Must handle concurrent task submissions from multiple sources
# - Must properly manage thread lifecycle
# - Must support variable task priorities
# - Must ensure proper thread cleanup during shutdown
# - Must prevent resource leaks and thread leaks
###############################################################################
# [Dependencies]
# system:threading
# system:logging
# system:time
# system:queue
# system:typing
# system:enum
# system:dataclasses
###############################################################################
# [GenAI tool change history]
# 2025-04-29T00:10:00Z : Initial implementation of thread manager for fs_monitor redesign by CodeAssistant
# * Created ThreadManager class for managing worker threads
# * Implemented ThreadPriority enum for thread prioritization
# * Added DispatchTask dataclass for task encapsulation
###############################################################################

import threading
import logging
import time
import queue
from typing import Dict, List, Callable, Optional
from enum import Enum, auto
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ThreadPriority(Enum):
    """
    [Class intent]
    Defines priorities for dispatcher threads.
    
    [Design principles]
    - Simple prioritization of tasks
    - Alignment with OS thread priorities
    
    [Implementation details]
    - Enum values correspond to priority levels
    """
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()


@dataclass
class DispatchTask:
    """
    [Class intent]
    Represents a task to be executed by a dispatcher thread.
    
    [Design principles]
    - Encapsulate task information
    - Support for task prioritization
    
    [Implementation details]
    - Contains target function and arguments
    - Stores creation time for diagnostics
    
    Attributes:
        target: Function to call
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        created_at: When the task was created (for diagnostics)
    """
    target: Callable
    args: tuple = ()
    kwargs: dict = None
    created_at: float = 0.0
    
    def __post_init__(self):
        """Initialize default values and record creation time"""
        if self.kwargs is None:
            self.kwargs = {}
        self.created_at = time.time()


class ThreadManager:
    """
    [Class intent]
    Manages threads for event dispatching.
    
    [Design principles]
    - Efficient thread utilization
    - Support for task prioritization
    - Graceful shutdown handling
    
    [Implementation details]
    - Maintains a pool of worker threads
    - Uses a queue for task distribution
    - Supports thread priority configuration
    """
    
    def __init__(self, num_threads: int = 1, priority: ThreadPriority = ThreadPriority.NORMAL) -> None:
        """
        [Function intent]
        Initialize a new thread manager.
        
        [Design principles]
        - Configurable thread pool size
        - Support for thread priority
        
        [Implementation details]
        - Creates task queue
        - Initializes worker threads
        
        Args:
            num_threads: Number of worker threads to create
            priority: Priority level for the worker threads
        """
        self._num_threads = max(1, num_threads)  # At least one thread
        self._priority = priority
        self._task_queue = queue.Queue()
        self._threads: List[threading.Thread] = []
        self._running = False
        self._lock = threading.RLock()
    
    def start(self) -> None:
        """
        [Function intent]
        Start the thread manager.
        
        [Design principles]
        - Automatic thread initialization
        
        [Implementation details]
        - Creates and starts worker threads
        - Sets running flag
        """
        with self._lock:
            if self._running:
                logger.warning("ThreadManager already running")
                return
            
            self._running = True
            
            for i in range(self._num_threads):
                thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name=f"FSMonitor-Worker-{i}"
                )
                self._threads.append(thread)
                thread.start()
            
            logger.debug(f"Started {self._num_threads} worker threads")
    
    def stop(self) -> None:
        """
        [Function intent]
        Stop the thread manager.
        
        [Design principles]
        - Graceful shutdown
        
        [Implementation details]
        - Clears running flag
        - Adds poison pills to task queue
        - Waits for threads to terminate
        """
        with self._lock:
            if not self._running:
                logger.debug("ThreadManager already stopped")
                return
            
            self._running = False
            
            # Add poison pills to wake up all threads
            for _ in range(self._num_threads):
                self._task_queue.put(None)
            
            # Wait for threads to terminate
            for thread in self._threads:
                if thread.is_alive():
                    thread.join(timeout=1.0)
            
            # Clear thread list
            self._threads.clear()
            logger.debug("Stopped all worker threads")
    
    def submit_task(self, target: Callable, *args, **kwargs) -> None:
        """
        [Function intent]
        Submit a task for execution by a worker thread.
        
        [Design principles]
        - Simple API for task submission
        
        [Implementation details]
        - Creates a task object
        - Adds it to the task queue
        
        Args:
            target: Function to call
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
        """
        if not self._running:
            logger.warning("ThreadManager not running, task will not be executed")
            return
        
        task = DispatchTask(target, args, kwargs)
        self._task_queue.put(task)
    
    def _worker_loop(self) -> None:
        """
        [Function intent]
        Main loop for worker threads.
        
        [Design principles]
        - Continuous task processing
        - Error handling
        
        [Implementation details]
        - Gets tasks from queue
        - Executes tasks
        - Handles errors
        """
        while self._running:
            try:
                # Get a task from the queue
                task = self._task_queue.get()
                
                # Check for poison pill
                if task is None:
                    break
                
                # Execute the task
                try:
                    task.target(*task.args, **(task.kwargs or {}))
                except Exception as e:
                    logger.error(f"Error executing task: {e}")
                finally:
                    # Mark the task as done
                    self._task_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
        
        logger.debug("Worker thread exiting")
    
    def set_thread_priority(self, priority: ThreadPriority) -> None:
        """
        [Function intent]
        Set the priority for worker threads.
        
        [Design principles]
        - Runtime configuration
        
        [Implementation details]
        - Updates the priority setting
        - This is a placeholder, actual implementation varies by platform
        
        Args:
            priority: New priority level
        """
        self._priority = priority
        
        # Actual implementation of thread priority setting depends on the platform
        # This would require platform-specific code for Windows, Linux, and macOS
        # For now, this is just a placeholder
        logger.debug(f"Thread priority set to {priority}")
    
    @property
    def is_running(self) -> bool:
        """
        [Function intent]
        Check if the thread manager is running.
        
        [Design principles]
        - State verification
        
        [Implementation details]
        - Returns the current running state
        
        Returns:
            True if the thread manager is running, False otherwise
        """
        with self._lock:
            return self._running
    
    @property
    def queue_size(self) -> int:
        """
        [Function intent]
        Get the number of tasks in the queue.
        
        [Design principles]
        - Status monitoring
        
        [Implementation details]
        - Returns the current size of the task queue
        
        Returns:
            Number of tasks waiting in the queue
        """
        return self._task_queue.qsize()
