# Model Discovery Implementation

This document details the implementation of dynamic model discovery for the Bedrock test command using the current LangChain implementation.

## Design Goals

The model discovery implementation aims to:
1. Dynamically discover all available Bedrock model implementations using LangChain wrappers
2. Avoid hardcoding model IDs
3. Group models by family for better organization
4. Provide enough metadata to correctly initialize model clients

## Model Discovery Algorithm

The model discovery implementation will use Python's reflection capabilities to:
1. Import model modules (claude3, nova, etc.)
2. Find model client classes that extend EnhancedChatBedrockConverse
3. Extract supported model IDs from SUPPORTED_MODELS class attributes
4. Organize models by family

```python
def _get_available_models(self):
    """
    [Function intent]
    Dynamically discover supported Bedrock models using LangChain wrapper classes.
    
    [Design principles]
    - Dynamic discovery instead of hardcoding
    - Robust error handling for missing modules
    - Organization by model family
    
    [Implementation details]
    - Uses reflection to find model classes
    - Checks for SUPPORTED_MODELS attribute
    - Returns dictionary mapping model_id to model information
    
    Returns:
        dict: Dictionary mapping model_id to model information
    """
    models_dict = {}
    
    # Import model modules
    try:
        from src.dbp.llm.bedrock.models import claude3, nova
        # Add more model modules as they become available
    except ImportError as e:
        self.output_formatter.warning(f"Could not import model modules: {e}")
        return models_dict
        
    # Get all modules to scan
    modules_to_scan = [claude3, nova]  # Add more as needed
    
    # Find model client classes in each module
    for module in modules_to_scan:
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, EnhancedChatBedrockConverse) and 
                obj != EnhancedChatBedrockConverse and
                hasattr(obj, 'SUPPORTED_MODELS')):
                
                # Get model family name from class name
                family_name = name.replace('EnhancedChatBedrockConverse', '')
                
                # Register each supported model
                for model_id in obj.SUPPORTED_MODELS:
                    models_dict[model_id] = {
                        'class': obj,
                        'module': module.__name__,
                        'family': self._determine_model_family(model_id, family_name)
                    }
    
    return models_dict
```

## Model Family Determination

To organize models by family for the user interface, the implementation includes a function to determine the model family based on the model ID and class name:

```python
def _determine_model_family(self, model_id, family_name=""):
    """
    [Function intent]
    Determine the model family based on model ID and class name.
    
    [Design principles]
    - Reliable pattern matching
    - Human-readable family names
    
    [Implementation details]
    - Uses both model ID patterns and class name
    - Returns human-readable family name
    
    Args:
        model_id: The model ID to determine family for
        family_name: Optional family name hint from class name
        
    Returns:
        str: Human-readable model family name
    """
    model_id_lower = model_id.lower()
    
    if "claude" in model_id_lower or "anthropic" in model_id_lower or family_name == "Claude":
        return "Claude (Anthropic)"
    elif "titan" in model_id_lower:
        return "Titan (Amazon)"
    elif "nova" in model_id_lower or family_name == "Nova":
        return "Nova (Amazon)"
    elif "llama" in model_id_lower or "meta" in model_id_lower:
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

When the `--model` argument is not provided, the implementation presents an interactive model selection UI:

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

Once a model is selected, it needs to be properly initialized with the appropriate LangChain class:

```python
def _initialize_model(self, model_id):
    """
    [Function intent]
    Initialize the selected LangChain model implementation.
    
    [Design principles]
    - Use correct model-specific implementation
    - Proper configuration from system settings
    
    [Implementation details]
    - Gets AWS credentials from config manager
    - Uses the model class from discovery
    - Initializes with appropriate parameters
    
    Args:
        model_id: ID of the model to initialize
        
    Raises:
        ValueError: If the model initialization fails
    """
    # Get AWS configuration from config manager
    config_manager = ConfigurationManager()
    config = config_manager.get_typed_config()
    
    # Get the appropriate model class
    available_models = self._get_available_models()
    if model_id not in available_models:
        raise ValueError(f"Model {model_id} is not supported")
    
    # Get the model class for this model ID
    model_class = available_models[model_id]['class']
    
    # Initialize the model client with LangChain parameters
    self.model_client = model_class(
        model_id=model_id,
        region_name=config.aws.region,
        profile_name=config.aws.profile,
        # Add any other required parameters
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

## Extensibility

The model discovery implementation is designed to be extensible:

1. **New Model Classes**: As new model implementations are added, they will be automatically discovered
2. **Additional Models**: When new models are added to SUPPORTED_MODELS in existing classes, they will be included
3. **New Families**: The family determination logic can be extended for new model families

This ensures that the command will continue to work as the set of supported models evolves over time.

## Testing Considerations

To ensure the model discovery works correctly, it should be tested in various scenarios:

1. With different model implementations available
2. With missing or malformed model implementations
3. With varying AWS configurations

The implementation should also include debug logging to help diagnose issues when they occur.
