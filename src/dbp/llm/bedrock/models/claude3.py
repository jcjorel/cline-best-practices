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
# Implements a specialized client for Anthropic's Claude 3.5+ models on Amazon Bedrock
# through the LangChain integration. This client adds Claude-specific text extraction
# capabilities while inheriting the core LangChain functionality.
###############################################################################
# [Source file design principles]
# - Claude-specific text extraction
# - Clean extension of EnhancedChatBedrockConverse
# - Support for Claude 3.5+ model variants
# - KISS approach focusing on core functionality
###############################################################################
# [Source file constraints]
# - Must be compatible with Claude 3.5 and newer models only
# - Must maintain full compatibility with LangChain
# - Must handle Claude-specific response formats correctly
# - Must integrate with client_factory.py
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/common/exceptions.py
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:15:07Z : Refactored to use EnhancedChatBedrockConverse by CodeAssistant
# * Removed legacy EnhancedBedrockBase implementation
# * Created new ClaudeEnhancedChatBedrockConverse class
# * Implemented Claude-specific _extract_text_from_chunk method
# * Preserved SUPPORTED_MODELS definition for discovery
# 2025-05-05T11:08:00Z : Removed all reasoning functionality by CodeAssistant
# * Removed all reasoning-related methods
# * Cleaned up implementation for better maintainability
# * Simplified parameter handling and processing
# * Applied KISS approach to reduce code complexity
# 2025-05-05T01:30:13Z : Updated _get_system_content method signature by CodeAssistant
# * Modified method to accept system_prompt parameter
# * Added handling for directly provided system prompts
# * Enhanced implementation to handle different system prompt types
# * Updated method documentation to reflect the changes
# 2025-05-05T00:39:00Z : Updated method names for abstract class compatibility by CodeAssistant
# * Renamed _format_messages_internal to _format_messages
# * Renamed _format_model_kwargs_internal to _format_model_kwargs
# * No functional changes, only method renaming for abstract method implementation
###############################################################################

import json
from typing import Any, Dict, ClassVar

from ..langchain_wrapper import EnhancedChatBedrockConverse


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
    - Maintains SUPPORTED_MODELS for model discovery
    - Optimized for Claude 3.5+ models
    """
    
    # Keep the supported models list from the original class
    # Supported Claude models - helps with validation
    # Only supporting Claude 3.5+ models as per requirements
    _CLAUDE_MODELS = [
        "anthropic.claude-3-5-haiku-20241022-v1:0", 
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-7-sonnet-20250219-v1:0"
    ]
    
    # Set the class-level SUPPORTED_MODELS for model discovery
    SUPPORTED_MODELS: ClassVar[list] = _CLAUDE_MODELS
    
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
