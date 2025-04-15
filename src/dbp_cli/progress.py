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
###############################################################################

import sys
import threading
import time
import logging

logger = logging.getLogger(__name__)

class ProgressIndicator:
    """Displays a simple spinner animation in the console for long-running tasks."""

    def __init__(self, message: str = "Processing...", delay: float = 0.1):
        """
        Initializes the ProgressIndicator.

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
        """The target function for the animation thread."""
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
        """Starts the progress indicator animation in a background thread."""
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
        """Stops the progress indicator animation."""
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
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
