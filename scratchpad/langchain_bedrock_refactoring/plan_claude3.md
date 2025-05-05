# Phase 2: Refactor `claude3.py`

## Current Issues

The current `ClaudeClient` class in `claude3.py` extends `EnhancedBedrockBase` and provides functionality for interacting with Claude models directly using the Bedrock SDK. This approach is being deprecated in favor of the LangChain integration.

We need to preserve the Claude-specific model definitions and adapt the Claude-specific response handling to work with the new LangChain-based approach.

## Planned Changes

We'll completely refactor `claude3.py` to:

1. Keep only the Claude model definitions from the current implementation
2. Create a new `ClaudeEnhancedChatBedrockConverse` class that extends `EnhancedChatBedrockConverse`
3. Implement a Claude-specific `_extract_text_from_chunk` method
4. Remove all other code not related to the LangChain integration

### Code Changes

```python
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
# 2025-05-05T21:55:00Z : Refactored to use EnhancedChatBedrockConverse by CodeAssistant
# * Removed legacy EnhancedBedrockBase implementation
# * Created new ClaudeEnhancedChatBedrockConverse class
# * Implemented Claude-specific _extract_text_from_chunk method
# * Preserved SUPPORTED_MODELS definition for discovery
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
    
    @classmethod
    def _extract_text_from_chunk(cls, content: Any) -> str:
        """
        [Method intent]
        Extract text specifically from Claude model response chunks.
        
        [Design principles]
        - Claude-specific text extraction
        - Focus on Claude response format
        - Clean, maintainable implementation
        
        [Implementation details]
        - Handles Claude's specific response structure
        - Extracts text content from delta and content fields
        - Falls back to generic extraction if format is unexpected
        
        Args:
            content: Claude response chunk in any format
            
        Returns:
            str: Extracted text content
        """
        # Handle empty content
        if not content:
            return ""
        
        # Check for Claude-specific formats first
        if isinstance(content, dict):
            # For Anthropic Claude delta structure
            if "delta" in content and isinstance(content["delta"], dict):
                if "text" in content["delta"]:
                    return content["delta"]["text"]
                elif "content" in content["delta"]:
                    return content["delta"]["content"]
            
            # For direct Claude output (non-delta)
            if "completion" in content:
                return content["completion"]
        
        # Use parent implementation for non-Claude-specific formats
        return super()._extract_text_from_chunk(content)
```

## Implementation Notes

1. The `ClaudeClient` class is completely replaced by the new `ClaudeEnhancedChatBedrockConverse` class.
2. We keep only the `_CLAUDE_MODELS` and `SUPPORTED_MODELS` constants, discarding all other functionality.
3. The `_extract_text_from_chunk` method is implemented to handle Claude-specific formats:
   - The delta structure with text or content fields
   - The completion field in direct responses
4. We delegate to the parent class's implementation for all other formats.

## Test Considerations

1. Test with Claude 3.5 Haiku, Claude 3.5 Sonnet, and Claude 3.7 Sonnet to ensure compatibility.
2. Verify that the `_extract_text_from_chunk` method correctly handles Claude-specific response formats.
3. Test streaming responses to ensure the text extraction works properly.

## Compatibility Considerations

1. The `client_factory.py` file will need to be updated to use this new class instead of the previous `ClaudeClient`.
2. Any direct references to `ClaudeClient` in other parts of the codebase will need to be updated to use `ClaudeEnhancedChatBedrockConverse`.
