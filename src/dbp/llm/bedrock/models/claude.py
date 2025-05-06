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
    
    @classmethod
    def get_model_version(cls, model_id: str) -> str:
        """
        [Method intent]
        Extract Claude version (e.g., 3.0, 3.5, 3.7) from model ID.
        
        [Design principles]
        - Claude-specific version parsing
        - Format standardization 
        - Handle diverse Claude model ID formats
        
        [Implementation details]
        - Parses Claude model ID format to extract version
        - Returns standardized version string
        - Falls back to version detection by key segments in model ID
        
        Args:
            model_id: The model ID to extract version from
            
        Returns:
            str: Version string (e.g., "3.0", "3.5", "3.7")
        """
        # Claude models follow pattern: anthropic.claude-<version>-<variant>-<date>-<model_rev>:<minor>
        if "claude-3-5" in model_id:
            return "3.5"
        elif "claude-3-7" in model_id:
            return "3.7"
        elif "claude-3" in model_id:
            return "3.0"
        elif "claude-2" in model_id:
            return "2.0"
        elif "claude-instant" in model_id:
            return "1.0"
        return "Unknown"
    
    @classmethod
    def get_model_variant(cls, model_id: str) -> str:
        """
        [Method intent]
        Extract Claude variant (e.g., "Sonnet", "Haiku", "Opus") from model ID.
        
        [Design principles]
        - Claude-specific variant parsing
        - Proper capitalization
        - Handle diverse Claude model ID formats
        
        [Implementation details]
        - Parses Claude model ID format to extract variant
        - Returns standardized variant string with proper capitalization
        - Falls back to "Unknown" if variant can't be determined
        
        Args:
            model_id: The model ID to extract variant from
            
        Returns:
            str: Variant string (e.g., "Sonnet", "Haiku", "Opus")
        """
        if "sonnet" in model_id.lower():
            return "Sonnet"
        elif "haiku" in model_id.lower():
            return "Haiku"
        elif "opus" in model_id.lower():
            return "Opus"
        return "Unknown"

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
