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
# Package initialization file for common LLM interfaces and utilities.
# Exports the provider-agnostic base classes and shared utilities
# used across all LLM providers.
###############################################################################
# [Source file design principles]
# - Export all common interfaces from this package
# - Provide clean imports for shared LLM components
# - Keep initialization minimal to prevent circular dependencies
###############################################################################
# [Source file constraints]
# - Should only export common interfaces and utilities
# - Must not import provider-specific implementations
# - Must not contain implementation logic
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-05-02T07:10:00Z : Initial creation of common LLM package by Cline
# * Created common LLM package for provider-agnostic interfaces
# * Added exports for base interfaces and types
###############################################################################

from .base import ModelClientBase, Message
from .prompt_manager import LLMPromptManager
from .exceptions import (
    LLMError,
    ModelError,
    ClientError,
    ModelClientError,
    ModelNotAvailableError,
    InvocationError,
    PromptError,
    PromptNotFoundError,
    PromptRenderingError
)

__all__ = [
    # Base classes
    "ModelClientBase",
    "Message",
    
    # Prompt Manager
    "LLMPromptManager",
    
    # Exceptions
    "LLMError",
    "ModelError",
    "ClientError",
    "ModelClientError",
    "ModelNotAvailableError",
    "InvocationError",
    "PromptError",
    "PromptNotFoundError",
    "PromptRenderingError"
]
