# Model Discovery Implementation

This document details the implementation of dynamic model discovery for the Bedrock test command.

## Design Goals

The model discovery implementation aims to:
1. Dynamically discover all available Bedrock model implementations
2. Avoid hardcoding model IDs
3. Group models by family for better organization
4. Provide enough metadata to correctly initialize model clients

## Model Discovery Algorithm

The model discovery implementation will use Python's reflection capabilities to:
1. Scan the `src/dbp/llm/bedrock/models/` directory for model implementation modules
2. Load each module dynamically
3. Find model client classes (subclasses of `EnhancedBedrockBase`)
4. Extract supported model IDs from class attributes
5. Organize models by family

```python
def _get_available_models(self):
    """
    [Function intent]
    Dynamically discover supported Bedrock models by inspecting the model modules.
    
    [Design principles]
    - Dynamic discovery instead of hardcoding
    - Robust error handling for missing modules
    - Organization by model family
    
    [Implementation details]
    - Uses reflection to examine model modules
    - Finds subclasses of EnhancedBedrockBase
    - Extracts model IDs from class attributes
    - Returns dictionary mapping model_id to model class and metadata
    
    Returns:
        dict: Dictionary mapping model_id to model information
    """
    import os
    import importlib
    import inspect
    from src.dbp.llm.bedrock.enhanced_base import EnhancedBedrockBase
    
    models_dict = {}
    
    # Get the directory where model implementations are located
    models_dir = os.path.join(os.path.dirname(__file__), "../../../dbp/llm/bedrock/models")
    
    if not os.path.exists(models_dir):
        self.output_formatter.warning(f"Models directory not found: {models_dir}")
        return models_dict
    
    # Iterate through modules in the models directory
    for filename in os.listdir(models_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the module dynamically
                module_path = f"src.dbp.llm.bedrock.models.{module_name}"
                module = importlib.import_module(module_path)
                
                # Find model client classes (subclasses of EnhancedBedrockBase)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, EnhancedBedrockBase) and 
                        obj != EnhancedBedrockBase):
                        
                        # Get supported model IDs if available
                        if hasattr(obj, 'SUPPORTED_MODELS'):
                            for model_id in obj.SUPPORTED_MODELS:
                                models_dict[model_id] = {
                                    'class': obj,
                                    'module': module_name,
                                    'family': self._determine_model_family(model_id)
                                }
                        
                        # If no SUPPORTED_MODELS attribute, check for DEFAULT_MODEL_ID
                        elif hasattr(obj, 'DEFAULT_MODEL_ID'):
                            model_id = obj.DEFAULT_MODEL_ID
                            models_dict[model_id] = {
                                'class': obj,
                                'module': module_name,
                                'family': self._determine_model_family(model_id)
                            }
            
            except (ImportError, AttributeError) as e:
                # Log error but continue with other modules
                self.output_formatter.warning(f"Could not load models from {module_name}: {e}")
    
    return models_dict
```

## Model Family Determination

To organize models by family for the user interface, the implementation will include a function to determine the model family based on the model ID:

```python
def _determine_model_family(self, model_id):
    """
    [Function intent]
    Determine the model family based on model ID.
    
    [Design principles]
    - Reliable pattern matching
    - Maintainable grouping rules
    - Human-readable family names
    
    [Implementation details]
    - Uses pattern matching on model ID
    - Returns human-readable family name
    
    Args:
        model_id: The model ID to determine family for
        
    Returns:
        str: Human-readable model family name
    """
    model_id_lower = model_id.lower()
    
    if "claude" in model_id_lower:
        return "Claude (Anthropic)"
    elif "titan" in model_id_lower:
        return "Titan (Amazon)"
    elif "llama" in model_id_lower:
        return "Llama (Meta)"
    elif "falcon" in model_id_lower:
        return "Falcon (TII)"
    elif "mistral" in model_id_lower:
        return "Mistral"
    elif "cohere" in model_id_lower:
        return "Cohere"
    else:
        return "Other"
```

## Model Selection UI

When the `--model` argument is not provided, the implementation will present an interactive model selection UI:

```python
def _prompt_for_model_selection(self):
    """
    [Function intent]
    Prompt the user to select a model from available Bedrock models.
    
    [Design principles]
    - Clear organization by model family
    - User-friendly selection interface
    - Graceful handling of cancellation
    
    [Implementation details]
    - Groups models by family
    - Displays numbered list for selection
    - Supports cancellation via 'q' or Ctrl+C
    
    Returns:
        str: Selected model ID or None if cancelled
    """
    # Get available models
    available_models = self._get_available_models()
    
    if not available_models:
        self.output_formatter.error("No Bedrock model implementations found.")
        return None
    
    # Group models by family
    model_groups = {}
    for model_id, model_info in available_models.items():
        family = model_info['family']
        
        if family not in model_groups:
            model_groups[family] = []
        model_groups[family].append(model_id)
    
    # Display available models grouped by family
    self.output_formatter.print("\nAvailable Bedrock models:")
    model_options = []
    idx = 1
    
    for family in sorted(model_groups.keys()):
        self.output_formatter.print(f"\n{family}:")
        for model_id in sorted(model_groups[family]):
            self.output_formatter.print(f"  [{idx}] {model_id}")
            model_options.append(model_id)
            idx += 1
    
    # Prompt for selection
    while True:
        try:
            choice = input("\nEnter model number (or 'q' to quit): ")
            
            if choice.lower() in ('q', 'quit', 'exit'):
                self.output_formatter.print("Exiting...")
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(model_options):
                selected_model = model_options[choice_idx]
                model_info = available_models[selected_model]
                self.output_formatter.print(f"Selected model: {selected_model} ({model_info['family']})")
                
                # Store the model class for initialization
                self.model_class = model_info['class']
                return selected_model
            else:
                self.output_formatter.print(f"Please enter a number between 1 and {len(model_options)}")
        except ValueError:
            self.output_formatter.print("Please enter a valid number")
        except KeyboardInterrupt:
            self.output_formatter.print("\nOperation cancelled")
            return None
```

## Model Initialization

Once a model is selected, it needs to be properly initialized with the appropriate class:

```python
def _initialize_model(self, model_id):
    """
    [Function intent]
    Initialize the Bedrock model client using the appropriate model class.
    
    [Design principles]
    - Use correct model-specific implementation
    - Graceful fallback if model class not found
    - Proper configuration from system settings
    
    [Implementation details]
    - Uses the model class from discovery when available
    - Falls back to generic class if needed
    - Gets AWS credentials from config manager
    
    Args:
        model_id: ID of the model to initialize
        
    Raises:
        ValueError: If the model initialization fails
    """
    # Get AWS configuration from config manager
    from dbp.config.config_manager import ConfigurationManager
    
    config_manager = ConfigurationManager()
    config = config_manager.get_typed_config()
    
    # If we already have the model class from selection, use it
    if hasattr(self, 'model_class') and self.model_class is not None:
        model_class = self.model_class
    else:
        # Otherwise, re-discover the appropriate model class
        available_models = self._get_available_models()
        if model_id not in available_models:
            # Fallback to EnhancedBedrockBase if specific model class not found
            from src.dbp.llm.bedrock.enhanced_base import EnhancedBedrockBase
            model_class = EnhancedBedrockBase
        else:
            model_class = available_models[model_id]['class']
    
    # Initialize the model client using the discovered class
    self.model_client = model_class(
        model_id=model_id,
        region_name=config.aws.region,
        profile_name=config.aws.profile
    )
    
    # Test the client initialization
    if self.model_client is None:
        raise ValueError(f"Failed to initialize client for model: {model_id}")
```

## Error Handling

The model discovery implementation includes robust error handling to deal with various edge cases:

1. **Missing Module**: If a module cannot be imported, the error is logged and the discovery continues with other modules
2. **No Models Found**: If no models are discovered, the user is informed and the command exits
3. **Model Initialization Failure**: If a model cannot be initialized, a clear error message is shown

These error handling mechanisms ensure a smooth user experience even when things go wrong.

## Testing Considerations

To ensure the model discovery works correctly, it should be tested in various scenarios:

1. With different model implementations available
2. With missing or malformed model implementations
3. With varying AWS configurations

The implementation should also include debug logging to help diagnose issues when they occur.
