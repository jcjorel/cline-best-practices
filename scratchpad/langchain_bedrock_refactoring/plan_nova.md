# Phase 3: Refactor `nova.py`

## Current Issues

Similar to the Claude case, the current `NovaClient` class in `nova.py` extends `EnhancedBedrockBase` and provides functionality for interacting with Nova models directly using the Bedrock SDK. This approach is being deprecated in favor of the LangChain integration.

We need to preserve the Nova-specific model definitions and adapt the Nova-specific response handling to work with the new LangChain-based approach.

## Planned Changes

We'll completely refactor `nova.py` to:

1. Keep only the Nova model definitions from the current implementation
2. Create a new `NovaEnhancedChatBedrockConverse` class that extends `EnhancedChatBedrockConverse`
3. Implement a Nova-specific `_extract_text_from_chunk` method
4. Remove all other code not related to the LangChain integration

### Code Changes

```python
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
# 2025-05-05T21:55:00Z : Refactored to use EnhancedChatBedrockConverse by CodeAssistant
# * Removed legacy EnhancedBedrockBase implementation
# * Created new NovaEnhancedChatBedrockConverse class
# * Implemented Nova-specific _extract_text_from_chunk method
# * Preserved SUPPORTED_MODELS definition for discovery
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
    
    @classmethod
    def _extract_text_from_chunk(cls, content: Any) -> str:
        """
        [Method intent]
        Extract text specifically from Nova model response chunks.
        
        [Design principles]
        - Nova-specific text extraction
        - Focus on Nova response format
        - Clean, maintainable implementation
        
        [Implementation details]
        - Handles Nova's specific response structure
        - Extracts text content from Nova-specific fields
        - Falls back to generic extraction if format is unexpected
        
        Args:
            content: Nova response chunk in any format
            
        Returns:
            str: Extracted text content
        """
        # Handle empty content
        if not content:
            return ""
        
        # Check for Nova-specific formats first
        if isinstance(content, dict):
            # For Nova output format
            if "output" in content and isinstance(content["output"], dict) and "text" in content["output"]:
                return content["output"]["text"]
               
            # For Nova chunk format
            if "chunk" in content and "bytes" in content["chunk"]:
                try:
                    # Nova sometimes sends JSON-encoded chunk data
                    chunk_data = json.loads(content["chunk"]["bytes"])
                    if isinstance(chunk_data, dict) and "text" in chunk_data:
                        return chunk_data["text"]
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, might be plain text
                    return content["chunk"]["bytes"]
        
        # Use parent implementation for non-Nova-specific formats
        return super()._extract_text_from_chunk(content)
```

## Implementation Notes

1. The `NovaClient` class is completely replaced by the new `NovaEnhancedChatBedrockConverse` class.
2. We keep only the `_NOVA_MODELS` and `SUPPORTED_MODELS` constants, discarding all other functionality.
3. The `_extract_text_from_chunk` method is implemented to handle Nova-specific formats:
   - The output structure with a text field
   - The chunk format with bytes field that might contain JSON
4. We delegate to the parent class's implementation for all other formats.

## Test Considerations

1. Test with all Nova models (Micro, Lite, Pro, Premier) to ensure compatibility.
2. Verify that the `_extract_text_from_chunk` method correctly handles Nova-specific response formats.
3. Test streaming responses to ensure the text extraction works properly.
4. Test handling of JSON-encoded chunks to ensure proper parsing.

## Compatibility Considerations

1. The `client_factory.py` file will need to be updated to use this new class instead of the previous `NovaClient`.
2. Any direct references to `NovaClient` in other parts of the codebase will need to be updated to use `NovaEnhancedChatBedrockConverse`.
