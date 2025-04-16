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
# Core package for the Documentation-Based Programming system.
# Implements the core component framework and lifecycle management.
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


# src/dbp/core/__init__.py

"""
Core package for the Documentation-Based Programming system.

Contains the simplified building blocks for the application's structure
and lifecycle management, using the KISS component initialization framework.

Key components:
- Component: Base class for all system components with simplified lifecycle methods.
- InitializationContext: Compatibility class for component initialization.
- ComponentSystem: Central registry managing component dependencies and initialization.
- LifecycleManager: High-level application entry point managing the overall lifecycle.
"""

from .component import Component, InitializationContext
from .system import ComponentSystem
from .lifecycle import LifecycleManager

__all__ = [
    "Component",
    "InitializationContext",
    "ComponentSystem",
    "LifecycleManager",
]
