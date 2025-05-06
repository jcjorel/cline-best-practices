# LangChain CLI LLM Test Command Implementation Plan

## Overview

This document outlines the comprehensive implementation plan for adding proper parameter handling to the Bedrock test command using Pydantic models. The implementation will follow the approach of model-specific parameters defined in their respective files, with clean accessor methods to minimize custom logic at the consumer side.

## Problem Statement

The current implementation of the Bedrock test command in the CLI has the following issues:

1. **Parameter Handling**: Parameters like `temperature`, `max_tokens`, and `top_p` are not properly passed to the LangChain models, resulting in errors.
2. **Model-Specific Parameters**: Different Bedrock models have different parameters, but there's no clear way to define which parameters are available for each model.
3. **Parameter Validation**: Parameter validation is done manually, which is error-prone and not consistent.
4. **Consumer Logic**: The CLI command handler contains too much custom logic for handling parameters.

## Implementation Approach

The implementation will follow a clean, modular approach with these key components:

1. **Base Parameter Class**: A common `ModelParameters` class using Pydantic for validation and schema management
2. **Model-Specific Parameters**: Parameter subclasses defined directly in their model files
3. **Parameter Registry**: Self-registration mechanism for model parameter classes
4. **Clean Accessors**: Methods to convert between different formats (CLI args, model_kwargs, etc.)
5. **Consumer Simplification**: Minimize custom logic in the CLI command handler

# Design Principles for Model Parameters System

## Core Design Principles

1. **Parameter Definition and Validation**
   - Use Pydantic for strong type checking and validation
   - Define a consistent interface for all model parameters
   - Support model-specific parameter constraints and defaults
   - Allow customization by subclasses while maintaining type safety

2. **Model Registration and Discovery**
   - Implement self-registration of parameter classes 
   - Associate model IDs with appropriate parameter classes
   - Support both exact matching and prefix matching of model IDs
   - Provide graceful fallbacks when model-specific classes aren't found

3. **Parameter Applicability Rules**
   - Enable declarative parameter applicability via profiles
   - Maintain clear semantics for inclusion/exclusion logic
   - Support both whitelist and blacklist approaches
   - Ensure consistent behavior across all use cases

4. **Profile System**
   - Require a "default" profile in all parameter classes
   - Support profile inheritance and override in subclasses
   - Allow profile-specific parameter defaults
   - Enable model-specific operating modes (e.g., Claude reasoning mode)

## Parameter Definition Guide

Parameters are defined as class attributes with type annotations and Field() constraints:

```python
temperature: float = Field(
    default=0.7,       # Default value if not specified  
    ge=0.0,            # Minimum value (>=)
    le=1.0,            # Maximum value (<=)
    description="Controls randomness in the output."
)
```

Derived classes can:
1. Override existing parameters with model-specific constraints
2. Add new parameters specific to that model type
3. Inherit parameters without changes

Example:
```python
class ClaudeParameters(ModelParameters):
    # Override with Claude-specific constraints
    max_tokens: int = Field(
        default=4000,      # Different default for Claude
        ge=1,              # Same minimum
        le=100000,         # Different maximum for Claude
        description="Maximum tokens to generate."
    )
    
    # Add Claude-specific parameter
    stop_sequences: List[str] = Field(
        default_factory=list,
        description="Sequences that trigger generation to stop."
    )
```

## Profile System Documentation

### Profile Definition

Profiles are defined in the `_profiles` class variable. Every model MUST have at least
a "default" profile. Each profile has three configuration sections:

1. `applicable_params`: Controls which parameters are allowed in this profile
2. `not_applicable_params`: Controls which parameters are excluded in this profile
3. `param_overrides`: Defines profile-specific default values

### Applicability Rules

The system follows these rules to determine if a parameter applies in a profile:

1. If `applicable_params` is specified (not None):
   - ONLY parameters in this list are applicable
   - `not_applicable_params` is ignored
   
2. If `applicable_params` is None:
   - ALL parameters are potentially applicable
   - Parameters in `not_applicable_params` are excluded
   
3. Special cases:
   - Empty `applicable_params` list ([]) means NO parameters are applicable
   - Empty `not_applicable_params` list ([]) means NO parameters are excluded
   - If `not_applicable_params` is None, it means ALL parameters are excluded

### Applicability Reference Table

| Scenario                   | applicable_params | not_applicable_params | Result                              |
|----------------------------|-------------------|----------------------|-------------------------------------|
| All params allowed         | None              | []                   | All parameters are usable           |
| No params allowed          | []                | None                 | No parameters are usable            |
| Whitelist only             | ["a", "b"]        | [anything]           | Only "a" and "b" are usable         |
| Blacklist only             | None              | ["x", "y"]           | All except "x" and "y" are usable   |

