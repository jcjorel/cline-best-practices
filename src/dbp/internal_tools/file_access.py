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
# Implements a simple FileAccessService utility class providing basic, safe
# file system operations (listing files, reading files) required by the
# Internal LLM Tools, particularly the Context Assemblers. It abstracts
# direct os/pathlib calls for potentially easier testing or future enhancement
# (e.g., adding security checks, caching).
###############################################################################
# [Source file design principles]
# - Provides a simple, focused interface for file operations.
# - Uses standard Python libraries (`os`, `pathlib`).
# - Includes basic error handling and logging for file operations.
# - Assumes operations are relative to the application's current working
#   directory or a specified project root if integrated later.
# - Design Decision: Simple Service Class (2025-04-15)
#   * Rationale: Encapsulates file operations used by multiple assemblers.
#   * Alternatives considered: Direct `os` calls in assemblers (less reusable, harder to test).
###############################################################################
# [Source file constraints]
# - File operations are subject to filesystem permissions.
# - Error handling for file access is basic; might need enhancement.
# - Assumes UTF-8 encoding for reading files.
# - Listing files recursively can be slow on very large directories.
###############################################################################
# [Dependencies]
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:11:30Z : Initial creation of FileAccessService by CodeAssistant
# * Implemented list_files and read_file methods.
###############################################################################

import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class FileAccessService:
    """
    Provides basic utility functions for accessing the file system safely.
    Used by context assemblers to retrieve file lists and content.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None, base_path: Optional[str] = None):
        """
        Initializes the FileAccessService.

        Args:
            logger_override: Optional logger instance.
            base_path: Optional base path to resolve relative paths against. Defaults to CWD.
        """
        self.logger = logger_override or logger
        # Resolve the base path immediately
        try:
            self._base_path = Path(base_path).resolve() if base_path else Path.cwd()
        except Exception as e:
            self.logger.error(f"Invalid base_path provided: {base_path}. Defaulting to CWD. Error: {e}")
            self._base_path = Path.cwd()
        self.logger.debug(f"FileAccessService initialized with base path: {self._base_path}")

    def _resolve_path(self, relative_or_absolute_path: str) -> Path:
        """Resolves a given path against the base path."""
        path = Path(relative_or_absolute_path)
        if path.is_absolute():
            # If absolute, ensure it's within the intended scope if necessary (security)
            # For now, allow absolute paths but log a warning if outside base_path?
            # if not path.is_relative_to(self._base_path): # Python 3.9+
            if not str(path).startswith(str(self._base_path)):
                 self.logger.warning(f"Accessing absolute path outside base path: {path}")
            return path.resolve()
        else:
            # Resolve relative path against the base path
            return (self._base_path / path).resolve()

    def list_files(self, directory: str = "") -> List[str]:
        """
        Lists all files recursively within a given directory relative to the base path.

        Args:
            directory: The subdirectory relative to the base path. If empty, lists
                       from the base path.

        Returns:
            A list of file paths relative to the base path. Returns empty list on error.
        """
        start_path = self._resolve_path(directory)
        self.logger.debug(f"Listing files recursively under: {start_path}")
        relative_files: List[str] = []

        if not start_path.is_dir():
            self.logger.warning(f"Directory not found for listing: {start_path}")
            return []

        try:
            for item in start_path.rglob('*'): # Recursively find all items
                if item.is_file():
                    try:
                        # Store path relative to the original base_path
                        relative_path_str = str(item.relative_to(self._base_path)).replace(os.sep, '/')
                        relative_files.append(relative_path_str)
                    except ValueError:
                         # Should not happen if item is under start_path which is under _base_path
                         self.logger.warning(f"Could not make path relative: {item}")
                    except Exception as e_rel:
                         self.logger.error(f"Error making path relative {item}: {e_rel}")

            self.logger.debug(f"Found {len(relative_files)} files under {start_path}.")
            return relative_files
        except PermissionError:
            self.logger.error(f"Permission denied listing files in: {start_path}")
            return []
        except Exception as e:
            self.logger.error(f"Error listing files in {start_path}: {e}", exc_info=True)
            return []

    def read_file(self, file_path_rel: str) -> str:
        """
        Reads the content of a file specified by a path relative to the base path.

        Args:
            file_path_rel: The path to the file, relative to the base path.

        Returns:
            The content of the file as a string.

        Raises:
            FileNotFoundError: If the file does not exist at the resolved path.
            IOError: If the file cannot be read due to permissions or other issues.
            Exception: For other unexpected errors.
        """
        absolute_path = self._resolve_path(file_path_rel)
        self.logger.debug(f"Reading file content from: {absolute_path}")

        try:
            # Check if it exists and is a file before attempting to read
            if not absolute_path.is_file():
                raise FileNotFoundError(f"File not found or is not a regular file: {absolute_path}")

            with open(absolute_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            self.logger.debug(f"Successfully read {len(content)} bytes from {absolute_path}.")
            return content
        except FileNotFoundError as e:
             self.logger.error(f"File not found: {absolute_path}")
             raise e # Re-raise specific error
        except PermissionError as e:
            self.logger.error(f"Permission denied reading file: {absolute_path}")
            raise IOError(f"Permission denied for file: {absolute_path}") from e
        except Exception as e:
            self.logger.error(f"Error reading file {absolute_path}: {e}", exc_info=True)
            raise IOError(f"Could not read file {absolute_path}: {e}") from e # Raise generic IOError for other issues
