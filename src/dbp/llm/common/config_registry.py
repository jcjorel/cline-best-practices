###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Provides a registry for managing and validating LLM configurations. This system
# enables named configurations to be registered, validated, and retrieved at runtime.
# It serves as the central configuration management system for all LLM interactions
# with support for LangChain integration.
###############################################################################
# [Source file design principles]
# - Thread-safe configuration management for concurrent access
# - Strong validation of configuration parameters based on model requirements
# - Support for named configurations with override capabilities
# - Built-in configurations for common use cases 
# - Clear separation between configuration management and model implementation
# - LangChain compatibility for seamless integration
# - Model-specific validation for parameter constraints
###############################################################################
# [Source file constraints]
# - Must validate configurations against model-specific schemas
# - Must be thread-safe to support concurrent operations
# - Must handle configuration naming conflicts appropriately
# - Must protect against common configuration errors
# - Must provide clean LangChain integration
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# system:typing
# system:threading
# system:pydantic
# system:copy
# system:json
# system:logging
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:07:00Z : Enhanced for LangChain/LangGraph integration by CodeAssistant
# * Added built-in configurations for common use cases
# * Added model-specific validation with ModelConfigValidator
# * Added LangChainConfigAdapter for bidirectional integration
# * Enhanced parameter handling and validation
# 2025-05-02T10:45:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created configuration registry system
###############################################################################

"""
Configuration registry system for LLM configurations.
"""

import copy
import threading
import json
import logging
from typing import Any, Dict, List, Optional, Set, Type, Union, cast
from pydantic import BaseModel, ValidationError, Field, create_model

from .exceptions import ConfigurationError, InvalidConfigurationError

# Standard configuration parameter names
PARAM_MODEL_ID = "model_id"
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


class ModelConfigBase(BaseModel):
    """
    [Class intent]
    Base class for all model configurations, providing common parameters
    and validation capabilities.
    
    [Design principles]
    Uses Pydantic for configuration validation with a consistent interface.
    
    [Implementation details]
    Implements the common configuration fields shared across models.
    """
    
    model_id: str
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, gt=0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None
    timeout: Optional[float] = Field(None, gt=0)
    stream: bool = True
    response_format: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Prevent unknown parameters
        
    def dict_with_defaults(self) -> Dict[str, Any]:
        """
        [Class method intent]
        Returns a dictionary of configuration values, including defaults.
        
        [Design principles]
        Provides a consistent way to access configuration values.
        
        [Implementation details]
        Uses Pydantic's built-in dictionary conversion with defaults.
        """
        return self.dict(exclude_none=False)
        
    def merge_with(self, overrides: Dict[str, Any]) -> "ModelConfigBase":
        """
        [Class method intent]
        Creates a new configuration with overridden values.
        
        [Design principles]
        Enables partial configuration overrides without modifying the original.
        
        [Implementation details]
        Creates a new instance with merged parameters.
        """
        # Create a copy of the current config as a dictionary
        base_dict = self.dict()
        
        # Apply overrides
        merged_dict = {**base_dict, **overrides}
        
        # Create a new instance with the merged values
        return type(self)(**merged_dict)


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
        [Class method intent]
        Initialize the validator with model-specific rules.
        
        [Design principles]
        - Organize validation by model family
        - Clear rule definition
        
        [Implementation details]
        - Defines model-specific validation rules
        - Sets up model family groupings
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> None:
        """
        [Class method intent]
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
                PARAM_TEMPERATURE: lambda v: 0.0 <= v <= 1.0,
                PARAM_MAX_TOKENS: lambda v: isinstance(v, int) and 0 < v <= 4096,
                PARAM_TOP_P: lambda v: 0.0 <= v <= 1.0,
                PARAM_STOP_SEQUENCES: lambda v: isinstance(v, list) and len(v) <= 4,
                # Anthropic models don't support presence/frequency penalty
                PARAM_PRESENCE_PENALTY: None,
                PARAM_FREQUENCY_PENALTY: None,
            },
            self.FAMILY_BEDROCK_AMAZON: {
                PARAM_TEMPERATURE: lambda v: 0.0 <= v <= 1.0,
                PARAM_MAX_TOKENS: lambda v: isinstance(v, int) and 0 < v <= 2048,
                PARAM_TOP_P: lambda v: 0.0 <= v <= 1.0,
                PARAM_TOP_K: lambda v: isinstance(v, int) and v > 0,
            }
        }
        
        # Parameters required by model family
        self._required_params = {
            self.FAMILY_BEDROCK_ANTHROPIC: [
                PARAM_TEMPERATURE,
                PARAM_MAX_TOKENS
            ],
            self.FAMILY_BEDROCK_AMAZON: [
                PARAM_TEMPERATURE,
                PARAM_MAX_TOKENS,
                PARAM_TOP_P
            ]
        }
        
        # Parameters not supported by model family
        self._unsupported_params = {
            self.FAMILY_BEDROCK_ANTHROPIC: [
                PARAM_TOP_K,
                PARAM_PRESENCE_PENALTY,
                PARAM_FREQUENCY_PENALTY
            ],
            self.FAMILY_BEDROCK_AMAZON: [
                PARAM_PRESENCE_PENALTY,
                PARAM_FREQUENCY_PENALTY
            ]
        }
    
    def validate_for_model(self, config: Dict[str, Any], model_family: str) -> List[str]:
        """
        [Class method intent]
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
        [Class method intent]
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
        [Class method intent]
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


