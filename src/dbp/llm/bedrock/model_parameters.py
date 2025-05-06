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
# Defines parameter models for AWS Bedrock LLM models using Pydantic for validation,
# serialization, and documentation. Provides a unified interface for working with
# model-specific parameters while maintaining strong typing and validation.
###############################################################################
# [Source file design principles]
# - Single source of truth for Bedrock parameter definitions
# - Self-registration of model-specific parameter classes
# - Clean accessors for parameter format conversion
# - Minimize consumer-side custom logic
# - Consistent structure across all Bedrock model types
# - Strong validation for all parameter values
# - Support for parameter profiles with applicability rules
###############################################################################
# [Source file constraints]
# - Requires Pydantic for model definitions
# - Must maintain compatibility with LangChain parameter formats
# - Parameter names must match those expected by the Bedrock API
# - Parameter ranges must reflect AWS Bedrock documentation
# - Must support model-specific parameter constraints
###############################################################################
# [Dependencies]
# system:logging
# system:typing
# system:pydantic
###############################################################################
# [GenAI tool change history]
# 2025-05-06T18:37:00Z : Added explicit parameter validation capabilities by CodeAssistant
# * Added validate_config method for validating parameter values against constraints
# * Updated update_from_args to validate parameters before applying them
# * Enhanced _apply_profile to validate profile parameter overrides
# * Improved error reporting with detailed error messages for validation failures
# 2025-05-06T11:22:15Z : Made get_model_id_constraint non-abstract by CodeAssistant
# * Changed get_model_id_constraint from abstract to concrete implementation
# * Implemented DRY design by using Config.supported_models directly
# * Added proper error handling when supported_models is missing
# * Eliminated redundancy in model ID constraint definitions
# 2025-05-06T10:33:00Z : Fixed field info access in add_arguments_to_parser by CodeAssistant
# * Updated method to correctly access Field constraints without using field_info attribute
# * Added direct access to constraint attributes rather than nesting
# * Improved error handling when parsing field constraints
# 2025-05-06T09:35:00Z : Fixed type handling for CLI arguments by CodeAssistant
# * Updated add_arguments_to_parser to use annotations instead of field type
# * Added explicit type detection for parameters
# * Fixed error handling to prevent attribute access errors
###############################################################################

"""
Parameters definition for AWS Bedrock LLM models with Pydantic validation.
"""

import logging
import inspect
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, ClassVar, Optional, List, Union, get_type_hints, Tuple
from pydantic import BaseModel, Field, validator, ValidationError

