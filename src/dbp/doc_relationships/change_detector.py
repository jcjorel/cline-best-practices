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
# Implements the ChangeDetector class, responsible for identifying specific
# changes between two versions of a document's content and correlating these
# changes with the potential impacts identified by the ImpactAnalyzer.
###############################################################################
# [Source file design principles]
# - Compares old and new document content to detect changes (additions, deletions, modifications).
# - Uses a placeholder strategy (section-based diff) for content change detection.
# - Integrates with ImpactAnalyzer to link detected changes to potentially impacted documents.
# - Populates DocChangeImpact data structures with detailed information.
# - Design Decision: Section-Based Diff (Placeholder) (2025-04-15)
#   * Rationale: Provides a basic mechanism to identify coarse-grained changes. A more sophisticated diff algorithm (e.g., using difflib or external libraries) would be needed for line-level accuracy.
#   * Alternatives considered: Line-by-line diff (more complex), AST parsing (language-specific).
###############################################################################
# [Source file constraints]
# - Depends on `ImpactAnalyzer` and `DocChangeImpact` data model.
# - The accuracy of change detection is limited by the placeholder implementation.
# - Assumes document content is text-based (e.g., Markdown).
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - src/dbp/doc_relationships/impact_analyzer.py
# - src/dbp/doc_relationships/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:22:40Z : Initial creation of ChangeDetector class by CodeAssistant
# * Implemented placeholder content change detection and integration with impact analysis.
###############################################################################

import logging
import re
from typing import List, Dict, Optional, Any

# Assuming necessary imports
try:
    from .impact_analyzer import ImpactAnalyzer, DocImpact
    from .data_models import DocChangeImpact
except ImportError:
    logging.getLogger(__name__).error("Failed to import dependencies for ChangeDetector.", exc_info=True)
    # Placeholders
    ImpactAnalyzer = object
    DocImpact = object
    DocChangeImpact = object

logger = logging.getLogger(__name__)

