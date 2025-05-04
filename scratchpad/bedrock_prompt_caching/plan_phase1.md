# Phase 1: Model Capability System Enhancement

## Overview

This phase focuses on enhancing the model capability system to support Amazon Bedrock prompt caching. It includes adding a new capability type, implementing model detection logic, and updating the model discovery system to identify which models support prompt caching.

## Implementation Steps

### 1. Add Prompt Caching Capability

Update the `ModelCapability` enum in `src/dbp/llm/bedrock/enhanced_base.py` to include prompt caching:

```python
class ModelCapability(str, enum.Enum):
    # Existing capabilities...
    
    # Advanced features
    MULTIMODAL = "multimodal"
    VISION = "vision"
    RAG = "retrieval_augmented_generation"
    PROMPT_CACHING = "prompt_caching"  # New capability for prompt caching
```

### 2. Update Model Discovery for Prompt Caching Support

Enhance the `BedrockModelDiscovery` class in `src/dbp/llm/bedrock/discovery/models.py` to identify models that support prompt caching:

```python
class BedrockModelDiscovery(BaseDiscovery):
    # Existing code...
    
    # Define models that support prompt caching
    _PROMPT_CACHING_SUPPORTED_MODELS = [
        "anthropic.claude-3-5-haiku-",  # Claude 3.5 Haiku
        "anthropic.claude-3-7-sonnet-", # Claude 3.7 Sonnet
        "amazon.nova-micro-",           # Nova Micro
        "amazon.nova-lite-",            # Nova Lite
        "amazon.nova-pro-"              # Nova Pro
    ]
    
    def supports_prompt_caching(self, model_id: str) -> bool:
        """
        [Method intent]
        Check if a specific model supports prompt caching.
        
        [Design principles]
        - Simple capability checking
        - Model ID prefix matching
        - Clear boolean interface
        
        [Implementation details]
        - Checks if model ID starts with any of the supported model prefixes
        - Returns boolean indicating support
        
        Args:
            model_id: The Bedrock model ID to check
            
        Returns:
            bool: True if the model supports prompt caching, False otherwise
        """
        # Check if the model ID starts with any of the supported prefixes
        for prefix in self._PROMPT_CACHING_SUPPORTED_MODELS:
            if model_id.startswith(prefix):
                return True
                
        return False
```

### 3. Extend Model Discovery with Filtering Method

Add a method to get all models that support prompt caching:

```python
def get_prompt_caching_models(self) -> List[Dict[str, Any]]:
    """
    [Method intent]
    Get all models that support prompt caching.
    
    [Design principles]
    - Filtering based on model capability
    - Reuse existing model data
    - Provide complete model information
    
    [Implementation details]
    - Gets all available models
    - Filters models that support prompt caching
    - Returns filtered list with full model information
    
    Returns:
        List[Dict[str, Any]]: List of models that support prompt caching
    """
    all_models = self.get_all_models()
    return [
        model for model in all_models 
        if self.supports_prompt_caching(model["modelId"])
    ]
```

### 4. Add Testing Helper Method

Add a helper method for testing if prompt caching is supported:

```python
def get_prompt_caching_support_status(self) -> Dict[str, bool]:
    """
    [Method intent]
    Get prompt caching support status for all available models.
    
    [Design principles]
    - Comprehensive support status
    - Simple mapping format
    - Useful for debugging and testing
    
    [Implementation details]
    - Gets all available models
    - Creates a mapping of model IDs to support status
    - Returns dictionary for easy lookup
    
    Returns:
        Dict[str, bool]: Dictionary mapping model IDs to prompt caching support status
    """
    all_models = self.get_all_models()
    return {
        model["modelId"]: self.supports_prompt_caching(model["modelId"])
        for model in all_models
    }
```

## Testing Strategy

The following tests should be implemented to verify the Phase 1 changes:

1. Test that the `ModelCapability.PROMPT_CACHING` enum is added correctly
2. Test the `supports_prompt_caching` method with known supported and unsupported models
3. Test the `get_prompt_caching_models` method returns only supported models
4. Test the `get_prompt_caching_support_status` method returns correct mapping

## Compatibility Considerations

- These changes are entirely additive and do not affect existing functionality
- The new capability is only used if explicitly checked by clients
- Model support detection is based on model ID prefixes for future compatibility
