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
# Package initialization file for the LLM module, which provides generic
# utilities for working with Large Language Models across the application.
###############################################################################
# [Source file design principles]
# - Export public interfaces from submodules.
# - Handle import errors gracefully.
###############################################################################
# [Source file constraints]
# - Keep imports minimal to prevent circular dependencies.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
# codebase:- doc/llm/prompts/README.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T13:45:00Z : Added Claude 3.7 Sonnet client by Cline
# * Added Claude37SonnetClient for working with Anthropic's Claude 3.7 Sonnet
# * Updated exports and registrations
# 2025-04-16T13:00:00Z : Added Bedrock client system by Cline
# * Created BedrockModelClientBase abstract base class
# * Implemented NovaLiteClient for Amazon Nova Lite
# * Created singleton BedrockClientManager for client lifecycle management
# 2025-04-16T11:57:00Z : Initial creation of LLM package by Cline
# * Created package initialization file with prompt manager
###############################################################################

try:
    from .prompt_manager import LLMPromptManager, PromptLoadError
    from .bedrock_base import BedrockModelClientBase, BedrockClientError
    from .nova_lite_client import NovaLiteClient
    from .claude3_7_client import Claude37SonnetClient
    from .bedrock_manager import BedrockClientManager
    
    # Export public interfaces
    __all__ = [
        "LLMPromptManager",
        "PromptLoadError",
        "BedrockModelClientBase",
        "BedrockClientError",
        "NovaLiteClient",
        "Claude37SonnetClient",
        "BedrockClientManager"
    ]
except ImportError as e:
    import logging
    logging.getLogger(__name__).error(f"Error importing LLM module components: {e}", exc_info=True)
