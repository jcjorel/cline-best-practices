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
# Implements a simple ProgressIndicator class using a spinning character animation
# to provide visual feedback for long-running CLI operations. Runs in a separate thread.
###############################################################################
# [Source file design principles]
# - Simple text-based spinner animation.
# - Runs in a background daemon thread.
# - Provides `start` and `stop` methods.
# - Cleans up the output line upon stopping.
###############################################################################
# [Source file constraints]
# - Assumes running in a TTY environment for correct display.
# - Animation is basic and might not be suitable for all terminal types.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T11:00:35Z : Initial creation of ProgressIndicator class by CodeAssistant
# * Implemented basic spinner animation in a background thread.
# 2025-04-15T14:09:00Z : Fixed missing import for Optional type by CodeAssistant
# * Added import from typing import Optional to fix NameError
###############################################################################

import sys
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ProgressIndicator:
    """
    [Class intent]
    Displays a simple spinner animation in the console to provide visual feedback
    during long-running CLI operations, enhancing user experience by indicating
    ongoing activity.
    
    [Implementation details]
    Implements a text-based spinner using a rotating character sequence that runs
    in a separate daemon thread. Manages the animation lifecycle through start/stop
    methods and cleans up the display when stopped. Supports both direct method
    calls and context manager usage (with statement).
    
    [Design principles]
    Thread safety - uses proper synchronization to prevent race conditions.
    Resource cleanup - ensures proper termination and display cleanup.
    Non-blocking operation - runs animation in background thread.
    User experience - provides visual feedback without blocking main operations.
    """

    def __init__(self, message: str = "Processing...", delay: float = 0.1):
        """
        [Function intent]
        Initialize the progress indicator with customizable message and animation speed.

        [Implementation details]
        Sets up the spinner character sequence, initial message, delay between frames,
        and creates thread synchronization objects (event and lock) for safe operation.
        Also initializes thread and active state tracking variables.

        [Design principles]
        Thread safety - uses proper synchronization primitives (lock, event).
        Customizable - allows setting custom message and animation speed.
        Configurable defaults - provides reasonable default values.

        Args:
            message: The message to display next to the spinner.
            delay: The delay between animation frames in seconds.
        """
        self.spinner_chars = "|/-\\"
        self.delay = delay
        self.message = message
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock() # To protect access to active flag
        self._active = False

    def _animate(self):
        """
        [Function intent]
        Display and animate the spinner character sequence in a loop until stopped.

        [Implementation details]
        Runs in a separate thread and continuously displays an animated spinner.
        Characters rotate through the spinner_chars sequence at regular intervals.
        Writes directly to stderr to avoid interfering with command output on stdout.
        When stopping, clears the line to maintain a clean console.

        [Design principles]
        Non-blocking UI - runs in a background thread to avoid blocking main execution.
        Output isolation - writes to stderr instead of stdout to avoid output conflicts.
        Clean termination - clears the line when stopped to maintain clean console output.
        """
        char_index = 0
        while not self._stop_event.is_set():
            char = self.spinner_chars[char_index % len(self.spinner_chars)]
            # Write to stderr to avoid interfering with command output on stdout
            sys.stderr.write(f"\r{self.message} {char} ")
            sys.stderr.flush()
            char_index += 1
            time.sleep(self.delay)

        # Clear the line when stopped
        sys.stderr.write("\r" + " " * (len(self.message) + 5) + "\r")
        sys.stderr.flush()

    def start(self, message: Optional[str] = None):
        """
        [Function intent]
        Start displaying the animated progress indicator in a background thread.

        [Implementation details]
        Sets the display message if provided, otherwise uses the current message.
        Creates and starts a daemon thread that runs the _animate method.
        Uses thread-safe mechanisms to prevent multiple concurrent animations.
        Sets the active flag to track the animation state.

        [Design principles]
        Thread safety - uses lock to protect shared state.
        Resource efficiency - returns immediately if already running.
        User experience - allows changing the message on restart.

        Args:
            message: Optional new message to display next to the spinner
        """
        with self._lock:
            if self._active:
                # logger.debug("Progress indicator already active.")
                return # Already running
            if message:
                self.message = message
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
            self._active = True
            # logger.debug("Progress indicator started.")

    def stop(self):
        """
        [Function intent]
        Stop the progress indicator animation and clean up resources.

        [Implementation details]
        Signals the animation thread to stop using the stop event.
        Waits briefly for the thread to finish but continues if it doesn't.
        Cleans up resources and resets the thread reference and active state.
        Uses thread-safe mechanisms to handle concurrent stop calls.

        [Design principles]
        Thread safety - uses lock to protect shared state.
        Resource cleanup - joins the thread and clears references.
        Graceful degradation - logs warning but continues if thread doesn't join.
        Idempotent - safe to call multiple times or when not running.
        """
        with self._lock:
            if not self._active:
                # logger.debug("Progress indicator already stopped.")
                return # Already stopped
            self._stop_event.set()
            active_thread = self._thread # Capture thread locally before clearing

        if active_thread:
            active_thread.join(timeout=self.delay * 2) # Wait briefly for thread to finish
            if active_thread.is_alive():
                 logger.warning("Progress indicator thread did not join cleanly.")

        with self._lock:
             self._thread = None
             self._active = False
        # logger.debug("Progress indicator stopped.")

    def __enter__(self):
        """
        [Function intent]
        Start the progress indicator when entering a context manager block.

        [Implementation details]
        Calls the start() method to begin the animation.
        Returns self to allow context variable assignment.

        [Design principles]
        Context manager protocol - implements standard __enter__ method.
        Delegation - reuses the start() method logic.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        [Function intent]
        Stop the progress indicator when exiting a context manager block.

        [Implementation details]
        Calls the stop() method to end the animation.
        Handles any exception type without suppressing it.

        [Design principles]
        Context manager protocol - implements standard __exit__ method.
        Delegation - reuses the stop() method logic.
        Exception transparency - doesn't suppress exceptions.

        Args:
            exc_type: Exception type if an exception was raised in the with block, None otherwise
            exc_val: Exception value if an exception was raised in the with block, None otherwise
            exc_tb: Exception traceback if an exception was raised in the with block, None otherwise
        """
        self.stop()