### Profile Inheritance

When extending a class:
1. Parent profiles are automatically inherited
2. Child class can override existing profiles
3. Child class can add new profiles
4. The "default" profile MUST exist in every class

Example:
```python
class BaseParams(ModelParameters):
    _profiles = {
        "default": {
            "applicable_params": None,
            "not_applicable_params": [],
            "param_overrides": {}
        }
    }
    
class DerivedParams(BaseParams):
    # Will inherit "default" from BaseParams if not specified
    _profiles = {
        # Override parent's default profile
        "default": {
            "applicable_params": None,
            "not_applicable_params": ["experimental_param"],
            "param_overrides": {}
        },
        # Add new profile
        "custom": {
            "applicable_params": ["temperature", "max_tokens"],
            "not_applicable_params": None,  # Ignored when applicable_params is specified
            "param_overrides": {
                "temperature": 0.8
            }
        }
    }
```

### Parameter Overrides

The `param_overrides` section allows setting profile-specific default values:

1. These override the class-level defaults but not explicit user values
2. Validation constraints still apply (min/max values)
3. Overrides only affect default values, not constraints

Example:
```python
_profiles = {
    "creative": {
        "applicable_params": None,
        "not_applicable_params": [],
        "param_overrides": {
            "temperature": 0.9,  # Higher temperature for creative profile
            "top_p": 0.95
        }
    }
}
```

## Complete Class Example

```python
class ClaudeParameters(ModelParameters):
    """Parameter definitions specific to Claude models with different operating modes."""

    # Override common parameter with Claude-specific constraints
    max_tokens: int = Field(
        default=4000,  # Claude-specific default
        ge=1,          # Minimum is the same
        le=100000,     # Claude-specific maximum
        description="Maximum tokens to generate in the response."
    )
    
    # Add Claude-specific parameter
    stop_sequences: List[str] = Field(
        default_factory=list,  # Empty list default
        description="Sequences that will cause the model to stop generating."
    )
    
    # Define Claude-specific profiles
    _profiles = {
        # Default profile - inherited from parent but overridden here
        "default": {
            "applicable_params": None,      # All parameters are potentially applicable
            "not_applicable_params": [],    # No parameters are excluded
            "param_overrides": {}           # No parameter overrides
        },
        
        # Reasoning mode - disallows all parameters
        "reasoning": {
            "applicable_params": [],        # No parameters are allowed
            "not_applicable_params": None,  # Alternative way to express same thing
            "param_overrides": {}           # No parameter overrides (wouldn't be used anyway)
        },
        
        # Creative mode - selective parameters with adjusted defaults
        "creative": {
            "applicable_params": ["temperature", "top_p", "max_tokens"],
            "not_applicable_params": None,   # Ignored when applicable_params is specified
            "param_overrides": {
                "temperature": 0.9,          # Higher temperature for creative output
                "top_p": 0.95                # Higher top_p for creative output
            }
        }
    }
    
    class Config:
        model_name = "Claude"
        supported_models = [
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-7-sonnet-20250219-v1:0"
        ]
```

## Implementation Plan

### Phase 1: Create Base Parameter Framework

#### 1.1 Create Base Parameter Class

Create a base `ModelParameters` class in `src/dbp/llm/common/model_parameters.py`:

