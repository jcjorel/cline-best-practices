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
# Implements the RelationshipAnalyzer class, responsible for parsing document
# content (primarily Markdown and the specific DOCUMENT_RELATIONSHIPS.md format)
# to identify and extract explicit or implicit relationships between documents.
###############################################################################
# [Source file design principles]
# - Provides methods to analyze different types of documentation files.
# - Uses regular expressions and string processing for relationship extraction (placeholder logic).
# - Handles path normalization for linked documents.
# - Converts extracted information into DocumentRelationship objects.
# - Design Decision: Rule-Based/Regex Analysis (Placeholder) (2025-04-15)
#   * Rationale: Provides a basic mechanism for relationship extraction based on common patterns (links, specific headers). A more robust solution might involve NLP or AST parsing later.
#   * Alternatives considered: LLM-based analysis (potentially slower, more complex for this specific task), Manual definition only (doesn't leverage existing links).
###############################################################################
# [Source file constraints]
# - Depends on `data_models.py` for `DocumentRelationship`.
# - Relies on specific formats in `DOCUMENT_RELATIONSHIPS.md`.
# - Markdown link parsing is basic and might miss complex cases.
# - Assumes file paths are relative or resolvable from the document's location.
# - Placeholder extraction logic needs refinement for production use.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
# - src/dbp/doc_relationships/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:21:15Z : Initial creation of RelationshipAnalyzer class by CodeAssistant
# * Implemented analysis logic for DOCUMENT_RELATIONSHIPS.md and general Markdown files (placeholders).
###############################################################################

import logging
import os
import re
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

# Assuming data_models and potentially other components are accessible
try:
    from .data_models import DocumentRelationship
    # May need FileAccessService or direct file reading
    from ..internal_tools.file_access import FileAccessService # Example dependency
