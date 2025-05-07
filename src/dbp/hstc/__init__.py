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
# Package initialization for the HSTC module that manages Hierarchical Semantic Tree 
# Context (HSTC) files. Provides public imports for key components and functions.
###############################################################################
# [Source file design principles]
# - Minimal imports to avoid circular dependencies
# - Clear public interface through explicit exports
# - Version information for module tracking
###############################################################################
# [Source file constraints]
# - Must not contain implementation details, only imports and version
###############################################################################
# [Dependencies]
# codebase:src/dbp/hstc/component.py
###############################################################################
# [GenAI tool change history]
# 2025-05-07T11:46:00Z : Initial creation of HSTC module package by CodeAssistant
# * Created package initialization file
# * Added version information and imports
# * Established public interface
###############################################################################

"""
HSTC (Hierarchical Semantic Tree Context) module for managing HSTC.md files.
"""

__version__ = '0.1.0'

# Public imports
from .component import HSTCComponent