```python
"""
Parameters definition for LLM models with Pydantic validation.
"""

import logging
from typing import Dict, Any, Type, ClassVar, Optional, List, Union, get_type_hints
from pydantic import BaseModel, Field, validator

class ModelParameters(BaseModel):
    """
    [Class intent]
    Base class for all Bedrock model parameters, providing common parameter definitions
    and utility methods for parameter handling across all model types.
    
    [Design principles]
    - Single source of truth for parameter definitions
    - Self-registration of model-specific parameter classes
    - Clean accessors for parameter conversion
    
    [Implementation details]
    - Uses Pydantic for validation and schema management
    - Registry pattern for model-specific parameter lookup
    - Factory method for creating appropriate parameter instance
    """
    
    # Common parameters for most models
    temperature: float = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Controls randomness in the output. Higher values make output more diverse."
    )
    max_tokens: int = Field(
        default=1024, 
        ge=1, 
        le=4096, 
        description="Maximum number of tokens to generate in the response."
    )
    top_p: float = Field(
        default=0.9, 
        ge=0.0, 
        le=1.0, 
        description="Nucleus sampling parameter."
    )

    # Class registry to keep track of all parameter models
    _registry: ClassVar[Dict[str, Type["ModelParameters"]]] = {}
    
    def __init_subclass__(cls, **kwargs):
        """Register all subclasses for factory method use."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "Config") and hasattr(cls.Config, "supported_models"):
            for model_id in cls.Config.supported_models:
                ModelParameters._registry[model_id] = cls
    
    @classmethod
    def for_model(cls, model_id: str) -> "ModelParameters":
        """
        [Method intent]
        Factory method to create appropriate parameter model instance for a given model ID.
        
        [Design principles]
        - Automatic parameter class selection
        - Fallback to base parameters for unknown models
        
        [Implementation details]
        - Matches model ID against registered model prefixes
        - Returns new instance of appropriate parameter class
        
        Args:
            model_id: The Bedrock model ID
            
        Returns:
            ModelParameters: Instance of appropriate parameter class
        """
        # First try exact match
        if model_id in cls._registry:
            return cls._registry[model_id]()
            
        # Try prefix match
        for registered_id, param_cls in cls._registry.items():
            # Match model family prefix (before the first colon)
            if model_id.startswith(registered_id.split(':')[0]):
                return param_cls()
        
        # Default to base model if no match
        logging.warning(f"No parameter model found for {model_id}, using base parameters")
        return cls()
    
    @classmethod
    def get_all_param_fields(cls) -> Dict[str, Field]:
        """
        [Method intent]
        Get all parameter fields from all registered parameter classes.
        
        [Design principles]
        - Complete parameter discovery
        - No field duplication
        
        [Implementation details]
        - Collects fields from all registered parameter classes
        - Ensures each field is only included once
        
        Returns:
            Dict[str, Field]: All parameter fields from all classes
        """
        all_fields = {}
        
        # Add base class fields first
        for field_name, field in cls.__fields__.items():
            all_fields[field_name] = field
            
        # Add fields from registered classes
        for param_cls in set(cls._registry.values()):
            for field_name, field in param_cls.__fields__.items():
                if field_name not in all_fields:
                    all_fields[field_name] = field
                
        return all_fields
    
    def to_model_kwargs(self) -> Dict[str, Any]:
        """
        [Method intent]
        Convert parameters to model_kwargs format for LangChain.
        
        [Design principles]
        - Clean conversion to LangChain format
        - Exclude undefined or None values
        
        [Implementation details]
        - Uses Pydantic's dict() method with appropriate exclusions
        
        Returns:
            Dict[str, Any]: Parameters in model_kwargs format
        """
        # Convert to dict, excluding None values and unset fields
        return self.dict(exclude_none=True, exclude_unset=True)
    
    def update_from_args(self, args_dict: Dict[str, Any]) -> "ModelParameters":
        """
        [Method intent]
        Update parameters from arguments dictionary (e.g., CLI args).
        
        [Design principles]
        - Seamless integration with CLI arguments
        - Skip None values
        
        [Implementation details]
        - Updates only fields defined in the model
        - Returns self for method chaining
        
        Args:
            args_dict: Dictionary of arguments
            
        Returns:
            ModelParameters: Self, for method chaining
        """
        for field_name in self.__fields__:
            if field_name in args_dict and args_dict[field_name] is not None:
                setattr(self, field_name, args_dict[field_name])
        return self
    
    @classmethod
    def add_arguments_to_parser(cls, parser) -> None:
        """
        [Method intent]
        Add all parameter fields to an argument parser.
        
        [Design principles]
        - Automatic CLI argument generation
        - Informative help text
        
        [Implementation details]
        - Adds all fields from all parameter classes
        - Includes model name in help text for model-specific parameters
        
        Args:
            parser: ArgumentParser to add arguments to
        """
        all_fields = cls.get_all_param_fields()
        
        for field_name, field in all_fields.items():
            # Determine field type for argument
            field_type = field.type_
            if hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
                # Handle Optional[] types
                field_type = field_type.__args__[0]
            
            # Get field metadata
            description = field.field_info.description or ""
            default = field.default
            
            # Get model name for field if it's from a specific model
            model_name = "Common"
            for param_cls in set(cls._registry.values()):
                if field_name in param_cls.__fields__ and hasattr(param_cls, "Config") and hasattr(param_cls.Config, "model_name"):
                    model_name = param_cls.Config.model_name
                    break
            
            if model_name != "Common":
                description = f"[{model_name}] {description}"
                
            parser.add_argument(
                f"--{field_name}",
                type=field_type,
                default=default,
                help=description
            )
```

### Phase 2: Add Model-Specific Parameters

#### 2.1 Update Claude Parameters in `src/dbp/llm/bedrock/models/claude3.py`

Add Claude-specific parameters to the existing Claude model file:

