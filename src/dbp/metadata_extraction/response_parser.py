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
# Implements the ResponseParser class, responsible for parsing the raw text
# response received from the LLM (via BedrockClient). It extracts the expected
# JSON payload, potentially from within markdown code blocks, and performs
# initial validation against the expected metadata structure.
###############################################################################
# [Source file design principles]
# - Handles common LLM response formats (plain JSON, JSON within markdown ```json ... ``` blocks).
# - Uses standard `json` library for parsing.
# - Includes basic schema validation checks (e.g., presence of required keys).
# - Provides specific error types for parsing and validation failures.
# - Logs relevant information during parsing and validation.
# - Design Decision: Regex for JSON Extraction (2025-04-15)
#   * Rationale: Simple and effective way to handle JSON potentially wrapped in markdown code fences, a common LLM output pattern.
#   * Alternatives considered: More complex parsing libraries (overkill), Assuming plain JSON (brittle).
###############################################################################
# [Source file constraints]
# - Relies on the LLM generally adhering to the instruction to output JSON.
# - Basic validation currently only checks for top-level keys; more robust validation
#   could be added using Pydantic models if needed later.
# - Assumes UTF-8 encoding for the LLM response.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/DATA_MODEL.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:51:55Z : Initial creation of ResponseParser class by CodeAssistant
# * Implemented JSON extraction from text and basic validation logic.
# 2025-04-15T18:04:24Z : Fixed missing import in ResponseParser by CodeAssistant
# * Added Optional type import from typing module.
###############################################################################

import json
import logging
import re
from typing import Dict, Any, Optional

# Import Pydantic's validation error for potential future use or consistency
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class ResponseParsingError(Exception):
    """Custom exception for errors during LLM response parsing (JSON decoding)."""
    pass

class ResponseValidationError(Exception):
    """Custom exception for errors when LLM response fails schema validation."""
    pass

class ResponseParser:
    """
    Parses raw text responses from an LLM, expecting a JSON payload,
    potentially embedded within markdown code blocks. Performs basic validation.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ResponseParser.

        Args:
            logger_override: Optional logger instance to use.
        """
        self.logger = logger_override or logger
        # Regex to find JSON within ```json ... ``` or ``` ... ``` blocks
        self._json_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.MULTILINE)
        self.logger.debug("ResponseParser initialized.")

    def parse(self, llm_response: str, file_path: Optional[str] = "unknown_file") -> Dict[str, Any]:
        """
        Parses the LLM's text response to extract and validate the JSON metadata.

        Args:
            llm_response: The raw string response from the LLM.
            file_path: The path of the source file being processed (for logging context).

        Returns:
            A dictionary containing the parsed metadata.

        Raises:
            ResponseParsingError: If the response cannot be parsed as JSON.
            ResponseValidationError: If the parsed JSON fails basic schema validation.
        """
        self.logger.debug(f"Parsing LLM response for: {file_path} (length: {len(llm_response)})")
        if not llm_response or not llm_response.strip():
             self.logger.error(f"LLM response for {file_path} is empty.")
             raise ResponseParsingError("Received empty response from LLM.")

        try:
            # 1. Extract JSON content
            json_content = self._extract_json(llm_response)
            if not json_content:
                 self.logger.error(f"Could not extract JSON content from LLM response for {file_path}.")
                 self.logger.debug(f"Raw LLM response for {file_path}:\n{llm_response[:500]}...") # Log snippet
                 raise ResponseParsingError("No JSON content found in LLM response.")

            # 2. Parse JSON string into Python dictionary
            parsed_data = json.loads(json_content)
            if not isinstance(parsed_data, dict):
                 # Should be caught by json.loads, but double-check
                 raise ResponseParsingError("Parsed JSON content is not a dictionary.")

            # 3. Basic Validation (can be expanded)
            self._validate_response_schema(parsed_data, file_path)

            self.logger.info(f"Successfully parsed and validated LLM response for: {file_path}")
            return parsed_data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON from LLM response for {file_path}: {e}")
            self.logger.debug(f"Extracted content attempted for JSON parsing:\n{json_content[:500]}...")
            raise ResponseParsingError(f"Failed to parse LLM response as JSON: {e}") from e
        # Catch validation errors specifically
        except ResponseValidationError as e:
             # Already logged in _validate_response_schema
             raise e
        except Exception as e:
            # Catch any other unexpected errors during parsing/validation
            self.logger.error(f"Unexpected error parsing response for {file_path}: {e}", exc_info=True)
            raise ResponseParsingError(f"Unexpected error during response parsing: {e}") from e


    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extracts JSON content from text, handling potential markdown code fences.

        Args:
            text: The raw text potentially containing JSON.

        Returns:
            The extracted JSON string, or None if no valid JSON block is found.
        """
        text = text.strip()

        # Try finding JSON within markdown code blocks first
        match = self._json_pattern.search(text)
        if match:
            json_str = match.group(1).strip()
            # Basic check for valid JSON structure
            if json_str.startswith('{') and json_str.endswith('}'):
                 self.logger.debug("Extracted JSON content from markdown code block.")
                 return json_str
            else:
                 self.logger.warning("Found markdown block, but content doesn't look like valid JSON object.")

        # If no markdown block found or content invalid, assume the whole text might be JSON
        # Basic check: does it start with { and end with }?
        if text.startswith('{') and text.endswith('}'):
            self.logger.debug("Assuming the entire response is JSON content.")
            return text

        self.logger.warning("Could not reliably extract JSON object from the response.")
        return None


    def _validate_response_schema(self, data: Dict[str, Any], file_path: str):
        """
        Performs basic validation on the parsed JSON data.
        Checks for the presence of essential top-level keys.

        Args:
            data: The parsed dictionary from the LLM response.
            file_path: The path of the source file (for logging).

        Raises:
            ResponseValidationError: If validation fails.
        """
        self.logger.debug(f"Performing basic validation on parsed response for: {file_path}")
        required_keys = ["language", "headerSections", "functions", "classes"]
        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            error_msg = f"LLM response for {file_path} is missing required top-level keys: {', '.join(missing_keys)}"
            self.logger.error(error_msg)
            # Log snippet of data for context
            self.logger.debug(f"Parsed data keys: {list(data.keys())}")
            raise ResponseValidationError(error_msg)

        # Add more specific checks if needed (e.g., types of values)
        if not isinstance(data.get("headerSections"), dict):
             raise ResponseValidationError(f"Invalid type for 'headerSections' in response for {file_path} (expected dict).")
        if not isinstance(data.get("functions"), list):
             raise ResponseValidationError(f"Invalid type for 'functions' in response for {file_path} (expected list).")
        if not isinstance(data.get("classes"), list):
             raise ResponseValidationError(f"Invalid type for 'classes' in response for {file_path} (expected list).")

        self.logger.debug(f"Basic validation passed for: {file_path}")
        # Note: More detailed validation against Pydantic models would happen
        # in the ExtractionResultProcessor.