class ModelParameters(BaseModel, ABC):
    """
    [Class intent]
    Abstract base class for all Bedrock model parameters, providing common parameter definitions,
    validation rules, and utility methods for parameter handling across all Bedrock model types.
    
    [Design principles]
    - Single source of truth for parameter definitions
    - Self-registration of model-specific parameter classes
    - Clean accessors for parameter conversion
    - Profile-based parameter configuration with applicability rules
    - Clear precedence rules: applicable_params (when specified) takes complete precedence over not_applicable_params
    
    [Implementation details]
    - Uses Pydantic for validation and schema management
    - Registry pattern for model-specific parameter lookup
    - Factory method for creating appropriate parameter instance
    - Profile system for parameter applicability and defaults
    - Abstract base class preventing direct instantiation
    
    # Parameter Definition Guide
    
    ## Basic Parameter Declaration
    
    Parameters are defined as class attributes with type annotations and Field() constraints:
    
    ```
    temperature: float = Field(
        default=0.7,       # Default value if not specified  
        ge=0.0,            # Minimum value (>=)
        le=1.0,            # Maximum value (<=)
        description="Controls randomness in the output."
    )
    ```
    
    ## Extending in Subclasses
    
    Derived classes can:
    1. Override existing parameters with model-specific constraints
    2. Add new parameters specific to that model type
    3. Inherit parameters without changes
    
    Example:
    ```
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
    
    # Profile System Documentation
    
    ## Profile Definition
    
    Profiles are defined in the `_profiles` class variable. Every model MUST have at least
    a "default" profile. Each profile has three configuration sections:
    
    1. `applicable_params`: Controls which parameters are allowed in this profile
    2. `not_applicable_params`: Controls which parameters are excluded in this profile
    3. `param_overrides`: Defines profile-specific default values
    
    ## Applicability Rules
    
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
    
    @classmethod
    @abstractmethod
    def get_model_version(cls, model_id: str) -> str:
        """
        [Method intent]
        Retrieve the model version based on its model_id (e.g., 3.5 for Claude, 1.0 for Nova).
        
        [Design principles]
        - Consistent version format across model types
        - Model-specific parsing logic
        - Standardized return format
        
        [Implementation details]
        - Must be implemented by each concrete parameter class
        - Parses model_id string according to model-specific format
        - Returns version as a string in a consistent format (e.g. "1.0", "3.5")
        
        Args:
            model_id: The model ID to extract version from
            
        Returns:
            str: Version string
        """
        pass
        
    @classmethod
    @abstractmethod
    def get_model_variant(cls, model_id: str) -> str:
        """
        [Method intent]
        Retrieve the model variant based on its model_id (e.g., "Sonnet" for Claude, "Lite" for Nova).
        
        [Design principles]
        - Consistent variant naming across model types
        - Model-specific parsing logic
        - Proper capitalization and formatting
        
        [Implementation details]
        - Must be implemented by each concrete parameter class
        - Parses model_id string according to model-specific format
        - Returns variant as a properly formatted string
        
        Args:
            model_id: The model ID to extract variant from
            
        Returns:
            str: Variant string
        """
        pass

    # Class registry to keep track of all parameter models
    _registry: ClassVar[Dict[str, Type["ModelParameters"]]] = {}
    
    # Default profile configuration - all parameters allowed
    _profiles: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {
            "applicable_params": None,  # None means all are potentially applicable
            "not_applicable_params": [],  # Empty list means no exclusions
            "param_overrides": {}  # No parameter overrides by default
        }
    }
    
    # Track current profile
    _current_profile: str = "default"
    
    def __init_subclass__(cls, **kwargs):
        """
        [Method intent]
        Register all subclasses for factory method use and ensure they have valid profiles.
        
        [Design principles]
        - Automatic registration of model-specific parameter classes
        - Enforce existence of default profile
        - Support profile inheritance
        
        [Implementation details]
        - Uses Python's __init_subclass__ feature for automatic registration
        - Registers each supported model ID to the corresponding parameter class
        - Ensures default profile exists in every class
        
        Args:
            **kwargs: Keyword arguments passed to the parent __init_subclass__ method
        """
        super().__init_subclass__(**kwargs)
        
        # Register models
        if hasattr(cls, "Config") and hasattr(cls.Config, "supported_models"):
            for model_id in cls.Config.supported_models:
                ModelParameters._registry[model_id] = cls
        
        # Handle profile inheritance
        parent_profiles = getattr(cls.__base__, "_profiles", {})
        if not hasattr(cls, "_profiles"):
            # If class doesn't define _profiles, inherit from parent
            cls._profiles = dict(parent_profiles)
        else:
            # If class has _profiles but no default, inherit default from parent
            if "default" not in cls._profiles and "default" in parent_profiles:
                cls._profiles["default"] = dict(parent_profiles["default"])
        
        # Ensure default profile exists
        if "default" not in cls._profiles:
            raise ValueError(f"Class {cls.__name__} must have a 'default' profile")
    
    @classmethod
    def for_model(cls, model_id: str) -> "ModelParameters":
        """
        [Method intent]
        Factory method to create appropriate parameter model instance for a given model ID.
        
        [Design principles]
        - Automatic parameter class selection
        - Fallback to base parameters for unknown models
        - Enforce default profile existence
        
        [Implementation details]
        - Matches model ID against registered model prefixes
        - Returns new instance of appropriate parameter class
        - Uses NovaParameters as fallback for unknown models (non-abstract)
        
        Args:
            model_id: The Bedrock model ID
            
        Returns:
            ModelParameters: Instance of appropriate parameter class
        """
        # First try exact match
        if model_id in cls._registry:
            param_cls = cls._registry[model_id]
            return param_cls()
            
        # Try prefix match
        for registered_id, param_cls in cls._registry.items():
            # Match model family prefix (before the first colon)
            if model_id.startswith(registered_id.split(':')[0]):
                return param_cls()
        
        # Default to a specific concrete implementation for unknown models
        logging.warning(f"No parameter model found for {model_id}, using default parameters")
        
        # Get a concrete non-abstract class for fallback (prefer Nova as it's simpler)
        fallback_classes = [
            # First check for standard concrete classes
            c for c in cls._registry.values() 
            if not getattr(c, "__abstractmethods__", set()) and c.__name__ == "NovaParameters"
        ]
        
        if fallback_classes:
            # Use first Nova class found
            return fallback_classes[0]()
            
        # If no Nova class, try any concrete class
        fallback_classes = [
            c for c in cls._registry.values() 
            if not getattr(c, "__abstractmethods__", set())
        ]
        
        if fallback_classes:
            # Use first concrete class
            return fallback_classes[0]()
            
        # If all classes are abstract (shouldn't happen), create a simple concrete class on the fly
        raise ValueError(f"No concrete parameter class found for model {model_id}")
    
    def _apply_profile(self, profile_name: str, validate_overrides: bool = True) -> None:
        """
        [Method intent]
        Apply a named profile to this parameter instance with validation of parameter overrides.
        
        [Design principles]
        - Safe profile application with fallback
        - Strong validation of profile parameter values
        - Clear error reporting for profile parameter validation failures
        - Proper parameter value overrides
        
        [Implementation details]
        - Falls back to "default" profile if requested profile doesn't exist
        - Validates parameter overrides from profile using Pydantic validation
        - Applies parameter overrides from profile
        - Updates current profile tracking
        
        Args:
            profile_name: Name of the profile to apply
            validate_overrides: If True, validate profile parameter overrides before applying
            
        Raises:
            ValueError: If profile doesn't exist or if parameter overrides fail validation
        """
        # If profile doesn't exist, fall back to default
        if profile_name not in self._profiles:
            logging.warning(f"Unknown profile: {profile_name}, falling back to 'default'")
            profile_name = "default"
        
        profile = self._profiles[profile_name]
        
        # Get parameter overrides from profile
        param_overrides = profile.get("param_overrides", {})
        
        # Validate parameter overrides if requested
        if validate_overrides and param_overrides:
            valid, errors = self.validate_config(param_overrides)
            if not valid:
                error_messages = [f"- {param}: {msg}" for param, msg in errors.items()]
                raise ValueError(
                    f"Invalid parameter values in profile '{profile_name}':\n" + 
                    "\n".join(error_messages)
                )
        
        # Update current profile
        self._current_profile = profile_name
        
        # Apply overrides from profile
        for param, value in param_overrides.items():
            if hasattr(self, param):
                setattr(self, param, value)
    
    def is_applicable(self, param_name: str) -> bool:
        """
        [Method intent]
        Check if parameter is applicable in current profile.
        
        [Design principles]
        - Clear applicability logic
        - Support for whitelist/blacklist approaches
        
        [Implementation details]
        - Uses applicability rules defined in class docstring
        - Checks against current profile configuration
        
        Args:
            param_name: Parameter name to check
            
        Returns:
            bool: True if parameter is applicable in current profile, False otherwise
        """
        profile = self._profiles[self._current_profile]
        
        # If we have explicit applicable_params, use that
        if profile.get("applicable_params") is not None:
            return param_name in profile["applicable_params"]
            
        # Otherwise check against not_applicable_params
        not_applicable = profile.get("not_applicable_params", [])
        if not_applicable is None:  # None means all params are not applicable
            return False
            
        return param_name not in not_applicable
    
    @classmethod
    def get_all_param_fields(cls) -> Dict[str, Any]:
        """
        [Method intent]
        Get all parameter fields from all registered parameter classes along with model-specific
        variant information.
        
        [Design principles]
        - Complete parameter discovery across all model types
        - Track model-specific parameter variants for CLI help and validation
        - Support clear display of model-specific parameter constraints
        
        [Implementation details]
        - Collects all unique parameter fields across all registered models
        - Separately tracks model-specific parameter variants for the same parameter name
        - Parameter variants represent different constraints for the same parameter in different models
          (e.g., max_tokens might have different maximum values in Claude vs Nova)
        - Returns a structure that contains both fields and their variants
        
        Parameter variants are used to:
        1. Display comprehensive help text showing different constraints per model
        2. Apply the correct validation based on the selected model
        3. Document parameter differences between model types
        
        Returns:
            Dictionary with:
            - 'fields': Dict mapping parameter names to their base field definitions
            - 'model_variants': Dict mapping parameter names to lists of model-specific variants
              Each variant has 'model_name' and 'field' keys
        """
        all_fields = {}
        model_variants = {}
        
        # Add base class fields first
        for field_name, field in cls.__fields__.items():
            all_fields[field_name] = field
            model_variants[field_name] = []
            
        # Add fields from registered classes
        for param_cls in set(cls._registry.values()):
            for field_name, field in param_cls.__fields__.items():
                if field_name in all_fields:
                    # If field already exists, just track as model variant
                    if field_name in param_cls.__annotations__:
                        # This is a true override, not just inheritance
                        model_name = getattr(param_cls.Config, 'model_name', 'Unknown')
                        model_variants[field_name].append({
                            'model_name': model_name,
                            'field': field
                        })
                else:
                    # New field, add it
                    all_fields[field_name] = field
                    model_variants[field_name] = []
        
        return {
            'fields': all_fields,
            'model_variants': model_variants
        }
    
    def to_model_kwargs(self) -> Dict[str, Any]:
        """
        [Method intent]
        Convert parameters to model_kwargs format for LangChain.
        
        [Design principles]
        - Clean conversion to LangChain format
        - Exclude undefined or None values
        - Respect parameter applicability rules
        
        [Implementation details]
        - Uses Pydantic's dict() method with appropriate exclusions
        - Only includes applicable parameters based on current profile
        
        Returns:
            Dict[str, Any]: Parameters in model_kwargs format for LangChain
        """
        # Start with an empty dict
        result = {}
        
        # Add only applicable parameters
        for field_name, field in self.__fields__.items():
            # Check if parameter is applicable in current profile
            if self.is_applicable(field_name):
                value = getattr(self, field_name)
                # Only include if not None
                if value is not None:
                    result[field_name] = value
                    
        return result
    
    def validate_config(self, config_dict: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        [Function intent]
        Validate user-provided configuration values against parameter class constraints
        using Pydantic's validation mechanism.
        
        [Design principles]
        - Explicit validation before parameter application
        - Detailed error reporting for each invalid parameter
        - Support for batch validation of multiple parameters
        
        [Implementation details]
        - Validates each parameter individually to collect all errors
        - Returns validation status and error messages for each failed parameter
        - Only validates parameters that are applicable in current profile
        
        Args:
            config_dict: Dictionary of parameter values to validate
            
        Returns:
            Tuple containing:
            - bool: True if all provided values are valid, False otherwise
            - Dict[str, str]: Dictionary mapping parameter names to error messages for invalid parameters
        """
        errors = {}
        valid = True
        
        # Only validate applicable parameters
        applicable_config = {
            k: v for k, v in config_dict.items() 
            if k in self.__fields__ and self.is_applicable(k) and v is not None
        }
        
        # Validate each parameter individually to collect all errors
        for param_name, value in applicable_config.items():
            try:
                # Create a model with just this parameter to validate it
                param_dict = {param_name: value}
                type(self)(**param_dict)
            except ValidationError as e:
                valid = False
                for error in e.errors():
                    if error["loc"][0] == param_name:
                        errors[param_name] = error["msg"]
        
        return valid, errors
    
    def update_from_args(self, args_dict: Dict[str, Any], validate_first: bool = True) -> "ModelParameters":
        """
        [Method intent]
        Update parameters from arguments dictionary (e.g., CLI args) with optional validation.
        
        [Design principles]
        - Seamless integration with CLI arguments
        - Strong validation before parameter application
        - Detailed error reporting for validation failures
        - Skip None values and non-applicable parameters
        - Return self for chaining
        
        [Implementation details]
        - Optionally validates parameters before updating
        - Updates only fields defined in the model
        - Only updates applicable parameters
        - Returns self for method chaining
        - Raises ValueError with detailed error messages when validation fails
        
        Args:
            args_dict: Dictionary of arguments to update
            validate_first: If True, validate parameters before updating
            
        Returns:
            ModelParameters: Self, for method chaining
            
        Raises:
            ValueError: If validate_first is True and validation fails, with detailed error messages
        """
        # Filter to only include parameters that are applicable and not None
        applicable_args = {
            k: v for k, v in args_dict.items() 
            if k in self.__fields__ and self.is_applicable(k) and v is not None
        }
        
        # Validate parameters if requested
        if validate_first and applicable_args:
            valid, errors = self.validate_config(applicable_args)
            if not valid:
                error_messages = [f"- {param}: {msg}" for param, msg in errors.items()]
                raise ValueError(f"Invalid parameter values:\n" + "\n".join(error_messages))
                
        # Update parameters
        for field_name, value in applicable_args.items():
            setattr(self, field_name, value)
                
        return self
    
    @classmethod
    def add_arguments_to_parser(cls, parser) -> None:
        """
        [Method intent]
        Add all parameter fields to an argument parser.
        
        [Design principles]
        - Automatic CLI argument generation
        - Informative help text
        - Include model-specific constraints in help text
        - Safe parameter type detection
        
        [Implementation details]
        - Uses get_type_hints to safely get parameter types
        - Adds all fields from all parameter classes
        - Includes model name in help text for model-specific parameters
        - Adds profile selection argument
        - Directly accesses field metadata without using nested field_info attribute
        
        Args:
            parser: ArgumentParser to add arguments to
        """
        # Add profile selection argument
        parser.add_argument(
            "--profile",
            help="Parameter profile (e.g., default, reasoning, creative)",
            default="default"
        )
        
        # Get all parameter fields and their variants
        param_data = cls.get_all_param_fields()
        all_fields = param_data['fields']
        model_variants = param_data['model_variants']
        
        # Get type annotations for safe type access
        base_annotations = get_type_hints(cls)
        all_annotations = {}
        all_annotations.update(base_annotations)
        
        # Add annotations from registered model classes
        for param_cls in cls._registry.values():
            try:
                param_annotations = get_type_hints(param_cls)
                for name, type_hint in param_annotations.items():
                    if name not in all_annotations:
                        all_annotations[name] = type_hint
            except Exception as e:
                logging.warning(f"Failed to get type hints for {param_cls.__name__}: {str(e)}")
        
        for field_name, field in all_fields.items():
            try:
                # Determine field type from annotations
                if field_name in all_annotations:
                    field_type = all_annotations[field_name]
                    # Handle Optional types
                    if hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
                        # Extract from Optional
                        for arg in field_type.__args__:
                            if arg is not type(None):  # not NoneType
                                field_type = arg
                                break
                else:
                    # Default to str if type can't be determined
                    field_type = str
                
                # Get field metadata directly from field - note that structure may depend on Pydantic version
                description = ""
                default = None
                
                # Extract description - try different paths to access it
                if hasattr(field, 'description'):
                    description = field.description
                elif hasattr(field, 'field_info') and hasattr(field.field_info, 'description'):
                    description = field.field_info.description
                elif hasattr(field, 'schema') and callable(field.schema):
                    try:
                        schema = field.schema()
                        if isinstance(schema, dict) and 'description' in schema:
                            description = schema['description']
                    except:
                        pass
                
                # Extract default value
                if hasattr(field, 'default'):
                    default = field.default
                
                # Add constraint information to description
                constraints = []
                # Try different paths for accessing constraints
                # Direct attributes on field
                if hasattr(field, 'ge'):
                    constraints.append(f"min: {field.ge}")
                if hasattr(field, 'le'):
                    constraints.append(f"max: {field.le}")
                
                # On field_info if it exists
                if hasattr(field, 'field_info'):
                    if hasattr(field.field_info, 'ge'):
                        constraints.append(f"min: {field.field_info.ge}")
                    if hasattr(field.field_info, 'le'):
                        constraints.append(f"max: {field.field_info.le}")
                
                # Try extracting from schema
                if hasattr(field, 'schema') and callable(field.schema):
                    try:
                        schema = field.schema()
                        if isinstance(schema, dict):
                            if 'minimum' in schema:
                                constraints.append(f"min: {schema['minimum']}")
                            if 'maximum' in schema:
                                constraints.append(f"max: {schema['maximum']}")
                    except:
                        pass
                
                if constraints:
                    description += f" ({', '.join(constraints)})"
                
                # Add model-specific variant information to help text
                variants = model_variants.get(field_name, [])
                for variant in variants:
                    var_field = variant['field']
                    model_name = variant['model_name']
                    var_constraints = []
                    
                    # Try different access paths for variant fields too
                    if hasattr(var_field, 'ge'):
                        var_constraints.append(f"min: {var_field.ge}")
                    if hasattr(var_field, 'le'):
                        var_constraints.append(f"max: {var_field.le}")
                    
                    if hasattr(var_field, 'field_info'):
                        if hasattr(var_field.field_info, 'ge'):
                            var_constraints.append(f"min: {var_field.field_info.ge}")
                        if hasattr(var_field.field_info, 'le'):
                            var_constraints.append(f"max: {var_field.field_info.le}")
                    
                    # Try extracting from schema
                    if hasattr(var_field, 'schema') and callable(var_field.schema):
                        try:
                            schema = var_field.schema()
                            if isinstance(schema, dict):
                                if 'minimum' in schema:
                                    var_constraints.append(f"min: {schema['minimum']}")
                                if 'maximum' in schema:
                                    var_constraints.append(f"max: {schema['maximum']}")
                        except:
                            pass
                        
                    if var_constraints:
                        description += f"\n  [{model_name}]: ({', '.join(var_constraints)})"
                
                # Add argument to parser
                parser.add_argument(
                    f"--{field_name}",
                    type=field_type,
                    default=None,  # Default None so we can detect if it was explicitly set
                    help=description
                )
                
            except Exception as e:
                logging.warning(f"Failed to add argument for {field_name}: {str(e)}")
    
    def get_model_id_constraint(self) -> List[str]:
        """
        [Method intent]
        Return a list of model IDs compatible with this parameter class from the Config.supported_models.
        
        [Design principles]
        - DRY implementation that eliminates redundancy with Config.supported_models
        - Enforces that each parameter class specifies which models it supports
        - Enables runtime validation of parameter-to-model compatibility
        
        [Implementation details]
        - Gets supported models from Config.supported_models
        - Throws a clear error if Config.supported_models is not defined
        - Eliminates the need to redefine this method in each subclass
        
        Returns:
            List[str]: List of supported model IDs
            
        Raises:
            ValueError: If Config.supported_models is not defined
        """
        if hasattr(self, "Config"):
            if hasattr(self.Config, "supported_models"):
                return self.Config.supported_models
            
        # If we reach here, Config.supported_models is not defined
        cls_name = self.__class__.__name__
        raise ValueError(f"Parameter class '{cls_name}' must define Config.supported_models")
