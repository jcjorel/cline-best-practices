# Implementation Plan: Refactoring Client Factory for Dynamic Model Discovery

## Overview

This plan details the implementation of a dynamic model discovery system for Bedrock clients that:
1. Automatically discovers `EnhancedChatBedrockConverse` subclasses in the models directory
2. Associates parameter classes with client classes through a `PARAMETER_CLASSES` class variable
3. Creates a flexible mapping between model IDs, client classes, and parameter classes
4. Provides helper functions to access model metadata and relationships

## Current Issues

- Duplicate model lists are maintained in both the `XXXParameters` classes and `EnhancedChatBedrockConverse` subclasses
- Client factory uses hardcoded checks against `SUPPORTED_MODELS` class variables
- No direct way to access parameter classes associated with model IDs
- No automated discovery of model implementations

## Design Principles

- DRY (Don't Repeat Yourself): Eliminate duplicate model lists
- Single Source of Truth: Parameter classes define supported models
- Dynamic Discovery: Automatically find and register model implementations
- Lazy Loading: Initialize discovery only when needed, but cache results
- Backward Compatibility: Maintain API compatibility where possible
- Fail-Fast Error Handling: Raise clear exceptions for invalid models

## Implementation Steps

### 1. Base Class Modifications

#### 1.1 Update `EnhancedChatBedrockConverse` Base Class

```python
class EnhancedChatBedrockConverse:
    # Class variable to store associated parameter classes
    PARAMETER_CLASSES = []  # Base class has empty list, subclasses will override
    
    def __init__(self, model: str, **kwargs):
        self.model_id = model
        self.parameters = None  # Will be instantiated with appropriate parameter class
        
        # Find and instantiate the appropriate parameter class for this model
        self._initialize_parameters(model, **kwargs)
    
    def _initialize_parameters(self, model_id, **kwargs):
        """
        [Method intent]
        Initialize the appropriate parameter class instance based on model_id.
        
        [Design principles]
        - Automatic parameter class selection
        - Model ID validation
        - Initialization with appropriate parameters
        
        [Implementation details]
        - Searches through all parameter classes for matching model ID
        - Creates instance of matching parameter class
        - Raises clear exception if no match is found
        
        Args:
            model_id (str): The model ID to find parameters for
            **kwargs: Parameters to initialize the parameter class
            
        Raises:
            UnsupportedModelError: If no parameter class supports the model ID
        """
        for param_class in self.PARAMETER_CLASSES:
            if hasattr(param_class, 'Config') and hasattr(param_class.Config, 'supported_models'):
                if model_id in param_class.Config.supported_models:
                    self.parameters = param_class(**kwargs)
                    return
                
                # Check for model ID prefix match (for versioned models)
                model_base = model_id.split(':')[0]
                for supported_id in param_class.Config.supported_models:
                    supported_base = supported_id.split(':')[0]
                    if model_base == supported_base:
                        self.parameters = param_class(**kwargs)
                        return
                
        # If no matching parameter class is found, raise an exception
        raise UnsupportedModelError(f"No parameter class supports model ID: {model_id}")
    
    # Compatibility properties and methods
    
    @property
    def SUPPORTED_MODELS(self):
        """Legacy property for backward compatibility"""
        all_models = []
        for param_class in self.PARAMETER_CLASSES:
            if hasattr(param_class, 'Config') and hasattr(param_class.Config, 'supported_models'):
                all_models.extend(param_class.Config.supported_models)
        return all_models

    @classmethod
    def get_supported_models(cls):
        """Legacy method for backward compatibility"""
        all_models = []
        for param_class in cls.PARAMETER_CLASSES:
            if hasattr(param_class, 'Config') and hasattr(param_class.Config, 'supported_models'):
                all_models.extend(param_class.Config.supported_models)
        return all_models
```

### 2. Modify Model-Specific Client Classes

#### 2.1 Update `NovaEnhancedChatBedrockConverse`

```python
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
    - References NovaParameters class for supported models
    - Support for all Nova model variants
    """
    
    # Reference parameter classes instead of duplicating model lists
    PARAMETER_CLASSES = [NovaParameters]
    
    # Remove the _NOVA_MODELS and SUPPORTED_MODELS variables
    # The base class now provides SUPPORTED_MODELS property based on PARAMETER_CLASSES
    
    # Rest of class implementation remains the same...
```

#### 2.2 Update `ClaudeEnhancedChatBedrockConverse`

```python
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
    - References Claude parameter classes for supported models
    - Support for all Claude model variants
    """
    
    # Reference parameter classes instead of duplicating model lists
    PARAMETER_CLASSES = [Claude3Parameters, Claude35Parameters, Claude37Parameters]
    
    # Remove the _CLAUDE_MODELS and SUPPORTED_MODELS variables
    # The base class now provides SUPPORTED_MODELS property based on PARAMETER_CLASSES
    
    # Rest of class implementation remains the same...
```

### 3. Client Factory Discovery System

#### 3.1 Add Model and Client Discovery Module to `client_factory.py`

```python
# In client_factory.py

import importlib
import inspect
import pkgutil
import os
import sys
import logging
from typing import Dict, List, Type, Optional, Any, Set, Tuple

from .langchain_wrapper import EnhancedChatBedrockConverse
from ..common.exceptions import LLMError, UnsupportedModelError

# Cache for discovered classes to avoid repeated scans
_client_classes_cache = None
_model_to_client_class_cache = None
_model_to_parameter_class_cache = None

def _discover_client_classes() -> List[Type[EnhancedChatBedrockConverse]]:
    """
    [Function intent]
    Discovers all EnhancedChatBedrockConverse subclasses in the models directory.
    
    [Design principles]
    - Dynamic discovery without hardcoding
    - Import all modules in models directory
    - Inspect classes to find EnhancedChatBedrockConverse subclasses
    
    [Implementation details]
    - Uses pkgutil to find modules
    - Uses inspect to identify subclasses
    - Returns list of discovered classes
    
    Returns:
        List[Type[EnhancedChatBedrockConverse]]: List of discovered client classes
    """
    client_classes = []
    logger = logging.getLogger("BedrockClientFactory")
    
    # Define the package containing model implementations
    models_package = 'dbp.llm.bedrock.models'
    
    # Import models package
    try:
        package = importlib.import_module(models_package)
        package_path = os.path.dirname(package.__file__)
        
        # Find all modules in the package
        for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
            if not is_pkg:  # Skip subpackages, only load modules
                try:
                    # Import the module
                    module = importlib.import_module(f"{models_package}.{module_name}")
                    
                    # Find all EnhancedChatBedrockConverse subclasses
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, EnhancedChatBedrockConverse) and 
                            obj != EnhancedChatBedrockConverse):
                            client_classes.append(obj)
                except ImportError as e:
                    # Log warning but continue with other modules
                    logger.warning(f"Could not import module {module_name}: {str(e)}")
    except ImportError as e:
        # Log error if models package cannot be imported
        logger.error(f"Could not import models package: {str(e)}")
        
    return client_classes

def _build_model_mappings(client_classes: List[Type[EnhancedChatBedrockConverse]]) -> Tuple[Dict, Dict]:
    """
    [Function intent]
    Builds mappings between model IDs, client classes, and parameter classes.
    
    [Design principles]
    - Create efficient lookup structures
    - Map from model ID to client class
    - Map from model ID to parameter class
    
    [Implementation details]
    - Extracts supported models from parameter classes
    - Creates dictionary mappings for fast lookup
    - Validates no duplicate model IDs across client classes
    
    Args:
        client_classes: List of discovered EnhancedChatBedrockConverse subclasses
        
    Returns:
        Tuple[Dict, Dict]: Mappings from model ID to client class and parameter class
    """
    model_to_client_class = {}
    model_to_parameter_class = {}
    logger = logging.getLogger("BedrockClientFactory")
    
    for client_class in client_classes:
        if not hasattr(client_class, 'PARAMETER_CLASSES') or not client_class.PARAMETER_CLASSES:
            logger.warning(f"Client class {client_class.__name__} has no PARAMETER_CLASSES")
            continue
            
        for param_class in client_class.PARAMETER_CLASSES:
            if hasattr(param_class, 'Config') and hasattr(param_class.Config, 'supported_models'):
                for model_id in param_class.Config.supported_models:
                    # Check for duplicate model ID mappings
                    if model_id in model_to_client_class:
                        logger.warning(
                            f"Model ID {model_id} already mapped to {model_to_client_class[model_id].__name__}, "
                            f"now also found in {client_class.__name__}"
                        )
                    
                    # Map model ID to client class and parameter class
                    model_to_client_class[model_id] = client_class
                    model_to_parameter_class[model_id] = param_class
    
    return model_to_client_class, model_to_parameter_class

def _ensure_caches_initialized():
    """
    [Function intent]
    Ensures the discovery caches are initialized.
    
    [Design principles]
    - Lazy initialization
    - One-time discovery
    - Thread-safe initialization
    
    [Implementation details]
    - Checks if caches are already initialized
    - Performs discovery if needed
    - Updates all caches
    """
    global _client_classes_cache, _model_to_client_class_cache, _model_to_parameter_class_cache
    
    # If caches are already initialized, return
    if _client_classes_cache is not None:
        return
        
    # Discover client classes
    _client_classes_cache = _discover_client_classes()
    
    # Build model mappings
    _model_to_client_class_cache, _model_to_parameter_class_cache = _build_model_mappings(_client_classes_cache)
```

#### 3.2 Add Public Helper Functions to `client_factory.py`

```python
def get_all_supported_model_ids() -> List[str]:
    """
    [Function intent]
    Returns a list of all supported model IDs across all discovered client classes.
    
    [Design principles]
    - Provide complete model discovery
    - Ensure initialization happens
    
    [Implementation details]
    - Initializes discovery caches if needed
    - Returns all keys from model mapping
    
    Returns:
        List[str]: List of all supported model IDs
    """
    _ensure_caches_initialized()
    return list(_model_to_client_class_cache.keys())

def get_client_class_for_model(model_id: str) -> Type[EnhancedChatBedrockConverse]:
    """
    [Function intent]
    Returns the appropriate client class for a given model ID.
    
    [Design principles]
    - Direct mapping lookup
    - Error handling for unknown models
    
    [Implementation details]
    - Initializes discovery caches if needed
    - Looks up client class from mapping
    - Raises exception if model is not supported
    
    Args:
        model_id: The Bedrock model ID
        
    Returns:
        Type[EnhancedChatBedrockConverse]: The client class for the model
        
    Raises:
        UnsupportedModelError: If no client class supports the model ID
    """
    _ensure_caches_initialized()
    
    # Check for exact model ID match
    if model_id in _model_to_client_class_cache:
        return _model_to_client_class_cache[model_id]
    
    # Check for model ID prefix match (for versioned models)
    model_base = model_id.split(':')[0]
    for supported_model_id, client_class in _model_to_client_class_cache.items():
        supported_base = supported_model_id.split(':')[0]
        if model_base == supported_base:
            return client_class
    
    # No match found, raise exception
    raise UnsupportedModelError(f"No client class supports model ID: {model_id}")

def get_parameter_class_for_model(model_id: str):
    """
    [Function intent]
    Returns the appropriate parameter class for a given model ID.
    
    [Design principles]
    - Direct mapping lookup
    - Error handling for unknown models
    
    [Implementation details]
    - Initializes discovery caches if needed
    - Looks up parameter class from mapping
    - Raises exception if model is not supported
    
    Args:
        model_id: The Bedrock model ID
        
    Returns:
        The parameter class for the model
        
    Raises:
        UnsupportedModelError: If no parameter class supports the model ID
    """
    _ensure_caches_initialized()
    
    # Check for exact model ID match
    if model_id in _model_to_parameter_class_cache:
        return _model_to_parameter_class_cache[model_id]
    
    # Check for model ID prefix match (for versioned models)
    model_base = model_id.split(':')[0]
    for supported_model_id, param_class in _model_to_parameter_class_cache.items():
        supported_base = supported_model_id.split(':')[0]
        if model_base == supported_base:
            return param_class
    
    # No match found, raise exception
    raise UnsupportedModelError(f"No parameter class supports model ID: {model_id}")

def get_parameter_instance_for_client(client_instance: EnhancedChatBedrockConverse):
    """
    [Function intent]
    Returns the parameter instance associated with a client instance.
    
    [Design principles]
    - Direct access to client's parameter instance
    - Type verification
    
    [Implementation details]
    - Verifies client is an EnhancedChatBedrockConverse instance
    - Returns the parameters attribute
    
    Args:
        client_instance: The client instance
        
    Returns:
        The parameter instance for the client
        
    Raises:
        TypeError: If client_instance is not an EnhancedChatBedrockConverse instance
        AttributeError: If client_instance has no parameters attribute
    """
    if not isinstance(client_instance, EnhancedChatBedrockConverse):
        raise TypeError(f"Expected EnhancedChatBedrockConverse instance, got {type(client_instance).__name__}")
    
    # The client should have initialized its parameters instance
    if not hasattr(client_instance, 'parameters') or client_instance.parameters is None:
        raise AttributeError(f"Client instance has no initialized parameters")
        
    return client_instance.parameters
```

### 4. Update `create_langchain_chatbedrock` Method

```python
@classmethod
def create_langchain_chatbedrock(
    cls,
    model_id: str,
    # ... existing parameters
):
    """
    [Method intent]
    Create a native LangChain ChatBedrockConverse instance using our model discovery
    and AWS client factory infrastructure for optimal configuration.
    
    ... existing documentation ...
    """
    # Initialize logger
    logger = logger or logging.getLogger("BedrockClientFactory")
    
    try:
        # Check if LangChain is installed first before trying to use it
        try:
            import langchain_aws
            from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
        except ImportError as e:
            error_msg = "LangChain AWS is not installed. Please install langchain-aws package."
            logger.error(error_msg)
            raise ConfigurationError(error_msg, e)
                
        # Get model discovery instance
        discovery = BedrockModelDiscovery.get_instance()
        
        # Verify this model is supported by the project
        project_models = discovery._get_project_supported_models()
        if model_id not in project_models:
            # Check if the model has a supported base prefix
            model_base = model_id.split(":")[0]
            supported_prefixes = {m.split(":")[0] for m in project_models}
            
            if not any(model_base == prefix for prefix in supported_prefixes):
                error_msg = f"Model ID {model_id} is not supported by this project. " + \
                           f"Supported model prefixes: {', '.join(sorted(supported_prefixes))}"
                logger.error(error_msg)
                raise UnsupportedModelError(error_msg)
                
        # ... existing code for AWS client setup ...
        
        # Setup parameters for LangChain ChatBedrockConverse
        chat_model_params = {
            "model": model_param,  
            "client": bedrock_client,
        }
        
        # Use the new discovery system to get the appropriate model class
        try:
            model_class = get_client_class_for_model(model_id)
            logger.info(f"Using {model_class.__name__} for model {model_id}")
        except UnsupportedModelError:
            # Fall back to base class for unknown models (maintains backward compatibility)
            model_class = EnhancedChatBedrockConverse
            logger.warning(f"No specific client class found for {model_id}, using base class")
            
        # Create the model instance
        try:
            chat_bedrock = model_class(
                **chat_model_params,
                logger=logger
            )
            
            # Now that the model is created, we can set the model parameters 
            # as attributes directly if needed
            if model_kwargs:
                # Store model kwargs outside of the model for future use if needed
                object.__setattr__(chat_bedrock, "_cached_model_kwargs", model_kwargs)
        
        except Exception as e:
            # Detailed error logging to help debug parameter issues
            logger.error(f"Failed to create model with parameters: {chat_model_params}")
            logger.error(f"Model class: {model_class.__name__}")
            if model_kwargs:
                logger.error(f"Model kwargs: {model_kwargs}")
            raise e
        
        logger.info(f"Created LangChain ChatBedrockConverse for model {model_id} in region {region_name}")
        return chat_bedrock
        
    except (UnsupportedModelError, ConfigurationError, ImportError) as e:
        # Re-raise specific exceptions
        raise e
    except Exception as e:
        # Wrap other exceptions
        error_msg = f"Failed to create LangChain ChatBedrockConverse for model {model_id}: {str(e)}"
        logger.error(error_msg)
        raise LLMError(error_msg, e)
```

## Testing

### Unit Test Cases

1. **Client Class Discovery**
   - Verify that all client classes are correctly discovered
   - Verify proper handling of import errors for invalid modules

2. **Model ID to Client Class Mapping**
   - Verify exact model ID matches
   - Verify model ID prefix matches
   - Verify unknown model ID handling

3. **Parameter Class Initialization**
   - Verify correct parameter class is selected for each model ID
   - Verify parameter values are correctly passed to parameter class

4. **Helper Functions**
   - Verify get_all_supported_model_ids returns all expected model IDs
   - Verify get_client_class_for_model returns correct client class
   - Verify get_parameter_class_for_model returns correct parameter class
   - Verify get_parameter_instance_for_client returns correct instance

5. **Backward Compatibility**
   - Verify SUPPORTED_MODELS property works correctly
   - Verify existing code using SUPPORTED_MODELS still works

6. **Integration**
   - Verify end-to-end client creation with discovery

## Migration Path

1. First update the base `EnhancedChatBedrockConverse` class
2. Then update individual client classes one by one
3. Add discovery functions to `client_factory.py`
4. Update `create_langchain_chatbedrock` to use discovery
5. Run tests to verify everything works correctly
6. Update any documentation to reflect the new approach

## Benefits of This Approach

1. **DRY Principle**: Eliminates duplication by maintaining models in only one place
2. **Maintainability**: Adding new model IDs requires updating only one location
3. **Flexibility**: Adding new client classes is simpler without needing to update the factory
4. **Clarity**: Makes the relationship between client classes and parameter classes explicit
5. **Performance**: Lazy loading with caching optimizes resource usage

## Potential Risks and Mitigations

1. **Risk**: Import errors during discovery
   **Mitigation**: Robust error handling and logging during discovery

2. **Risk**: Performance impact of reflection-based discovery
   **Mitigation**: One-time discovery with result caching

3. **Risk**: Backward compatibility issues
   **Mitigation**: Maintaining compatibility properties and methods

4. **Risk**: Thread-safety during cache initialization
   **Mitigation**: Consider adding thread synchronization if needed
