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
# Provides adapters that allow our custom LLM clients to be used with LangChain's
# interfaces. This enables seamless integration with LangChain's ecosystem of
# chains, agents, and tools while maintaining our streaming-first approach.
###############################################################################
# [Source file design principles]
# - Clean adaptation between our API and LangChain's interface
# - Streaming-first approach with callback integration
# - Proper error handling and fallback mechanisms
# - Minimal overhead for performance
# - Comprehensive docstrings for public methods
###############################################################################
# [Source file constraints]
# - Must implement LangChain's BaseLLM interface correctly
# - Must handle all callback mechanisms as per LangChain specs
# - Must maintain compatibility with streaming responses
# - Must properly convert between response formats
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/common/exceptions.py
# system:asyncio
# system:typing
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T13:13:00Z : Added capability-aware LangChain integration by CodeAssistant
# * Implemented CapabilityAwareLLMAdapter to use with EnhancedBedrockBase models
# * Added capability-based method routing for specialized features
# * Added convenience methods for common capabilities like reasoning, summarization
# * Implemented graceful fallbacks for unsupported capabilities
# 2025-05-02T11:25:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Implemented LangChainLLMAdapter for integration with LangChain
# * Added streaming support with callbacks
# * Added prompt handling and response conversion
###############################################################################

"""
Adapters for integrating custom LLM clients with LangChain's interfaces.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable, Type, Mapping, cast

from langchain_core.language_models import BaseLLM
from langchain_core.outputs import LLMResult, Generation
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from ..common.base import ModelClientBase
from ..common.exceptions import LLMError

class LangChainLLMAdapter(BaseLLM):
    """
    [Class intent]
    Adapts our custom LLM clients to LangChain's LLM interface.
    This adapter allows our LLM implementations to be used anywhere
    LangChain expects a language model, enabling seamless integration
    with chains, agents, and other LangChain components.
    
    [Design principles]
    - Clean adaptation between our client API and LangChain's interface
    - Streaming-first approach with fallback to non-streaming
    - Proper callback handling for LangChain's observability
    - Minimal overhead for performance
    
    [Implementation details]
    - Implements BaseLLM for compatibility with LangChain
    - Adapts our streaming responses to LangChain's callback system
    - Handles input/output conversion between formats
    - Preserves model configuration options
    """
    
    model_client: ModelClientBase
    client_kwargs: Dict[str, Any]
    streaming: bool = True
    
    def __init__(
        self,
        model_client: ModelClientBase,
        streaming: bool = True,
        **kwargs
    ):
        """
        [Method intent]
        Initialize the LangChain LLM adapter with a model client.
        
        [Design principles]
        - Simple initialization with our model client
        - Support for LangChain-specific configuration
        - Clean separation of concerns
        
        [Implementation details]
        - Stores model client for delegation
        - Passes LangChain-specific kwargs to parent class
        - Sets up logging for adapter operations
        
        Args:
            model_client: Instance of our model client
            streaming: Whether to use streaming by default
            **kwargs: Additional arguments for LangChain
        """
        # Initialize our adapter fields
        self.model_client = model_client
        self.client_kwargs = {}
        self.streaming = streaming
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set standard LangChain fields
        self.model_client_class = model_client.__class__.__name__
        self.model_id = model_client.model_id
        
        # Initialize parent
        super().__init__(**kwargs)
    
    @property
    def _llm_type(self) -> str:
        """
        [Method intent]
        Return type name for LangChain registry.
        
        [Design principles]
        - Clear identification of our adapter
        - Consistent naming convention
        
        [Implementation details]
        - Creates a clear identifier using our client class
        
        Returns:
            str: LLM type name for registry
        """
        return f"DBP-{self.model_client_class}"
    
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """
        [Method intent]
        Generate completions for prompts using synchronous interface.
        
        [Design principles]
        - Adaptation to LangChain's synchronous interface
        - Proper callback integration
        - Support for stop sequences
        
        [Implementation details]
        - Uses asyncio to run async methods in sync context
        - Delegates to _agenerate for actual implementation
        - Handles LangChain callbacks
        
        Args:
            prompts: List of prompts to complete
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            LLMResult: LangChain result container
        """
        # Use asyncio to run async method in sync context
        return asyncio.run(self._agenerate(prompts, stop, run_manager, **kwargs))
    
    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """
        [Method intent]
        Generate completions for prompts using asynchronous interface.
        
        [Design principles]
        - Streaming as primary interaction pattern
        - Proper error handling and reporting
        - Effective callback integration
        
        [Implementation details]
        - Processes prompts sequentially
        - Uses streaming and collects results
        - Handles LangChain callbacks for each chunk
        - Converts our format to LangChain's LLMResult
        
        Args:
            prompts: List of prompts to complete
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            LLMResult: LangChain result container
        """
        generations = []
        
        # Prepare parameters
        model_kwargs = self.client_kwargs.copy()
        model_kwargs.update(kwargs)
        if stop:
            model_kwargs["stop_sequences"] = stop
        
        # Process each prompt
        for i, prompt in enumerate(prompts):
            # Get callback for this specific prompt
            prompt_callback = run_manager.get_child() if run_manager else None
            
            # Generate text via streaming
            generation = await self._process_prompt_stream(
                prompt, prompt_callback, **model_kwargs
            )
            generations.append([generation])
        
        return LLMResult(generations=generations, llm_output={"model_id": self.model_id})
    
    async def _process_prompt_stream(
        self,
        prompt: str,
        run_manager: Optional[AsyncCallbackManagerForLLMRun],
        **kwargs
    ) -> Generation:
        """
        [Method intent]
        Process a single prompt with streaming and callbacks.
        
        [Design principles]
        - Streaming focused for efficiency
        - Complete callback integration
        - Proper error handling
        
        [Implementation details]
        - Streams response chunks from model client
        - Sends each chunk to LangChain callbacks
        - Builds complete response for final Generation
        - Handles errors with appropriate responses
        
        Args:
            prompt: Text prompt to complete
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            Generation: LangChain Generation object
        """
        # Initialize before streaming
        full_text = ""
        stop_reason = None
        
        try:
            # Start LangChain callbacks
            if run_manager:
                await run_manager.on_llm_start(
                    {"name": self._llm_type},
                    [prompt],
                    invocation_params=kwargs,
                )
            
            # Initialize model client if not already done
            if not self.model_client.is_initialized():
                await self.model_client.initialize()
            
            # Stream generate from our client
            async for chunk in self.model_client.stream_generate(prompt, **kwargs):
                # Extract text chunk if available
                if "delta" in chunk and "text" in chunk["delta"]:
                    chunk_text = chunk["delta"]["text"]
                    full_text += chunk_text
                    
                    # Send chunk to callback if available
                    if run_manager:
                        await run_manager.on_llm_new_token(chunk_text)
                        
                # Check for stop reason
                if chunk.get("type") == "message_stop" and "stop_reason" in chunk:
                    stop_reason = chunk["stop_reason"]
            
            # Create Generation
            generation_info = {"stop_reason": stop_reason} if stop_reason else {}
            generation = Generation(text=full_text, generation_info=generation_info)
            
            # Final callback
            if run_manager:
                await run_manager.on_llm_end({"generations": [[generation]]})
                
            return generation
        
        except Exception as e:
            # Log error
            self.logger.error(f"Error in LLM generation: {str(e)}")
            
            # Handle callback for error
            if run_manager:
                await run_manager.on_llm_error(str(e))
            
            # Create error generation
            error_text = f"Error: {str(e)}"
            return Generation(text=error_text, generation_info={"error": str(e)})
