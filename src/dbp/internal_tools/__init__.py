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
# Internal Tools package for the Documentation-Based Programming system.
# Provides internal tools for LLM-based processing and analysis.
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
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


# src/dbp/internal_tools/__init__.py

"""
Internal LLM Tools package for the Documentation-Based Programming system.

This package contains the implementation of specialized tools that are invoked
by the LLM Coordinator to gather specific types of context or perform analysis.
Each tool typically involves context assembly, LLM interaction, and response handling.

Key components:
- InternalToolsComponent: The main component conforming to the core framework.
- ContextAssemblers: Classes responsible for gathering context for each tool.
- LLMInterfaces: Interfaces and placeholder implementations for different LLMs.
- ResponseHandlers: Classes for parsing and formatting LLM responses for each tool.
- ExecutionEngine: Orchestrates the execution flow for each internal tool.
- FileAccessService: Utility for filesystem operations.
- PromptLoader: Utility for loading prompt templates.
"""

# Expose key classes for easier import from the package level
from .file_access import FileAccessService
from .prompt_loader import PromptLoader, PromptLoadError
from .context_assemblers import ContextAssembler # Expose base class? Or specific ones if needed?
from .llm_interface import LLMInstance, NovaLiteInstance, ClaudeInstance # Expose placeholders/base
from .response_handlers import ResponseParser, ResultFormatter, ResponseParsingError, ResponseValidationError # Expose base classes and errors
from .execution_engine import InternalToolExecutionEngine, InternalToolError
from .component import InternalToolsComponent, ComponentNotInitializedError

__all__ = [
    # Main Component
    "InternalToolsComponent",
    # Utilities
    "FileAccessService",
    "PromptLoader",
    # Core Logic (Expose if needed by other parts, e.g., for testing/extension)
    "InternalToolExecutionEngine",
    "ContextAssembler",
    "LLMInstance",
    "ResponseParser",
    "ResultFormatter",
    # Specific Implementations (Optional - usually internal detail)
    # "NovaLiteInstance",
    # "ClaudeInstance",
    # Exceptions
    "ComponentNotInitializedError",
    "InternalToolError",
    "PromptLoadError",
    "ResponseParsingError",
    "ResponseValidationError",
]
