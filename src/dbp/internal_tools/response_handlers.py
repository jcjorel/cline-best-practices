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
# Implements response parsing and formatting logic for the results returned by
# the different internal LLM tools. Includes abstract base classes and concrete
# implementations tailored to the expected output structure of each tool.
###############################################################################
# [Source file design principles]
# - Abstract base classes (`ResponseParser`, `ResultFormatter`) define common interfaces.
# - Concrete parsers handle extraction of structured data (likely JSON) from raw LLM responses.
# - Concrete formatters structure the parsed data into the final result payload for each tool.
# - Includes error handling for parsing failures.
# - Placeholder implementations return mock/example data structures.
# - Design Decision: Separate Parser/Formatter Classes per Tool (2025-04-15)
#   * Rationale: Isolates the logic for handling the specific output format of each internal tool's LLM, making it easier to adapt if LLM outputs change.
#   * Alternatives considered: Single generic parser/formatter (harder to manage tool-specific structures).
###############################################################################
# [Source file constraints]
# - Parsers rely on the LLM producing output in an expected format (e.g., JSON).
# - Formatters depend on the output structure defined by the parsers.
# - Placeholder implementations need to be replaced with actual parsing/formatting logic.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/INTERNAL_LLM_TOOLS.md
# - scratchpad/dbp_implementation_plan/plan_internal_tools.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:14:10Z : Initial creation of response handler classes by CodeAssistant
# * Implemented ABCs and concrete placeholder parsers/formatters for each tool.
###############################################################################

import logging
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ResponseParsingError(Exception):
    """Custom exception for errors during internal tool response parsing."""
    pass

# --- Abstract Base Classes ---

class ResponseParser(ABC):
    """Abstract base class for internal tool LLM response parsers."""

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        self.logger = logger_override or logger.getChild(self.__class__.__name__)

    @abstractmethod
    def parse(self, response_text: str) -> Dict[str, Any]:
        """
        Parses the raw LLM response string into a structured dictionary.

        Args:
            response_text: The raw text response from the LLM.

        Returns:
            A dictionary containing the parsed data.

        Raises:
            ResponseParsingError: If parsing fails.
        """
        pass

    def _extract_json(self, text: str) -> Optional[str]:
        """Helper to extract JSON content from text, handling markdown code fences."""
        text = text.strip()
        # Regex to find JSON within ```json ... ``` or ``` ... ``` blocks
        json_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.MULTILINE)
        match = json_pattern.search(text)
        if match:
            json_str = match.group(1).strip()
            if json_str.startswith('{') and json_str.endswith('}'):
                 self.logger.debug("Extracted JSON content from markdown code block.")
                 return json_str
            else:
                 self.logger.warning("Found markdown block, but content doesn't look like valid JSON object.")

        # If no markdown block found, check if the whole text might be JSON
        if text.startswith('{') and text.endswith('}'):
            self.logger.debug("Assuming the entire response is JSON content.")
            return text

        self.logger.warning("Could not reliably extract JSON object from the response.")
        return None


