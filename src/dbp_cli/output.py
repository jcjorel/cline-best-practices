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
# Implements the OutputFormatter class for the DBP CLI. This class is responsible
# for taking structured data (usually dictionaries or lists) returned from command
# handlers and formatting it for display on the console in various formats like
# plain text, JSON, Markdown, or basic HTML. It also handles colored output.
###############################################################################
# [Source file design principles]
# - Provides a consistent interface for formatting different types of output data.
# - Supports multiple output formats selectable via configuration or command-line flags.
# - Uses `colorama` (if available) or standard ANSI escape codes for colored text output.
# - Includes helper methods for formatting specific data structures (e.g., inconsistencies, recommendations).
# - Handles basic data type formatting.
# - Design Decision: Dedicated Formatter Class (2025-04-15)
#   * Rationale: Separates presentation logic from command execution and API interaction logic. Allows easy addition of new output formats.
#   * Alternatives considered: Print statements directly in command handlers (poor separation), Using complex templating engines (overkill for CLI).
###############################################################################
# [Source file constraints]
# - Depends on `colorama` library for cross-platform color support (optional).
# - Text formatting for complex data structures is basic.
# - HTML formatting is rudimentary.
# - Assumes input data is generally serializable or has a reasonable string representation.
###############################################################################
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:59:30Z : Initial creation of OutputFormatter class by CodeAssistant
# * Implemented formatting for text, JSON, Markdown, HTML and color support.
###############################################################################

import sys
import json
import logging
import html
import re
from typing import Dict, List, Any, Optional

# Optional import for colorama
try:
    import colorama
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

logger = logging.getLogger(__name__)