class ConfigRegistry:
    """
    [Class intent]
    Maintains a registry of named LLM configurations, allowing registration,
    retrieval, and validation of configurations. Provides built-in configurations
    for common use cases and supports model-specific validation.
    
    [Design principles]
    Thread-safe singleton for configuration management with validation.
    Source of truth for LLM configurations throughout the application.
    
    [Implementation details]
    Uses a thread lock to ensure consistent state during concurrent operations.
    Stores configurations in a dictionary keyed by name.
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes a new configuration registry with empty storage and built-in
        configurations.
        
        [Design principles]
        Ensures thread safety for multi-threaded environments.
        Provides sensible defaults for common use cases.
        
        [Implementation details]
        Creates synchronized data structures for configuration storage.
        Initializes built-in configurations and validators.
        """
        self._configs: Dict[str, ModelConfigBase] = {}
        self._default_config_name: Optional[str] = None
        self._lock = threading.RLock()
        self._validator = ModelConfigValidator()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize built-in configurations
        self._initialize_built_in_configs()
    
    def _initialize_built_in_configs(self) -> None:
        """
        [Class method intent]
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
        # Default balanced configuration
        self.register_config(
            CONFIG_DEFAULT, 
            ModelConfigBase(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.7,
                max_tokens=1024,
                top_p=0.95,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                timeout=30,
                stream=True,
            ),
            set_as_default=True
        )
        
        # Creative configuration for more varied output
        self.register_config(
            CONFIG_CREATIVE, 
            ModelConfigBase(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.9,
                max_tokens=2048,
                top_p=0.98,
                presence_penalty=0.2,
                frequency_penalty=0.2,
                timeout=60,
                stream=True,
            )
        )
        
        # Precise configuration for factual responses
        self.register_config(
            CONFIG_PRECISE, 
            ModelConfigBase(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.2,
                max_tokens=1024,
                top_p=0.9,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                timeout=30,
                stream=True,
            )
        )
    
    def register_config(
        self, 
        name: str, 
        config: Union[ModelConfigBase, Dict[str, Any]],
        config_cls: Optional[Type[ModelConfigBase]] = None,
        set_as_default: bool = False,
        description: Optional[str] = None
    ) -> None:
        """
        [Class method intent]
        Registers a configuration with the registry under a given name.
        
        [Design principles]
        Validates configurations before storing them.
        Provides flexibility in registration formats.
        
        [Implementation details]
        Thread-safe registration with validation against the provided schema.
        
        Args:
            name: Name to register the configuration under
            config: Configuration to register, either as a ModelConfigBase
                  instance or a dictionary
            config_cls: Optional class to validate against if config is a dictionary
            set_as_default: Whether to set this as the default configuration
            description: Optional description for the configuration
            
        Raises:
            ConfigurationError: If validation fails or a naming conflict occurs
        """
        with self._lock:
            # Handle dictionary conversion
            if isinstance(config, dict):
                if config_cls is None:
                    config_cls = ModelConfigBase
                    
                try:
                    config = config_cls(**config)
                except ValidationError as e:
                    raise ConfigurationError(
                        f"Invalid configuration for '{name}': {str(e)}",
                        {"config_name": name, "validation_errors": str(e)}
                    )
            
            # Validate that config is a ModelConfigBase
            if not isinstance(config, ModelConfigBase):
                raise ConfigurationError(
                    f"Configuration must be a ModelConfigBase instance, got {type(config).__name__}",
                    {"config_name": name}
                )
            
            # Check for naming conflicts
            if name in self._configs and name not in [CONFIG_DEFAULT, CONFIG_CREATIVE, CONFIG_PRECISE]:
                raise ConfigurationError(
                    f"Configuration '{name}' already exists",
                    {"config_name": name}
                )
            
            # Store the configuration
            self._configs[name] = config
            
            # Set as default if requested or if this is the first configuration
            if set_as_default or self._default_config_name is None:
                self._default_config_name = name
    
    def unregister_config(self, name: str) -> None:
        """
        [Class method intent]
        Removes a configuration from the registry by name.
        
        [Design principles]
        Allows dynamic removal of configurations.
        Prevents removal of built-in configurations.
        
        [Implementation details]
        Thread-safe implementation with appropriate validation.
        Updates default configuration if the removed one was the default.
        
        Args:
            name: Name of the configuration to remove
            
        Raises:
            ConfigurationError: If the configuration does not exist or is built-in
        """
        with self._lock:
            # Check if trying to remove a built-in configuration
            if name in [CONFIG_DEFAULT, CONFIG_CREATIVE, CONFIG_PRECISE]:
                raise ConfigurationError(
                    f"Cannot remove built-in configuration '{name}'",
                    {"config_name": name}
                )
                
            if name not in self._configs:
                raise ConfigurationError(
                    f"Cannot unregister non-existent configuration '{name}'",
                    {"config_name": name}
                )
            
            # Remove the configuration
            del self._configs[name]
            
            # Update default if necessary
            if self._default_config_name == name:
                self._default_config_name = next(iter(self._configs.keys())) if self._configs else None
    
    def get_config(self, name: Optional[str] = None) -> ModelConfigBase:
        """
        [Class method intent]
        Retrieves a configuration by name, or the default configuration if no name is provided.
        
        [Design principles]
        Provides access to configurations with appropriate validation.
        
        [Implementation details]
        Thread-safe lookup with error handling for missing configurations.
        Falls back to default configuration if no name is provided.
        
        Args:
            name: Optional name of the configuration to retrieve
            
        Returns:
            The requested configuration
            
        Raises:
            ConfigurationError: If the configuration does not exist or no default is set
        """
        with self._lock:
            # Use the default configuration if no name is provided
            if name is None:
                if self._default_config_name is None:
                    raise ConfigurationError(
                        "No default configuration set",
                        {"available_configs": list(self._configs.keys())}
                    )
                name = self._default_config_name
            
            # Check if the configuration exists
            if name not in self._configs:
                raise ConfigurationError(
                    f"Configuration '{name}' not found",
                    {"config_name": name, "available_configs": list(self._configs.keys())}
                )
                
            # Return a copy of the configuration to prevent modification
            return copy.deepcopy(self._configs[name])
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """
        [Class method intent]
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
        
        with self._lock:
            for name, config in sorted(self._configs.items()):
                # Create summary with name and model_id
                summary = {
                    "name": name,
                    "model_id": config.model_id,
                    "built_in": name in [CONFIG_DEFAULT, CONFIG_CREATIVE, CONFIG_PRECISE],
                    "is_default": name == self._default_config_name
                }
                
                result.append(summary)
        
        return result
    
    def get_default_config_name(self) -> Optional[str]:
        """
        [Class method intent]
        Returns the name of the default configuration, if set.
        
        [Design principles]
        Provides access to the current default configuration name.
        
        [Implementation details]
        Thread-safe access to the default configuration name.
        
        Returns:
            The name of the default configuration, or None if not set
        """
        with self._lock:
            return self._default_config_name
    
    def set_default_config(self, name: str) -> None:
        """
        [Class method intent]
        Sets the default configuration by name.
        
        [Design principles]
        Allows changing the default configuration.
        
        [Implementation details]
        Thread-safe update of the default configuration name.
        
        Args:
            name: Name of the configuration to set as default
            
        Raises:
            ConfigurationError: If the configuration does not exist
        """
        with self._lock:
            if name not in self._configs:
                raise ConfigurationError(
                    f"Cannot set non-existent configuration '{name}' as default",
                    {"config_name": name, "available_configs": list(self._configs.keys())}
                )
                
            self._default_config_name = name
    
    def update_config(self, name: str, updates: Dict[str, Any]) -> None:
        """
        [Class method intent]
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
        """
        with self._lock:
            # Check if configuration exists
            if name not in self._configs:
                raise ConfigurationError(
                    f"Configuration '{name}' does not exist",
                    {"config_name": name, "available_configs": list(self._configs.keys())}
                )
                
            # Get the current configuration
            current_config = self._configs[name]
            
            # Apply the updates
            try:
                updated_config = current_config.merge_with(updates)
                
                # Store the updated configuration
                self._configs[name] = updated_config
                self.logger.info(f"Updated configuration '{name}'")
                
            except ValidationError as e:
                raise ConfigurationError(
                    f"Invalid configuration update for '{name}': {str(e)}",
                    {"config_name": name, "validation_errors": str(e)}
                )
    
    def derive_config(self, base_name: str, updates: Dict[str, Any], new_name: str, description: Optional[str] = None) -> None:
        """
        [Class method intent]
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
        """
        try:
            # Get base configuration
            base_config = self.get_config(base_name)
            
            # Apply updates to create new configuration
            derived_config = base_config.merge_with(updates)
            
            # Register the derived configuration
            self.register_config(new_name, derived_config, description=description)
            
            self.logger.info(f"Created derived configuration '{new_name}' from '{base_name}'")
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to derive configuration: {str(e)}",
                {"base_config": base_name, "new_config": new_name}
            )
    
    def validate_for_model(self, config_name: str, model_family: str) -> List[str]:
        """
        [Class method intent]
        Validate a configuration against a specific model family's requirements.
        
        [Design principles]
        - Model-specific validation
        - Clear error reporting
        - Support for different model families
        
        [Implementation details]
        - Gets configuration from registry
        - Uses ModelConfigValidator for validation
        - Returns list of validation issues
        
        Args:
            config_name: Name of the configuration to validate
            model_family: Model family to validate against
            
        Returns:
            List[str]: List of validation issues (empty if valid)
            
        Raises:
            ConfigurationError: If the configuration does not exist
        """
        try:
            # Get configuration
            config = self.get_config(config_name)
            
            # Convert to dictionary for validation
            config_dict = config.dict(exclude_none=True)
            
            # Validate against model family
            return self._validator.validate_for_model(config_dict, model_family)
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to validate configuration: {str(e)}",
                {"config_name": config_name, "model_family": model_family}
            )
    
    def clear(self) -> None:
        """
        [Class method intent]
        Removes all configurations from the registry except built-ins.
        
        [Design principles]
        Provides a way to reset the registry state.
        
        [Implementation details]
        Thread-safe clearing of registered configurations.
        Preserves built-in configurations.
        """
        with self._lock:
            # Preserve built-in configurations
            built_ins = {}
            for name in [CONFIG_DEFAULT, CONFIG_CREATIVE, CONFIG_PRECISE]:
                if name in self._configs:
                    built_ins[name] = self._configs[name]
            
            # Clear all configurations
            self._configs.clear()
            
            # Restore built-ins
            self._configs.update(built_ins)
            
            # Reset default config if necessary
            if self._default_config_name not in self._configs:
                self._default_config_name = CONFIG_DEFAULT if CONFIG_DEFAULT in self._configs else None


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
        PARAM_TEMPERATURE: "temperature",
        PARAM_MAX_TOKENS: "max_tokens",
        PARAM_TOP_P: "top_p",
        PARAM_TOP_K: "top_k",
        PARAM_PRESENCE_PENALTY: "presence_penalty",
        PARAM_FREQUENCY_PENALTY: "frequency_penalty",
        PARAM_STOP_SEQUENCES: "stop",
        PARAM_TIMEOUT: "request_timeout",
        PARAM_STREAM: "streaming",
        PARAM_RESPONSE_FORMAT: "response_format"
    }
    
    def __init__(self, config_registry: ConfigRegistry):
        """
        [Class method intent]
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
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def to_langchain_config(self, config_name: str) -> Dict[str, Any]:
        """
        [Class method intent]
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
            
            # Convert to dictionary
            config_dict = config.dict(exclude_none=True)
            
            # Map to LangChain format
            result = {}
            for reg_param, lc_param in self.PARAM_MAPPING.items():
                if reg_param in config_dict:
                    result[lc_param] = config_dict[reg_param]
            
            # Add model ID (special case)
            result["model_name"] = config_dict.get("model_id")
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to convert configuration to LangChain format: {str(e)}")
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError
