# Phase 2: Core API Implementation

## Overview

This phase focuses on implementing the core APIs for Amazon Bedrock prompt caching. These APIs will allow enabling prompt caching for model instances and marking cache points in conversations. The implementation will succeed gracefully even if the underlying model doesn't support prompt caching.

## Implementation Steps

### 1. Implement Enable Prompt Caching API

Add a method to `EnhancedBedrockBase` in `src/dbp/llm/bedrock/enhanced_base.py` to enable/disable prompt caching:

```python
def enable_prompt_caching(self, enabled: bool = True) -> bool:
    """
    [Method intent]
    Enable or disable prompt caching for this model client if supported.
    
    [Design principles]
    - Simple interface to toggle caching
    - No errors for unsupported models
    - Consistent with capability system
    - Clear return value indicating actual state
    
    [Implementation details]
    - Stores desired state in instance variable
    - Checks model support via capability system
    - Returns actual state (may be false if not supported)
    
    Args:
        enabled: Whether to enable prompt caching (default: True)
        
    Returns:
        bool: True if prompt caching is now enabled, False otherwise
    """
    # Store desired state
    self._prompt_caching_enabled = enabled
    
    # Check if model supports caching
    supports_caching = self.has_capability(ModelCapability.PROMPT_CACHING)
    
    # If enabling but model doesn't support it, log warning
    if enabled and not supports_caching:
        self.logger.warning(f"Model {self.model_id} does not support prompt caching")
        return False
        
    # Return actual state (enabled only if supported)
    return enabled and supports_caching

def is_prompt_caching_enabled(self) -> bool:
    """
    [Method intent]
    Check if prompt caching is currently enabled for this model client.
    
    [Design principles]
    - Simple status check
    - Clear boolean interface
    
    [Implementation details]
    - Checks stored state and capability support
    - Returns boolean indicating if caching is active
    
    Returns:
        bool: True if prompt caching is enabled and supported
    """
    has_setting = hasattr(self, '_prompt_caching_enabled')
    is_enabled = getattr(self, '_prompt_caching_enabled', False)
    supports_caching = self.has_capability(ModelCapability.PROMPT_CACHING)
    
    return has_setting and is_enabled and supports_caching
```

### 2. Implement Mark Cache Point API

Add a method to `EnhancedBedrockBase` to mark cache points in conversations:

```python
import time
import copy
import uuid

def mark_cache_point(
    self, 
    messages: List[Dict[str, Any]], 
    cache_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    [Method intent]
    Mark a cache point in a conversation for prompt caching.
    
    [Design principles]
    - Non-destructive operation (creates copies)
    - No errors for unsupported models
    - Support for custom cache IDs
    
    [Implementation details]
    - Creates a copy of messages to avoid modifying originals
    - Adds cache point metadata to the last message
    - Generates a cache ID if not provided
    - Returns information about the cache point
    
    Args:
        messages: List of message objects to mark with cache point
        cache_id: Optional custom cache ID (generated if not provided)
        
    Returns:
        Dict[str, Any]: Cache point information including modified messages
    """
    # Check if caching is enabled and supported
    caching_active = self.is_prompt_caching_enabled()
    
    # Generate or use provided cache ID
    cache_id = cache_id or f"cache-{uuid.uuid4()}"
    
    result = {
        "cache_id": cache_id,
        "cache_active": caching_active,
        "timestamp": time.time()
    }
    
    # If caching not active, return early with original messages
    if not caching_active:
        result["status"] = "ignored"
        result["messages"] = messages
        return result
    
    # Create a copy of messages to avoid modifying originals
    messages_copy = copy.deepcopy(messages)
    
    # Mark cache point in the last message
    if messages_copy:
        # If last message doesn't have metadata, add it
        if "metadata" not in messages_copy[-1]:
            messages_copy[-1]["metadata"] = {}
            
        # Add cache marker
        messages_copy[-1]["metadata"]["cache_point"] = {
            "id": result["cache_id"],
            "timestamp": result["timestamp"]
        }
    
    result["status"] = "marked"
    result["messages"] = messages_copy
    return result
```

