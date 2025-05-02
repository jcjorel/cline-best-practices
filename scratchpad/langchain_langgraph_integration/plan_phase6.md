# Phase 6: LLM Configuration Registry

This phase implements the LLM Configuration Registry for the LangChain/LangGraph integration. It focuses on providing a centralized repository for named LLM configurations, which allows for consistent model behavior across the application and minimizes LLM-specific code throughout the codebase.

## Objectives

1. Design and implement a configuration registry system
2. Create validation mechanisms for configurations
3. Establish predefined configurations for common use cases
4. Implement configuration override capabilities

## ConfigRegistry Implementation

Create the configuration registry implementation in `src/dbp/llm/common/config_registry.py`:

```python
import logging
import json
import copy
from typing import Dict, Any, List, Optional, Set, Type, Union

from src.dbp.llm.common.exceptions import ConfigurationError, InvalidConfigurationError

class ConfigRegistry:
    """
    [Class intent]
    Manages named configurations for LLM interactions, providing a centralized 
    repository of predefined settings. This enables consistent model behavior
    across the application and minimizes LLM-specific code in business logic.
    
    [Design principles]
    - Single source of truth for LLM configurations
    - Support for predefined configurations for common use cases
    - Dynamic registration and modification of configurations
    - Clear validation of configuration parameters
    - Immutable configuration access to prevent modification
    
    [Implementation details]
    - Maintains registry of named configurations
    - Provides built-in defaults for common scenarios
    - Implements validation for configuration parameters
    - Supports overriding and extension of configurations
    """
    
    # Standard configuration parameter names for consistency
    PARAM_TEMPERATURE = "temperature"
    PARAM_MAX_TOKENS = "max_tokens"
    PARAM_TOP_P = "top_p"
    PARAM_TOP_K = "top_k"
    PARAM_PRESENCE_PENALTY = "presence_penalty"
    PARAM_FREQUENCY_PENALTY = "frequency_penalty"
    PARAM_STOP_SEQUENCES = "stop_sequences"
    PARAM_TIMEOUT = "timeout"
    PARAM_STREAM = "stream"
    PARAM_RESPONSE_FORMAT = "response_format"
    
    # Built-in configuration names
    CONFIG_DEFAULT = "default"
    CONFIG_CREATIVE = "creative"
    CONFIG_PRECISE = "precise"
    
    def __init__(self):
        """
        [Method intent]
        Initialize the configuration registry with built-in configurations.
        
        [Design principles]
        - Provide sensible defaults for common use cases
        - Establish baseline configurations that can be extended
        
        [Implementation details]
        - Creates internal registry storage
        - Initializes built-in configurations
        - Sets up validation rules
        """
        self._configs = {}
        self._validation_rules = {}
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize built-in configurations
        self._initialize_built_in_configs()
        
        # Initialize validation rules
        self._initialize_validation_rules()
    
    def _initialize_built_in_configs(self) -> None:
        """
        [Method intent]
        Initialize built-in configurations for common use cases.
        
        [Design principles]
        - Provide ready-to-use configurations
        - Cover common usage scenarios
        - Establish baselines for customization
        
        [Implementation details]
        - Creates default configuration for balanced behavior
        - Creates creative configuration for more varied output
        - Creates precise configuration for factual responses
        """
        # Standard balanced configuration
        self._configs[self.CONFIG_DEFAULT] = {
            self.PARAM_TEMPERATURE: 0.7,
            self.PARAM_MAX_TOKENS: 1024,
            self.PARAM_TOP_P: 0.95,
            self.PARAM_PRESENCE_PENALTY: 0.0,
            self.PARAM_FREQUENCY_PENALTY: 0.0,
            self.PARAM_TIMEOUT: 30,
            self.PARAM_STREAM: True,
            "_description": "Balanced configuration for general use cases"
        }
        
        # Creative configuration for more varied output
        self._configs[self.CONFIG_CREATIVE] = {
            self.PARAM_TEMPERATURE: 0.9,
            self.PARAM_MAX_TOKENS: 2048,
            self.PARAM_TOP_P: 0.98,
            self.PARAM_PRESENCE_PENALTY: 0.2,
            self.PARAM_FREQUENCY_PENALTY: 0.2,
            self.PARAM_TIMEOUT: 60,
            self.PARAM_STREAM: True,
            "_description": "Creative configuration for varied and exploratory responses"
        }
        
        # Precise configuration for factual responses
        self._configs[self.CONFIG_PRECISE] = {
            self.PARAM_TEMPERATURE: 0.2,
            self.PARAM_MAX_TOKENS: 1024,
            self.PARAM_TOP_P: 0.9,
            self.PARAM_PRESENCE_PENALTY: 0.0,
            self.PARAM_FREQUENCY_PENALTY: 0.0,
            self.PARAM_TIMEOUT: 30,
            self.PARAM_STREAM: True,
            "_description": "Precise configuration for factual and deterministic responses"
        }
    
    def _initialize_validation_rules(self) -> None:
        """
        [Method intent]
        Initialize validation rules for configuration parameters.
        
        [Design principles]
        - Ensure configurations are valid and safe
        - Provide clear feedback on validation failures
        - Support different parameter types
        
        [Implementation details]
        - Defines validation functions for each parameter
        - Sets up allowed ranges and types
        """
        self._validation_rules = {
            self.PARAM_TEMPERATURE: lambda v: 0.0 <= v <= 2.0,
            self.PARAM_MAX_TOKENS: lambda v: isinstance(v, int) and v > 0,
            self.PARAM_TOP_P: lambda v: 0.0 <= v <= 1.0,
            self.PARAM_TOP_K: lambda v: isinstance(v, int) and v > 0,
            self.PARAM_PRESENCE_PENALTY: lambda v: -2.0 <= v <= 2.0,
            self.PARAM_FREQUENCY_PENALTY: lambda v: -2.0 <= v <= 2.0,
            self.PARAM_STOP_SEQUENCES: lambda v: isinstance(v, list) and all(isinstance(s, str) for s in v),
            self.PARAM_TIMEOUT: lambda v: isinstance(v, (int, float)) and v > 0,
            self.PARAM_STREAM: lambda v: isinstance(v, bool),
            self.PARAM_RESPONSE_FORMAT: lambda v: isinstance(v, dict)
        }
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        [Method intent]
        Validate a configuration against defined rules.
        
        [Design principles]
        - Ensure configuration safety
        - Provide clear error messages
        - Check all parameters against rules
        
        [Implementation details]
        - Validates each parameter against its rule
        - Skips validation for unknown parameters
        - Raises specific exceptions for validation failures
        
        Args:
            config: Configuration to validate
            
        Raises:
            InvalidConfigurationError: If validation fails
        """
        for param, value in config.items():
            # Skip internal parameters (starting with underscore)
            if param.startswith('_'):
                continue
                
            # Skip parameters without validation rules
            if param not in self._validation_rules:
                continue
                
            # Validate parameter
            if not self._validation_rules[param](value):
                raise InvalidConfigurationError(
                    f"Invalid value for parameter '{param}': {value}"
                )
    
    def register_config(self, name: str, config: Dict[str, Any], description: Optional[str] = None) -> None:
        """
        [Method intent]
        Register a configuration with the registry.
        
        [Design principles]
        - Support dynamic configuration management
        - Ensure configuration validity
        - Prevent duplicate registrations
        
        [Implementation details]
        - Validates configuration against rules
        - Stores configuration with metadata
        - Prevents overwriting built-in configurations
        
        Args:
            name: Unique name for the configuration
            config: Configuration parameters
            description: Optional description of the configuration
            
        Raises:
            ConfigurationError: If registration fails
            InvalidConfigurationError: If configuration is invalid
        """
        # Check if trying to modify a built-in configuration
        if name in [self.CONFIG_DEFAULT, self.CONFIG_CREATIVE, self.CONFIG_PRECISE]:
            raise ConfigurationError(f"Cannot modify built-in configuration '{name}'")
            
        # Check if configuration already exists
        if name in self._configs:
            raise ConfigurationError(f"Configuration '{name}' already exists")
        
        try:
            # Create a copy to avoid external modification
            config_copy = copy.deepcopy(config)
            
            # Add description if provided
            if description:
                config_copy["_description"] = description
            
            # Validate configuration
            self._validate_config(config_copy)
            
            # Store configuration
            self._configs[name] = config_copy
            
            self._logger.info(f"Registered configuration '{name}'")
        except Exception as e:
            if isinstance(e, (ConfigurationError, InvalidConfigurationError)):
                raise e
            raise ConfigurationError(f"Failed to register configuration '{name}': {str(e)}")
    
    def update_config(self, name: str, updates: Dict[str, Any]) -> None:
        """
        [Method intent]
        Update an existing configuration.
        
        [Design principles]
        - Support configuration modifications
        - Ensure configuration validity
        - Prevent modification of built-in configurations
        
        [Implementation details]
        - Checks if configuration exists
        - Updates only the specified parameters
        - Validates resulting configuration
        
        Args:
            name: Name of the configuration to update
            updates: Parameter updates to apply
            
        Raises:
            ConfigurationError: If update fails
            InvalidConfigurationError: If resulting configuration is invalid
        """
        # Check if trying to modify a built-in configuration
        if name in [self.CONFIG_DEFAULT, self.CONFIG_CREATIVE, self.CONFIG_PRECISE]:
            raise ConfigurationError(f"Cannot modify built-in configuration '{name}'")
            
        # Check if configuration exists
        if name not in self._configs:
            raise ConfigurationError(f"Configuration '{name}' does not exist")
        
        try:
            # Create a copy of the current configuration
            current_config = copy.deepcopy(self._configs[name])
            
            # Apply updates
            for param, value in updates.items():
                current_config[param] = value
            
            # Validate updated configuration
            self._validate_config(current_config)
            
            # Store updated configuration
            self._configs[name] = current_config
            
            self._logger.info(f"Updated configuration '{name}'")
        except Exception as e:
            if isinstance(e, (ConfigurationError, InvalidConfigurationError)):
                raise e
            raise ConfigurationError(f"Failed to update configuration '{name}': {str(e)}")
    
    def unregister_config(self, name: str) -> None:
        """
        [Method intent]
        Remove a configuration from the registry.
        
        [Design principles]
        - Support dynamic configuration management
        - Prevent removal of built-in configurations
        
        [Implementation details]
        - Checks if configuration exists
        - Prevents removal of built-in configurations
        - Removes configuration from registry
        
        Args:
            name: Name of the configuration to remove
            
        Raises:
            ConfigurationError: If removal fails
        """
        # Check if trying to remove a built-in configuration
        if name in [self.CONFIG_DEFAULT, self.CONFIG_CREATIVE, self.CONFIG_PRECISE]:
            raise ConfigurationError(f"Cannot remove built-in configuration '{name}'")
            
        # Check if configuration exists
        if name not in self._configs:
            raise ConfigurationError(f"Configuration '{name}' does not exist")
            
        # Remove configuration
        del self._configs[name]
        
        self._logger.info(f"Removed configuration '{name}'")
    
    def get_config(self, name: str = "default") -> Dict[str, Any]:
        """
        [Method intent]
        Get a configuration by name.
        
        [Design principles]
        - Provide access to stored configurations
        - Return immutable copies to prevent modification
        - Support default configuration access
        
        [Implementation details]
        - Checks if configuration exists
        - Returns a deep copy to prevent modification
        - Removes internal metadata before returning
        
        Args:
            name: Name of the configuration to retrieve (default: "default")
            
        Returns:
            Dict[str, Any]: Configuration parameters
            
        Raises:
            ConfigurationError: If configuration does not exist
        """
        # Check if configuration exists
        if name not in self._configs:
            raise ConfigurationError(f"Configuration '{name}' does not exist")
            
        # Get a deep copy to prevent modification
        config = copy.deepcopy(self._configs[name])
        
        # Remove internal metadata
        for key in list(config.keys()):
            if key.startswith('_'):
                del config[key]
                
        return config
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """
        [Method intent]
        List all available configurations with metadata.
        
        [Design principles]
        - Support configuration discovery
        - Include metadata for informed selection
        
        [Implementation details]
        - Creates list of configuration summaries
        - Includes names and descriptions
        - Preserves built-in vs custom distinction
        
        Returns:
            List[Dict[str, Any]]: List of configuration summaries
        """
        result = []
        
        for name, config in sorted(self._configs.items()):
            # Create summary with name and description
            summary = {
                "name": name,
                "description": config.get("_description", "No description"),
                "built_in": name in [self.CONFIG_DEFAULT, self.CONFIG_CREATIVE, self.CONFIG_PRECISE]
            }
            
            result.append(summary)
            
        return result
    
    def derive_config(self, base_name: str, updates: Dict[str, Any], new_name: str, description: Optional[str] = None) -> None:
        """
        [Method intent]
        Create a new configuration derived from an existing one.
        
        [Design principles]
        - Support configuration reuse and extension
        - Maintain configuration validity
        - Enable creation of specialized configurations
        
        [Implementation details]
        - Gets base configuration
        - Applies updates to create new configuration
        - Validates and registers the derived configuration
        
        Args:
            base_name: Name of the base configuration
            updates: Parameter updates to apply
            new_name: Name for the derived configuration
            description: Optional description for the derived configuration
            
        Raises:
            ConfigurationError: If derivation fails
            InvalidConfigurationError: If resulting configuration is invalid
        """
        # Get base configuration
        try:
            base_config = self._configs[base_name].copy()
            
            # Remove internal metadata
            for key in list(base_config.keys()):
                if key.startswith('_'):
                    del base_config[key]
                    
            # Apply updates
            for param, value in updates.items():
                base_config[param] = value
                
            # Register derived configuration
            self.register_config(new_name, base_config, description)
            
            self._logger.info(f"Created derived configuration '{new_name}' from '{base_name}'")
        except Exception as e:
            if isinstance(e, (ConfigurationError, InvalidConfigurationError)):
                raise e
            raise ConfigurationError(f"Failed to derive configuration: {str(e)}")
    
    def get_config_description(self, name: str) -> str:
        """
        [Method intent]
        Get the description of a configuration.
        
        [Design principles]
        - Provide access to configuration metadata
        - Support informed configuration selection
        
        [Implementation details]
        - Checks if configuration exists
        - Returns the description or a default message
        
        Args:
            name: Name of the configuration
            
        Returns:
            str: Configuration description
            
        Raises:
            ConfigurationError: If configuration does not exist
        """
        # Check if configuration exists
        if name not in self._configs:
            raise ConfigurationError(f"Configuration '{name}' does not exist")
            
        # Return description or default
        return self._configs[name].get("_description", "No description available")
    
    def merge_configs(self, configs: List[str], prefer_later: bool = True) -> Dict[str, Any]:
        """
        [Method intent]
        Merge multiple configurations into a single parameter set.
        
        [Design principles]
        - Support composite configurations
        - Handle parameter conflicts
        - Maintain configuration validity
        
        [Implementation details]
        - Gets all specified configurations
        - Merges them with configurable conflict resolution
        - Validates the resulting merged configuration
        
        Args:
            configs: List of configuration names to merge
            prefer_later: Whether later configs in the list should override earlier ones
            
        Returns:
            Dict[str, Any]: Merged configuration parameters
            
        Raises:
            ConfigurationError: If merge fails
        """
        if not configs:
            raise ConfigurationError("No configurations specified for merge")
            
        result = {}
        
        # Process configurations
        for name in configs:
            # Get configuration
            if name not in self._configs:
                raise ConfigurationError(f"Configuration '{name}' does not exist")
                
            config = self._configs[name].copy()
            
            # Remove internal metadata
            for key in list(config.keys()):
                if key.startswith('_'):
                    del config[key]
            
            if prefer_later:
                # Later configs override earlier ones
                result.update(config)
            else:
                # Earlier configs take precedence
                for param, value in config.items():
                    if param not in result:
                        result[param] = value
        
        # Validate merged configuration
        try:
            self._validate_config(result)
        except InvalidConfigurationError as e:
            raise ConfigurationError(f"Merged configuration is invalid: {str(e)}")
            
        return result
```