```python
from typing import List
from pydantic import Field
from src.dbp.llm.common.model_parameters import ModelParameters

class ClaudeParameters(ModelParameters):
    """
    [Class intent]
    Parameters specific to Claude models.
    
    [Design principles]
    - Complete set of Claude-specific parameters
    - Documentation from official Claude API
    
    [Implementation details]
    - Extends base ModelParameters
    - Adds Claude-specific parameters
    """
    stop_sequences: List[str] = Field(
        default_factory=list,
        description="Sequences that will cause the model to stop generating."
    )
    
    class Config:
        model_name = "Claude"
        supported_models = [
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-7-sonnet-20250219-v1:0"
        ]
```

#### 2.2 Update Nova Parameters in `src/dbp/llm/bedrock/models/nova.py`

Add Nova-specific parameters to the existing Nova model file:

```python
from pydantic import Field
from src.dbp.llm.common.model_parameters import ModelParameters

class NovaParameters(ModelParameters):
    """
    [Class intent]
    Parameters specific to Nova models.
    
    [Design principles]
    - Complete set of Nova-specific parameters
    - Documentation from official Nova API
    
    [Implementation details]
    - Extends base ModelParameters
    - Adds Nova-specific parameters
    """
    top_k: int = Field(
        default=50, 
        ge=0, 
        le=500, 
        description="Only sample from the top K most likely tokens."
    )
    repetition_penalty: float = Field(
        default=1.0,
        ge=1.0,
        le=2.0,
        description="Penalizes repetition in generated text."
    )
    
    class Config:
        model_name = "Nova"
        supported_models = [
            "amazon.nova-lite-v1:0",
            "amazon.nova-micro-v1:0",
            "amazon.nova-premier-v1:0",
            "amazon.nova-pro-v1:0"
        ]
```

### Phase 3: Update CLI Command Handler

#### 3.1 Update `src/dbp_cli/commands/test/bedrock.py`

Update the CLI command handler to use the new parameter framework:

```python
# Add imports
from src.dbp.llm.common.model_parameters import ModelParameters

class BedrockTestCommandHandler:
    # Update the model parameters structure
    MODEL_PARAMETERS = None  # We'll use Pydantic models instead
    
    @staticmethod
    def add_arguments(parser):
        """
        [Function intent]
        Add command-line arguments for the Bedrock test command.
        """
        parser.add_argument(
            "--model", "-m",
            help="Bedrock model to use (if not specified, will prompt to choose)"
        )
        
        # Add all parameters from all models using the ModelParameters class
        ModelParameters.add_arguments_to_parser(parser)
    
    def execute(self, args):
        """
        [Function intent]
        Execute the Bedrock test command.
        """
        try:
            # Extract model parameters from args - just store the args for later
            self.args = args
            
            # If model is not specified, prompt user to choose
            model_id = args.model
            if not model_id:
                model_id = self._prompt_for_model_selection()
                if not model_id:  # User cancelled
                    return 1
            
            # Initialize the model client
            self._initialize_model(model_id)
            
            # Start interactive chat session
            return self._run_interactive_chat()
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return 130
        except Exception as e:
            self.output.error(f"Error in Bedrock test: {str(e)}")
            traceback.print_exc()
            return 1
    
    def _initialize_model(self, model_id):
        """
        [Function intent]
        Initialize the selected LangChain model implementation.
        """
        # Get AWS configuration from config manager
        config_manager = ConfigurationManager()
        config = config_manager.get_typed_config()
        
        # Import the BedrockClientFactory
        from src.dbp.llm.bedrock.client_factory import BedrockClientFactory
        
        # Get region and profile name if available
        region_name = None
        profile_name = None
        if hasattr(config, 'aws'):
            if hasattr(config.aws, 'region'):
                region_name = config.aws.region
            if hasattr(config.aws, 'profile_name'):
                profile_name = config.aws.profile_name
        
        # Create parameter model for selected model and populate from args
        self.model_param_model = ModelParameters.for_model(model_id)
        self.model_param_model.update_from_args(vars(self.args))
        
        # Convert to model_kwargs format
        model_kwargs = self.model_param_model.to_model_kwargs()
        
        # Use the BedrockClientFactory to create the model instance
        self.model_client = BedrockClientFactory.create_langchain_chatbedrock(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            model_kwargs=model_kwargs,  # Pass model parameters properly formatted
            use_model_discovery=True,
            logger=logging.getLogger("BedrockTestCommandHandler")
        )
        
        # Test the client initialization
        if self.model_client is None:
            raise ValueError(f"Failed to initialize client for model: {model_id}")
    
    def _handle_config_command(self, command_input):
        """
        [Function intent]
        Handle the config command to show or modify model parameters.
        """
        parts = command_input.split(None, 2)
        
        # Just "config" - show current config
        if len(parts) == 1:
            self.output.print("\nCurrent model parameters:")
            for field_name, field in self.model_param_model.__fields__.items():
                value = getattr(self.model_param_model, field_name)
                desc = field.field_info.description
                self.output.print(f"  {field_name} = {value} ({desc})")
            self.output.print()
            return
        
        # "config param value" - set parameter
        if len(parts) >= 3:
            param = parts[1]
            value_str = parts[2]
            
            if param not in self.model_param_model.__fields__:
                self.output.error(f"Unknown parameter: {param}")
                return
            
            field = self.model_param_model.__fields__[param]
            
            try:
                # Get field type
                field_type = field.outer_type_
                
                # Convert and validate value
                value = field_type(value_str)
                
                # Validate against min/max
                min_val = getattr(field.field_info, "ge", None)
                if min_val is not None and value < min_val:
                    self.output.error(f"Value for {param} must be at least {min_val}")
                    return
                    
                max_val = getattr(field.field_info, "le", None)
                if max_val is not None and value > max_val:
                    self.output.error(f"Value for {param} must be at most {max_val}")
                    return
                
                # Set parameter
                setattr(self.model_param_model, param, value)
                self.output.print(f"Set {param} = {value}")
                
            except ValueError:
                self.output.error(f"Invalid value for {param}: {value_str}")
            
            return
        
        # "config param" - show specific parameter
        if len(parts) == 2:
            param = parts[1]
            if param not in self.model_param_model.__fields__:
                self.output.error(f"Unknown parameter: {param}")
                return
                
            value = getattr(self.model_param_model, param)
            field = self.model_param_model.__fields__[param]
            desc = field.field_info.description
            self.output.print(f"{param} = {value} ({desc})")
            return
            
        self.output.print("Usage: config [param] [value]")
    
    def _process_model_response(self):
        """
        [Function intent]
        Process the user input through the model and display streaming response.
        """
        self.output.print("\nAssistant > ", end="", flush=True)
        
        response_text = ""
        
        async def process_stream():
            nonlocal response_text
            try:
                # Format messages for the LangChain model
                messages = [{"role": msg["role"], "content": msg["content"]} 
                            for msg in self.chat_history]
                
                # Stream the response - no parameters passed here
                # Parameters were already set during model initialization
                async for chunk in self.model_client.astream_text(messages):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                    
            except Exception as e:
                print(f"\nError during streaming: {str(e)}")
        
        # Run the async function
        try:
            asyncio.run(process_stream())
            print()  # New line after response
        except KeyboardInterrupt:
            print("\n[Response interrupted]")
        
        # Add to history if we got a response
        if response_text:
            self.chat_history.append({"role": "assistant", "content": response_text})
```

### Phase 4: Testing and Validation

#### 4.1 Test with Claude Models

Verify that the implementation works properly with Claude models:
1. Run the CLI command: `python -m dbp_cli test llm bedrock`
2. Select a Claude model
3. Test basic chat functionality
4. Test parameter changes with the `config` command

#### 4.2 Test with Nova Models

Verify that the implementation works properly with Nova models:
1. Run the CLI command: `python -m dbp_cli test llm bedrock`
2. Select a Nova model
3. Test basic chat functionality
4. Test parameter changes with the `config` command

#### 4.3 Test with CLI Parameters

Verify that the parameters can be set via command line:
1. Run the CLI command: `python -m dbp_cli test llm bedrock --model anthropic.claude-3-5-haiku-20241022-v1:0 --temperature 0.5 --max_tokens 500`
2. Verify that the parameters are correctly applied

## Implementation Schedule

1. Phase 1: Base Parameter Framework - 1 day
2. Phase 2: Model-Specific Parameters - 1 day
3. Phase 3: CLI Command Handler Updates - 1 day
4. Phase 4: Testing and Validation - 1 day

## Dependencies

1. Pydantic for parameter models
2. Existing LangChain wrapper classes
3. BedrockClientFactory for model creation

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Different behavior across model types | Test each model type separately with its specific parameters |
| Changes to LangChain API | Keep up to date with LangChain documentation and adapt as needed |
| Parameter validation failures | Add clear error messages and fail gracefully |
| Missing model-specific parameters | Research official documentation for each model type |

## Conclusion

This implementation will provide a robust, maintainable solution for handling model parameters in the Bedrock test command. By leveraging Pydantic for validation and using a clean, modular approach with model-specific parameters defined in their respective files, we create a flexible system that can easily accommodate new model types and parameters in the future.