### 3. Update Request Formatting

Modify the `_format_model_kwargs` method in `BedrockBase` class to include caching configuration when prompt caching is enabled:

```python
# In BedrockBase class (_format_model_kwargs method)
def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    [Method intent]
    Format model-specific parameters for the Bedrock Converse API.
    
    [Design principles]
    - Clean separation of parameter formatting
    - Support for model-specific overrides
    - Support for prompt caching configuration
    
    [Implementation details]
    - Formats parameters for Bedrock API
    - Handles parameter naming conventions
    - Adds caching configuration when enabled
    
    Args:
        kwargs: Model-specific parameters
        
    Returns:
        Dict[str, Any]: Parameters formatted for Bedrock API
    """
    # Base implementation for common parameters
    result = {
        "temperature": kwargs.get("temperature", 0.7),
        "maxTokens": kwargs.get("max_tokens", 1024),
        "topP": kwargs.get("top_p", 0.9),
        "stopSequences": kwargs.get("stop_sequences", [])
    }
    
    # Add caching configuration if enabled
    caching_enabled = kwargs.get("enable_caching") or getattr(self, '_prompt_caching_enabled', False)
    
    if caching_enabled:
        result["caching"] = {
            "cachingState": "ENABLED"
        }
    
    return result
```

### 4. Add Integration with Stream Chat Method

Enhance the `stream_chat` method in `EnhancedBedrockBase` to handle cache points:

```python
# In EnhancedBedrockBase class (enhance stream_chat method)
async def stream_chat(
    self, 
    messages: List[Dict[str, Any]], 
    **kwargs
) -> AsyncIterator[Dict[str, Any]]:
    """
    [Method intent]
    Generate a response from the model for a chat conversation using streaming.
    
    [Design principles]
    - Streaming as the standard interaction pattern
    - Support for model-specific parameters and caching
    - Clean parameter passing
    
    [Implementation details]
    - Checks for cache point metadata
    - Forwards caching settings to parent method
    - Handles streaming response
    
    Args:
        messages: List of message objects with role and content
        **kwargs: Model-specific parameters
        
    Yields:
        Dict[str, Any]: Response chunks from the model
        
    Raises:
        LLMError: If chat generation fails
    """
    # Check if caching should be enabled for this request
    if self.is_prompt_caching_enabled():
        kwargs["enable_caching"] = True
    
    # Delegate to parent implementation
    async for chunk in super().stream_chat(messages, **kwargs):
        yield chunk
```

## Testing Strategy

The following tests should be implemented to verify the Phase 2 changes:

1. Test `enable_prompt_caching` method with both supported and unsupported models
2. Test `is_prompt_caching_enabled` returns correct status
3. Test `mark_cache_point` properly modifies message metadata
4. Test request formatting includes caching configuration when enabled
5. Test integration with `stream_chat` method

## Usage Examples

```python
# Example 1: Enable prompt caching
client = ClaudeClient("anthropic.claude-3-5-haiku-20241022-v1:0")
await client.initialize()
caching_enabled = client.enable_prompt_caching()
print(f"Prompt caching enabled: {caching_enabled}")

# Example 2: Mark a cache point
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me about prompt caching"}
]
result = client.mark_cache_point(messages)
print(f"Cache point status: {result['status']}")
print(f"Cache ID: {result['cache_id']}")

# Use the marked messages in a conversation
if result["cache_active"]:
    response = await client.stream_chat(result["messages"])
else:
    response = await client.stream_chat(messages)  # Use original messages
```

## Compatibility Considerations

- The implementation gracefully handles unsupported models
- The API design follows existing patterns in the codebase
- All methods have clear return values indicating actual state
- No errors are raised for unsupported models
