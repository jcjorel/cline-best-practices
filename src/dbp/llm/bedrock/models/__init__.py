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
# Package initialization file for the AWS Bedrock model implementations.
# Exports the specific model client classes for various foundation models
# available through AWS Bedrock.
###############################################################################
# [Source file design principles]
# - Export all model-specific client implementations
# - Provide clean imports for model client classes
# - Keep initialization minimal to prevent circular dependencies
###############################################################################
# [Source file constraints]
# - Should only export model-specific client implementations
# - Must not contain implementation logic
# - Must maintain backward compatibility with existing code
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-05-02T12:14:00Z : Consolidated Claude model implementations by Cline
# * Removed Claude37SonnetClient export
# * Added ClaudeClient export from claude3.py
# * Consolidated to use single Claude implementation
# 2025-05-02T07:26:00Z : Initial creation of models package by Cline
# * Created package initialization file for model implementations
# * Added exports for model-specific client classes
###############################################################################

from .claude3 import ClaudeClient
from .nova import NovaClient

__all__ = [
    "ClaudeClient",
    "NovaClient"
]
