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
# Package initialization file for the AWS Bedrock LLM provider implementation.
# Exports the Bedrock-specific client classes and interfaces for use by
# the rest of the application.
###############################################################################
# [Source file design principles]
# - Export all Bedrock-specific interfaces and client classes
# - Provide clean imports for Bedrock components
# - Keep initialization minimal to prevent circular dependencies
###############################################################################
# [Source file constraints]
# - Should only export Bedrock-specific interfaces and classes
# - Must not contain implementation logic
# - Must maintain backward compatibility with existing code
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-05-02T22:12:00Z : Added model discovery exports by CodeAssistant
# * Added import and export for BedrockModelDiscovery class
# * Updated __all__ list to include new model discovery component
# 2025-05-02T07:20:00Z : Initial creation of AWS Bedrock package by Cline
# * Created Bedrock LLM provider package initialization file
# * Added exports for Bedrock interfaces and errors
###############################################################################

# Legacy imports with compatibility wrappers
from .base import BedrockBase as BedrockModelClientBase

# Client common utilities
from .client_common import BedrockClientError
from .client_common import BedrockRequestFormatter, BedrockClientMixin, invoke_bedrock_model

# Discovery components
from .discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
from .discovery.models_capabilities import BedrockModelCapabilities
from .discovery.profiles import BedrockProfileDiscovery

# New LangChain-based implementations
from .langchain_wrapper import EnhancedChatBedrockConverse
from .models.claude3 import ClaudeEnhancedChatBedrockConverse
from .models.nova import NovaEnhancedChatBedrockConverse
from .client_factory import BedrockClientFactory

__all__ = [
    # Legacy components (compatibility)
    "BedrockModelClientBase",
    "BedrockClientError",
    "BedrockRequestFormatter",
    "BedrockClientMixin",
    "invoke_bedrock_model",
    
    # Discovery components
    "BedrockModelDiscovery",
    "BedrockModelCapabilities",
    "BedrockProfileDiscovery",
    
    # New LangChain-based implementations
    "EnhancedChatBedrockConverse",
    "ClaudeEnhancedChatBedrockConverse",
    "NovaEnhancedChatBedrockConverse",
    "BedrockClientFactory"
]
