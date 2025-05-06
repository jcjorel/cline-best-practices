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
# Implements specialized clients and parameter classes for Anthropic's Claude models
# on Amazon Bedrock through the LangChain integration. This includes model-specific
# parameter constraints and text extraction capabilities.
###############################################################################
# [Source file design principles]
# - Model-specific parameter constraints
# - Claude-specific text extraction
# - Clean extension of EnhancedChatBedrockConverse
# - Support for all Claude model variants
# - KISS approach focusing on core functionality
###############################################################################
# [Source file constraints]
# - Must be compatible with Claude model family
# - Must maintain full compatibility with LangChain
# - Must handle Claude-specific response formats correctly
# - Must integrate with client_factory.py
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/models/claude.py
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/common/exceptions.py
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-06T13:41:59Z : Implemented Dynamic Model Discovery by CodeAssistant
# * Updated ClaudeEnhancedChatBedrockConverse to use PARAMETER_CLASSES instead of SUPPORTED_MODELS
# * Removed duplicate _CLAUDE_MODELS list in favor of parameter class definition
# * Linked parameter classes directly to client class via PARAMETER_CLASSES
# * Maintained backward compatibility with existing code
# 2025-05-06T11:23:45Z : Removed redundant get_model_id_constraint methods by CodeAssistant
# * Removed get_model_id_constraint methods from all parameter classes
# * Using base class implementation that references Config.supported_models
# * Applied DRY principle to eliminate code duplication
# * Maintained functionality with cleaner code
# 2025-05-06T10:30:00Z : Fixed profiles implementation for Pydantic compatibility by CodeAssistant
# * Fixed _profiles structure to use proper class variables instead of direct base class access
# * Added model-specific profiles as ClassVar dictionaries for proper Pydantic handling
# * Updated profile inheritance mechanism to be compatible with Pydantic
# 2025-05-06T10:25:00Z : Updated with concrete Claude parameter classes by CodeAssistant
# * Added Claude3Parameters, Claude35Parameters, and Claude37Parameters classes
# * Imported abstract ClaudeParameters from claude.py
# * Added model-specific max_tokens constraints
# * Added Claude 3.7-exclusive reasoning profile
###############################################################################

import json
from typing import Any, Dict, ClassVar, List
import copy

from ..langchain_wrapper import EnhancedChatBedrockConverse
from .claude import ClaudeParameters
from pydantic import Field


class Claude3Parameters(ClaudeParameters):
    """
    [Class intent]
    Parameters specific to original Claude 3 models (Haiku, Sonnet, Opus).
    
    [Design principles]
    - Define Claude 3-specific parameter constraints
    - Support proper max_tokens limit for this model family
    
    [Implementation details]
    - Sets max_tokens limit specific to Claude 3 models (4096)
    - Lists only Claude 3 model variants in supported models
    """

    max_tokens: int = Field(
        default=1024,  # Conservative default
        ge=1,
        le=4096,       # Claude 3 specific maximum from documentation
        description="Maximum number of tokens to generate in the response. Claude 3 supports up to 4K tokens output."
    )
    
    # Combine base profiles with any Claude 3 specific profiles
    _profiles = ClaudeParameters.base_profiles
    
    class Config:
        model_name = "Claude 3"
        supported_models = [
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-opus-20240229-v1:0"
        ]


class Claude35Parameters(ClaudeParameters):
    """
    [Class intent]
    Parameters specific to Claude 3.5 models, with appropriate token limits.
    
    [Design principles]
    - Define Claude 3.5-specific parameter constraints
    - Support proper max_tokens limit for this model family
    
    [Implementation details]
    - Sets max_tokens limit specific to Claude 3.5 models (8192)
    - Lists only Claude 3.5 model variants in supported models
    """

    max_tokens: int = Field(
        default=2048,  # Conservative default
        ge=1,
        le=8192,       # Claude 3.5 specific maximum from documentation
        description="Maximum number of tokens to generate in the response. Claude 3.5 supports up to 8K tokens output."
    )
    
    # Combine base profiles with any Claude 3.5 specific profiles
    _profiles = ClaudeParameters.base_profiles
    
    class Config:
        model_name = "Claude 3.5"
        supported_models = [
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        ]


