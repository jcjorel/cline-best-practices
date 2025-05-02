# Phase 9: Nova Model Implementation

This phase implements the Amazon Bedrock Nova model client for the LangChain/LangGraph integration. It builds on the Bedrock Base implementation from Phase 7 to add Nova-specific functionality, particularly parameter handling and response processing tailored for Amazon's Titan models.

## Objectives

1. Create a Nova-specific client implementation
2. Build parameter handling for Nova models
3. Implement Nova response processing
4. Support Nova model variants

## NovaClient Implementation

Create the Nova model client in `src/dbp/llm/bedrock/models/nova.py`:

```python
import logging
from typing import Dict, Any, List, Optional, AsyncIterator

from src.dbp.llm.bedrock.base import BedrockBase
from src.dbp.llm.common.exceptions import LLMError, InvocationError

class NovaClient(BedrockBase):
    """
    [Class intent]
    Implements a specialized client for Amazon Bedrock's Nova (Amazon Titan) models.
    This client adds Nova-specific features and parameter handling while
    maintaining the streaming-focused approach.
    
    [Design principles]
    - Nova-specific parameter optimization
    - Specialized message formatting for Nova models
    - Clean extension of BedrockBase
    - Streaming-only interface
    
    [Implementation details]
    - Supports all Nova model variants
    - Implements Nova-specific parameter mapping
    - Optimizes default parameters for Nova
    - Handles Nova's response format
    """
    
    # Supported Nova models - helps with validation
    _NOVA_MODELS = [
        "amazon.titan-text-lite-v1",
        "amazon.titan-text-express-v1",
        "amazon.titan-text-premier-v1"
    ]
    
    # Default Nova parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024
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
        Initialize the Nova client with model validation and Nova-specific defaults.
        
        [Design principles]
        - Strong model validation
        - Nova-specific configuration
        - Clean delegation to base class
        
        [Implementation details]
        - Validates that model_id is a Nova model
        - Sets up Nova-specific logging
        - Initializes with Nova defaults
        
        Args:
            model_id: Nova model ID (e.g., "amazon.titan-text-express-v1")
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            
        Raises:
            ValueError: If model_id is not a supported Nova model
        """
        # Validate model is a Nova model
        base_model_id = model_id.split(":")[0]
        is_nova_model = any(base_model_id.startswith(model) for model in self._NOVA_MODELS)
        
        if not is_nova_model:
            raise ValueError(f"Model {model_id} is not a supported Nova model")
        
        # Initialize base class
        super().__init__(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            credentials=credentials,
            max_retries=max_retries,
            timeout=timeout,
            logger=logger or logging.getLogger("NovaClient")
        )
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Format messages specifically for Nova models.
        
        [Design principles]
        - Nova-specific message formatting
        - Support for system messages
        - Handle content format variations
        
        [Implementation details]
        - Properly formats system messages for Nova
        - Handles content blocks for different content types
        - Ensures proper message role mapping
        
        Args:
            messages: List of message objects in standard format
            
        Returns:
            List[Dict[str, Any]]: Messages formatted for Nova API
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Map role names to Nova expected roles
            if role == "user":
                nova_role = "user"
            elif role == "assistant":
                nova_role = "assistant" 
            elif role == "system":
                nova_role = "system"
            else:
                raise ValueError(f"Unsupported role: {role}")
            
            # Format for Nova's expected structure
            formatted_msg = {"role": nova_role}
            
            # Handle content formatting
            if isinstance(content, str):
                formatted_msg["content"] = content
            else:
                # Currently Nova doesn't support complex content, fall back to string
                raise ValueError(f"Nova models only support string content, got {type(content)}")
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages
    
    def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Format model parameters specifically for Nova models.
        
        [Design principles]
        - Nova-specific parameter mapping
        - Parameter validation and defaults
        - Support for Nova-specific features
        
        [Implementation details]
        - Maps standard parameters to Nova-specific names
        - Adds Nova-specific parameters
        - Provides Nova-optimized defaults
        
        Args:
            kwargs: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Parameters formatted for Nova API
        """
        # Start with basic parameters
        formatted_kwargs = {
            "temperature": kwargs.get("temperature", self.DEFAULT_TEMPERATURE),
            "maxTokenCount": kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS),
            "topP": kwargs.get("top_p", self.DEFAULT_TOP_P),
        }
        
        # Add Nova-specific parameters
        if "top_k" in kwargs:
            formatted_kwargs["topK"] = kwargs["top_k"]
            
        if "stop_sequences" in kwargs:
            formatted_kwargs["stopSequences"] = kwargs["stop_sequences"]
            
        return formatted_kwargs
    
    def _parse_nova_response(self, response_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Method intent]
        Parse Nova-specific response chunks into a standard format.
        
        [Design principles]
        - Consistent response format
        - Nova-specific parsing logic
        - Error handling for unexpected formats
        
        [Implementation details]
        - Extracts relevant information from Nova responses
        - Standardizes response format
        - Handles Nova-specific metadata
        
        Args:
            response_chunk: Response chunk from Nova
            
        Returns:
            Dict[str, Any]: Standardized response chunk
        """
        # Handle different chunk types
        if "type" not in response_chunk:
            return response_chunk  # Already processed elsewhere
        
        chunk_type = response_chunk.get("type", "")
        
        if chunk_type == "content_block_delta":
            # Extract text from Nova delta format
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

1. **Create Nova Client Class**
   - Implement `NovaClient` in `src/dbp/llm/bedrock/models/nova.py`
   - Add model validation for Nova models
   - Create constructor with proper delegation to BedrockBase

2. **Add Message Formatting for Nova**
   - Override `_format_messages` to handle Nova message format
   - Add role mapping between standard roles and Nova roles
   - Handle content block formatting for Nova

3. **Implement Parameter Handling**
   - Override `_format_model_kwargs` for Nova-specific parameters
   - Add Nova-specific defaults (temperature, max_tokens, etc.)
   - Map standard parameter names to Nova parameter names

4. **Create Response Processing**
   - Implement `_parse_nova_response` for handling Nova response format
   - Add standardized response parsing
   - Handle Nova stream event types

## Notes

- This implementation extends BedrockBase to add Nova-specific functionality
- All interactions maintain the streaming-only approach
- The client supports all Nova model variants (Titan Text Lite, Express, Premier)
- Parameter handling is optimized for Nova's specific requirements
- Nova currently doesn't support complex content types, so only string content is accepted

## Next Steps

After completing this phase:
1. Proceed to Phase 10 (LangChain Integration)
2. Create LangChain adapter interfaces
3. Implement LangChain LLM wrappers
