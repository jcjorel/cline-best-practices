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
# Provides common functionality for Bedrock model clients, reducing code duplication
# across different model implementations. This includes shared methods for prompt
# formatting, model invocation, error handling, and response processing.
###############################################################################
# [Source file design principles]
# - Extract common patterns from model-specific clients into reusable components
# - Implement the template method pattern for model invocation flow
# - Provide hooks for model-specific customizations
# - Use composition to handle varying request/response formats
# - Maintain consistent error handling and logging across all clients
###############################################################################
# [Source file constraints]
# - Must not introduce tight coupling between specific model implementations
# - Must preserve the ability to add new model types with minimal code
# - Must maintain compatibility with the existing BedrockModelClientBase interface
# - Must handle model-specific parameters appropriately
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T13:55:00Z : Initial creation of common Bedrock client utilities by CodeAssistant
# * Extracted common methods from model-specific clients
# * Implemented shared prompt formatting and model invocation logic
# * Created request formatter interface for model-specific formatting
###############################################################################

import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator, Optional, Union, List, TypeVar, Generic

from .bedrock_base import BedrockModelClientBase, BedrockClientError
from .prompt_manager import LLMPromptManager, PromptLoadError

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Type for model-specific request body
R = TypeVar('R')  # Type for model-specific response parsing

class BedrockRequestFormatter(ABC, Generic[T]):
    """
    [Class intent]
    Abstract interface for formatters that prepare request bodies for specific Bedrock models.
    
    [Implementation details]
    Defines the contract for model-specific request formatting, allowing the common
    invocation code to remain model-agnostic while supporting different request formats.
    
    [Design principles]
    - Separates request formatting logic from invocation logic
    - Enables model-specific request formatting without duplicating invocation code
    - Uses the strategy pattern to allow runtime selection of formatters
    """
    
    @abstractmethod
    def format_request(self, prompt: Union[str, Dict[str, Any], List[Dict[str, Any]]], **kwargs) -> T:
        """
        Format a prompt into a model-specific request body.
        
        Args:
            prompt: The prompt content in various possible formats
            **kwargs: Additional model-specific parameters
            
        Returns:
            Properly formatted request body for the specific model
        """
        pass

class BedrockClientMixin:
    """
    [Class intent]
    Mixin that provides common functionality for Bedrock model clients.
    
    [Implementation details]
    Implements common methods that can be reused across different model client
    implementations to avoid code duplication.
    
    [Design principles]
    - Reduces code duplication through composition
    - Provides template method pattern for common workflows
    - Maintains consistent logging and error handling
    """
    
    def format_prompt(self, prompt_manager: LLMPromptManager, prompt_name: str, **kwargs) -> str:
        """
        [Function intent]
        Format a prompt using the provided prompt manager.
        
        [Implementation details]
        Uses the LLMPromptManager to load and format prompt templates
        with the provided parameters.
        
        [Design principles]
        - Encapsulates prompt handling logic
        - Provides clear error messages for debugging
        - Follows fail-fast principle for missing dependencies
        
        Args:
            prompt_manager: LLMPromptManager instance to use
            prompt_name: Name of the prompt template to use
            **kwargs: Parameters for the prompt template
            
        Returns:
            Formatted prompt string
            
        Raises:
            BedrockClientError: If prompt formatting fails
        """
        if not prompt_manager:
            raise BedrockClientError("Prompt manager not configured for this client")
            
        try:
            return prompt_manager.format_prompt(prompt_name, **kwargs)
        except PromptLoadError as e:
            raise BedrockClientError(f"Failed to load prompt template '{prompt_name}': {e}") from e
        except Exception as e:
            raise BedrockClientError(f"Failed to format prompt '{prompt_name}': {e}") from e