class OutputFormatter:
    """Formats output data for display in the CLI."""

    def __init__(self, default_format: str = "text", use_color: bool = True):
        """
        Initializes the OutputFormatter.

        Args:
            default_format: The default output format ('text', 'json', etc.).
            use_color: Whether to enable colored output (if supported).
        """
        self.format = default_format
        self.use_color = use_color and self._should_use_color()
        self.colors = self._get_colors()
        if self.use_color and HAS_COLORAMA:
            colorama.init(autoreset=True) # Initialize colorama
        logger.debug(f"OutputFormatter initialized (format={self.format}, color={self.use_color}).")

    def _should_use_color(self) -> bool:
        """Determines if color output should be enabled."""
        # Basic check: disable color if output is not a TTY (e.g., redirected to file)
        # or if NO_COLOR env var is set.
        return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def _get_colors(self) -> Dict[str, str]:
        """Gets color codes, using ANSI escapes as fallback if colorama is missing."""
        if not self.use_color:
            # Return empty strings if color is disabled
            return defaultdict(str)

        if HAS_COLORAMA:
            return {
                "reset": colorama.Style.RESET_ALL,
                "bold": colorama.Style.BRIGHT,
                "red": colorama.Fore.RED,
                "green": colorama.Fore.GREEN,
                "yellow": colorama.Fore.YELLOW,
                "blue": colorama.Fore.BLUE,
                "magenta": colorama.Fore.MAGENTA,
                "cyan": colorama.Fore.CYAN,
                "white": colorama.Fore.WHITE,
                "dim": colorama.Style.DIM,
            }
        else:
            # ANSI escape codes fallback
            return {
                "reset": "\033[0m",
                "bold": "\033[1m",
                "red": "\033[91m", # Bright red
                "green": "\033[92m", # Bright green
                "yellow": "\033[93m", # Bright yellow
                "blue": "\033[94m", # Bright blue
                "magenta": "\033[95m", # Bright magenta
                "cyan": "\033[96m", # Bright cyan
                "white": "\033[97m", # Bright white
                "dim": "\033[2m",
            }

    def set_format(self, format_type: str):
        """Sets the desired output format."""
        self.format = format_type.lower()
        logger.debug(f"Output format set to: {self.format}")

    def set_color_enabled(self, enabled: bool):
        """Enables or disables colored output."""
        self.use_color = enabled and self._should_use_color()
        self.colors = self._get_colors() # Update color map
        logger.debug(f"Color output set to: {self.use_color}")

    def print(self, message: str = "", end: str = "\n", **kwargs):
        """Prints a message to stdout."""
        # Central print function allows easy redirection or modification later
        print(message, end=end, **kwargs)

    def error(self, message: str):
        """Prints an error message to stderr, usually in red."""
        print(f"{self.colors.get('red','')}Error: {message}{self.colors.get('reset','')}", file=sys.stderr)

    def warning(self, message: str):
        """Prints a warning message to stderr, usually in yellow."""
        print(f"{self.colors.get('yellow','')}Warning: {message}{self.colors.get('reset','')}", file=sys.stderr)

    def success(self, message: str):
        """Prints a success message, usually in green."""
        print(f"{self.colors.get('green','')}{message}{self.colors.get('reset','')}")

    def info(self, message: str):
        """Prints an informational message, usually in blue."""
        print(f"{self.colors.get('blue','')}{message}{self.colors.get('reset','')}")

    def format_output(self, data: Any):
        """
        Formats and prints the given data based on the configured format.

        Args:
            data: The data to format and print (e.g., dict, list, string).
        """
        if self.format == "json":
            output = self._format_as_json(data)
        elif self.format == "markdown":
            output = self._format_as_markdown(data)
        elif self.format == "html":
            output = self._format_as_html(data)
        else: # Default to text
            output = self._format_as_text(data)

        self.print(output)

    # --- Private Formatting Methods ---

    def _format_as_json(self, data: Any) -> str:
        """Formats data as a pretty-printed JSON string."""
        try:
            return json.dumps(data, indent=2, default=str) # Use default=str for non-serializable types like datetime
        except TypeError as e:
            self.logger.error(f"Failed to serialize data to JSON: {e}")
            return json.dumps({"error": "Data could not be serialized to JSON.", "detail": str(e)})

    def _format_as_text(self, data: Any) -> str:
        """Formats data as human-readable plain text."""
        if isinstance(data, str):
            return data
        if isinstance(data, (int, float, bool)) or data is None:
             return str(data)

        # Check for specific known structures from API responses
        if isinstance(data, dict):
            if "inconsistencies" in data and "summary" in data:
                return self._format_inconsistencies_as_text(data)
            elif "recommendations" in data: # Could check for 'title', 'description' etc.
                return self._format_recommendations_as_text(data)
            elif "relationships" in data and "document_path" in data:
                return self._format_relationships_as_text(data)
            elif "diagram" in data: # Mermaid diagram result
                 return data["diagram"] # Print raw diagram for text
            else:
                # Generic dictionary formatting
                return self._format_dict_as_text(data)
        elif isinstance(data, list):
            # Generic list formatting
            return self._format_list_as_text(data)
        else:
            # Fallback for unknown types
            return repr(data)

    def _format_as_markdown(self, data: Any) -> str:
        """Formats data as Markdown."""
        if isinstance(data, str):
            # Basic escaping? Or assume pre-formatted? Assume pre-formatted for now.
            return data
        if isinstance(data, (int, float, bool)) or data is None:
             return f"`{str(data)}`"

        # Check for specific known structures
        if isinstance(data, dict):
            if "inconsistencies" in data and "summary" in data:
                return self._format_inconsistencies_as_markdown(data)
            elif "recommendations" in data:
                return self._format_recommendations_as_markdown(data)
            elif "relationships" in data and "document_path" in data:
                return self._format_relationships_as_markdown(data)
            elif "diagram" in data: # Mermaid diagram result
                 return data["diagram"] # Return raw diagram in markdown block
            else:
                # Generic dictionary formatting
                return self._format_dict_as_markdown(data)
        elif isinstance(data, list):
            # Generic list formatting
            return self._format_list_as_markdown(data)
        else:
            # Fallback for unknown types
            return f"```\n{repr(data)}\n```"

    def _format_as_html(self, data: Any) -> str:
        """Formats data as basic HTML."""
        # Very basic HTML conversion for demonstration
        if isinstance(data, str):
            return html.escape(data).replace('\n', '<br>\n')
        if isinstance(data, (int, float, bool)) or data is None:
             return f"<code>{html.escape(str(data))}</code>"

        # Use JSON as an intermediate representation for complex types in HTML
        try:
             json_str = json.dumps(data, indent=2, default=str)
             return f"<pre><code>{html.escape(json_str)}</code></pre>"
        except TypeError:
             return f"<pre><code>{html.escape(repr(data))}</code></pre>"


    # --- Text Formatting Helpers ---

    def _c(self, color_name: str, text: Any) -> str:
        """Applies color if enabled."""
        return f"{self.colors.get(color_name,'')}{text}{self.colors.get('reset','')}"

    def _severity_color(self, severity: Optional[str]) -> str:
        """Gets color based on severity string."""
        sev_lower = str(severity).lower()
        if sev_lower == "high": return self.colors.get("red", "")
        if sev_lower == "medium": return self.colors.get("yellow", "")
        if sev_lower == "low": return self.colors.get("green", "")
        return self.colors.get("reset", "")

    def _format_dict_as_text(self, data: Dict, indent: int = 0) -> str:
        """Formats a dictionary nicely as text."""
        lines = []
        indent_str = "  " * indent
        max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
        for key, value in data.items():
            key_str = str(key).ljust(max_key_len)
            if isinstance(value, dict):
                lines.append(f"{indent_str}{self._c('bold', key_str)}:")
                lines.append(self._format_dict_as_text(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}{self._c('bold', key_str)}:")
                lines.append(self._format_list_as_text(value, indent + 1))
            else:
                lines.append(f"{indent_str}{self._c('bold', key_str)}: {value}")
        return "\n".join(lines)

    def _format_list_as_text(self, data: List, indent: int = 0) -> str:
        """Formats a list nicely as text."""
        lines = []
        indent_str = "  " * indent
        for i, item in enumerate(data):
            prefix = f"{indent_str}- "
            if isinstance(item, dict):
                # Format dict inline if simple, else multi-line
                if len(item) <= 3 and all(isinstance(v, (str, int, float, bool, type(None))) for v in item.values()):
                     item_str = ", ".join(f"{self._c('dim', k)}: {v}" for k, v in item.items())
                     lines.append(f"{prefix}{item_str}")
                else:
                     lines.append(f"{prefix}{self._c('dim', f'Item {i+1}:')}")
                     lines.append(self._format_dict_as_text(item, indent + 1))
            elif isinstance(item, list):
                 lines.append(f"{prefix}{self._c('dim', f'List Item {i+1}:')}")
                 lines.append(self._format_list_as_text(item, indent + 1))
            else:
                lines.append(f"{prefix}{item}")
        return "\n".join(lines)

    def _format_inconsistencies_as_text(self, data: Dict) -> str:
        """Formats inconsistency results as text."""
        lines = []
        if summary := data.get("summary"):
            lines.append(self._c('bold', "--- Inconsistency Summary ---"))
            lines.append(f"Total Found: {summary.get('total_inconsistencies', 0)}")
            if sev_counts := summary.get("by_severity"):
                 lines.append("By Severity:")
                 for sev, count in sev_counts.items():
                      lines.append(f"  {self._severity_color(sev)}{sev.upper()}{self.colors.get('reset','')}: {count}")
            if type_counts := summary.get("by_type"):
                 lines.append("By Type:")
                 for type_name, count in type_counts.items():
                      lines.append(f"  {type_name}: {count}")
            lines.append("-" * 27 + "\n")

        if inconsistencies := data.get("inconsistencies"):
            lines.append(self._c('bold', "--- Detected Inconsistencies ---"))
            for i, inc in enumerate(inconsistencies, 1):
                sev_color = self._severity_color(inc.get('severity'))
                lines.append(f"{i}. {sev_color}[{inc.get('severity','UNKNOWN').upper()}]{self.colors.get('reset','')} {inc.get('description', 'No description')}")
                lines.append(f"   ID: {self._c('dim', inc.get('id', 'N/A'))}")
                lines.append(f"   Type: {inc.get('inconsistency_type', 'N/A')}")
                lines.append(f"   Source: {self._c('cyan', inc.get('source_file', 'N/A'))}")
                if target := inc.get('target_file'): lines.append(f"   Target: {self._c('cyan', target)}")
                if details := inc.get('details'):
                     lines.append(f"   Details: {json.dumps(details)}") # Simple details format
                lines.append("") # Spacer
        elif not summary: # If no summary and no inconsistencies
             lines.append("No inconsistencies found.")

        return "\n".join(lines)

    def _format_recommendations_as_text(self, data: Dict) -> str:
        """Formats recommendation results as text."""
        lines = []
        if recommendations := data.get("recommendations"):
            lines.append(self._c('bold', f"--- Recommendations ({len(recommendations)}) ---"))
            for i, rec in enumerate(recommendations, 1):
                sev_color = self._severity_color(rec.get('severity'))
                lines.append(f"{i}. {sev_color}[{rec.get('severity','UNKNOWN').upper()}]{self.colors.get('reset','')} {rec.get('title', 'No Title')}")
                lines.append(f"   ID: {self._c('dim', rec.get('id', 'N/A'))}")
                lines.append(f"   Status: {rec.get('status', 'N/A')}")
                lines.append(f"   Strategy: {rec.get('strategy_name', 'N/A')}")
                lines.append(f"   Description: {rec.get('description', 'N/A')}")
                if snippet := rec.get('doc_snippet'):
                     lines.append("   Doc Snippet:\n```markdown")
                     lines.append(snippet)
                     lines.append("```")
                if snippet := rec.get('code_snippet'):
                     lines.append("   Code Snippet:\n```") # Add language detection later?
                     lines.append(snippet)
                     lines.append("```")
                lines.append("") # Spacer
        else:
             lines.append("No recommendations generated.")
        return "\n".join(lines)

    def _format_relationships_as_text(self, data: Dict) -> str:
        """Formats document relationship results as text."""
        lines = []
        doc_path = data.get('document_path', 'Unknown Document')
        lines.append(self._c('bold', f"--- Relationships for: {doc_path} ---"))
        if relationships := data.get("relationships"):
            lines.append(f"Found {len(relationships)} relationships:")
            for i, rel in enumerate(relationships, 1):
                 lines.append(f"{i}. {self._c('cyan', rel.get('source_document'))} "
                              f"--[{self._c('yellow', rel.get('relationship_type'))}]--> "
                              f"{self._c('cyan', rel.get('target_document'))}")
                 if topic := rel.get('topic'): lines.append(f"   Topic: {topic}")
                 if scope := rel.get('scope'): lines.append(f"   Scope: {scope}")
            lines.append("")
        else:
             lines.append("No relationships found.")
        return "\n".join(lines)

    # --- Markdown Formatting Helpers ---
    # (Similar structure to text helpers, but outputting Markdown syntax)

    def _format_dict_as_markdown(self, data: Dict) -> str:
        # Basic implementation
        lines = []
        for key, value in data.items():
             lines.append(f"- **{key}**: `{value}`")
        return "\n".join(lines)

    def _format_list_as_markdown(self, data: List) -> str:
         # Basic implementation
         lines = [f"- `{item}`" for item in data]
         return "\n".join(lines)

    def _format_inconsistencies_as_markdown(self, data: Dict) -> str:
        # Delegate to text formatting for now, wrap in code block
        return f"```\n{self._format_inconsistencies_as_text(data)}\n```"

    def _format_recommendations_as_markdown(self, data: Dict) -> str:
         # Delegate to text formatting for now, wrap in code block
         return f"```\n{self._format_recommendations_as_text(data)}\n```"

    def _format_relationships_as_markdown(self, data: Dict) -> str:
         # Delegate to text formatting for now, wrap in code block
         return f"```\n{self._format_relationships_as_text(data)}\n```"

# Helper for HTML escaping (if html module not imported directly)
# def html_escape(text: str) -> str:
#     """Escape special characters for HTML."""
#     return html.escape(text)

# Need to import defaultdict if using it
from collections import defaultdict