## LangChainConfigAdapter Implementation

Create an adapter for integrating with LangChain configuration formats:

```python
from typing import Dict, Any, List, Optional, Union

class LangChainConfigAdapter:
    """
    [Class intent]
    Adapts the ConfigRegistry to work with LangChain configuration formats.
    This enables seamless integration between the custom ConfigRegistry and
    the LangChain configuration system.
    
    [Design principles]
    - Bridge between ConfigRegistry and LangChain
    - Support for LangChain model configuration
    - Maintain configuration consistency
    
    [Implementation details]
    - Uses ConfigRegistry for underlying configuration management
    - Converts configurations between formats
    - Maps parameter names between systems
    """
    
    # Mapping from ConfigRegistry parameters to LangChain parameters
    PARAM_MAPPING = {
        ConfigRegistry.PARAM_TEMPERATURE: "temperature",
        ConfigRegistry.PARAM_MAX_TOKENS: "max_tokens",
        ConfigRegistry.PARAM_TOP_P: "top_p",
        ConfigRegistry.PARAM_TOP_K: "top_k",
        ConfigRegistry.PARAM_PRESENCE_PENALTY: "presence_penalty",
        ConfigRegistry.PARAM_FREQUENCY_PENALTY: "frequency_penalty",
        ConfigRegistry.PARAM_STOP_SEQUENCES: "stop",
        ConfigRegistry.PARAM_TIMEOUT: "request_timeout",
        ConfigRegistry.PARAM_STREAM: "streaming",
        ConfigRegistry.PARAM_RESPONSE_FORMAT: "response_format"
    }
    
    def __init__(self, config_registry):
        """
        [Method intent]
        Initialize the adapter with a ConfigRegistry instance.
        
        [Design principles]
        - Composition over inheritance
        - Delegate configuration management to ConfigRegistry
        
        [Implementation details]
        - Stores reference to ConfigRegistry
        
        Args:
            config_registry: ConfigRegistry instance
        """
        self.config_registry = config_registry
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def to_langchain_config(self, config_name: str) -> Dict[str, Any]:
        """
        [Method intent]
        Convert a ConfigRegistry configuration to LangChain format.
        
        [Design principles]
        - Support for LangChain integration
        - Parameter name mapping
        - Configuration format consistency
        
        [Implementation details]
        - Gets configuration from registry
        - Maps parameter names to LangChain format
        - Handles special cases for specific parameters
        
        Args:
            config_name: Name of the configuration to convert
            
        Returns:
            Dict[str, Any]: Configuration in LangChain format
            
        Raises:
            ConfigurationError: If conversion fails
        """
        try:
            # Get configuration from registry
            config = self.config_registry.get_config(config_name)
            
            # Map to LangChain format
            result = {}
            for reg_param, lc_param in self.PARAM_MAPPING.items():
                if reg_param in config:
                    result[lc_param] = config[reg_param]
            
            return result
        except Exception as e:
            self._logger.error(f"Failed to convert configuration to LangChain format: {str(e)}")
            raise
    
    def from_langchain_config(
        self, 
        lc_config: Dict[str, Any], 
        name: str, 
        description: Optional[str] = None
    ) -> None:
        """
        [Method intent]
        Convert a LangChain configuration to ConfigRegistry format and register it.
        
        [Design principles]
        - Support bidirectional integration
        - Parameter name reverse mapping
        - Configuration validation
        
        [Implementation details]
        - Maps LangChain parameter names to registry format
        - Registers the converted configuration
        - Handles special cases for specific parameters
        
        Args:
            lc_config: Configuration in LangChain format
            name: Name to register the configuration under
            description: Optional description for the configuration
            
        Raises:
            ConfigurationError: If conversion or registration fails
        """
        try:
            # Map from LangChain format
            config = {}
            reverse_mapping = {lc: reg for reg, lc in self.PARAM_MAPPING.items()}
            
            for lc_param, value in lc_config.items():
                if lc_param in reverse_mapping:
                    config[reverse_mapping[lc_param]] = value
            
            # Register with the registry
            self.config_registry.register_config(name, config, description)
        except Exception as e:
            self._logger.error(f"Failed to convert LangChain configuration: {str(e)}")
            raise
    
    def get_langchain_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        [Method intent]
        Get all configurations in LangChain format.
        
        [Design principles]
        - Support bulk conversion
        - Maintain configuration organization
        
        [Implementation details]
        - Gets all configurations from registry
        - Converts each to LangChain format
        - Maintains configuration names as keys
        
        Returns:
            Dict[str, Dict[str, Any]]: Configurations in LangChain format
        """
        result = {}
        
        for config_summary in self.config_registry.list_configs():
            name = config_summary["name"]
            result[name] = self.to_langchain_config(name)
        
        return result
```

