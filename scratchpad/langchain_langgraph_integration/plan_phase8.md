# Phase 8: Claude Model Implementation

This phase implements the Claude-specific model client for the LangChain/LangGraph integration. It builds on the Bedrock Base implementation from Phase 7 to add Claude-specific functionality, particularly reasoning support and parameter handling.

## Objectives

1. Create a Claude-specific client implementation
2. Implement reasoning support feature
3. Build Claude-specific parameter handling
4. Develop Claude response processing

## ClaudeClient Implementation

Create the Claude model client in `src/dbp/llm/bedrock/models/claude3.py`:

```python
import logging
import json
from typing import Dict, Any, List, Optional, AsyncIterator, Union

from src.dbp.llm.bedrock.base import BedrockBase
from src.dbp.llm.common.streaming import StreamingResponse
from src.dbp.llm.common.exceptions import LLMError, InvocationError

class ClaudeClient(BedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Claude models.
    This client adds Claude-specific features like reasoning support and
    parameter handling while maintaining the streaming-focused approach.
    
    [Design principles]
    - Claude-specific parameter optimization
    - Reasoning support for enhanced outputs
    - Specialized message formatting for Claude
    - Clean extension of BedrockBase
    
    [Implementation details]
    - Supports all Claude model variants (Claude 3 Haiku, Sonnet, etc.)
    - Implements Claude-specific parameter mapping
    - Adds specialized reasoning support
    - Optimizes default parameters for Claude
    """
    
    # Supported Claude models - helps with validation
    _CLAUDE_MODELS = [
        "anthropic.claude-3-haiku-20240307-v1",
        "anthropic.claude-3-sonnet-20240229-v1",
        "anthropic.claude-3-opus-20240229-v1",
        "anthropic.claude-instant-v1",
        "anthropic.claude-v2",
        "anthropic.claude-v2:1"
    ]
    
    # Default Claude parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TOP_P = 0.9
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = BedrockBase.DEFAULT_RETRIES,
        timeout: int = BedrockBase.DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the Claude client with model validation and Claude-specific defaults.
        
        [Design principles]
        - Strong model validation
        - Claude-specific configuration
        - Clean delegation to base class
        
        [Implementation details]
        - Validates that model_id is a Claude model
        - Sets up Claude-specific logging
        - Initializes with Claude defaults
        
        Args:
            model_id: Claude model ID (e.g., "anthropic.claude-3-haiku-20240307-v1:0")
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            
        Raises:
            ValueError: If model_id is not a supported Claude model
        """
        # Validate model is a Claude model
        base_model_id = model_id.split(":")[0]
        is_claude_model = any(base_model_id.startswith(model) for model in self._CLAUDE_MODELS)
        
        if not is_claude_model:
            raise ValueError(f"Model {model_id} is not a supported Claude model")
        
        # Initialize base class
        super().__init__(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            credentials=credentials,
            max_retries=max_retries,
            timeout=timeout,
            logger=logger or logging.getLogger("ClaudeClient")
        )
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Claude models.
        
        [Design principles]
        - Claude-specific message formatting
        - Support for system messages
        - Handle content format variations
        
        [Implementation details]
        - Properly formats system messages for Claude
        - Handles content blocks for different content types
        - Ensures proper message role mapping
        
        Args:
            messages: List of message objects in standard format
            
        Returns:
            List[Dict[str, Any]]: Messages formatted for Claude API
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Format for Claude's expected structure
            formatted_msg = {"role": role}
            
            # Handle content formatting
            if isinstance(content, str):
                formatted_msg["content"] = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                # Assume already in correct format for multimodal
                formatted_msg["content"] = content
            else:
                raise ValueError(f"Unsupported content format: {type(content)}")
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages
    
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters specifically for Claude models.
        
        [Design principles]
        - Claude-specific parameter mapping
        - Support for reasoning feature
        - Parameter validation and defaults
        
        [Implementation details]
        - Maps standard parameters to Claude-specific names
        - Adds Claude-specific parameters
        - Supports reasoning configuration
        - Provides Claude-optimized defaults
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Claude API
        """
        # Start with basic parameters
        formatted_kwargs = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokens": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P),
            "stopSequences": kwargs.get("stop_sequences", [])
        }
        
        # Add Claude-specific parameters
        if "anthropic_version" in kwargs:
            formatted_kwargs["anthropicVersion"] = kwargs["anthropic_version"]
            
        # Add reasoning configuration if requested
        use_reasoning = kwargs.get("use_reasoning", False)
        if use_reasoning:
            # Claude 3 models support the system parameter for reasoning
            formatted_kwargs["additionalModelRequestFields"] = {
                "anthropic_version": "bedrock-2023-05-31",
                "system": "Use step-by-step reasoning to solve this problem."
            }
        
        return formatted_kwargs
    
    async def stream_chat_with_reasoning(
        self, 
        messages: List[Dict[str, Any]], 
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        [Method intent]
        Stream a chat with reasoning enabled, which instructs Claude to show its work.
        
        [Design principles]
        - Simple interface for reasoning-enabled chats
        - Maintain streaming semantics
        - Parameter consistency with base methods
        
        [Implementation details]
        - Sets reasoning flag in parameters
        - Delegates to stream_chat with updated parameters
        - Preserves streaming behavior
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Additional parameters
            
        Yields:
            Dict[str, Any]: Response chunks from Claude
            
        Raises:
            LLMError: If chat generation fails
        """
        # Enable reasoning
        kwargs["use_reasoning"] = True
        
        # Delegate to stream_chat with reasoning enabled
        async for chunk in self.stream_chat(messages, **kwargs):
            yield chunk
    
    def _parse_claude_response(self, response_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Parse Claude-specific response chunks into a standard format.
        
        [Design principles]
        - Consistent response format
        - Claude-specific parsing logic
        - Error handling for unexpected formats
        
        [Implementation details]
        - Extracts relevant information from Claude responses
        - Standardizes response format
        - Handles Claude-specific metadata
        
        Args:
            response_chunk: Response chunk from Claude
            
        Returns:
            Dict[str, Any]: Standardized response chunk
        """
        # Handle different chunk types
        if "type" not in response_chunk:
            return response_chunk  # Already processed elsewhere
        
        chunk_type = response_chunk.get("type", "")
        
        if chunk_type == "content_block_delta":
            # Extract text from Claude delta format
            delta = response_chunk.get("delta", {})
            text = delta.get("text", "")
            
            return {
                "type": "text",
                "text": text
            }
        elif chunk_type == "message_stop":
            # Extract complete message and metadata
            message = response_chunk.get("message", {})
            stop_reason = response_chunk.get("stop_reason")
            
            return {
                "type": "stop",
                "text": message.get("content", ""),
                "stop_reason": stop_reason
            }
            
        # For other chunk types, return as is
        return response_chunk
```

