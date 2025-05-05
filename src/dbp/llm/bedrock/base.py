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
# DEPRECATED: This file provides backward compatibility for the legacy BedrockBase implementation.
# It redirects to the new LangChain-based implementation to minimize disruption during refactoring.
# This file will be removed in a future version - update your code to use EnhancedChatBedrockConverse directly.
###############################################################################
# [Source file design principles]
# - Preserve backward compatibility during transition
# - Forward calls to the new implementation
# - Avoid duplicating core functionality
# - Provide clear deprecation warnings
###############################################################################
# [Source file constraints]
# - Must maintain API compatibility with the original BedrockBase
# - Must not introduce new features or behaviors
# - Must log deprecation warnings when accessed
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# system:warnings
# system:logging
# system:abc
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:22:14Z : Refactored into a compatibility wrapper by CodeAssistant
# * Converted to a compatibility wrapper for LangChain-based implementation
# * Added deprecation warnings for all class usage
# * Updated imports to point to new LangChain-based implementation
# * Simplified implementation to minimize maintenance
# 2025-05-05T00:30:00Z : Refactored BedrockBase to an abstract class by CodeAssistant
# * Added abstract methods for model-specific implementations
# * Improved code organization and documentation
# * Made API more consistent across all methods
# * Enhanced error handling with specific exceptions
# * Simplified constructor to reduce parameter complexity
###############################################################################

import warnings
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Iterator, AsyncIterator

from ..common.base import ModelClientBase, AsyncTextStreamProvider
from .langchain_wrapper import EnhancedChatBedrockConverse

# Display deprecation warning
warnings.warn(
    "BedrockBase is deprecated and will be removed in a future version. "
    "Use EnhancedChatBedrockConverse from langchain_wrapper.py instead.",
    DeprecationWarning, 
    stacklevel=2
)

class BedrockBase(ModelClientBase, AsyncTextStreamProvider, ABC):
    """
    [Class intent]
    DEPRECATED: Legacy abstract base class for AWS Bedrock model clients.
    This class is maintained for backward compatibility and will be removed in a future version.
    Please use EnhancedChatBedrockConverse from langchain_wrapper.py instead.
    
    [Design principles]
    - Provide backward compatibility during transition
    - Forward calls to the new implementation
    - Warn about deprecation
    
    [Implementation details]
    - Implements the required ABC interfaces for backward compatibility
    - Forwards actual functionality to EnhancedChatBedrockConverse
    - Logs deprecation warnings to encourage transition to new implementation
    """
    
    DEFAULT_RETRIES = 3
    DEFAULT_TIMEOUT = 30
    
    def __init__(
        self,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = DEFAULT_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = True,
        preferred_regions: Optional[List[str]] = None,
        inference_profile_arn: Optional[str] = None
    ):
        """
        [Method intent]
        Initialize the BedrockBase with AWS credentials and configuration.
        DEPRECATED: This constructor is maintained for backward compatibility.
        
        [Design principles]
        - Preserve backward compatibility
        - Forward to new implementation
        - Warn about deprecation
        
        [Implementation details]
        - Logs deprecation warning
        - Stores parameters for potential use by subclasses
        - Actual implementation is now in EnhancedChatBedrockConverse
        """
        # Log deprecation warning
        self.logger = logger or logging.getLogger("BedrockBase")
        self.logger.warning(
            "BedrockBase is deprecated. Use EnhancedChatBedrockConverse from langchain_wrapper.py instead."
        )
        
        # Store core parameters for compatibility
        self.model_id = model_id
        self.region_name = region_name
        self.profile_name = profile_name
        self.credentials = credentials
        self.max_retries = max_retries
        self.timeout = timeout
        self.use_model_discovery = use_model_discovery
        self.preferred_regions = preferred_regions
        self.inference_profile_arn = inference_profile_arn
        
        # To be implemented by subclasses
        self._client = None