class ResultFormatter(ABC):
    """Abstract base class for formatting parsed results into the final tool output."""

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        self.logger = logger_override or logger.getChild(self.__class__.__name__)

    @abstractmethod
    def format(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the parsed data into the final result payload dictionary.

        Args:
            parsed_response: The dictionary resulting from the parsing step.

        Returns:
            A dictionary representing the final formatted result payload for the tool.
        """
        pass

# --- Concrete Implementations (Placeholders) ---

# --- Tool: coordinator_get_codebase_context ---

class CodebaseContextParser(ResponseParser):
    def parse(self, response_text: str) -> Dict[str, Any]:
        self.logger.debug("Parsing codebase context response (placeholder)...")
        # Placeholder: Assume LLM returns JSON matching expected structure
        json_content = self._extract_json(response_text)
        if not json_content:
             raise ResponseParsingError("No JSON found in codebase context response.")
        try:
            # Basic parsing, more validation could be added
            data = json.loads(json_content)
            if not isinstance(data, dict): raise ValueError("Parsed data is not a dictionary")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse codebase context JSON: {e}")
            raise ResponseParsingError(f"Invalid JSON in codebase context response: {e}") from e

class CodebaseContextFormatter(ResultFormatter):
    def format(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.debug("Formatting codebase context result (placeholder)...")
        # Placeholder: Return parsed data, maybe add some metadata
        return {
            "relevant_files": parsed_response.get("relevant_files", []),
            "codebase_organization": parsed_response.get("codebase_organization", {}),
        }

# --- Tool: coordinator_get_codebase_changelog_context ---

class CodebaseChangelogParser(ResponseParser):
     def parse(self, response_text: str) -> Dict[str, Any]:
        self.logger.debug("Parsing codebase changelog response (placeholder)...")
        json_content = self._extract_json(response_text)
        if not json_content:
             raise ResponseParsingError("No JSON found in codebase changelog response.")
        try:
            data = json.loads(json_content)
            if not isinstance(data, dict): raise ValueError("Parsed data is not a dictionary")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse codebase changelog JSON: {e}")
            raise ResponseParsingError(f"Invalid JSON in codebase changelog response: {e}") from e

class CodebaseChangelogFormatter(ResultFormatter):
     def format(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.debug("Formatting codebase changelog result (placeholder)...")
        return {
            "recent_changes": parsed_response.get("recent_changes", []),
        }

# --- Tool: coordinator_get_documentation_context ---

class DocumentationContextParser(ResponseParser):
     def parse(self, response_text: str) -> Dict[str, Any]:
        self.logger.debug("Parsing documentation context response (placeholder)...")
        json_content = self._extract_json(response_text)
        if not json_content:
             raise ResponseParsingError("No JSON found in documentation context response.")
        try:
            data = json.loads(json_content)
            if not isinstance(data, dict): raise ValueError("Parsed data is not a dictionary")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse documentation context JSON: {e}")
            raise ResponseParsingError(f"Invalid JSON in documentation context response: {e}") from e

class DocumentationContextFormatter(ResultFormatter):
     def format(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.debug("Formatting documentation context result (placeholder)...")
        return {
            "relevant_docs": parsed_response.get("relevant_docs", []),
            "relationships": parsed_response.get("relationships", {}),
        }

# --- Tool: coordinator_get_documentation_changelog_context ---

class DocumentationChangelogParser(ResponseParser):
     def parse(self, response_text: str) -> Dict[str, Any]:
        self.logger.debug("Parsing documentation changelog response (placeholder)...")
        json_content = self._extract_json(response_text)
        if not json_content:
             raise ResponseParsingError("No JSON found in documentation changelog response.")
        try:
            data = json.loads(json_content)
            if not isinstance(data, dict): raise ValueError("Parsed data is not a dictionary")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse documentation changelog JSON: {e}")
            raise ResponseParsingError(f"Invalid JSON in documentation changelog response: {e}") from e

class DocumentationChangelogFormatter(ResultFormatter):
     def format(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.debug("Formatting documentation changelog result (placeholder)...")
        return {
            "recent_doc_changes": parsed_response.get("recent_doc_changes", []),
        }

# --- Tool: coordinator_get_expert_architect_advice ---

class ExpertAdviceParser(ResponseParser):
     def parse(self, response_text: str) -> Dict[str, Any]:
        self.logger.debug("Parsing expert advice response (placeholder)...")
        # This tool might return less structured text, or JSON. Assume JSON for now.
        json_content = self._extract_json(response_text)
        if not json_content:
             # Fallback: if no JSON, return the raw text under an 'advice_text' key
             self.logger.warning("No JSON found in expert advice response, returning raw text.")
             return {"advice_text": response_text.strip()}
        try:
            data = json.loads(json_content)
            if not isinstance(data, dict): raise ValueError("Parsed data is not a dictionary")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse expert advice JSON: {e}. Returning raw text.")
            # Fallback to raw text if JSON parsing fails
            return {"advice_text": response_text.strip()}


class ExpertAdviceFormatter(ResultFormatter):
     def format(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.debug("Formatting expert advice result (placeholder)...")
        # Pass through the parsed structure, whether it was JSON or the raw text fallback
        return parsed_response
