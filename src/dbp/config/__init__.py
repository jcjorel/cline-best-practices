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
# Configuration management package for the Documentation-Based Programming system.
# Provides imports for configuration-related classes and defines the public API.
###############################################################################
# [Source file design principles]
# - Exports only the essential configuration classes needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for configuration interfaces
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/CONFIGURATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:55:04Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################

"""
Configuration management package for the Documentation-Based Programming system.

This package includes:
- Configuration schema definition using Pydantic (`config_schema.py`).
- A singleton manager for loading and accessing configuration (`config_manager.py`).
- A helper for managing project-specific configuration contexts (`project_config.py`).
"""

# Make key classes easily importable from the package level
from .config_schema import AppConfig
from .config_manager import ConfigurationManager
from .project_config import ProjectConfigManager

__all__ = [
    "AppConfig",
    "ConfigurationManager",
    "ProjectConfigManager",
]
