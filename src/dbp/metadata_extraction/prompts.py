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
# Implements the LLMPromptManager class, responsible for loading and formatting
# prompts used to instruct the LLM (Amazon Nova Lite) for metadata extraction
# from source code files. It combines template text with file-specific information.
###############################################################################
# [Source file design principles]
# - Centralizes prompt management logic.
# - Loads prompt templates from external files (or uses defaults if files are missing).
# - Dynamically inserts file path, content, and expected output schema into the template.
# - Handles potential errors during template loading.
# - Design Decision: Template-Based Prompts (2025-04-15)
#   * Rationale: Allows easy modification and tuning of LLM instructions without changing code. Separates prompt engineering from core logic.
#   * Alternatives considered: Hardcoding prompts (less flexible).
###############################################################################
# [Source file constraints]
# - Requires access to configuration for template file paths.
# - Assumes template files exist at the specified paths or provides defaults.
# - Prompt effectiveness depends heavily on the quality of the templates and the LLM's capabilities.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/DATA_MODEL.md
# - scratchpad/dbp_implementation_plan/plan_metadata_extraction.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:50:50Z : Initial creation of LLMPromptManager class by CodeAssistant
# * Implemented template loading (with defaults) and prompt formatting logic.
###############################################################################

import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Default Templates (Used if files are not found) ---

DEFAULT_EXTRACTION_PROMPT_TEMPLATE = """
Analyze the following source code file and extract metadata based on the provided JSON schema. Focus on documentation within header comments and docstrings. Infer the programming language.

FILE PATH: {file_path}
FILE EXTENSION: {file_extension}

EXPECTED JSON OUTPUT SCHEMA:
```json
{output_schema}
```

FILE CONTENT:
```
{file_content}
```

EXTRACTED METADATA (JSON format):
"""

DEFAULT_OUTPUT_SCHEMA_TEMPLATE = """
{
  "path": "string (should match input file_path)",
  "language": "string (e.g., 'Python', 'JavaScript', 'Java')",
  "headerSections": {
    "intent": "string | null",
    "designPrinciples": ["string"],
    "constraints": ["string"],
    "referenceDocumentation": ["string"],
    "changeHistory": [
      {
        "timestamp": "string (ISO8601 format, e.g., YYYY-MM-DDTHH:MM:SSZ) | null",
        "summary": "string | null",
        "details": ["string"]
      }
    ]
  },
  "functions": [
    {
      "name": "string",
      "docSections": {
        "intent": "string | null",
        "designPrinciples": ["string"],
        "implementationDetails": "string | null",
        "designDecisions": "string | null"
      },
      "parameters": ["string"],
      "lineRange": {"start": "number | null", "end": "number | null"}
    }
  ],
  "classes": [
    {
      "name": "string",
      "docSections": { /* Same structure as function docSections */ },
      "methods": [ /* Same structure as functions */ ],
      "lineRange": {"start": "number | null", "end": "number | null"}
    }
  ]
}
"""

# --- End Default Templates ---

class TemplateLoadError(Exception):
    """Custom exception for errors during template loading."""
    pass

class LLMPromptManager:
    """
    Manages the creation and formatting of prompts for LLM-based metadata extraction.
    Loads templates from configured file paths or uses internal defaults.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the LLMPromptManager.

        Args:
            config: Configuration object providing template paths. Expected keys:
                    'metadata_extraction.extraction_prompt_template',
                    'metadata_extraction.output_schema_template'. Can be None to use defaults.
            logger_override: Optional logger instance to use instead of the default.
        """
        self.config = config
        self.logger = logger_override or logger # Use provided logger or the module logger

        # Determine template paths from config or use defaults
        # Using .get() on config assumes it's dict-like or has a get method
        extraction_template_path = self.config.get('metadata_extraction.extraction_prompt_template', None) if self.config else None
        output_schema_path = self.config.get('metadata_extraction.output_schema_template', None) if self.config else None

        # Load templates, falling back to defaults if paths are invalid or loading fails
        self.extraction_template = self._load_template(extraction_template_path, DEFAULT_EXTRACTION_PROMPT_TEMPLATE)
        self.output_schema = self._load_template(output_schema_path, DEFAULT_OUTPUT_SCHEMA_TEMPLATE)
        self.logger.debug("LLMPromptManager initialized.")

    def _load_template(self, path: Optional[str], default_template: str) -> str:
        """
        Loads a template from the given file path. Uses the default template if
        the path is None, not found, or fails to load.

        Args:
            path: The file path to the template.
            default_template: The default template content to use on failure.

        Returns:
            The content of the loaded template or the default template.
        """
        if path:
            try:
                # Ensure path is absolute or resolve relative to a known location if needed
                # For now, assume path is absolute or relative to CWD
                template_path = os.path.abspath(path)
                self.logger.info(f"Attempting to load template from: {template_path}")
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content:
                     self.logger.info(f"Successfully loaded template: {path}")
                     return content
                else:
                     self.logger.warning(f"Template file is empty: {path}. Using default.")
            except FileNotFoundError:
                self.logger.warning(f"Template file not found: {path}. Using default.")
            except Exception as e:
                self.logger.error(f"Failed to load template file {path}: {e}. Using default.", exc_info=True)
        else:
             self.logger.info("No template path provided. Using default template.")

        # Return default if path is None or loading failed
        return default_template

    def create_extraction_prompt(self, file_path: str, file_content: str) -> str:
        """
        Creates the final extraction prompt by formatting the loaded template
        with file-specific information and the expected output schema.

        Args:
            file_path: The absolute path to the source code file.
            file_content: The content of the source code file.

        Returns:
            The formatted prompt string ready to be sent to the LLM.

        Raises:
            ValueError: If required formatting keys are missing in the template.
        """
        self.logger.debug(f"Creating extraction prompt for: {file_path}")
        try:
            # Get file extension to potentially help the LLM identify the language
            _, extension = os.path.splitext(file_path)

            # Format the prompt using the loaded templates
            prompt = self.extraction_template.format(
                file_path=file_path,
                file_extension=extension,
                file_content=file_content,
                output_schema=self.output_schema # Embed the schema definition
            )
            self.logger.debug(f"Formatted prompt created for {file_path} (length: {len(prompt)}).")
            return prompt
        except KeyError as e:
            self.logger.error(f"Missing key in extraction prompt template: {e}. Check template file content.")
            raise ValueError(f"Extraction prompt template is missing required key: {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to format extraction prompt for {file_path}: {e}", exc_info=True)
            # Return a fallback prompt or raise? Raising is safer.
            raise RuntimeError(f"Failed to create extraction prompt for {file_path}") from e
