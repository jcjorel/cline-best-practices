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
# Implements a specialized Bedrock client for Anthropic's Claude 3.7 Sonnet model.
# This client handles model-specific request formatting, invocation parameters,
# and response parsing for both single-shot and conversational interactions.
###############################################################################
# [Source file design principles]
# - Implement the BedrockModelClientBase interface for Claude 3.7 Sonnet
# - Handle Claude-specific request and response formats
# - Provide optimal default parameters for Claude 3.7 Sonnet
# - Support the streaming-only interface pattern
# - Integrate with the prompt manager for template-based prompting
###############################################################################
# [Source file constraints]
# - Must adhere to Claude 3.7 model-specific API requirements
# - Must handle Claude 3.7 error conditions appropriately
# - Must process responses according to Claude 3.7's output format
# - Must implement the streaming-only interface
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-05-02T07:26:00Z : Refactored and moved to bedrock/models directory by Cline
# * Relocated from src/dbp/llm/claude3_7_client.py to current location
# * Updated imports to reflect new directory structure
# * Refactored to use streaming-only invoke interface
# * Consolidated methods to follow updated architecture
# 2025-04-16T13:41:00Z : Initial creation of Claude 3.7 Sonnet client by Cline
# * Implemented Claude 3.7 specific request/response handling
# * Added support for streaming and non-streaming invocations
# * Integrated with LLMPromptManager for template-based prompting
###############################################################################

import logging
from typing import Dict, Any, Iterator, Optional, Union, List

from ...common.base import ModelMessage
from ...common.prompt_manager import LLMPromptManager
from ..base import BedrockModelClientBase, BedrockClientError
from ..client_common import BedrockRequestFormatter, BedrockClientMixin, invoke_bedrock_model

logger = logging.getLogger(__name__)

