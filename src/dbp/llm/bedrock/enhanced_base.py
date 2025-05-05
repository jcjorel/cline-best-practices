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
# DEPRECATED: This file provides backward compatibility for the legacy EnhancedBedrockBase implementation.
# It redirects to the new LangChain-based implementation to minimize disruption during refactoring.
# This file will be removed in a future version - update your code to use EnhancedChatBedrockConverse directly.
###############################################################################
# [Source file design principles]
# - Preserve backward compatibility during transition
# - Forward calls to the new implementation
# - Maintain model capability functionality
# - Provide clear deprecation warnings
###############################################################################
# [Source file constraints]
# - Must maintain API compatibility with the original EnhancedBedrockBase
# - Must preserve ModelCapability enum for compatibility
# - Must log deprecation warnings when accessed
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/bedrock/base.py
# system:warnings
# system:logging
# system:abc
# system:enum
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:23:29Z : Refactored into a compatibility wrapper by CodeAssistant
# * Converted to a compatibility wrapper for LangChain-based implementation
# * Added deprecation warnings for all class usage
# * Maintained ModelCapability enum for backward compatibility
# * Simplified implementation to minimize maintenance
# 2025-05-05T00:33:00Z : Refactored EnhancedBedrockBase to improve DRY principles by CodeAssistant
# * Made EnhancedBedrockBase abstract class to enforce contract
# * Enhanced error handling throughout class
# * Cleaned up formatting and code style
# * Fixed parameter ordering and documentation
# 2025-05-05T00:30:30Z : Fixed region_name handling bug by CodeAssistant
# * Fixed bug in EnhancedBedrockBase.__init__ to use self.region_name rather than original region_name
# * Improved error handling for AWS client errors
# * Added more detailed client error classification
# * Enhanced logging for better debugging
# 2025-05-04T13:52:00Z : Added multimodal support to EnhancedBedrockBase by CodeAssistant
# * Added process_multimodal_message method
# * Implemented image processing for BytesIO and base64 sources
# * Added support for model-specific message formats
# * Improved error handling and validation
###############################################################################

import warnings
import logging
import enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Set

from .base import BedrockBase
from .langchain_wrapper import EnhancedChatBedrockConverse

# Display deprecation warning
warnings.warn(
    "EnhancedBedrockBase is deprecated and will be removed in a future version. "
    "Use EnhancedChatBedrockConverse from langchain_wrapper.py instead.",
    DeprecationWarning, 
    stacklevel=2
)

class ModelCapability(enum.Enum):
    """
    [Class intent]
    Enumeration of capabilities that a model might support.
    Maintained for backward compatibility.
    
    [Design principles]
    - Clear enumeration of distinct capabilities
    - Each capability maps to a specific model feature
    
    [Implementation details]
    - Simple enum values
    - Used by capability checks throughout the system
    - Maintained for backward compatibility
    """
    CHAT = "chat"
    COMPLETION = "completion"
    STREAM = "stream"
    FUNCTION_CALLING = "function_calling"
    TOOL_USE = "tool_use"
    IMAGE_GENERATION = "image_generation"
    MULTIMODAL = "multimodal"
    STREAMING = "streaming"  # Alias for STREAM for backward compatibility

class EnhancedBedrockBase(BedrockBase, ABC):
    """
    [Class intent]
    DEPRECATED: Legacy enhanced base class for AWS Bedrock model clients that adds
    access to model details and capabilities. This class is maintained for backward
    compatibility and will be removed in a future version.
    Please use EnhancedChatBedrockConverse from langchain_wrapper.py instead.
    
    [Design principles]
    - Provide backward compatibility during transition
    - Forward calls to the new implementation
    - Maintain model capability checks
    - Warn about deprecation
    
    [Implementation details]
    - Implements the required abstract methods for backward compatibility
    - Forwards actual functionality to EnhancedChatBedrockConverse
    - Logs deprecation warnings to encourage transition to new implementation
    """
    
    # List of model IDs supported by this client class
    # To be overridden by subclasses
    SUPPORTED_MODELS: List[str] = []
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = BedrockBase.DEFAULT_RETRIES,
        timeout: int = BedrockBase.DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = True,
        preferred_regions: Optional[List[str]] = None,
        inference_profile_arn: Optional[str] = None
    ):
        """
        [Method intent]
        Initialize the EnhancedBedrockBase with AWS credentials and configuration.
        DEPRECATED: This constructor is maintained for backward compatibility.
        
        [Design principles]
        - Preserve backward compatibility
        - Forward to new implementation
        - Warn about deprecation
        
        [Implementation details]
        - Logs deprecation warning
        - Calls parent BedrockBase constructor
        - Basic capability tracking for backward compatibility
        """
        # Call parent constructor for compatibility
        super().__init__(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            credentials=credentials,
            max_retries=max_retries,
            timeout=timeout,
            logger=logger or logging.getLogger("EnhancedBedrockBase"),
            use_model_discovery=use_model_discovery,
            preferred_regions=preferred_regions,
            inference_profile_arn=inference_profile_arn
        )
        
        # Placeholder for model capabilities
        self._model_capabilities: Set[ModelCapability] = set()
        
    def has_capability(self, capability: ModelCapability) -> bool:
        """
        [Method intent]
        Check if the model has a specific capability.
        
        [Design principles]
        - Simple capability checking
        - Clear boolean return value
        
        [Implementation details]
        - Basic stub implementation for backward compatibility
        - Will always return False in this compatibility wrapper
        
        Args:
            capability: The capability to check for
            
        Returns:
            bool: False (default compatibility implementation)
        """
        return False
        
    def get_capabilities(self) -> Set[ModelCapability]:
        """
        [Method intent]
        Get all capabilities supported by this model.
        
        [Design principles]
        - Return copy of internal set
        - Immutable response
        
        [Implementation details]
        - Simple stub implementation for backward compatibility
        - Returns empty set in this compatibility wrapper
        
        Returns:
            Set[ModelCapability]: Empty set (default compatibility implementation)
        """
        return set()
