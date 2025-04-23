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
# Implements the FormattingEngine class, responsible for formatting generated
# Recommendation objects into various human-readable or machine-readable formats
# (e.g., Markdown, plain text, HTML, JSON) for display or integration.
###############################################################################
# [Source file design principles]
# - Provides a single entry point (`format`) for different output formats.
# - Implements separate private methods for each supported format.
# - Handles the structure of the Recommendation object to produce clear output.
# - Includes basic escaping for formats like HTML.
# - Design Decision: Dedicated Formatting Engine (2025-04-15)
#   * Rationale: Separates presentation logic from the recommendation generation and management logic. Allows adding new formats easily.
#   * Alternatives considered: Formatting methods on the Recommendation object itself (mixes data and presentation), Formatting in the main component (less modular).
###############################################################################
# [Source file constraints]
# - Depends on the `Recommendation` data model.
# - HTML formatting is basic; requires CSS for better presentation.
# - JSON output relies on standard `json` library serialization.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# system:- src/dbp/recommendation_generator/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:42:05Z : Initial creation of FormattingEngine class by CodeAssistant
# * Implemented formatting logic for Markdown, plain text, HTML, and JSON.
###############################################################################

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import html # For HTML escaping

# Assuming data_models defines Recommendation and related enums/classes
try:
    from .data_models import Recommendation, RecommendationFeedback, RecommendationStatus, RecommendationSeverity, RecommendationFixType
except ImportError:
    logging.getLogger(__name__).error("Failed to import data models for FormattingEngine.", exc_info=True)
    # Placeholders
    Recommendation = object
    RecommendationFeedback = object
    RecommendationStatus = object
    RecommendationSeverity = object
    RecommendationFixType = object
    # Dummy Enum for placeholder
    class Enum:
        def __init__(self, value): self.value = value


logger = logging.getLogger(__name__)

