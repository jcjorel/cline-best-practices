# Phase 4: Update `client_factory.py`

## Current Issues

The current `BedrockClientFactory` class in `client_factory.py` provides two methods for client creation:
1. `create_client()`: Creates clients extending `EnhancedBedrockBase` for direct Bedrock API access (legacy approach)
2. `create_langchain_chatbedrock()`: Creates instances of `EnhancedChatBedrockConverse` for LangChain integration (new approach)

We need to remove the legacy `create_client()` method and update `create_langchain_chatbedrock()` to create model-specific subclasses of `EnhancedChatBedrockConverse` based on the model ID.

## Planned Changes

We'll update `client_factory.py` to:

1. Remove the entire `create_client()` method
2. Update imports to reference the new model-specific classes
3. Modify the `create_langchain_chatbedrock()` method to create the appropriate model-specific class based on the model ID

### Code Changes

#### Import Changes

```python
# Remove imports
from .enhanced_base import EnhancedBedrockBase

# Add imports for model-specific classes
from .models.claude3 import ClaudeEnhancedChatBedrockConverse
from .models.nova import NovaEnhancedChatBedrockConverse
```

#### Remove `create_client()` Method

Remove the entire `create_client()` method from the `BedrockClientFactory` class:

```python
# Remove this entire method
@classmethod
def create_client(
    cls,
    model_id: str,
    region_name: Optional[str] = None,
    profile_name: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
    max_retries: int = 3,
    timeout: int = 30,
    logger: Optional[logging.Logger] = None,
    use_model_discovery: bool = True,
    preferred_regions: Optional[List[str]] = None,
    inference_profile_arn: Optional[str] = None
) -> EnhancedBedrockBase:
    # Method body to remove
```

#### Update `create_langchain_chatbedrock()` Method

Modify the `create_langchain_chatbedrock()` method to instantiate the appropriate model-specific subclass:

```python
@classmethod
def create_langchain_chatbedrock(
    cls,
    model_id: str,
    region_name: Optional[str] = None,
    profile_name: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
    max_retries: int = 3,
    timeout: int = 30,
    logger: Optional[logging.Logger] = None,
    use_model_discovery: bool = True,
    preferred_regions: Optional[List[str]] = None,
    inference_profile_arn: Optional[str] = None,
    streaming: bool = True,
    **langchain_kwargs
) -> Any:
    """
    [Method intent]
    Create a model-specific EnhancedChatBedrockConverse instance based on model ID.
    
    [Design principles]
    - Uses model-specific implementations when possible
    - Falls back to generic implementation when necessary
    - Maintains existing parameter interface
    
    [Implementation details]
    - Determines model type from model ID
    - Creates appropriate subclass instance
    - Passes all parameters to the constructor
    
    Args, Returns, Raises: Same as original implementation
    """
    # Most of the existing method remains the same...
    
    # After creating chat_model_params, but before instantiating the class:
    
    # Determine the appropriate class based on model ID
    model_class = EnhancedChatBedrockConverse  # Default fallback
    
    # Check for Claude models
    if any(model_id.startswith(m.split(':')[0]) for m in ClaudeEnhancedChatBedrockConverse.SUPPORTED_MODELS):
        model_class = ClaudeEnhancedChatBedrockConverse
        logger.info(f"Using Claude-specific implementation for model {model_id}")
    
    # Check for Nova models
    elif any(model_id.startswith(m.split(':')[0]) for m in NovaEnhancedChatBedrockConverse.SUPPORTED_MODELS):
        model_class = NovaEnhancedChatBedrockConverse
        logger.info(f"Using Nova-specific implementation for model {model_id}")
    
    # Create the model-specific instance
    chat_bedrock = model_class(
        **chat_model_params,
        logger=logger
    )
    
    logger.info(f"Created LangChain model instance for {model_id} in region {region_name}")
    return chat_bedrock
```

#### Clean up `_discover_client_classes()` Method

Remove or modify the `_discover_client_classes()` method since it is only used by the now-removed `create_client()` method:

```python
# This method can be removed if it's not used elsewhere, or it can be simplified
# if it's used for other purposes (e.g., model discovery)
@classmethod
def _discover_client_classes(cls) -> Dict[str, Type]:
    """
    [Method intent]
    Dynamically discover available model classes and their supported models for LangChain integration.
    
    [Design principles]
    - Dynamic class discovery without hardcoding
    - Introspection of class capabilities
    - Caching for performance
    
    [Implementation details]
    - Uses importlib to scan the models package
    - Inspects classes for LangChain extensions and SUPPORTED_MODELS attribute
    - Maps each model ID to its supporting client class
    - Caches discovery results for performance
    
    Returns:
        Dict[str, Type]: Dictionary mapping model IDs to client classes
    """
    if cls._model_to_client_map is not None:
        return cls._model_to_client_map
    
    # Maps model IDs to their supporting client classes
    model_to_client = {}
    client_classes = []
    logger = logging.getLogger("BedrockClientFactory")
    
    # Import models package
    try:
        from . import models
        model_package_path = models.__path__
        model_package_name = models.__name__
        
        # Scan all modules in the models package
        for _, module_name, _ in pkgutil.iter_modules(model_package_path):
            try:
                # Import module
                module = importlib.import_module(f"{model_package_name}.{module_name}")
                
                # Find all client classes in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, EnhancedChatBedrockConverse) and 
                        obj != EnhancedChatBedrockConverse and
                        hasattr(obj, 'SUPPORTED_MODELS')):
                        
                        # Add to client classes list
                        client_classes.append(obj)
                        
                        # Register the client class for each supported model
                        for model_id in obj.SUPPORTED_MODELS:
                            model_to_client[model_id] = obj
                            
            except (ImportError, AttributeError) as e:
                # Log but continue with other modules
                logger.error(f"Error loading client module {module_name}: {str(e)}")
                
    except Exception as e:
        # Critical error in discovery process
        error_msg = f"Failed to discover client classes: {str(e)}"
        logger.error(error_msg)
        raise LLMError(error_msg, e)
    
    if not client_classes:
        error_msg = "No Bedrock client classes found"
        logger.error(error_msg)
        raise LLMError(error_msg)
    
    # Cache the discovered classes
    cls._client_classes = client_classes
    cls._model_to_client_map = model_to_client
    
    return model_to_client
```

## Implementation Notes

1. The `create_client()` method is completely removed, as we're no longer supporting the legacy approach.
2. The `create_langchain_chatbedrock()` method is updated to create model-specific subclasses of `EnhancedChatBedrockConverse` based on the model ID.
3. We dynamically select the appropriate class by checking if the model ID matches any of the supported models in each class.
4. A default fallback to the base `EnhancedChatBedrockConverse` class is provided for unsupported models.
5. The `_discover_client_classes()` method may need to be updated or removed depending on its usage elsewhere in the codebase.

## Test Considerations

1. Test with Claude models to ensure the correct Claude-specific class is created.
2. Test with Nova models to ensure the correct Nova-specific class is created.
3. Test with other models to ensure the fallback to the generic class works correctly.
4. Ensure all parameters are correctly passed to the created class instance.

## Compatibility Considerations

1. Any code that was previously using `create_client()` will need to be updated to use `create_langchain_chatbedrock()` instead.
2. Classes in the model discovery system that were expecting `EnhancedBedrockBase` subclasses may need to be updated.