def invoke_model_common(
    client: BedrockModelClientBase,
    request_formatter: BedrockRequestFormatter[T],
    prompt: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    **kwargs
) -> Dict[str, Any]:
    """
    [Function intent]
    Common implementation for invoking a Bedrock model with error handling and logging.
    
    [Implementation details]
    Provides a reusable implementation of the model invocation workflow including
    initialization, request preparation, error handling, and response processing.
    
    [Design principles]
    - Template method pattern for standard invocation flow
    - Consistent error handling and logging across model types
    - Separation of model-specific formatting from invocation logic
    
    Args:
        client: The Bedrock client to use for invocation
        request_formatter: Model-specific request formatter
        prompt: The prompt in various possible formats
        **kwargs: Additional model-specific parameters
        
    Returns:
        Dict[str, Any]: The model's response
        
    Raises:
        BedrockClientError: On invocation failure
    """
    # Initialize if not already done
    if not client.initialized:
        client.initialize()
    
    # Generate a request ID for correlation
    request_id = str(uuid.uuid4())
    
    client.logger.info({
        "message": f"Invoking {client.__class__.__name__}",
        "request_id": request_id,
        "model_id": client.model_id,
        "prompt_type": type(prompt).__name__
    })
    
    try:
        # Prepare the request body using the formatter
        request_body = request_formatter.format_request(prompt, **kwargs)
        
        # Log request details at debug level
        client.logger.debug({
            "message": "Request parameters",
            "request_id": request_id,
            "model_parameters": {k: v for k, v in request_body.items() if k not in ['inputText', 'messages', 'content']}
        })
        
        # Invoke the model
        response = client.bedrock_client.invoke_model(
            modelId=client.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        
        client.logger.info({
            "message": f"{client.__class__.__name__} invocation successful",
            "request_id": request_id,
            "model_id": client.model_id,
            "response_type": type(response_body).__name__
        })
        
        return response_body
        
    except client.bedrock_client.exceptions.ModelTimeoutException as e:
        client.logger.error({
            "message": "Model timeout during invocation",
            "request_id": request_id,
            "model_id": client.model_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
        raise BedrockClientError(f"Bedrock model timeout: {str(e)}") from e
        
    except client.bedrock_client.exceptions.ModelErrorException as e:
        client.logger.error({
            "message": "Model error during invocation",
            "request_id": request_id,
            "model_id": client.model_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
        raise BedrockClientError(f"Bedrock model error: {str(e)}") from e
        
    except Exception as e:
        client.logger.error({
            "message": f"Failed to invoke {client.__class__.__name__}",
            "request_id": request_id,
            "model_id": client.model_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        }, exc_info=True)
        raise BedrockClientError(f"Failed to invoke {client.__class__.__name__}: {str(e)}") from e

def invoke_model_stream_common(
    client: BedrockModelClientBase,
    request_formatter: BedrockRequestFormatter[T],
    prompt: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    **kwargs
) -> Iterator[Dict[str, Any]]:
    """
    [Function intent]
    Common implementation for streaming invocation of a Bedrock model.
    
    [Implementation details]
    Provides a reusable implementation of the streaming model invocation workflow including
    initialization, request preparation, chunk processing, and error handling.
    
    [Design principles]
    - Template method pattern for standard streaming flow
    - Consistent error handling and logging across model types
    - Efficient processing of streamed response chunks
    
    Args:
        client: The Bedrock client to use for invocation
        request_formatter: Model-specific request formatter
        prompt: The prompt in various possible formats
        **kwargs: Additional model-specific parameters
        
    Yields:
        Dict[str, Any]: Chunks of the model's response
        
    Raises:
        BedrockClientError: On invocation failure
    """
    # Initialize if not already done
    if not client.initialized:
        client.initialize()
    
    # Generate a request ID for correlation
    request_id = str(uuid.uuid4())
    
    client.logger.info({
        "message": f"Invoking {client.__class__.__name__} (streaming)",
        "request_id": request_id,
        "model_id": client.model_id,
        "prompt_type": type(prompt).__name__
    })
    
    try:
        # Prepare the request body using the formatter
        request_body = request_formatter.format_request(prompt, **kwargs)
        
        # Log request details at debug level
        client.logger.debug({
            "message": "Streaming request parameters",
            "request_id": request_id,
            "model_parameters": {k: v for k, v in request_body.items() if k not in ['inputText', 'messages', 'content']}
        })
        
        # Invoke the model with streaming
        response_stream = client.bedrock_client.invoke_model_with_response_stream(
            modelId=client.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Process and yield each chunk
        for event in response_stream.get("body"):
            if event.get("chunk"):
                chunk_bytes = event["chunk"]["bytes"]
                chunk_data = json.loads(chunk_bytes.decode("utf-8"))
                
                client.logger.debug({
                    "message": "Received response chunk",
                    "request_id": request_id,
                    "chunk_size": len(chunk_bytes)
                })
                
                yield chunk_data
        
        client.logger.info({
            "message": f"{client.__class__.__name__} streaming invocation completed",
            "request_id": request_id,
            "model_id": client.model_id
        })
        
    except client.bedrock_client.exceptions.ModelTimeoutException as e:
        client.logger.error({
            "message": "Model timeout during streaming invocation",
            "request_id": request_id,
            "model_id": client.model_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
        raise BedrockClientError(f"Bedrock model timeout during streaming: {str(e)}") from e
        
    except client.bedrock_client.exceptions.ModelErrorException as e:
        client.logger.error({
            "message": "Model error during streaming invocation",
            "request_id": request_id,
            "model_id": client.model_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
        raise BedrockClientError(f"Bedrock model error during streaming: {str(e)}") from e
        
    except Exception as e:
        client.logger.error({
            "message": f"Failed during {client.__class__.__name__} streaming invocation",
            "request_id": request_id,
            "model_id": client.model_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        }, exc_info=True)
        raise BedrockClientError(f"Failed during {client.__class__.__name__} streaming invocation: {str(e)}") from e
