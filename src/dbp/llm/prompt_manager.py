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
# Implements the LLMPromptManager class, a generic utility for loading and
# formatting prompt templates for use with Large Language Models across the
# application. It provides a centralized mechanism for managing prompt templates
# stored in the doc/llm/prompts/ directory.
###############################################################################
# [Source file design principles]
# - Centralizes prompt management logic across the application.
# - Loads prompt templates exclusively from doc/llm/prompts directory.
# - Provides a simple interface for formatting prompts with variables.
# - Strict error handling with no fallbacks for missing templates.
# - Design Decision: Template-Based Prompts (2025-04-16)
#   * Rationale: Separates prompt engineering from core logic, allows for easier iteration
#     and refinement of prompts without code changes.
#   * Alternatives considered: Hardcoding prompts (less flexible), per-component prompt managers.
###############################################################################
# [Source file constraints]
# - All templates must be located in doc/llm/prompts/ directory.
# - Templates must include expected output format instructions for the LLM.
# - No fallback implementations if templates are missing.
# - Templates must be valid markdown or text files.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
# codebase:- doc/llm/prompts/README.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T11:58:00Z : Initial creation of LLMPromptManager class by Cline
# * Created generic prompt manager with strict template loading requirements.
###############################################################################

import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Constants
PROMPTS_DIR = "doc/llm/prompts"


class PromptLoadError(Exception):
    """Custom exception for errors during prompt template loading."""
    pass


class LLMPromptManager:
    """
    Manages loading and formatting of prompt templates for LLMs across the application.
    Templates are loaded exclusively from doc/llm/prompts/ directory with strict error
    handling (no fallbacks) for missing templates.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the LLMPromptManager.

        [Function intent]
        Creates a new prompt manager instance that will load templates from the
        doc/llm/prompts directory.

        Args:
            config: Configuration object (may contain overrides for prompt paths).
            logger_override: Optional logger instance to use instead of the default.
        """
        self.config = config or {}
        self.logger = logger_override or logger
        
        # Initialize template cache
        self.template_cache = {}
        self.logger.debug("LLMPromptManager initialized.")

    def get_prompt_template(self, template_name: str) -> str:
        """
        Loads a prompt template from the doc/llm/prompts directory.
        
        [Function intent]
        Retrieves the content of a prompt template file, caching results for
        efficiency. Strict error handling ensures that missing templates
        raise appropriate exceptions rather than using fallbacks.
        
        Args:
            template_name: The name of the template file (with or without extension).
                          Example: "coordinator_general_query_classifier"

        Returns:
            The content of the template as a string.

        Raises:
            PromptLoadError: If the template file cannot be found or loaded.
        """
        # Check if template is already cached
        if template_name in self.template_cache:
            return self.template_cache[template_name]
        
        # Normalize template name to ensure we have the right extension
        if not (template_name.endswith('.md') or template_name.endswith('.txt')):
            template_name_md = f"{template_name}.md"
            template_name_txt = f"{template_name}.txt"
            
            # Try both common extensions
            if os.path.exists(os.path.join(PROMPTS_DIR, template_name_md)):
                template_name = template_name_md
            elif os.path.exists(os.path.join(PROMPTS_DIR, template_name_txt)):
                template_name = template_name_txt
            else:
                template_name = template_name_md  # Default to .md if not found
        
        # Construct full path to template file
        template_path = os.path.join(PROMPTS_DIR, template_name)
        
        try:
            self.logger.debug(f"Loading prompt template: {template_path}")
            
            if not os.path.exists(template_path):
                raise PromptLoadError(f"Prompt template not found: {template_path}")
                
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                raise PromptLoadError(f"Prompt template is empty: {template_path}")
                
            # Cache the template for future use
            self.template_cache[template_name] = content
            
            self.logger.debug(f"Successfully loaded template: {template_name} ({len(content)} chars)")
            return content
            
        except Exception as e:
            if isinstance(e, PromptLoadError):
                # Re-raise our custom exception
                raise
            # Wrap other exceptions in our custom exception
            raise PromptLoadError(f"Failed to load prompt template '{template_name}': {str(e)}") from e

    def format_prompt(self, template_name: str, **kwargs) -> str:
        """
        Loads a prompt template and formats it with the provided variables.
        
        [Function intent]
        Creates a formatted prompt by loading a template and substituting
        the provided variables into the template placeholders.
        
        Args:
            template_name: The name of the template file (with or without extension).
            **kwargs: Variables to format into the template.

        Returns:
            The formatted prompt as a string.

        Raises:
            PromptLoadError: If the template file cannot be found or loaded.
            KeyError: If the template contains placeholders not provided in kwargs.
        """
        template = self.get_prompt_template(template_name)
        
        try:
            formatted_prompt = template.format(**kwargs)
            self.logger.debug(f"Formatted prompt '{template_name}' successfully ({len(formatted_prompt)} chars)")
            return formatted_prompt
        except KeyError as e:
            self.logger.error(f"Missing key in template formatting: {e}")
            raise KeyError(f"Prompt template '{template_name}' requires '{e}' but it was not provided") from e
        except Exception as e:
            self.logger.error(f"Failed to format prompt: {e}")
            raise RuntimeError(f"Failed to format prompt template '{template_name}': {str(e)}") from e