class ChangeDetector:
    """
    Detects specific changes between document versions and correlates them
    with potential impacts on related documents.
    """

    def __init__(self, impact_analyzer: ImpactAnalyzer, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ChangeDetector.

        Args:
            impact_analyzer: An instance of ImpactAnalyzer to determine potential impacts.
            logger_override: Optional logger instance.
        """
        self.impact_analyzer = impact_analyzer
        self.logger = logger_override or logger
        self.logger.debug("ChangeDetector initialized.")

    def detect_changes_and_impact(
        self,
        document_path: str,
        old_content: Optional[str],
        new_content: Optional[str]
    ) -> List[DocChangeImpact]:
        """
        Detects changes between old and new content for a document and determines
        the impact of these changes on related documents.

        Args:
            document_path: The path of the document that changed.
            old_content: The previous content of the document (or None if created).
            new_content: The new content of the document (or None if deleted).

        Returns:
            A list of DocChangeImpact objects detailing the changes and their impacts.
        """
        self.logger.info(f"Detecting changes and analyzing impact for: {document_path}")

        if old_content is None and new_content is None:
            self.logger.warning(f"Both old and new content are None for {document_path}. Cannot detect changes.")
            return []
        elif old_content is None: # Document Creation
             changes = [{"type": "document_created", "section": None, "content": "Document created"}]
             old_content = "" # Treat as change from empty
        elif new_content is None: # Document Deletion
             changes = [{"type": "document_deleted", "section": None, "content": "Document deleted"}]
             new_content = "" # Treat as change to empty
        else: # Document Modification
             changes = self._detect_content_changes(old_content, new_content)

        if not changes:
            self.logger.info(f"No significant content changes detected in {document_path}")
            return []

        self.logger.debug(f"Detected {len(changes)} changes in {document_path}: {changes}")

        # Analyze the potential impact of changing this document
        try:
            potential_impacts = self.impact_analyzer.analyze_impact(document_path)
        except Exception as e:
             self.logger.error(f"Failed to analyze impact for {document_path}: {e}", exc_info=True)
             return [] # Cannot proceed without impact analysis

        if not potential_impacts:
            self.logger.info(f"No potential impacts found for changes in {document_path}")
            return []

        # Combine detected changes with potential impacts
        change_impacts: List[DocChangeImpact] = []
        for change in changes:
            for impact in potential_impacts:
                # Create a DocChangeImpact object linking a specific change to a potential impact
                change_impact = DocChangeImpact(
                    source_document=document_path,
                    target_document=impact.target_document,
                    change_type=change["type"],
                    change_section=change.get("section"),
                    change_content=change.get("content"),
                    impact_type=impact.impact_type,
                    impact_level=impact.impact_level,
                    relationship_type=impact.relationship_type,
                    topic=impact.topic,
                    scope=impact.scope
                )
                change_impacts.append(change_impact)

        self.logger.info(f"Generated {len(change_impacts)} change impact records for {document_path}")
        return change_impacts

    def _detect_content_changes(self, old_content: str, new_content: str) -> List[Dict[str, Any]]:
        """
        Placeholder method to detect changes between old and new document content.
        Currently implements a simple section-based comparison.

        Args:
            old_content: The old document content.
            new_content: The new document content.

        Returns:
            A list of dictionaries, each describing a detected change
            (e.g., {"type": "section_modified", "section": "Section Title", "content": "Description"}).
        """
        changes: List[Dict[str, Any]] = []
        self.logger.debug("Detecting content changes (section-based placeholder)...")

        try:
            old_sections = self._split_into_sections(old_content)
            new_sections = self._split_into_sections(new_content)

            all_section_titles = set(old_sections.keys()) | set(new_sections.keys())

            for title in all_section_titles:
                old_sec_content = old_sections.get(title)
                new_sec_content = new_sections.get(title)

                if old_sec_content is None and new_sec_content is not None:
                    changes.append({
                        "type": "section_added",
                        "section": title,
                        "content": (new_sec_content[:100] + "...") if len(new_sec_content or "") > 103 else new_sec_content
                    })
                elif old_sec_content is not None and new_sec_content is None:
                    changes.append({
                        "type": "section_removed",
                        "section": title,
                        "content": None # Content is gone
                    })
                elif old_sec_content != new_sec_content:
                    # More sophisticated diff could be used here (e.g., difflib)
                    changes.append({
                        "type": "section_modified",
                        "section": title,
                        "content": f"Content changed (length {len(old_sec_content or '')} -> {len(new_sec_content or '')})"
                    })
        except Exception as e:
             self.logger.error(f"Error during content change detection: {e}", exc_info=True)
             # Return a generic change if diffing fails
             if old_content != new_content:
                  changes.append({"type": "content_modified", "section": None, "content": "Document content modified"})

        return changes

    def _split_into_sections(self, content: str) -> Dict[str, str]:
        """
        Splits document content into sections based on Markdown headers (## Section Title).
        Content before the first header is under the key "__preamble__".

        Args:
            content: The document content string.

        Returns:
            A dictionary mapping section titles to their content (including the header line).
        """
        sections: Dict[str, str] = {}
        current_section_title = "__preamble__" # Content before the first header
        current_content: List[str] = []
        header_pattern = re.compile(r"^(#+)\s+(.*)") # Matches lines starting with #

        lines = content.splitlines()

        for line in lines:
            match = header_pattern.match(line)
            if match:
                # Store the previous section
                if current_content:
                    sections[current_section_title] = "\n".join(current_content).strip()

                # Start the new section
                current_section_title = match.group(2).strip() # Get title after #s and space
                current_content = [line] # Include header line in content
            else:
                current_content.append(line)

        # Store the last section
        if current_content or current_section_title not in sections:
             sections[current_section_title] = "\n".join(current_content).strip()

        # Remove preamble if it's empty and there are other sections
        if not sections.get("__preamble__") and len(sections) > 1:
             sections.pop("__preamble__", None)

        return sections
