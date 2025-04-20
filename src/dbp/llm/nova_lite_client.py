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
# Implements a specialized Bedrock client for the Amazon Nova Lite model.
# This client handles model-specific request formatting, invocation parameters,
# and response parsing for both streaming and non-streaming operations.
###############################################################################
# [Source file design principles]
# - Implement the BedrockModelClientBase interface for the Nova Lite model
# - Handle Nova Lite specific request and response formats
# - Provide optimal default parameters for Nova Lite
# - Support both streaming and non-streaming invocations
# - Integrate with the prompt manager for template-based prompting
###############################################################################
# [Source file constraints]
# - Must adhere to Amazon Bedrock service limits for Nova Lite
# - Must handle model-specific error conditions appropriately
# - Must process responses according to Nova Lite's output format
# - Must use the common BedrockModelClientBase interface
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T12:58:00Z : Initial creation of Nova Lite client by Cline
# * Implemented Nova Lite specific request/response handling
# * Added support for streaming and non-streaming invocations
# * Integrated with LLMPromptManager for template-based prompting
###############################################################################

import logging
from typing import Dict, Any, Iterator, Optional, Union

from .bedrock_base import BedrockModelClientBase, BedrockClientError
from .prompt_manager import LLMPromptManager
from .bedrock_client_common import (
    BedrockRequestFormatter,
    BedrockClientMixin,
    invoke_model_common,
    invoke_model_stream_common
)

logger = logging.getLogger(__name__)

class NovaLiteRequestFormatter(BedrockRequestFormatter[Dict[str, Any]]):
    """
    [Class intent]
    Formats prompts for the Nova Lite model's specific request structure.
    
    [Implementation details]
    Handles different input formats and applies appropriate model parameters.
    
    [Design principles]
    - Encapsulates Nova Lite-specific request formatting logic
    - Provides clean separation from common invocation code
    """
    
    def __init__(self, temperature: float, top_p: float, max_tokens: int):
        """
        Initialize the Nova Lite request formatter with default parameters.
        
        Args:
            temperature: Temperature parameter (0.0 to 1.0)
            top_p: Top-p sampling parameter (0.0 to 1.0)  
            max_tokens: Maximum tokens to generate in response
        """
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
    
    def format_request(self, prompt: Union[str, Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        [Function intent]
        Format a prompt into a Nova Lite-specific request body.
        
        [Implementation details]
        Converts different prompt formats into Nova Lite's expected structure
        and applies appropriate parameters with override support.
        
        [Design principles]
        - Handles multiple input formats flexibly
        - Applies defaults with parameter override capability
        
        Args:
            prompt: String prompt or pre-formatted request body
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Request body formatted for Nova Lite
        """
        # If prompt is already a dict, use it as base
        if isinstance(prompt, dict):
            request_body = prompt.copy()
        else:
            # Otherwise create a new request body with the prompt
            request_body = {
                "inputText": prompt
            }
        
        # Apply model parameters, allowing overrides from kwargs
        inference_params = {
            "temperature": kwargs.get("temperature", self.temperature),
            "topP": kwargs.get("top_p", self.top_p),
            "maxTokens": kwargs.get("max_tokens", self.max_tokens),
        }
        
        # Only add parameters that aren't explicitly set in the request body
        for key, value in inference_params.items():
            if key not in request_body:
                request_body[key] = value
        
        return request_body

class NovaLiteClient(BedrockModelClientBase, BedrockClientMixin):
    """
    [Class intent]
    Specialized Bedrock client implementation for Amazon Nova Lite model.
    
    [Implementation details]
    Handles the specific invocation parameters, request formatting,
    and response parsing needed for effective use of the Nova Lite model.
    Uses common code for shared functionality while implementing
    model-specific behavior through the request formatter.
    
    [Design principles]
    - Implements BedrockModelClientBase interface for consistency
    - Uses composition with BedrockClientMixin for common functionality
    - Delegates request formatting to specialized formatter component
    - Minimizes code duplication through common invocation methods
    """
    
    DEFAULT_MODEL_ID = "amazon.nova-lite-v1:0"
    
    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region: Optional[str] = None,
        max_retries: int = 3,
        connect_timeout: int = 10,
        read_timeout: int = 30,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2000,
        prompt_manager: Optional[LLMPromptManager] = None,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initialize a new Nova Lite client.
        
        Args:
            model_id: The Bedrock model ID (defaults to Nova Lite)
            region: AWS region for the Bedrock service
            max_retries: Maximum number of retry attempts for AWS API calls
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            temperature: Model temperature parameter (0.0 to 1.0)
            top_p: Top-p sampling parameter (0.0 to 1.0)
            max_tokens: Maximum tokens to generate in response
            prompt_manager: Optional LLMPromptManager instance
            logger_override: Optional logger instance
        """
        super().__init__(
            model_id=model_id,
            region=region,
            max_retries=max_retries,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            logger_override=logger_override
        )
        
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.prompt_manager = prompt_manager
        
        self.logger.debug({
            "message": "Nova Lite client created",
            "model_id": self.model_id,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens
        })

    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        [Function intent]
        Format a prompt template for Nova Lite using the prompt manager.
        
        [Implementation details]
        Delegates to the common implementation in BedrockClientMixin.
        
        [Design principles]
        - Maintains backward compatibility with existing code
        - Reuses common implementation to avoid duplication
        
        Args:
            prompt_name: Name of the prompt template to use
            **kwargs: Parameters for the prompt template
            
        Returns:
            Formatted prompt string
            
        Raises:
            BedrockClientError: If prompt formatting fails
        """
        return super().format_prompt(self.prompt_manager, prompt_name, **kwargs)
        
    def invoke_model(self, prompt: Union[str, Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        [Function intent]
        Invoke the Nova Lite model with a prompt and return the complete response.
        
        [Implementation details]
        Creates the appropriate request formatter and delegates to common implementation.
        
        [Design principles]
        - Reuses common invocation code to avoid duplication
        - Focuses only on model-specific aspects (request formatting)
        
        Args:
            prompt: String prompt or pre-formatted request body
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dict[str, Any]: The model's response
            
        Raises:
            BedrockClientError: On invocation failure
        """
        # Create request formatter with current parameters
        formatter = NovaLiteRequestFormatter(
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens
        )
        
        # Delegate to common implementation
        return invoke_model_common(self, formatter, prompt, **kwargs)

    def invoke_model_stream(self, prompt: Union[str, Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """
        [Function intent]
        Invoke the Nova Lite model with streaming response.
        
        [Implementation details]
        Creates the appropriate request formatter and delegates to common implementation.
        
        [Design principles]
        - Reuses common streaming invocation code to avoid duplication
        - Maintains focus on model-specific aspects through the formatter
        
        Args:
            prompt: String prompt or pre-formatted request body
            **kwargs: Additional model-specific parameters
            
        Yields:
            Dict[str, Any]: Chunks of the model's response
            
        Raises:
            BedrockClientError: On invocation failure
        """
        # Create request formatter with current parameters
        formatter = NovaLiteRequestFormatter(
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens
        )
        
        # Delegate to common implementation
        yield from invoke_model_stream_common(self, formatter, prompt, **kwargs)