class Claude37Parameters(ClaudeParameters):
    """
    [Class intent]
    Parameters specific to Claude 3.7 models, with support for higher token output
    limits and exclusive features such as reasoning.
    
    [Design principles]
    - Define Claude 3.7-specific parameter constraints
    - Support extended output capabilities with appropriate max_tokens limit
    - Provide Claude 3.7-specific profiles including exclusive reasoning mode
    
    [Implementation details]
    - Sets higher max_tokens limit specific to Claude 3.7 Sonnet (64000)
    - Defines profiles optimized for extended output generation
    - Includes exclusive reasoning profile only available for Claude 3.7
    - Lists only Claude 3.7 model variants in supported models
    """

    max_tokens: int = Field(
        default=4096,  # Conservative default that works well in most cases
        ge=1,
        le=64000,      # Claude 3.7 specific maximum from documentation
        description="Maximum number of tokens to generate in the response. Claude 3.7 supports up to 64K tokens output."
    )
    
    # Define Claude 3.7 specialized profiles as a class variable
    claude37_profiles: ClassVar[Dict[str, Dict[str, Any]]] = {
        # Add Claude 3.7 exclusive reasoning profile
        "reasoning": {
            "applicable_params": [],
            "not_applicable_params": None,
            "param_overrides": {}
        },
        
        # Add Claude 3.7 specific profiles for extended output
        "extended": {
            "applicable_params": None,
            "not_applicable_params": [],
            "param_overrides": {
                "max_tokens": 16000,  # Higher but reasonable default for extended outputs
                "temperature": 0.7
            }
        },
        
        "long_form": {
            "applicable_params": None,
            "not_applicable_params": [],
            "param_overrides": {
                "max_tokens": 32000,  # For very long-form content generation
                "temperature": 0.8,
                "top_p": 0.95
            }
        }
    }
    
    # Combine base profiles with Claude 3.7 specific profiles
    _profiles = {**ClaudeParameters.base_profiles, **claude37_profiles}
    
    class Config:
        model_name = "Claude 3.7"
        supported_models = [
            "anthropic.claude-3-7-sonnet-20250219-v1:0"
        ]


class ClaudeEnhancedChatBedrockConverse(EnhancedChatBedrockConverse):
    """
    [Class intent]
    Provides Claude-specific implementation of EnhancedChatBedrockConverse with
    specialized text extraction for Claude response formats.
    
    [Design principles]
    - Claude-specific text extraction
    - Clean extension of EnhancedChatBedrockConverse
    - Simple and maintainable implementation
    
    [Implementation details]
    - Implements Claude-specific _extract_text_from_chunk method
    - References parameter classes for supported models
    - Optimized for Claude models
    """
    
    # Implementation of required abstract properties
    model_provider: ClassVar[str] = "Anthropic"
    model_family_friendly_name: ClassVar[str] = "Claude"
    
    # Reference parameter classes instead of duplicating model lists
    PARAMETER_CLASSES = [Claude3Parameters, Claude35Parameters, Claude37Parameters]
    
    def _extract_text_from_chunk(self, content: Any) -> str:
        """
        [Method intent]
        Extract text specifically from Claude model response chunks.
        
        [Design principles]
        - Claude-specific text extraction focusing on core object types
        - Handles list and dict formats directly without string parsing
        - Clear separation between different response formats
        
        [Implementation details]
        - Primarily handles list and dict objects as received from Claude
        - Focuses on the content/text format used by Claude
        - Extracts text content from all chunks for complete response
        
        Args:
            content: Claude response chunk (None, list, or dict)
            
        Returns:
            str: Extracted text content
        """
        # Handle None/empty content
        if content is None:
            return ""
        
        # Handle list formats (multiple content parts)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    # Claude might use {'text': 'content'} format in lists
                    if "text" in item:
                        text_parts.append(item["text"])
                    # Or sometimes {'type': 'text', 'text': 'content'} like Nova
                    elif item.get("type") == "text" and "text" in item:
                        text_parts.append(item["text"])
                    
            # Join all found text parts
            return ''.join(text_parts)
        
        # Handle dictionary format
        elif isinstance(content, dict):
            # Most common Claude pattern with content list
            if "content" in content and isinstance(content["content"], list):
                text_parts = []
                for item in content["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                if text_parts:
                    return ''.join(text_parts)
                        
            # Direct content as string
            if "content" in content and isinstance(content["content"], str):
                return content["content"]
            
            # For Claude delta streaming format
            if "delta" in content and isinstance(content["delta"], dict):
                if "text" in content["delta"]:
                    return content["delta"]["text"]
                elif "content" in content["delta"]:
                    return content["delta"]["content"]
            
            # For direct Claude completion output
            if "completion" in content:
                return content["completion"]
                
            # Simple text field
            if "text" in content:
                return content["text"]
                
        # Handle LangChain wrapper objects
        if hasattr(content, "content"):
            # If content is a list (typical Claude format)
            if isinstance(content.content, list):
                text_parts = []
                for item in content.content:
                    # Standard Claude format in LangChain
                    if hasattr(item, "text"):
                        text_parts.append(item.text)
                    # Dict format in list
                    elif isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                if text_parts:
                    return ''.join(text_parts)
                    
            # If it's already a string
            if isinstance(content.content, str):
                return content.content
                
            # If it has a dict or list structure, recursively extract text
            return self._extract_text_from_chunk(content.content)
            
        if hasattr(content, "message") and hasattr(content.message, "content"):
            # Extract from message content
            return self._extract_text_from_chunk(content.message.content)
            
        # For string content
        if isinstance(content, str):
            return content
            
        # For any other case, safely convert to string
        if content is not None:
            return str(content)
            
        return ""
