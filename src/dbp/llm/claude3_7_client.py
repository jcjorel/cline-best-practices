###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements a specialized Bedrock client for Anthropic's Claude 3.7 Sonnet model.
# This client handles model-specific request formatting, invocation parameters,
# and response parsing for both streaming and non-streaming operations.
###############################################################################
# [Source file design principles]
# - Implement the BedrockModelClientBase interface for Claude 3.7 Sonnet
# - Handle Claude-specific request and response formats
# - Provide optimal default parameters for Claude 3.7 Sonnet
# - Support both streaming and non-streaming invocations
# - Integrate with the prompt manager for template-based prompting
###############################################################################
# [Source file constraints]
# - Must adhere to Claude 3.7 model-specific API requirements
# - Must handle Claude 3.7 error conditions appropriately
# - Must process responses according to Claude 3.7's output format
# - Must use the common BedrockModelClientBase interface
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T13:41:00Z : Initial creation of Claude 3.7 Sonnet client by Cline
# * Implemented Claude 3.7 specific request/response handling
# * Added support for streaming and non-streaming invocations
# * Integrated with LLMPromptManager for template-based prompting
###############################################################################

import logging
from typing import Dict, Any, Iterator, Optional, Union, List

from .bedrock_base import BedrockModelClientBase, BedrockClientError
from .prompt_manager import LLMPromptManager
from .bedrock_client_common import (
    BedrockRequestFormatter,
    BedrockClientMixin,
    invoke_model_common,
    invoke_model_stream_common
)

logger = logging.getLogger(__name__)

class Claude37RequestFormatter(BedrockRequestFormatter[Dict[str, Any]]):
    """
    [Class intent]
    Formats prompts for Claude 3.7 model's specific request structure.
    
    [Implementation details]
    Handles multiple input formats (string, dict, message list) and
    structures them according to Claude's API requirements.
    
    [Design principles]
    - Encapsulates Claude-specific request formatting logic
    - Supports flexible input formats for improved usability
    - Maintains clear separation from common invocation code
    """
    
    def __init__(self, temperature: float, top_p: float, max_tokens: int, system_prompt: Optional[str] = None):
        """
        Initialize the Claude 3.7 request formatter with default parameters.
        
        Args:
            temperature: Temperature parameter (0.0 to 1.0)
            top_p: Top-p sampling parameter (0.0 to 1.0)
            max_tokens: Maximum tokens to generate in response
            system_prompt: Optional system prompt for all requests
        """
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
    
    def format_request(self, prompt: Union[str, Dict[str, Any], List[Dict[str, Any]]], **kwargs) -> Dict[str, Any]:
        """
        [Function intent]
        Format a prompt into a Claude 3.7-specific request body.
        
        [Implementation details]
        Converts different prompt formats into Claude's expected message structure
        and applies appropriate parameters with override support.
        
        [Design principles]
        - Handles multiple input formats flexibly
        - Applies defaults with parameter override capability
        - Follows Claude API specifications precisely
        
        Args:
            prompt: String prompt, pre-formatted request, or message list
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Request body formatted for Claude 3.7
        """
        # Build messages array for Claude 3.7
        messages = []
        
        # Handle different input types
        if isinstance(prompt, str):
            # Simple string prompt becomes a user message
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list) and all(isinstance(m, dict) for m in prompt):
            # Use provided message list directly (already in Claude format)
            messages = prompt
        elif isinstance(prompt, dict) and "messages" in prompt:
            # If request already has a messages field, use it directly
            return prompt
        elif isinstance(prompt, dict) and "content" in prompt:
            # Single message - wrap in a list
            role = prompt.get("role", "user")
            messages = [{"role": role, "content": prompt["content"]}]
        else:
            # Default to treating as user message content
            logger.warning({
                "message": "Unrecognized prompt format, treating as user message content",
                "prompt_type": type(prompt).__name__
            })
            messages = [{"role": "user", "content": str(prompt)}]
            
        # Build the request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p)
        }
        
        # Add system prompt if available
        system_prompt = kwargs.get("system_prompt", self.system_prompt)
        if system_prompt:
            request_body["system"] = system_prompt
            
        return request_body

