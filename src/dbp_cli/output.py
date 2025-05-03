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
# [Dependencies]
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:59:30Z : Initial creation of OutputFormatter class by CodeAssistant
# * Implemented formatting for text, JSON, Markdown, HTML and color support.
###############################################################################

import sys
import os
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
    """
    [Class intent]
    Formats and displays command output in various formats (text, JSON, Markdown, HTML)
    with consistent styling and optional color highlighting to provide a user-friendly
    interface for the CLI application.
    
    [Implementation details]
    Manages multiple output formats with specific formatters for each type.
    Detects terminal capabilities and respects environment settings for color support.
    Provides specialized formatting for common data structures returned by API calls.
    Contains helper methods for different message types (info, warning, error, success).
    
    [Design principles]
    Separation of concerns - isolates output formatting logic from command execution.
    Format polymorphism - handles different output formats through specialized methods.
    Progressive disclosure - supports basic and verbose output modes.
    Security-aware - masks sensitive data and properly escapes output when needed.
    """

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
        """
        [Function intent]
        Determine if color output should be enabled based on environment factors.
        
        [Implementation details]
        Checks if stdout is connected to a TTY terminal (vs. redirected to a file).
        Also checks for the NO_COLOR environment variable which disables color.
        Returns False if either condition indicates color should be disabled.
        
        [Design principles]
        Environment awareness - respects terminal capabilities and user preferences.
        Standard compliance - follows the NO_COLOR convention.
        Conservative approach - disables color when output is redirected to avoid cluttering files.
        
        Returns:
            True if color should be enabled, False otherwise
        """
        # Basic check: disable color if output is not a TTY (e.g., redirected to file)
        # or if NO_COLOR env var is set.
        return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def _get_colors(self) -> Dict[str, str]:
        """
        [Function intent]
        Create a dictionary of color/formatting codes based on available libraries.
        
        [Implementation details]
        Uses colorama if available, falls back to standard ANSI escape codes if not.
        Returns empty strings for all colors if color output is disabled.
        Includes codes for reset, bold, various colors, and dim text.
        Uses defaultdict as a fallback mechanism to avoid KeyError if using an undefined color.
        
        [Design principles]
        Graceful degradation - falls back to ANSI codes if colorama is unavailable.
        Self-contained - includes all necessary color definitions without external dependencies.
        Complete palette - provides a consistent set of formatting options.
        
        Returns:
            Dictionary mapping color names to their respective codes
        """
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
        """
        [Function intent]
        Change the current output format to the specified type.
        
        [Implementation details]
        Converts the format type to lowercase for case-insensitive comparison.
        Stores the format for use in subsequent output operations.
        Logs the format change for debugging purposes.
        
        [Design principles]
        Case insensitivity - accepts format strings in any case.
        Runtime configurability - allows changing format during execution.
        Audit trail - logs format changes for troubleshooting.
        
        Args:
            format_type: The output format to use ('text', 'json', 'markdown', 'html')
        """
        self.format = format_type.lower()
        logger.debug(f"Output format set to: {self.format}")

    def set_color_enabled(self, enabled: bool):
        """
        [Function intent]
        Enable or disable colored output based on the provided flag.
        
        [Implementation details]
        Updates the use_color flag to the logical AND of the provided value
        and the result of _should_use_color() to respect environmental constraints.
        Refreshes the colors dictionary to reflect the new setting.
        Logs the color setting change for debugging purposes.
        
        [Design principles]
        Environment awareness - still respects terminal capabilities even when enabled.
        Dynamic reconfiguration - allows toggling color at runtime.
        State consistency - updates color map immediately when setting changes.
        
        Args:
            enabled: Whether color output should be enabled
        """
        self.use_color = enabled and self._should_use_color()
        self.colors = self._get_colors() # Update color map
        logger.debug(f"Color output set to: {self.use_color}")

    def print(self, message: str = "", end: str = "\n", **kwargs):
        """
        [Function intent]
        Print a message to stdout with specified end character and options.
        
        [Implementation details]
        Centralizes all print operations to allow for future redirection or modification.
        Passes through all keyword arguments to the underlying print function.
        
        [Design principles]
        Single responsibility - provides a dedicated method for output.
        Future-proofing - allows for easy redirection or modification of output behavior.
        Simplicity - thin wrapper around the built-in print function.
        
        Args:
            message: The message to print (defaults to empty string)
            end: String appended after the message (defaults to newline)
            **kwargs: Additional keyword arguments passed to print()
        """
        # Central print function allows easy redirection or modification later
        print(message, end=end, **kwargs)

    def error(self, message: str):
        """
        [Function intent]
        Display an error message to stderr with appropriate formatting.
        
        [Implementation details]
        Uses red color for the entire message if color is enabled.
        Always outputs to stderr rather than stdout.
        Does not add any prefix to avoid duplicating log level information.
        
        [Design principles]
        Visual distinction - uses color to highlight errors.
        Proper stream direction - writes errors to stderr instead of stdout.
        Consistent formatting - provides uniform appearance for all error messages.
        Compatibility - works with centralized log formatters without duplication.
        
        Args:
            message: The error message to display
        """
        print(f"{self.colors.get('red','')}{message}{self.colors.get('reset','')}", file=sys.stderr)

    def warning(self, message: str):
        """
        [Function intent]
        Display a warning message to stderr with appropriate formatting.
        
        [Implementation details]
        Uses yellow color for the entire message if color is enabled.
        Always outputs to stderr rather than stdout.
        Does not add any prefix to avoid duplicating log level information.
        
        [Design principles]
        Visual distinction - uses color to highlight warnings.
        Proper stream direction - writes warnings to stderr instead of stdout.
        Consistent formatting - provides uniform appearance for all warning messages.
        Compatibility - works with centralized log formatters without duplication.
        
        Args:
            message: The warning message to display
        """
        print(f"{self.colors.get('yellow','')}{message}{self.colors.get('reset','')}", file=sys.stderr)

    def success(self, message: str):
        """
        [Function intent]
        Display a success message with appropriate formatting.
        
        [Implementation details]
        Uses green color for the message if color is enabled.
        Outputs to stdout without any special prefix.
        
        [Design principles]
        Visual distinction - uses color to highlight successful operations.
        Positive feedback - provides clear indication of successful results.
        
        Args:
            message: The success message to display
        """
        print(f"{self.colors.get('green','')}{message}{self.colors.get('reset','')}")

    def info(self, message: str):
        """
        [Function intent]
        Display an informational message with appropriate formatting.
        
        [Implementation details]
        Uses blue color for the message if color is enabled.
        Outputs to stdout without any special prefix.
        
        [Design principles]
        Visual distinction - uses color to highlight informational messages.
        Information hierarchy - provides differentiation from normal, success, warning and error messages.
        
        Args:
            message: The informational message to display
        """
        print(f"{self.colors.get('blue','')}{message}{self.colors.get('reset','')}")
    
    def debug(self, message: str):
        """
        [Function intent]
        Handle debug messages in a manner compatible with logging interfaces.
        
        [Implementation details]
        Uses dim (gray) color for the message if color is enabled.
        Only outputs when verbose logging is enabled (currently always falls back to logger).
        Uses the system logger to record the message rather than printing directly.
        
        [Design principles]
        Logger compatibility - provides a method compatible with the logging interface.
        Visual distinction - uses dim color to indicate debug level messages.
        Silent by default - doesn't clutter standard output with debug information.
        
        Args:
            message: The debug message to log
        """
        # Forward to system logger at debug level rather than printing directly
        # This provides compatibility with the logger interface
        logger.debug(message)

    def format_output(self, data: Any):
        """
        [Function intent]
        Format and print data according to the configured output format.
        
        [Implementation details]
        Determines which formatter to use based on the configured format.
        Delegates to the appropriate format method (_format_as_json, _format_as_text, etc.).
        Handles various data types including dictionaries, lists, strings, and primitives.
        Prints the formatted output to stdout.
        
        [Design principles]
        Format polymorphism - handles different output formats through specialized methods.
        Data type flexibility - accommodates various data structures.
        Single responsibility - separates formatting logic from printing.
        
        Args:
            data: The data to format and print (e.g., dict, list, string)
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
        """
        [Function intent]
        Convert data to a pretty-printed JSON string representation.
        
        [Implementation details]
        Uses json.dumps with indentation for readable formatting.
        Handles non-serializable types using str() conversion.
        Catches and reports serialization errors in a structured way.
        
        [Design principles]
        Error resilience - catches and reports serialization errors without crashing.
        Human readability - uses indentation for clearer output.
        Type handling - gracefully handles non-serializable types.
        
        Args:
            data: The data to format as JSON
            
        Returns:
            Pretty-printed JSON string representation of the data
        """
        try:
            return json.dumps(data, indent=2, default=str) # Use default=str for non-serializable types like datetime
        except TypeError as e:
            self.logger.error(f"Failed to serialize data to JSON: {e}")
            return json.dumps({"error": "Data could not be serialized to JSON.", "detail": str(e)})

    def _format_as_text(self, data: Any) -> str:
        """
        [Function intent]
        Convert data to a human-readable plain text representation.
        
        [Implementation details]
        Handles different data types specifically:
        - Strings returned as-is
        - Primitives (int, float, bool, None) converted to string
        - Special handling for known API response structures (inconsistencies, recommendations, etc.)
        - Generic dictionary and list formatting for other structures
        
        [Design principles]
        Content awareness - special formatting for known data structures.
        Type-specific handling - different approaches for different data types.
        Recursive processing - handles nested structures through helper methods.
        
        Args:
            data: The data to format as text
            
        Returns:
            Human-readable text representation of the data
        """
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
        """
        [Function intent]
        Convert data to a Markdown-formatted string representation.
        
        [Implementation details]
        Handles different data types specifically:
        - Strings assumed to be pre-formatted or raw Markdown
        - Primitives wrapped in backticks as code
        - Special handling for known API response structures
        - Generic dictionary and list formatting for other structures
        - Unknown types displayed in code blocks
        
        [Design principles]
        Content awareness - special formatting for known data structures.
        Markdown compatibility - generates valid Markdown syntax.
        Type-specific handling - different approaches for different data types.
        
        Args:
            data: The data to format as Markdown
            
        Returns:
            Markdown-formatted representation of the data
        """
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
        """
        [Function intent]
        Convert data to a basic HTML-formatted string representation.
        
        [Implementation details]
        Handles different data types with basic HTML formatting:
        - Strings escaped with line breaks preserved
        - Primitives wrapped in <code> tags
        - Complex types converted to JSON and displayed in <pre><code> blocks
        - Uses HTML escaping to prevent injection vulnerabilities
        
        [Design principles]
        Security first - escapes HTML to prevent injection attacks.
        Basic formatting - provides minimal but functional HTML representation.
        Fallback strategy - uses JSON as intermediate format for complex types.
        
        Args:
            data: The data to format as HTML
            
        Returns:
            HTML-formatted representation of the data
        """
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
        """
        [Function intent]
        Apply color formatting to text if color output is enabled.
        
        [Implementation details]
        Wraps the provided text with the requested color code and reset code.
        Returns the text unchanged if color is disabled.
        Converts the text to string implicitly.
        
        [Design principles]
        Conditional formatting - only applies color when enabled.
        Helper utility - centralizes color application logic.
        Convenience - handles non-string input through implicit conversion.
        
        Args:
            color_name: The name of the color to apply
            text: The text to colorize
            
        Returns:
            Colorized text if color is enabled, otherwise plain text
        """
        return f"{self.colors.get(color_name,'')}{text}{self.colors.get('reset','')}"

    def _severity_color(self, severity: Optional[str]) -> str:
        """
        [Function intent]
        Determine the appropriate color code based on severity level.
        
        [Implementation details]
        Maps common severity levels (high, medium, low) to corresponding colors.
        Uses red for high severity, yellow for medium, and green for low.
        Normalizes input to lowercase for case-insensitive comparison.
        Returns reset color for unknown severity levels.
        
        [Design principles]
        Standardized color coding - consistent color mapping for severity levels.
        Case insensitivity - handles various capitalization styles.
        Safe default - returns reset code for unknown values.
        
        Args:
            severity: The severity level string
            
        Returns:
            The corresponding color code string
        """
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