class FormattingEngine:
    """
    Formats lists of Recommendation objects into various output formats.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the FormattingEngine.

        Args:
            logger_override: Optional logger instance.
        """
        self.logger = logger_override or logger
        self.logger.debug("FormattingEngine initialized.")

    def format(self, recommendations: List[Recommendation], format_type: str = "markdown") -> str:
        """
        Formats a list of recommendations into the specified format.

        Args:
            recommendations: A list of Recommendation objects.
            format_type: The desired output format ('markdown', 'plain', 'html', 'json').
                         Defaults to 'markdown'.

        Returns:
            A string containing the formatted recommendations.
        """
        self.logger.debug(f"Formatting {len(recommendations)} recommendations as {format_type}.")
        if not recommendations:
            return "No recommendations to format."

        format_type = format_type.lower()
        if format_type == "json":
            return self._format_as_json(recommendations)
        elif format_type == "html":
            return self._format_as_html(recommendations)
        elif format_type == "plain":
            return self._format_as_plain(recommendations)
        elif format_type == "markdown":
            return self._format_as_markdown(recommendations)
        else:
            self.logger.warning(f"Unsupported format type '{format_type}'. Defaulting to markdown.")
            return self._format_as_markdown(recommendations)

    def _format_as_markdown(self, recommendations: List[Recommendation]) -> str:
        """Formats recommendations as Markdown."""
        lines = [
            "# Recommendations Report",
            f"\n*Generated: {datetime.now().isoformat()}*",
            f"\n**Total Recommendations: {len(recommendations)}**\n"
        ]

        # Optional: Group by severity or status
        # Simple list for now
        for i, r in enumerate(recommendations, 1):
            lines.append(f"## {i}. {r.title} (`{r.id}`)")
            lines.append(f"- **Status:** {r.status.value}")
            lines.append(f"- **Severity:** {r.severity.value}")
            lines.append(f"- **Strategy:** `{r.strategy_name}`")
            lines.append(f"- **Fix Type:** {r.fix_type.value}")
            if r.source_file: lines.append(f"- **Source:** `{r.source_file}`")
            if r.target_file: lines.append(f"- **Target:** `{r.target_file}`")
            if r.inconsistency_ids: lines.append(f"- **Related Inconsistencies:** `{', '.join(r.inconsistency_ids)}`")

            lines.append("\n**Description:**")
            lines.append(r.description)

            if r.doc_snippet:
                lines.append("\n**Documentation Suggestion:**")
                lines.append("```markdown")
                lines.append(r.doc_snippet)
                lines.append("```")

            if r.code_snippet:
                lines.append("\n**Code Suggestion:**")
                # Try to guess language for syntax highlighting, default to text
                lang_guess = ""
                if r.source_file and '.' in r.source_file:
                     ext = r.source_file.split('.')[-1]
                     lang_map = {'py': 'python', 'js': 'javascript', 'ts': 'typescript', 'java': 'java', 'md': 'markdown'}
                     lang_guess = lang_map.get(ext, "")
                lines.append(f"```{lang_guess}")
                lines.append(r.code_snippet)
                lines.append("```")

            if r.feedback:
                 lines.append("\n**Feedback:**")
                 lines.append(f"- Accepted: {r.feedback.accepted}")
                 if r.feedback.reason: lines.append(f"- Reason: {r.feedback.reason}")
                 if r.feedback.improvements: lines.append(f"- Improvements: {'; '.join(r.feedback.improvements)}")
                 if r.feedback.provided_at: lines.append(f"- Provided At: {r.feedback.provided_at.isoformat()}")

            lines.append("\n---\n") # Separator

        return "\n".join(lines)

    def _format_as_plain(self, recommendations: List[Recommendation]) -> str:
        """Formats recommendations as plain text."""
        lines = [
            "==========================",
            " RECOMMENDATIONS REPORT",
            "==========================",
            f"Generated: {datetime.now().isoformat()}",
            f"Total Recommendations: {len(recommendations)}\n"
        ]

        for i, r in enumerate(recommendations, 1):
            lines.append(f"--- Recommendation {i} ---")
            lines.append(f"ID: {r.id}")
            lines.append(f"Title: {r.title}")
            lines.append(f"Status: {r.status.value}")
            lines.append(f"Severity: {r.severity.value}")
            lines.append(f"Strategy: {r.strategy_name}")
            lines.append(f"Fix Type: {r.fix_type.value}")
            if r.source_file: lines.append(f"Source: {r.source_file}")
            if r.target_file: lines.append(f"Target: {r.target_file}")
            if r.inconsistency_ids: lines.append(f"Related Inconsistencies: {', '.join(r.inconsistency_ids)}")

            lines.append("\nDescription:")
            lines.append(r.description)

            if r.doc_snippet:
                lines.append("\nDocumentation Suggestion:")
                lines.append(r.doc_snippet)

            if r.code_snippet:
                lines.append("\nCode Suggestion:")
                lines.append(r.code_snippet)

            if r.feedback:
                 lines.append("\nFeedback:")
                 lines.append(f"  Accepted: {r.feedback.accepted}")
                 if r.feedback.reason: lines.append(f"  Reason: {r.feedback.reason}")
                 if r.feedback.improvements: lines.append(f"  Improvements: {'; '.join(r.feedback.improvements)}")
                 if r.feedback.provided_at: lines.append(f"  Provided At: {r.feedback.provided_at.isoformat()}")

            lines.append("-" * 20 + "\n")

        return "\n".join(lines)

    def _format_as_html(self, recommendations: List[Recommendation]) -> str:
        """Formats recommendations as simple HTML."""
        # Basic HTML structure
        html_parts = [
            "<!DOCTYPE html>", "<html><head><title>Recommendations Report</title>",
            "<style>",
            "body { font-family: sans-serif; line-height: 1.4; }",
            ".recommendation { border: 1px solid #ccc; margin-bottom: 1em; padding: 1em; border-radius: 5px; }",
            ".recommendation h2 { margin-top: 0; }",
            ".severity-high { border-left: 5px solid red; }",
            ".severity-medium { border-left: 5px solid orange; }",
            ".severity-low { border-left: 5px solid green; }",
            "pre { background-color: #f0f0f0; padding: 0.5em; border: 1px solid #ddd; overflow-x: auto; }",
            "code { font-family: monospace; }",
            ".meta { font-size: 0.9em; color: #555; }",
            "</style>", "</head><body>",
            f"<h1>Recommendations Report</h1>",
            f"<p>Generated: {datetime.now().isoformat()}</p>",
            f"<p>Total Recommendations: {len(recommendations)}</p>"
        ]

        for r in recommendations:
            severity_class = f"severity-{r.severity.value.lower()}"
            html_parts.append(f"<div class='recommendation {severity_class}'>")
            html_parts.append(f"<h2>{html.escape(r.title)}</h2>")
            html_parts.append("<p class='meta'>")
            html_parts.append(f"ID: <code>{html.escape(r.id)}</code><br>")
            html_parts.append(f"Status: {html.escape(r.status.value)}<br>")
            html_parts.append(f"Severity: {html.escape(r.severity.value)}<br>")
            html_parts.append(f"Strategy: {html.escape(r.strategy_name)}<br>")
            html_parts.append(f"Fix Type: {html.escape(r.fix_type.value)}<br>")
            if r.source_file: html_parts.append(f"Source: <code>{html.escape(r.source_file)}</code><br>")
            if r.target_file: html_parts.append(f"Target: <code>{html.escape(r.target_file)}</code><br>")
            if r.inconsistency_ids: html_parts.append(f"Inconsistencies: {html.escape(', '.join(r.inconsistency_ids))}<br>")
            html_parts.append("</p>")

            html_parts.append(f"<p>{html.escape(r.description)}</p>")

            if r.doc_snippet:
                html_parts.append("<h3>Documentation Suggestion:</h3>")
                html_parts.append(f"<pre><code>{html.escape(r.doc_snippet)}</code></pre>")

            if r.code_snippet:
                html_parts.append("<h3>Code Suggestion:</h3>")
                html_parts.append(f"<pre><code>{html.escape(r.code_snippet)}</code></pre>")

            if r.feedback:
                 html_parts.append("<h3>Feedback:</h3><p class='meta'>")
                 html_parts.append(f"Accepted: {r.feedback.accepted}<br>")
                 if r.feedback.reason: html_parts.append(f"Reason: {html.escape(r.feedback.reason)}<br>")
                 if r.feedback.improvements: html_parts.append(f"Improvements: {html.escape('; '.join(r.feedback.improvements))}<br>")
                 if r.feedback.provided_at: html_parts.append(f"Provided At: {r.feedback.provided_at.isoformat()}<br>")
                 html_parts.append("</p>")

            html_parts.append("</div>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def _format_as_json(self, recommendations: List[Recommendation]) -> str:
        """Formats recommendations as a JSON string."""
        output_data = {
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "recommendation_count": len(recommendations),
            },
            "recommendations": []
        }

        for r in recommendations:
            rec_dict = {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "strategy_name": r.strategy_name,
                "fix_type": r.fix_type.value,
                "severity": r.severity.value,
                "status": r.status.value,
                "source_file": r.source_file,
                "target_file": r.target_file,
                "inconsistency_ids": r.inconsistency_ids,
                "code_snippet": r.code_snippet,
                "doc_snippet": r.doc_snippet,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "applied_at": r.applied_at.isoformat() if r.applied_at else None,
                "metadata": r.metadata,
                "feedback": r.feedback.to_dict() if r.feedback else None,
            }
            # Remove None values for cleaner JSON, except for explicitly allowed ones like target_file
            cleaned_rec_dict = {k: v for k, v in rec_dict.items() if v is not None or k in ['target_file', 'applied_at', 'feedback']}
            output_data["recommendations"].append(cleaned_rec_dict)

        try:
            return json.dumps(output_data, indent=2)
        except TypeError as e:
            self.logger.error(f"Failed to serialize recommendations to JSON: {e}")
            return json.dumps({"error": "Failed to serialize recommendations to JSON."})