except ImportError as e:
    logging.getLogger(__name__).error(f"RelationshipAnalyzer ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    DocumentRelationship = object
    FileAccessService = object

logger = logging.getLogger(__name__)

class RelationshipAnalyzer:
    """
    Analyzes document content to extract relationships between documents.
    Handles both the specific format of DOCUMENT_RELATIONSHIPS.md and
    general markdown link analysis.
    """

    def __init__(self, file_access_service: FileAccessService, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the RelationshipAnalyzer.

        Args:
            file_access_service: Service to read file content.
            logger_override: Optional logger instance.
        """
        self.file_access = file_access_service
        self.logger = logger_override or logger
        # Regex for markdown links: [text](target)
        self._link_pattern = re.compile(r"\[([^\]]+?)\]\(([^)]+?)\)")
        # Regex for DOCUMENT_RELATIONSHIPS.md sections and lines
        self._section_pattern = re.compile(r"^\s*##\s+\[(.*?)\]\s*$", re.MULTILINE)
        self._rel_line_pattern = re.compile(
            r"^\s*-\s+([\w\s]+?):\s*\[(.*?)\]" # Type and Target
            r"(?:\s+-\s+Topic:\s*\[(.*?)\])?" # Optional Topic
            r"(?:\s+-\s+Scope:\s*\[(.*?)\])?", # Optional Scope
            re.IGNORECASE
        )
        self.logger.debug("RelationshipAnalyzer initialized.")

    def analyze_document(self, document_path: str) -> List[DocumentRelationship]:
        """
        Analyzes a document to extract relationships. Determines the analysis method
        based on the filename.

        Args:
            document_path: The absolute path to the document file.

        Returns:
            A list of DocumentRelationship objects found in the document.
        """
        self.logger.info(f"Analyzing relationships for document: {document_path}")
        try:
            # Use FileAccessService to read content relative to its base path if needed
            # Assuming document_path is relative or FileAccessService handles absolute
            content = self.file_access.read_file(document_path)

            # Check if it's the special relationships file
            if Path(document_path).name == "DOCUMENT_RELATIONSHIPS.md":
                return self._analyze_relationships_document(document_path, content)
            elif document_path.lower().endswith(".md"):
                # Analyze standard markdown file
                return self._analyze_markdown_document(document_path, content)
            else:
                # Add logic for other file types (e.g., code) if needed later
                self.logger.debug(f"Skipping relationship analysis for non-markdown file: {document_path}")
                return []

        except (FileNotFoundError, IOError) as e:
            self.logger.error(f"Cannot analyze document, file not found or unreadable: {document_path} - {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error analyzing document {document_path}: {e}", exc_info=True)
            return []

    def _analyze_relationships_document(self, doc_path: str, content: str) -> List[DocumentRelationship]:
        """Parses the specific format of DOCUMENT_RELATIONSHIPS.md."""
        self.logger.debug(f"Analyzing specific format of: {doc_path}")
        relationships = []
        current_source_doc = None

        lines = content.splitlines()
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line: continue

            # Check for section header
            section_match = self._section_pattern.match(line)
            if section_match:
                current_source_doc = section_match.group(1).strip()
                self.logger.debug(f"Found section for source document: {current_source_doc}")
                continue

            # If we are inside a section, check for relationship lines
            if current_source_doc:
                rel_match = self._rel_line_pattern.match(line)
                if rel_match:
                    rel_type, target_doc, topic, scope = [m.strip() if m else None for m in rel_match.groups()]

                    if not rel_type or not target_doc:
                         self.logger.warning(f"Skipping malformed relationship line {line_num+1} in {doc_path}: {line}")
                         continue

                    # Normalize paths relative to the project root (assuming doc_path is within project)
                    # This requires knowing the project root. Assuming file_access base_path is project root.
                    try:
                         source_rel = str(Path(current_source_doc).relative_to(self.file_access._base_path)).replace(os.sep, '/')
                         target_rel = str(Path(target_doc).relative_to(self.file_access._base_path)).replace(os.sep, '/')
                    except ValueError:
                         self.logger.warning(f"Could not make paths relative to base {self.file_access._base_path} on line {line_num+1} in {doc_path}. Using original paths.")
                         source_rel = current_source_doc
                         target_rel = target_doc
                    except Exception as e:
                         self.logger.error(f"Error normalizing paths on line {line_num+1} in {doc_path}: {e}")
                         continue


                    relationship = DocumentRelationship(
                        source_document=source_rel,
                        target_document=target_rel,
                        relationship_type=rel_type.lower(), # Normalize type
                        topic=topic,
                        scope=scope.lower() if scope else None, # Normalize scope
                        metadata={"source_line": line_num + 1} # Add line number as metadata
                    )
                    relationships.append(relationship)
                    self.logger.debug(f"Extracted relationship: {relationship}")

        self.logger.info(f"Found {len(relationships)} relationships defined in {doc_path}")
        return relationships

    def _analyze_markdown_document(self, doc_path: str, content: str) -> List[DocumentRelationship]:
        """Analyzes a standard Markdown file for links that imply relationships."""
        self.logger.debug(f"Analyzing markdown links in: {doc_path}")
        relationships = []
        doc_dir = Path(doc_path).parent

        for match in self._link_pattern.finditer(content):
            link_text = match.group(1).strip()
            link_target = match.group(2).strip()

            # Ignore external links, anchor links, and potentially mailto links etc.
            if link_target.startswith(('http://', 'https://', '#', 'mailto:')):
                continue

            # Ignore image links (heuristic: check common image extensions)
            if link_target.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                 continue

            try:
                # Resolve the target path relative to the current document's directory
                target_abs_path = (doc_dir / link_target).resolve()

                # Ensure the target exists (optional, could link to non-existent files)
                # if not target_abs_path.exists():
                #     self.logger.debug(f"Link target does not exist: {target_abs_path}")
                #     continue

                # Make paths relative to the project root for storage consistency
                source_rel = str(Path(doc_path).relative_to(self.file_access._base_path)).replace(os.sep, '/')
                target_rel = str(target_abs_path.relative_to(self.file_access._base_path)).replace(os.sep, '/')

                relationship = DocumentRelationship(
                    source_document=source_rel,
                    target_document=target_rel,
                    relationship_type="references", # Default type for markdown links
                    topic=link_text, # Use link text as topic
                    scope="narrow", # Assume links are narrow scope
                    metadata={"link_target_raw": link_target}
                )
                relationships.append(relationship)
                self.logger.debug(f"Extracted reference relationship: {relationship}")

            except ValueError:
                 self.logger.warning(f"Could not make link target relative to base path '{self.file_access._base_path}': Target '{link_target}' in doc '{doc_path}'")
            except Exception as e:
                self.logger.error(f"Error processing link target '{link_target}' in doc '{doc_path}': {e}", exc_info=True)


        # TODO: Add analysis for specific sections like "Depends on", "Impacts" as in the plan
        # This would involve regex matching for those sections and parsing list items within them.

        self.logger.info(f"Found {len(relationships)} reference relationships in {doc_path}")
        return relationships
