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
# Defines the Pydantic data models used to represent the structured metadata
# extracted from source code files by the Metadata Extraction component.
# These models align with the structure defined in doc/DATA_MODEL.md.
###############################################################################
# [Source file design principles]
# - Uses Pydantic models for data validation and clear structure definition.
# - Mirrors the FileMetadata structure outlined in the data model documentation.
# - Uses descriptive field names and type hints.
# - Allows for optional fields where appropriate based on LLM extraction variability.
# - Design Decision: Pydantic Models for Metadata (2025-04-15)
#   * Rationale: Provides data validation, serialization, and clear schema definition, consistent with configuration handling.
#   * Alternatives considered: Dataclasses (less validation), Plain dictionaries (no structure/validation).
###############################################################################
# [Source file constraints]
# - Requires Pydantic library.
# - Structure must be kept consistent with doc/DATA_MODEL.md and the expected
#   output schema used in LLM prompts.
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:50:30Z : Initial creation of metadata data structures by CodeAssistant
# * Defined Pydantic models for LineRange, ChangeRecord, HeaderSections, etc.
###############################################################################

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Using Pydantic models instead of dataclasses shown in the plan for consistency
# with config_schema and built-in validation.

class LineRange(BaseModel):
    """Represents a line range (start and end line numbers) in a file."""
    start: Optional[int] = None
    end: Optional[int] = None

class ChangeRecord(BaseModel):
    """Represents a single entry in a file's change history section."""
    timestamp: Optional[datetime] = None # Allow flexibility in parsing
    summary: Optional[str] = None
    details: Optional[List[str]] = Field(default_factory=list)

class HeaderSections(BaseModel):
    """Represents the structured documentation extracted from a file's header comment."""
    intent: Optional[str] = None
    design_principles: Optional[List[str]] = Field(default_factory=list)
    constraints: Optional[List[str]] = Field(default_factory=list)
    reference_documentation: Optional[List[str]] = Field(default_factory=list)
    change_history: Optional[List[ChangeRecord]] = Field(default_factory=list)

class DocSections(BaseModel):
    """Represents the structured documentation extracted from a function or class docstring."""
    intent: Optional[str] = None
    design_principles: Optional[List[str]] = Field(default_factory=list)
    implementation_details: Optional[str] = None
    design_decisions: Optional[str] = None # Could be structured further if needed

class FunctionMetadata(BaseModel):
    """Represents metadata extracted for a single function or method."""
    name: Optional[str] = None
    doc_sections: Optional[DocSections] = Field(default_factory=DocSections)
    parameters: Optional[List[str]] = Field(default_factory=list)
    line_range: Optional[LineRange] = Field(default_factory=LineRange)

class ClassMetadata(BaseModel):
    """Represents metadata extracted for a single class."""
    name: Optional[str] = None
    doc_sections: Optional[DocSections] = Field(default_factory=DocSections)
    methods: Optional[List[FunctionMetadata]] = Field(default_factory=list) # Nested methods
    line_range: Optional[LineRange] = Field(default_factory=LineRange)

class FileMetadata(BaseModel):
    """
    Represents the complete set of metadata extracted from a single source code file.
    This is the primary data structure produced by the Metadata Extraction component.
    """
    path: str # File path is mandatory
    language: Optional[str] = None # Detected programming language
    header_sections: Optional[HeaderSections] = Field(default_factory=HeaderSections)
    functions: Optional[List[FunctionMetadata]] = Field(default_factory=list)
    classes: Optional[List[ClassMetadata]] = Field(default_factory=list)

    # Additional metadata added during processing (not directly from LLM)
    size_bytes: Optional[int] = None
    md5_digest: Optional[str] = None
    last_modified: Optional[datetime] = None # Filesystem last modified time
    extraction_timestamp: Optional[datetime] = None # When this metadata was extracted

    class Config:
        # Allow extra fields if the LLM returns unexpected data, although parsing should handle this
        extra = 'ignore'
