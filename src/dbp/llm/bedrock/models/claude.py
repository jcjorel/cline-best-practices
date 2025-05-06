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
# Defines the abstract base parameter class for Anthropic Claude model variants on AWS Bedrock.
# This class serves as the foundation for all Claude-specific parameter implementations.
###############################################################################
# [Source file design principles]
# - Abstract base class for shared Claude functionality
# - Common parameter constraints across all Claude variants
# - Base profile definitions for Claude models
# - AWS-aligned parameter definitions
###############################################################################
# [Source file constraints]
# - Must accurately reflect AWS Bedrock documentation
# - Must maintain compatibility with ModelParameters interface
# - Parameter ranges must match official AWS documentation
# - Must serve as a proper base class for model-specific Claude classes
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/model_parameters.py
# system:abc
# system:typing
# system:pydantic
###############################################################################
# [GenAI tool change history]
# 2025-05-06T11:25:45Z : Removed abstract get_model_id_constraint method by CodeAssistant
# * Removed redundant abstract get_model_id_constraint method from base class
# * Now using ModelParameters implementation that references Config.supported_models
# * Applied DRY principle to eliminate redundancy
# * Maintained functionality by using parent class implementation
# 2025-05-06T10:29:14Z : Fixed profiles implementation for Pydantic compatibility by CodeAssistant
# * Updated base_profiles to be a class variable instead of a private attribute
# * Fixed compatibility with Pydantic's model system
# * Ensured profiles can be properly inherited by subclasses
# 2025-05-06T10:24:11Z : Initial implementation of abstract ClaudeParameters base class by CodeAssistant
# * Created abstract ClaudeParameters base class
# * Defined common parameters with Claude-specific constraints
# * Implemented base profiles for Claude models
# * Added abstract get_model_id_constraint method
###############################################################################

from abc import ABC
from typing import List, Optional, ClassVar, Dict, Any
from pydantic import Field

from ..model_parameters import ModelParameters

class ClaudeParameters(ModelParameters, ABC):
    """
    [Class intent]
    Abstract base class for all Claude model variants that defines common 
    Claude-specific parameters and constraints.
    
    [Design principles]
    - Define Claude-specific parameters shared across all Claude variants
    - Establish common profile framework for Claude models
    - Serve as abstract base class for concrete Claude model implementations
    
    [Implementation details]
    - Uses AWS-specified parameter constraints from documentation
    - Defines common Claude parameters like stop_sequences
    - Cannot be instantiated directly (abstract class)
    - Default profiles for base Claude functionality
    - Uses parent class get_model_id_constraint that references Config.supported_models
    """

    # Claude-specific parameters with official AWS constraints
    temperature: float = Field(
        default=1.0,  # AWS default
        ge=0.0,       # AWS minimum
        le=1.0,       # AWS maximum
        description="Controls randomness in the output. Higher values make output more diverse."
    )
    
    top_p: float = Field(
        default=0.999,  # AWS default
        ge=0.0,         # AWS minimum
        le=1.0,         # AWS maximum
        description="Nucleus sampling parameter. Controls diversity by limiting to top tokens whose probabilities add up to top_p."
    )
    
    top_k: Optional[int] = Field(
        default=None,  # Disabled by default per AWS docs
        ge=0,          # AWS minimum
        le=500,        # AWS maximum
        description="Only sample from the top K most likely tokens. Use to remove long tail low probability responses."
    )
    
    stop_sequences: List[str] = Field(
        default_factory=list,
        description="Sequences that will cause the model to stop generating."
    )
    
    # Base profiles for all Claude models - as class variable for Pydantic compatibility
    base_profiles: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {
            "applicable_params": None,  # All parameters are potentially applicable
            "not_applicable_params": [],  # No parameters are excluded
            "param_overrides": {
                "temperature": 1.0,
                "top_p": 0.999
            }
        },
        
        "creative": {
            "applicable_params": None,
            "not_applicable_params": [],
            "param_overrides": {
                "temperature": 0.9,
                "top_p": 1.0,
                "top_k": 350
            }
        },
        
        "concise": {
            "applicable_params": None,
            "not_applicable_params": [],
            "param_overrides": {
                "temperature": 0.5,
                "top_p": 0.8
            }
        }
    }
    
    # Use base_profiles as _profiles for compatibility with parent class
    _profiles = base_profiles
    
    class Config:
        model_name = "Claude"
