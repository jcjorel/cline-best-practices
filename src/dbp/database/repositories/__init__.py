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
# Entry point for the repository classes package that provide data access
# abstraction for the DBP system. Exports all repository implementations.
###############################################################################
# [Source file design principles]
# - Centralizes imports of all repository implementations
# - Provides a clean public API for repository access
# - Maintains backward compatibility with original repositories.py imports
###############################################################################
# [Source file constraints]
# - Must maintain the same public API as the original repositories.py
# - Must avoid circular imports
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:59:06Z : Created repositories package __init__.py by CodeAssistant
# * Part of refactoring repositories.py to comply with 600-line limit
###############################################################################

"""
Repository package for Database access abstractions in the DBP system.

This package contains repository implementations for each entity type,
providing data access methods and encapsulating database operations.
"""

# Import all repositories to make them available at the package level
from .base_repository import BaseRepository
from .document_repository import DocumentRepository
from .project_repository import ProjectRepository
from .relationship_repository import RelationshipRepository
from .function_repository import FunctionRepository
from .class_repository import ClassRepository
from .inconsistency_repository import InconsistencyRepository
from .recommendation_repository import RecommendationRepository
from .developer_decision_repository import DeveloperDecisionRepository
from .design_decision_repository import DesignDecisionRepository
from .change_record_repository import ChangeRecordRepository

# Define __all__ to control what gets imported with "from repositories import *"
__all__ = [
    'BaseRepository',
    'DocumentRepository',
    'ProjectRepository',
    'RelationshipRepository',
    'FunctionRepository',
    'ClassRepository',
    'InconsistencyRepository',
    'RecommendationRepository',
    'DeveloperDecisionRepository',
    'DesignDecisionRepository',
    'ChangeRecordRepository',
]