## ModelConfigValidator Implementation

Create a validator for model-specific configuration requirements:

```python
class ModelConfigValidator:
    """
    [Class intent]
    Validates configurations against model-specific requirements.
    Different LLM models have different parameter ranges and supported
    features, requiring validation beyond generic parameter types.
    
    [Design principles]
    - Model-specific validation rules
    - Clear error messages
    - Support for different model families
    
    [Implementation details]
    - Maintains validation rules by model family
    - Provides comprehensive validation
    - Handles special parameters by model
    """
    
    # Model families
    FAMILY_BEDROCK_ANTHROPIC = "bedrock_anthropic"
    FAMILY_BEDROCK_AMAZON = "bedrock_amazon"
    
    def __init__(self):
        """
        [Method intent]
        Initialize the validator with model-specific rules.
        
        [Design principles]
        - Organize validation by model family
        - Clear rule definition
        
        [Implementation details]
        - Defines model-specific validation rules
        - Sets up model family groupings
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> None:
        """
        [Method intent]
        Initialize model-specific validation rules.
        
        [Design principles]
        - Model-specific parameter constraints
        - Organized by parameter and model family
        
        [Implementation details]
        - Defines validation functions for parameters by model family
        - Sets model-specific allowed ranges and types
        """
        self._validation_rules = {
            self.FAMILY_BEDROCK_ANTHROPIC: {
                ConfigRegistry.PARAM_TEMPERATURE: lambda v: 0.0 <= v <= 1.0,
                ConfigRegistry.PARAM_MAX_TOKENS: lambda v: isinstance(v, int) and 0 < v <= 4096,
                ConfigRegistry.PARAM_TOP_P: lambda v: 0.0 <= v <= 1.0,
                ConfigRegistry.PARAM_STOP_SEQUENCES: lambda v: isinstance(v, list) and len(v) <= 4,
                # Anthropic models don't support presence/frequency penalty
                ConfigRegistry.PARAM_PRESENCE_PENALTY: None,
                ConfigRegistry.PARAM_FREQUENCY_PENALTY: None,
            },
            self.FAMILY_BEDROCK_AMAZON: {
                ConfigRegistry.PARAM_TEMPERATURE: lambda v: 0.0 <= v <= 1.0,
                ConfigRegistry.PARAM_MAX_TOKENS: lambda v: isinstance(v, int) and 0 < v <= 2048,
                ConfigRegistry.PARAM_TOP_P: lambda v: 0.0 <= v <= 1.0,
                ConfigRegistry.PARAM_TOP_K: lambda v: isinstance(v, int) and v > 0,
            }
        }
        
        # Parameters required by model family
        self._required_params = {
            self.FAMILY_BEDROCK_ANTHROPIC: [
                ConfigRegistry.PARAM_TEMPERATURE,
                ConfigRegistry.PARAM_MAX_TOKENS
            ],
            self.FAMILY_BEDROCK_AMAZON: [
                ConfigRegistry.PARAM_TEMPERATURE,
                ConfigRegistry.PARAM_MAX_TOKENS,
                ConfigRegistry.PARAM_TOP_P
            ]
        }
        
        # Parameters not supported by model family
        self._unsupported_params = {
            self.FAMILY_BEDROCK_ANTHROPIC: [
                ConfigRegistry.PARAM_TOP_K,
                ConfigRegistry.PARAM_PRESENCE_PENALTY,
                ConfigRegistry.PARAM_FREQUENCY_PENALTY
            ],
            self.FAMILY_BEDROCK_AMAZON: [
                ConfigRegistry.PARAM_PRESENCE_PENALTY,
                ConfigRegistry.PARAM_FREQUENCY_PENALTY
            ]
        }
    
    def validate_for_model(self, config: Dict[str, Any], model_family: str) -> List[str]:
        """
        [Method intent]
        Validate a configuration for a specific model family.
        
        [Design principles]
        - Comprehensive validation for a model
        - Accumulate all issues rather than failing on first
        - Clear error messages
        
        [Implementation details]
        - Checks for required parameters
        - Validates parameter values against model constraints
        - Warns about unsupported parameters
        
        Args:
            config: Configuration to validate
            model_family: Model family to validate against
            
        Returns:
            List[str]: List of validation issues (empty if valid)
        """
        if model_family not in self._validation_rules:
            return [f"Unknown model family: {model_family}"]
            
        issues = []
        
        # Check required parameters
        for param in self._required_params.get(model_family, []):
            if param not in config:
                issues.append(f"Missing required parameter for {model_family}: {param}")
        
        # Check parameter values
        for param, value in config.items():
            # Skip internal parameters
            if param.startswith('_'):
                continue
                
            # Check if parameter is supported
            if param in self._unsupported_params.get(model_family, []):
                issues.append(f"Parameter '{param}' is not supported by {model_family}")
                continue
                
            # Validate parameter value
            rule = self._validation_rules.get(model_family, {}).get(param)
            if rule is not None and not rule(value):
                issues.append(f"Invalid value for parameter '{param}' for {model_family}: {value}")
        
        return issues
    
    def get_supported_params(self, model_family: str) -> List[str]:
        """
        [Method intent]
        Get a list of parameters supported by a model family.
        
        [Design principles]
        - Support for configuration guidance
        - Clear parameter support information
        
        [Implementation details]
        - Returns list of supported parameters for a model family
        - Excludes unsupported parameters
        
        Args:
            model_family: Model family to check
            
        Returns:
            List[str]: List of supported parameter names
            
        Raises:
            ConfigurationError: If model family is unknown
        """
        if model_family not in self._validation_rules:
            raise ConfigurationError(f"Unknown model family: {model_family}")
            
        # Get all parameters with rules
        supported = []
        for param, rule in self._validation_rules[model_family].items():
            if rule is not None:
                supported.append(param)
                
        return supported
    
    def get_required_params(self, model_family: str) -> List[str]:
        """
        [Method intent]
        Get a list of parameters required by a model family.
        
        [Design principles]
        - Support for configuration guidance
        - Clear parameter requirements
        
        [Implementation details]
        - Returns list of required parameters for a model family
        
        Args:
            model_family: Model family to check
            
        Returns:
            List[str]: List of required parameter names
            
        Raises:
            ConfigurationError: If model family is unknown
        """
        if model_family not in self._required_params:
            raise ConfigurationError(f"Unknown model family: {model_family}")
            
        return self._required_params[model_family].copy()
```

## Implementation Steps

1. **Core Configuration Registry**
   - Implement `ConfigRegistry` class in `src/dbp/llm/common/config_registry.py`
   - Create built-in configurations for common use cases
   - Implement configuration validation
   - Build configuration management functions

2. **LangChain Integration**
   - Create `LangChainConfigAdapter` for bidirectional compatibility
   - Implement parameter mapping between systems
   - Build conversion functions

3. **Model-Specific Validation**
   - Implement `ModelConfigValidator` for model-specific constraints
   - Define validation rules for different model families
   - Create utility functions for parameter support

4. **Testing and Utility Functions**
   - Add methods for configuration discovery
   - Implement configuration merging and derivation
   - Create test helpers for validation
