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
# Provides backward compatibility for the refactored repository classes.
# This file is a shim that re-exports all repository classes from their
# individual module files to maintain API compatibility with existing code.
###############################################################################
# [Source file design principles]
# - Maintains backward compatibility with existing code.
# - Re-exports repository classes from their dedicated modules.
# - Provides explicit imports to clarify the actual location of implementations.
# - Maintains the same public API as the original repositories.py file.
###############################################################################
# [Source file constraints]
# - Must maintain exact same public API as the original monolithic repositories.py.
# - Should not contain any implementation code, only imports and re-exports.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:38:07Z : Refactored file to be a compatibility shim for modular repositories by CodeAssistant
# * Removed all implementation code and replaced with imports from modular files
# * Added deprecation warning for importing directly from this file
# 2025-04-15T09:33:05Z : Initial creation of repository classes by CodeAssistant
# * Implemented BaseRepository and DocumentRepository.
###############################################################################

"""
Repository classes for database access abstraction.

This file re-exports all repository classes from their individual modules
to maintain backward compatibility with existing code that imports repositories
from this file.

All actual implementations have been moved to the repositories/ package.
"""

import logging
logger = logging.getLogger(__name__)
logger.warning("Importing from repositories.py is deprecated. "
               "Import from repositories/ package modules directly.")

# Re-export all repository classes for backward compatibility
from .repositories.base_repository import BaseRepository
from .repositories.document_repository import DocumentRepository
from .repositories.project_repository import ProjectRepository
from .repositories.relationship_repository import RelationshipRepository
from .repositories.function_repository import FunctionRepository
from .repositories.class_repository import ClassRepository
from .repositories.inconsistency_repository import InconsistencyRepository
from .repositories.recommendation_repository import RecommendationRepository
from .repositories.developer_decision_repository import DeveloperDecisionRepository
from .repositories.design_decision_repository import DesignDecisionRepository
from .repositories.change_record_repository import ChangeRecordRepository

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