class Claude37SonnetClient(BedrockModelClientBase, BedrockClientMixin):
    """
    [Class intent]
    Specialized Bedrock client implementation for Anthropic's Claude 3.7 Sonnet model.
    
    [Implementation details]
    Handles the specific invocation parameters, request formatting,
    and response parsing needed for effective use of the Claude 3.7 Sonnet model.
    Uses common code for shared functionality while implementing
    model-specific behavior through the request formatter.
    
    [Design principles]
    - Implements BedrockModelClientBase interface for consistency
    - Uses composition with BedrockClientMixin for common functionality
    - Delegates request formatting to specialized formatter component
    - Minimizes code duplication through common invocation methods
    """
    
    DEFAULT_MODEL_ID = "anthropic.claude-3-7-sonnet-20240620-v1:0"  # Claude 3.7 Sonnet model ID
    
    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region: Optional[str] = None,
        max_retries: int = 3,
        connect_timeout: int = 10,
        read_timeout: int = 60,  # Claude can take longer for complex responses
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
        prompt_manager: Optional[LLMPromptManager] = None,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initialize a new Claude 3.7 Sonnet client.
        
        Args:
            model_id: The Bedrock model ID (defaults to Claude 3.7 Sonnet)
            region: AWS region for the Bedrock service
            max_retries: Maximum number of retry attempts for AWS API calls
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            temperature: Model temperature parameter (0.0 to 1.0)
            top_p: Top-p sampling parameter (0.0 to 1.0)
            max_tokens: Maximum tokens to generate in response
            system_prompt: Optional system prompt to use with all requests
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
        self.system_prompt = system_prompt
        self.prompt_manager = prompt_manager
        
        self.logger.debug({
            "message": "Claude 3.7 Sonnet client created",
            "model_id": self.model_id,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "has_system_prompt": system_prompt is not None
        })

    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        [Function intent]
        Format a prompt template for Claude 3.7 using the prompt manager.
        
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
        
    def invoke_model(self, prompt: Union[str, Dict[str, Any], List[Dict[str, Any]]], **kwargs) -> Dict[str, Any]:
        """
        [Function intent]
        Invoke the Claude 3.7 Sonnet model with a prompt and return the complete response.
        
        [Implementation details]
        Creates the appropriate request formatter and delegates to common implementation.
        
        [Design principles]
        - Reuses common invocation code to avoid duplication
        - Focuses only on model-specific aspects (request formatting)
        
        Args:
            prompt: String prompt, pre-formatted request, or message list
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dict[str, Any]: The model's response
            
        Raises:
            BedrockClientError: On invocation failure
        """
        # Create request formatter with current parameters
        formatter = Claude37RequestFormatter(
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            system_prompt=self.system_prompt
        )
        
        # Delegate to common implementation
        return invoke_model_common(self, formatter, prompt, **kwargs)

    def invoke_model_stream(self, prompt: Union[str, Dict[str, Any], List[Dict[str, Any]]], **kwargs) -> Iterator[Dict[str, Any]]:
        """
        [Function intent]
        Invoke the Claude 3.7 model with streaming response.
        
        [Implementation details]
        Creates the appropriate request formatter and delegates to common implementation.
        
        [Design principles]
        - Reuses common streaming invocation code to avoid duplication
        - Maintains focus on model-specific aspects through the formatter
        
        Args:
            prompt: String prompt, pre-formatted request, or message list
            **kwargs: Additional model-specific parameters
            
        Yields:
            Dict[str, Any]: Chunks of the model's response
            
        Raises:
            BedrockClientError: On invocation failure
        """
        # Create request formatter with current parameters
        formatter = Claude37RequestFormatter(
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            system_prompt=self.system_prompt
        )
        
        # Delegate to common implementation
        yield from invoke_model_stream_common(self, formatter, prompt, **kwargs)
