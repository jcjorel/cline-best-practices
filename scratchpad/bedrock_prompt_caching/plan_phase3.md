# Phase 3: Model-Specific Integration

## Overview

This phase focuses on updating model-specific client implementations to register prompt caching capabilities when the model supports it. This ensures the capability system accurately represents model features and allows for model-specific optimizations.

## Implementation Steps

### 1. Update ClaudeClient for Prompt Caching Support

Update the initialization of `ClaudeClient` in `src/dbp/llm/bedrock/models/claude3.py` to register the prompt caching capability when supported:

```python
class ClaudeClient(EnhancedBedrockBase):
    # Existing code...
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        timeout: int = 30,
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = False,
        preferred_regions: Optional[List[str]] = None,
        inference_profile_id: Optional[str] = None
    ):
        # Existing initialization code...
        
        # Register basic capabilities
        self.register_capabilities([
            ModelCapability.SYSTEM_PROMPT,
            ModelCapability.REASONING,
            ModelCapability.STRUCTURED_OUTPUT
        ])
        
        # Register capability handlers
        # Existing registration code...
        
        # Check if this model supports prompt caching
        if self._model_discovery and self._model_discovery.supports_prompt_caching(self.model_id):
            self.logger.info(f"Registering prompt caching capability for {self.model_id}")
            self.register_capability(ModelCapability.PROMPT_CACHING)
```

### 2. Update NovaClient (or other model clients)

Apply similar updates to other model clients that support prompt caching. For example, for `NovaClient`:

```python
class NovaClient(EnhancedBedrockBase):
    # Existing code...
    
    def __init__(
        self,
        model_id: str,
        # Other parameters...
    ):
        # Existing initialization code...
        
        # Register basic capabilities
        self.register_capabilities([
            # Existing capabilities...
        ])
        
        # Check if this model supports prompt caching
        if self._model_discovery and self._model_discovery.supports_prompt_caching(self.model_id):
            self.logger.info(f"Registering prompt caching capability for {self.model_id}")
            self.register_capability(ModelCapability.PROMPT_CACHING)
```

### 3. Add Model-Specific Optimizations (if needed)

If there are any model-specific optimizations or parameters needed for prompt caching, implement them in the appropriate model client class. For example, in `ClaudeClient`:

```python
def _format_model_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    [Method intent]
    Format model-specific parameters for Claude models in Bedrock Converse API format.
    
    [Design principles]
    - Claude-specific parameter mapping
    - Support for prompt caching
    - Parameter validation and defaults
    
    [Implementation details]
    - Formats parameters for Converse API
    - Adds Claude-specific caching parameters if needed
    - Provides Claude-optimized defaults
    
    Args:
        kwargs: Model-specific parameters
        
    Returns:
        Dict[str, Any]: Parameters formatted for Converse API
    """
    # Get base implementation parameters
    result = super()._format_model_kwargs(kwargs)
    
    # Claude-specific caching optimizations
    if getattr(self, '_prompt_caching_enabled', False) and self.has_capability(ModelCapability.PROMPT_CACHING):
        if "caching" not in result:
            result["caching"] = {}
            
        # Update with Claude-specific caching parameters if needed
        result["caching"]["cachingState"] = "ENABLED"
        
    return result
```

### 4. Add Helper Method for Getting Supported Models

Add a helper method to `EnhancedBedrockBase` to easily get a list of models that support prompt caching:

```python
@classmethod
def get_prompt_caching_supported_models(cls) -> List[str]:
    """
    [Method intent]
    Get a list of model IDs that support prompt caching.
    
    [Design principles]
    - Class method for easy access
    - Utilizes model discovery system
    - Provides information without instance creation
    
    [Implementation details]
    - Uses BedrockModelDiscovery to get supported models
    - Returns list of model IDs for use in client creation
    
    Returns:
        List[str]: List of model IDs that support prompt caching
    """
    try:
        model_discovery = BedrockModelDiscovery.get_instance()
        caching_models = model_discovery.get_prompt_caching_models()
        return [model["modelId"] for model in caching_models]
    except Exception as e:
        logging.warning(f"Failed to get prompt caching supported models: {str(e)}")
        return []
```

## Testing Strategy

The following tests should be implemented to verify the Phase 3 changes:

1. Test that `ClaudeClient` correctly registers the prompt caching capability for supported models
2. Test that `ClaudeClient` does not register the capability for unsupported models
3. Test any model-specific optimizations for prompt caching
4. Test the `get_prompt_caching_supported_models` helper method

## Usage Examples

```python
# Example 1: Check if a specific model is prompt caching compatible
from src.dbp.llm.bedrock.models.claude3 import ClaudeClient

# Get all models that support prompt caching
supported_models = ClaudeClient.get_prompt_caching_supported_models()
print(f"Models that support prompt caching: {supported_models}")

# Create a client for a supported model
if "anthropic.claude-3-5-haiku-20241022-v1:0" in supported_models:
    client = ClaudeClient("anthropic.claude-3-5-haiku-20241022-v1:0")
    await client.initialize()
    
    # Check if capability is registered
    has_caching = client.has_capability(ModelCapability.PROMPT_CACHING)
    print(f"Has prompt caching capability: {has_caching}")
```

## Compatibility Considerations

- The implementation checks model support via model discovery
- Capability registration only happens for supported models
- Existing code paths will continue to work for models that don't support caching
- The approach allows for model-specific optimizations when needed