## Implementation Steps

1. **Create Claude Client Class**
   - Implement `ClaudeClient` in `src/dbp/llm/bedrock/models/claude3.py`
   - Add model validation for Claude models
   - Create constructor with proper delegation to BedrockBase

2. **Add Message Formatting for Claude**
   - Override `_format_messages` to handle Claude message format
   - Add support for system messages
   - Implement content block formatting for different content types

3. **Implement Parameter Handling**
   - Override `_format_model_kwargs` for Claude-specific parameters
   - Add Claude-specific defaults (temperature, max_tokens, etc.)
   - Implement reasoning parameter support

4. **Create Reasoning Support**
   - Add `stream_chat_with_reasoning` method for simplified reasoning access
   - Implement proper reasoning configuration for Claude models
   - Add response parsing for reasoning output

## Notes

- This implementation extends BedrockBase to add Claude-specific functionality
- Reasoning support is implemented via Claude's system message capabilities
- All interactions maintain the streaming-only approach
- The client supports all Claude model variants (Claude 3 Haiku, Sonnet, Opus)
- Parameter handling is optimized for Claude's specific requirements

## Next Steps

After completing this phase:
1. Proceed to Phase 9 (Nova Model Implementation)
2. Create the Nova-specific client implementation
3. Implement Nova parameter handling and response processing
