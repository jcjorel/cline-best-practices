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
# Implements the PromptLoader utility class, responsible for loading prompt
# template files from a specified directory. It includes basic caching to avoid
# redundant file reads. Used by the InternalToolsComponent to load prompts for
# each specialized internal tool.
###############################################################################
# [Source file design principles]
# - Centralizes the logic for loading prompt files.
# - Takes the base directory for prompts during initialization.
# - Caches loaded prompts in memory to improve performance.
# - Handles file not found and read errors gracefully.
# - Design Decision: Simple File Loader with Cache (2025-04-15)
#   * Rationale: Straightforward approach for managing external prompt files. Caching reduces disk I/O.
#   * Alternatives considered: More complex resource management system (overkill).
###############################################################################
# [Source file constraints]
# - Assumes prompt files are UTF-8 encoded text files.
# - Requires the prompt directory path to be correctly configured and accessible.
# - Cache is simple and doesn't handle file updates automatically (requires re-initialization).
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/INTERNAL_LLM_TOOLS.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:14:45Z : Initial creation of PromptLoader class by CodeAssistant
# * Implemented prompt loading from file with basic caching and error handling.
###############################################################################

import os
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PromptLoadError(Exception):
    """Custom exception for errors loading prompt files."""
    pass

class PromptLoader:
    """
    Utility class responsible for loading prompt template files from a specified directory.
    Includes simple in-memory caching.
    """

    def __init__(self, prompt_dir: str, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the PromptLoader.

        Args:
            prompt_dir: The base directory where prompt template files are located.
            logger_override: Optional logger instance.

        Raises:
            ValueError: If the prompt directory does not exist or is not a directory.
        """
        self.logger = logger_override or logger
        try:
            self._prompt_dir = Path(prompt_dir).resolve(strict=True) # Ensure path exists
            if not self._prompt_dir.is_dir():
                raise ValueError(f"Prompt directory path is not a directory: {self._prompt_dir}")
        except FileNotFoundError:
             self.logger.error(f"Prompt template directory not found: {prompt_dir}")
             raise ValueError(f"Prompt directory not found: {prompt_dir}")
        except Exception as e:
             self.logger.error(f"Error resolving prompt directory '{prompt_dir}': {e}", exc_info=True)
             raise ValueError(f"Invalid prompt directory path: {prompt_dir}") from e

        self._cache: Dict[str, str] = {} # Cache for loaded prompts: prompt_name -> content
        self.logger.debug(f"PromptLoader initialized with directory: {self._prompt_dir}")

    def load_prompt(self, prompt_filename: str) -> str:
        """
        Loads a prompt template from a file within the configured prompt directory.
        Uses cached version if available.

        Args:
            prompt_filename: The name of the prompt file (e.g., 'my_prompt.txt').

        Returns:
            The content of the prompt template file as a string.

        Raises:
            PromptLoadError: If the file cannot be found or read.
        """
        if not prompt_filename:
            raise ValueError("prompt_filename cannot be empty.")

        # Check cache first
        if prompt_filename in self._cache:
            self.logger.debug(f"Loading prompt '{prompt_filename}' from cache.")
            return self._cache[prompt_filename]

        # Construct full path
        prompt_path = self._prompt_dir / prompt_filename

        self.logger.info(f"Loading prompt template from file: {prompt_path}")
        try:
            if not prompt_path.is_file():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            if not prompt_template.strip():
                 self.logger.warning(f"Prompt file '{prompt_filename}' is empty.")
                 # Return empty string or raise error? Let's return empty for now.

            # Cache the loaded prompt
            self._cache[prompt_filename] = prompt_template
            self.logger.info(f"Successfully loaded and cached prompt: {prompt_filename}")
            return prompt_template

        except FileNotFoundError as e:
            self.logger.error(f"Prompt file not found: {prompt_path}")
            raise PromptLoadError(f"Prompt file '{prompt_filename}' not found at {prompt_path}") from e
        except IOError as e:
            self.logger.error(f"Error reading prompt file {prompt_path}: {e}")
            raise PromptLoadError(f"Could not read prompt file '{prompt_filename}': {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error loading prompt {prompt_filename} from {prompt_path}: {e}", exc_info=True)
            raise PromptLoadError(f"Unexpected error loading prompt '{prompt_filename}'") from e

    def clear_cache(self):
        """Clears the internal prompt cache."""
        self._cache = {}
        self.logger.info("PromptLoader cache cleared.")
