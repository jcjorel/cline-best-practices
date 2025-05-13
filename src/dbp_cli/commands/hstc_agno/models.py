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
# This file defines the data models used by the HSTC implementation with Agno.
# It includes structures for representing file metadata, comments, dependencies,
# and documentation components needed for HSTC generation.
###############################################################################
# [Source file design principles]
# - Clean data structures with clear type annotations
# - Immutable data classes for core models
# - Serializable models for state persistence
# - Consistent representation of file and documentation components
###############################################################################
# [Source file constraints]
# - Should use standard Python data classes where possible
# - Models must be serializable for agent message passing
# - Field types must be explicitly defined
###############################################################################
# [Dependencies]
# system:dataclasses
# system:enum
# system:typing
# system:pathlib
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:07:00Z : Initial implementation by CodeAssistant
# * Created file skeleton with basic imports
# * Added placeholder structures
###############################################################################

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union
from pathlib import Path
from datetime import datetime


@dataclass
class CommentFormat:
    """
    [Class intent]
    Comment format information for a programming language.
    
    [Design principles]
    Encapsulates all comment-related syntax for consistent parsing.
    Provides a clear interface for language-specific comment handling.
    
    [Implementation details]
    Stores different comment markers and documentation formats.
    Used by the File Analyzer to identify and extract comments.
    """
    inline_comment: Optional[str] = None
    block_comment_start: Optional[str] = None
    block_comment_end: Optional[str] = None
    docstring_format: Optional[str] = None
    docstring_start: Optional[str] = None
    docstring_end: Optional[str] = None
    has_documentation_comments: bool = False


@dataclass
class Dependency:
    """
    [Class intent]
    Dependency information for a source file.
    
    [Design principles]
    Tracks relationships between source files and external components.
    Distinguishes between different dependency types for context-aware processing.
    
    [Implementation details]
    Uses standard naming conventions for dependency types.
    Stores optional function references for more specific dependency tracking.
    """
    name: str
    kind: str  # One of "codebase", "system", "external"
    path_or_package: str
    function_names: List[str] = field(default_factory=list)


@dataclass
class Definition:
    """
    [Class intent]
    Function, method or class definition extracted from source code.
    
    [Design principles]
    Represents code structural elements with their documentation.
    Maintains both original and updated comments for change tracking.
    
    [Implementation details]
    Stores location information for source mapping.
    Preserves comments for documentation generation.
    """
    name: str
    type: str  # One of "function", "method", "class"
    line_number: int
    comments: str = ""
    updated_comment: str = ""


@dataclass
class FileMetadata:
    """
    [Class intent]
    Comprehensive metadata about a source file.
    
    [Design principles]
    Central data structure for file analysis results.
    Aggregates all file-related information in a single structure.
    
    [Implementation details]
    Includes file system metadata, language detection, and comment parsing results.
    Stores extracted definitions and dependencies for documentation processing.
    """
    path: str
    size: int
    last_modified: float
    file_type: str
    is_binary: bool = False
    language: str = ""
    confidence: int = 0
    file_extension: str = ""
    comment_formats: Optional[CommentFormat] = None
    header_comment: str = ""
    dependencies: List[Dependency] = field(default_factory=list)
    definitions: List[Definition] = field(default_factory=list)


@dataclass
class HeaderDocumentation:
    """
    [Class intent]
    Documentation for a file header following HSTC standards.
    
    [Design principles]
    Structured representation of the standard HSTC header format.
    Separates content into logical sections for targeted updates.
    
    [Implementation details]
    Maps directly to the required HSTC header sections.
    Maintains change history for documentation updates.
    """
    intent: str
    design_principles: str
    constraints: str
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    change_history: List[str] = field(default_factory=list)
    raw_header: str = ""


@dataclass
class DefinitionDocumentation:
    """
    [Class intent]
    Documentation for a function, method, or class.
    
    [Design principles]
    Tracks both original and updated documentation.
    Provides clear structure for documentation generation agents.
    
    [Implementation details]
    Associates documentation with specific code elements.
    Supports evaluation of documentation quality and compliance.
    """
    name: str
    type: str
    original_comment: str
    updated_comment: str


@dataclass
class Documentation:
    """
    [Class intent]
    Complete documentation for a file, including header and definitions.
    
    [Design principles]
    Aggregates all documentation components for a file.
    Provides context for documentation generation and updates.
    
    [Implementation details]
    Maintains file metadata for context preservation.
    Tracks analysis and reasoning about documentation changes.
    """
    path: str
    file_type: str
    language: str = ""
    file_header: Optional[HeaderDocumentation] = None
    definitions: List[DefinitionDocumentation] = field(default_factory=list)
    documentation_updated: bool = False
    analysis: str = ""
    reason: str = ""


@dataclass
class ValidationResult:
    """
    [Class intent]
    Result of documentation validation against HSTC standards.
    
    [Design principles]
    Captures validation outcomes with detailed issue reporting.
    Provides actionable feedback for documentation improvement.
    
    [Implementation details]
    Reports specific issues with clear references to requirements.
    Includes reasoning for validation decisions.
    """
    valid: bool
    issues: List[str] = field(default_factory=list)
    file_path: str = ""
    reason: str = ""
