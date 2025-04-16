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
# Entry point for the database package that provides imports for all essential
# database-related modules and classes. Defines the public API for database access.
###############################################################################
# [Source file design principles]
# - Provides a clean, simple interface for accessing database functionality.
# - Maintains backward compatibility for existing imports.
# - Follows Python's explicit import philosophy.
# - Enables easy access to both models and repositories.
###############################################################################
# [Source file constraints]
# - Must avoid circular imports.
# - Should not expose internal implementation details.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:42:52Z : Created database package __init__ file by CodeAssistant
# * Added imports for database.py, models.py, and repositories.py
# * Defined public exports via __all__
###############################################################################

"""
Database package for the Documentation-Based Programming system.

This package provides database functionality including:
- A manager for SQLAlchemy session handling
- ORM models for database entities
- Repository classes that implement the Repository pattern for database access
"""

# Import essential components for easy access
from .database import DatabaseManager, DatabaseComponent
from . import models
from . import repositories

# Define what gets imported with "from database import *"
__all__ = [
    'DatabaseManager',
    'DatabaseComponent',
    'models',
    'repositories'
]
