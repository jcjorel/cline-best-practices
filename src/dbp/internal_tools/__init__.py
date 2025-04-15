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
