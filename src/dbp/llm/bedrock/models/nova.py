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
# Implements Amazon Bedrock Nova model support through the LangChain integration.
# This provides Nova-specific text extraction capabilities while inheriting the
# core LangChain functionality.
###############################################################################
# [Source file design principles]
# - Nova-specific text extraction
# - Clean extension of EnhancedChatBedrockConverse
# - Support for all Nova model variants
# - KISS approach focusing on core functionality
###############################################################################
# [Source file constraints]
# - Must handle Nova-specific response formats correctly
# - Must maintain full compatibility with LangChain
# - Must integrate with client_factory.py
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/common/exceptions.py
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:16:36Z : Refactored to use EnhancedChatBedrockConverse by CodeAssistant
# * Removed legacy EnhancedBedrockBase implementation
# * Created new NovaEnhancedChatBedrockConverse class
# * Implemented Nova-specific _extract_text_from_chunk method
# * Preserved SUPPORTED_MODELS definition for discovery
# 2025-05-05T01:30:50Z : Updated _get_system_content method signature by CodeAssistant
# * Modified method to accept system_prompt parameter
# * Added handling for directly provided system prompts
# * Enhanced implementation to support various system prompt types
# * Updated method documentation to reflect the changes
# 2025-05-05T00:38:00Z : Updated method names for abstract class compatibility by CodeAssistant
# * Renamed _format_messages_internal to _format_messages
# * Renamed _format_model_kwargs_internal to _format_model_kwargs
# * No functional changes, only method renaming for abstract method implementation
# 2025-05-04T23:45:00Z : Refactored to use template method pattern for request preparation by CodeAssistant
# * Removed duplicated stream_chat implementation
# * Added standardized parameter handling through internal methods
# * Implemented _format_messages_internal, _format_model_kwargs_internal
# * Added _get_system_content and _get_model_specific_params methods
# * Updated process_multimodal_message to use _prepare_request
###############################################################################

import json
from typing import Any, Dict, ClassVar

from ..langchain_wrapper import EnhancedChatBedrockConverse


class NovaEnhancedChatBedrockConverse(EnhancedChatBedrockConverse):
    """
    [Class intent]
    Provides Nova-specific implementation of EnhancedChatBedrockConverse with
    specialized text extraction for Nova response formats.
    
    [Design principles]
    - Nova-specific text extraction
    - Clean extension of EnhancedChatBedrockConverse
    - Simple and maintainable implementation
    
    [Implementation details]
    - Implements Nova-specific _extract_text_from_chunk method
    - Maintains SUPPORTED_MODELS for model discovery
    - Support for all Nova model variants
    """
    
    # Keep the supported models list from the original class
    _NOVA_MODELS = [
        "amazon.nova-lite-v1:0",
        "amazon.nova-micro-v1:0",
        "amazon.nova-pro-v1:0",
        "amazon.nova-premier-v1:0",
    ]
    
    # Set the class-level SUPPORTED_MODELS for model discovery
    SUPPORTED_MODELS: ClassVar[list] = _NOVA_MODELS
    
    def _extract_text_from_chunk(self, content: Any) -> str:
        """
        [Method intent]
        Extract text specifically from Nova model response chunks.
        
        [Design principles]
        - Nova-specific text extraction focusing on core object types
        - Handles list and dict formats directly without string parsing
        - Clear separation between different response formats
        
        [Implementation details]
        - Primarily handles list and dict objects as received from Nova
        - Focuses on the {'type': 'text', 'text': content} format
        - Extracts text content from all chunks for complete response
        
        Args:
            content: Nova response chunk (None, list, or dict)
            
        Returns:
            str: Extracted text content
        """
        # Handle None/empty content
        if content is None:
            return ""
            
        # Handle list of dictionaries (Nova's standard streaming format)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    # Nova uses {'type': 'text', 'text': 'content', 'index': 0} format
                    if item.get("type") == "text" and "text" in item:
                        text_parts.append(item["text"])
            
            # Join all found text parts
            return ''.join(text_parts)
        
        # Handle dictionary format
        elif isinstance(content, dict):
            # Nova type/text format: {'type': 'text', 'text': 'content', 'index': 0}
            if content.get("type") == "text" and "text" in content:
                return content["text"]
                
            # Standard Nova output format: {'output': {'text': 'content'}}
            if "output" in content and isinstance(content["output"], dict) and "text" in content["output"]:
                return content["output"]["text"]
               
            # For streaming chunks: {'chunk': {'bytes': '...'}}
            if "chunk" in content and "bytes" in content["chunk"]:
                try:
                    # Try to parse as JSON
                    chunk_data = json.loads(content["chunk"]["bytes"])
                    if isinstance(chunk_data, dict) and "text" in chunk_data:
                        return chunk_data["text"]
                except (json.JSONDecodeError, TypeError):
                    # Return bytes as string if not JSON
                    return str(content["chunk"]["bytes"])
            
            # Direct text field
            if "text" in content:
                return content["text"]
                
            # Completion field for older formats
            if "completion" in content:
                return content["completion"]
                
        # Handle LangChain wrapper objects
        if hasattr(content, "content"):
            # If it's already a string, return directly
            if isinstance(content.content, str):
                return content.content
                
            # If it has a dict or list structure, recursively extract text
            return self._extract_text_from_chunk(content.content)
            
        if hasattr(content, "message") and hasattr(content.message, "content"):
            # Extract from message content
            return self._extract_text_from_chunk(content.message.content)
            
        # For any other case, safely convert to string
        if content is not None:
            return str(content)
            
        return ""