class Claude37RequestFormatter(BedrockRequestFormatter[Dict[str, Any]]):
    """
    [Class intent]
    Formats prompts for Claude 3.7 model's specific request structure.
    
    [Design principles]
    - Encapsulates Claude-specific request formatting logic
    - Supports flexible input formats for improved usability
    - Maintains clear separation from common invocation code
    
    [Implementation details]
    - Handles multiple input formats (string, dict, message list) and
      structures them according to Claude's API requirements
    - Applies appropriate defaults and parameter overrides
    """
    
    def __init__(self, temperature: float, top_p: float, max_tokens: int, system_prompt: Optional[str] = None):
        """
        [Function intent]
        Initialize the Claude 3.7 request formatter with default parameters.
        
        [Design principles]
        - Store all formatting parameters for reuse
        - Support optional system prompt for all requests
        
        [Implementation details]
        - Sets up model-specific parameters with sensible defaults
        - Stores optional system prompt for all requests
        
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
    
    def format_request(self, messages: Union[str, Dict[str, Any], List[Union[Dict[str, Any], ModelMessage]]], **kwargs) -> Dict[str, Any]:
        """
        [Function intent]
        Format input messages into a Claude 3.7-specific request body.
        
        [Design principles]
        - Handle multiple input formats flexibly
        - Apply defaults with parameter override capability
        - Follow Claude API specifications precisely
        
        [Implementation details]
        - Converts different message formats (string, structured messages, conversation)
          into Claude's expected message structure
        - Applies appropriate parameters with override support
        - Handles system prompt appropriately
        
        Args:
            messages: Input in one of these formats:
                      - String: A simple prompt string for single-shot queries
                      - List[Dict|ModelMessage]: A conversation history
                      - Dict: A pre-formatted provider-specific request
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Request body formatted for Claude 3.7
        """
        # Build messages array for Claude 3.7
        claude_messages = []
        
        # Handle different input types
        if isinstance(messages, str):
            # Simple string prompt becomes a user message
            claude_messages = [{"role": "user", "content": messages}]
        elif isinstance(messages, list):
            # List of messages - convert each to Claude format
            claude_messages = []
            for msg in messages:
                if isinstance(msg, ModelMessage):
                    claude_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                elif isinstance(msg, dict) and "role" in msg and "content" in msg:
                    # Already in Claude-compatible format
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                else:
                    logger.warning({
                        "message": "Skipping invalid message format in list",
                        "message_type": type(msg).__name__
                    })
        elif isinstance(messages, dict):
            if "messages" in messages:
                # If request already has a messages field, use it directly
                return messages
            elif "content" in messages:
                # Single message - wrap in a list
                role = messages.get("role", "user")
                claude_messages = [{"role": role, "content": messages["content"]}]
            else:
                # Default to treating as user message content
                logger.warning({
                    "message": "Dict without expected keys, treating as user message",
                    "keys": list(messages.keys())
                })
                claude_messages = [{"role": "user", "content": str(messages)}]
        else:
            # Default to treating as user message content
            logger.warning({
                "message": "Unrecognized input format, treating as user message content",
                "input_type": type(messages).__name__
            })
            claude_messages = [{"role": "user", "content": str(messages)}]
            
        # Build the request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": claude_messages,
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
    
    [Design principles]
    - Implements BedrockModelClientBase interface for consistency
    - Uses composition with BedrockClientMixin for common functionality
    - Delegates request formatting to specialized formatter component
    - Uses the streaming-only interface pattern
    
    [Implementation details]
    - Handles the specific invocation parameters, request formatting,
      and response parsing needed for effective use of the Claude 3.7 Sonnet model
    - Uses common code for shared functionality while implementing
      model-specific behavior through the request formatter
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
        [Function intent]
        Initialize a new Claude 3.7 Sonnet client.
        
        [Design principles]
        - Provide sensible defaults for Claude 3.7 Sonnet
        - Support all common initialization parameters
        - Allow customization of model-specific parameters
        
        [Implementation details]
        - Calls parent class initializer with common parameters
        - Sets up model-specific parameters with appropriate defaults
        - Configures logging and prompt management
        
        Args:
            model_id: The Bedrock model ID (defaults to Claude 3.7 Sonnet)
            region: AWS region for the Bedrock service
            max_retries: Maximum number of retry attempts for AWS API calls
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds (higher for Claude)
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
        
        [Design principles]
        - Maintain backwards compatibility with existing code
        - Reuse common implementation to avoid duplication
        
        [Implementation details]
        - Delegates to the common implementation in BedrockClientMixin
        - Handles error conditions appropriately
        
        Args:
            prompt_name: Name of the prompt template to use
            **kwargs: Parameters for the prompt template
            
        Returns:
            Formatted prompt string
            
        Raises:
            BedrockClientError: If prompt formatting fails
        """
        return super().format_prompt(self.prompt_manager, prompt_name, **kwargs)
        
    def invoke(
        self, 
        messages: Union[str, List[Union[Dict[str, Any], ModelMessage]], Dict[str, Any]], 
        stream: bool = True, 
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        [Function intent]
        Invoke the Claude 3.7 Sonnet model with streaming response.
        This universal interface handles both single-shot queries and
        conversational interactions.
        
        [Design principles]
        - Implement streaming-only pattern for all interactions
        - Support both single-shot and conversational contexts
        - Delegate actual invocation to common implementation
        
        [Implementation details]
        - Creates the appropriate request formatter with model-specific parameters
        - Uses the common invoke_bedrock_model function for actual invocation
        - Passes through all parameters and handles both streaming and non-streaming cases
        
        Args:
            messages: Input in one of these formats:
                      - String: A simple prompt string for single-shot queries
                      - List[Dict|ModelMessage]: A conversation history
                      - Dict: A pre-formatted provider-specific request
            stream: Whether to stream the response (defaults to True)
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
        yield from invoke_bedrock_model(
            client=self,
            request_formatter=formatter,
            messages=messages,
            stream=stream,
            **kwargs
        )
