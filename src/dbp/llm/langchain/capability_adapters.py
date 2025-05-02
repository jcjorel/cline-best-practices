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
# Provides capability-aware adapters for LangChain that leverage model-specific
# capabilities. These adapters enable advanced features like reasoning, structured 
# output, and multimodal processing through a unified interface, while maintaining
# compatibility with LangChain's ecosystem.
###############################################################################
# [Source file design principles]
# - Clean capability discovery and validation
# - Unified interface for diverse model capabilities
# - Graceful fallback when capabilities are unavailable
# - Strong integration with LangChain's callback system
# - Support for streaming and async operations
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with LangChain interfaces
# - Must handle capability discovery and validation
# - Must provide graceful fallbacks for unsupported capabilities
# - Must integrate with our capability-enhanced model clients
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/llm/bedrock/enhanced_base.py
# system:asyncio
# system:logging
# system:typing
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T13:21:00Z : Created during code refactoring by CodeAssistant
# * Split capability-aware adapters into separate file from base adapters
# * Moved CapabilityAwareLLMAdapter from adapters.py
# * Updated imports and maintained compatibility
###############################################################################

"""
Capability-aware adapters for LangChain that leverage model-specific capabilities.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable, Type, Mapping, cast

from langchain_core.language_models import BaseLLM
from langchain_core.outputs import LLMResult, Generation
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.pydantic_v1 import root_validator

from ..common.base import ModelClientBase
from ..common.exceptions import LLMError, UnsupportedFeatureError
from ..bedrock.enhanced_base import EnhancedBedrockBase, ModelCapability


class CapabilityAwareLLMAdapter(BaseLLM):
    """
    [Class intent]
    Adapts capability-aware model clients to LangChain's LLM interface,
    enabling the use of model-specific capabilities through a unified interface.
    This adapter provides access to enhanced capabilities like reasoning,
    structured outputs, multimodal content processing, etc.
    
    [Design principles]
    - Capability discovery and validation
    - Unified interface for diverse model capabilities
    - Clean integration with LangChain
    - Graceful fallbacks when capabilities are unavailable
    
    [Implementation details]
    - Uses EnhancedBedrockBase capability system
    - Maps LangChain parameters to capability-based APIs
    - Handles errors when capabilities are unavailable
    - Provides specialized methods for common capabilities
    """
    
    model_client: EnhancedBedrockBase
    client_kwargs: Dict[str, Any]
    streaming: bool = True
    
    # Capability flags for easier checking
    _capabilities: Dict[str, bool] = {}
    
    def __init__(
        self,
        model_client: EnhancedBedrockBase,
        streaming: bool = True,
        **kwargs
    ):
        """
        [Method intent]
        Initialize the capability-aware adapter with an enhanced model client.
        
        [Design principles]
        - Verify client compatibility
        - Discover and cache capabilities
        - Proper error handling for initialization
        
        [Implementation details]
        - Verifies client is capability-aware
        - Sets up capability discovery
        - Initializes base adapter functionality
        
        Args:
            model_client: EnhancedBedrockBase model client instance
            streaming: Whether to use streaming by default
            **kwargs: Additional arguments for LangChain
            
        Raises:
            TypeError: If model_client is not an EnhancedBedrockBase instance
        """
        # Type checking
        if not isinstance(model_client, EnhancedBedrockBase):
            raise TypeError("CapabilityAwareLLMAdapter requires an EnhancedBedrockBase model client")
        
        # Initialize base fields
        self.model_client = model_client
        self.client_kwargs = {}
        self.streaming = streaming
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set standard LangChain fields
        self.model_client_class = model_client.__class__.__name__
        self.model_id = model_client.model_id
        
        # Initialize parent
        super().__init__(**kwargs)
    
    @root_validator(pre=True)
    def setup_capabilities(cls, values):
        """
        [Method intent]
        Set up capability discovery for the model client.
        This validator runs before initialization is complete and 
        prepares the capability caching.
        
        [Design principles]
        - Early capability discovery
        - Non-blocking setup
        - Handle missing capabilities gracefully
        
        [Implementation details]
        - Creates event for capability discovery
        - Sets up initialization sequence
        - Returns values without modification
        
        Args:
            values: The values being validated
            
        Returns:
            Dict[str, Any]: Unmodified values
        """
        # Just set up the capability cache - we'll populate it later
        values["_capabilities"] = {}
        return values
    
    async def _initialize_capabilities(self):
        """
        [Method intent]
        Initialize and cache model capabilities asynchronously.
        
        [Design principles]
        - Lazy initialization of capabilities
        - Full capability discovery
        - Graceful error handling
        
        [Implementation details]
        - Gets capabilities from the model client
        - Caches results for future use
        - Handles errors during capability discovery
        
        Raises:
            LLMError: If capability discovery fails
        """
        if not self._capabilities:
            try:
                # Initialize model client if needed
                if not self.model_client.is_initialized():
                    await self.model_client.initialize()
                
                # Get and cache capabilities
                capabilities = await self.model_client.get_model_capabilities()
                self._capabilities = capabilities
                self.logger.debug(f"Discovered capabilities: {capabilities}")
            except Exception as e:
                self.logger.error(f"Failed to initialize capabilities: {str(e)}")
                # Initialize with empty capabilities
                self._capabilities = {}
                raise LLMError(f"Failed to initialize capabilities: {str(e)}", e)
    
    @property
    def _llm_type(self) -> str:
        """
        [Method intent]
        Return type name for LangChain registry.
        
        [Design principles]
        - Clear identification of our adapter
        - Consistent naming convention
        - Include capability awareness
        
        [Implementation details]
        - Creates a clear identifier using our client class and capability awareness
        
        Returns:
            str: LLM type name for registry
        """
        return f"DBP-Capable-{self.model_client_class}"
    
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
        This method handles capability-specific parameters and features.
        
        [Design principles]
        - Capability-aware processing
        - Support for enhanced features
        - Fallback to standard generation
        
        [Implementation details]
        - Maps LangChain parameters to capability options
        - Processes prompts with appropriate capabilities
        - Falls back to basic generation when needed
        - Converts responses to LangChain format
        
        Args:
            prompts: List of prompts to complete
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            LLMResult: LangChain result container
        """
        # Initialize capabilities if needed
        await self._initialize_capabilities()
        
        generations = []
        
        # Prepare parameters
        model_kwargs = self.client_kwargs.copy()
        model_kwargs.update(kwargs)
        if stop:
            model_kwargs["stop_sequences"] = stop
        
        # Extract capability-specific parameters
        enhancement_type = kwargs.pop("enhancement_type", None)
        enhancement_options = kwargs.pop("enhancement_options", {})
        processing_type = kwargs.pop("processing_type", None)
        
        # Check for reasoning capability request
        if kwargs.pop("use_reasoning", False):
            enhancement_type = "reasoning"
        
        # Check for structured output request
        if kwargs.pop("structured_output", False):
            processing_type = "structured_output"
        
        # Process each prompt
        for i, prompt in enumerate(prompts):
            # Get callback for this specific prompt
            prompt_callback = run_manager.get_child() if run_manager else None
            
            try:
                # Process with capabilities if specified
                if enhancement_type or processing_type:
                    generation = await self._process_with_capabilities(
                        prompt, 
                        prompt_callback, 
                        enhancement_type=enhancement_type,
                        enhancement_options=enhancement_options,
                        processing_type=processing_type,
                        **model_kwargs
                    )
                else:
                    # Generate with standard method
                    generation = await self._process_prompt_stream(
                        prompt, prompt_callback, **model_kwargs
                    )
                
                generations.append([generation])
            except Exception as e:
                self.logger.error(f"Error processing prompt {i}: {str(e)}")
                # Create error generation
                error_gen = Generation(text=f"Error: {str(e)}", generation_info={"error": str(e)})
                generations.append([error_gen])
                
                # Handle callback for error
                if prompt_callback:
                    await prompt_callback.on_llm_error(str(e))
        
        return LLMResult(
            generations=generations, 
            llm_output={
                "model_id": self.model_id,
                "capabilities": self._capabilities
            }
        )
    
    async def _process_with_capabilities(
        self,
        prompt: str,
        run_manager: Optional[AsyncCallbackManagerForLLMRun],
        enhancement_type: Optional[str] = None,
        enhancement_options: Optional[Dict[str, Any]] = None,
        processing_type: Optional[str] = None,
        **kwargs
    ) -> Generation:
        """
        [Method intent]
        Process a prompt using model-specific capabilities.
        
        [Design principles]
        - Capability-specific processing
        - Consistent streaming and callback handling
        - Graceful fallback to standard methods
        
        [Implementation details]
        - Routes to appropriate capability-based methods
        - Handles streaming and callbacks
        - Falls back to standard generation when needed
        - Converts responses to LangChain format
        
        Args:
            prompt: Text prompt to complete
            run_manager: LangChain callback manager
            enhancement_type: Type of enhancement to apply
            enhancement_options: Options for the enhancement
            processing_type: Type of processing to apply
            **kwargs: Additional parameters for the model
            
        Returns:
            Generation: LangChain Generation object
        """
        # Start LangChain callbacks
        if run_manager:
            await run_manager.on_llm_start(
                {"name": self._llm_type},
                [prompt],
                invocation_params={
                    "enhancement_type": enhancement_type,
                    "processing_type": processing_type,
                    **kwargs
                },
            )
        
        try:
            # Initialize before streaming
            full_text = ""
            structured_output = None
            
            # Try enhanced generation if specified
            if enhancement_type:
                # Check if model supports the capability
                capability = enhancement_type
                if capability not in self._capabilities:
                    raise UnsupportedFeatureError(f"Model does not support the {enhancement_type} capability")
                
                # Use stream_enhanced_generation
                async for chunk in self.model_client.stream_enhanced_generation(
                    prompt, 
                    enhancement_type=enhancement_type,
                    enhancement_options=enhancement_options or {},
                    **kwargs
                ):
                    # Process chunk
                    if "delta" in chunk and "text" in chunk["delta"]:
                        chunk_text = chunk["delta"]["text"]
                        full_text += chunk_text
                        
                        # Send to callback
                        if run_manager:
                            await run_manager.on_llm_new_token(chunk_text)
                
            # Try content processing if specified
            elif processing_type:
                # Check if model supports the capability
                if processing_type not in self._capabilities:
                    raise UnsupportedFeatureError(f"Model does not support the {processing_type} capability")
                
                # Use process_content
                result = await self.model_client.process_content(
                    content=prompt,
                    content_type="text",
                    processing_type=processing_type,
                    **kwargs
                )
                
                # Handle different result types
                if isinstance(result, str):
                    full_text = result
                    if run_manager:
                        await run_manager.on_llm_new_token(full_text)
                elif isinstance(result, dict):
                    # Structured output
                    structured_output = result
                    full_text = str(result)
                    if run_manager:
                        await run_manager.on_llm_new_token("[Structured output available]")
                else:
                    # Unsupported result type
                    full_text = str(result)
                    if run_manager:
                        await run_manager.on_llm_new_token(full_text)
            
            # Fallback to standard generation if no capability specified
            else:
                # Just use standard stream_generate method
                async for chunk in self.model_client.stream_generate(prompt, **kwargs):
                    if "delta" in chunk and "text" in chunk["delta"]:
                        chunk_text = chunk["delta"]["text"]
                        full_text += chunk_text
                        
                        # Send to callback
                        if run_manager:
                            await run_manager.on_llm_new_token(chunk_text)
            
            # Create generation info
            generation_info = {}
            if enhancement_type:
                generation_info["enhancement_type"] = enhancement_type
            if processing_type:
                generation_info["processing_type"] = processing_type
            if structured_output:
                generation_info["structured_output"] = structured_output
            
            # Create Generation
            generation = Generation(text=full_text, generation_info=generation_info)
            
            # Final callback
            if run_manager:
                await run_manager.on_llm_end({"generations": [[generation]]})
                
            return generation
            
        except Exception as e:
            # Log error
            self.logger.error(f"Error in capability processing: {str(e)}")
            
            # Handle callback for error
            if run_manager:
                await run_manager.on_llm_error(str(e))
            
            # Create fallback generation - delegate to standard processing
            if isinstance(e, UnsupportedFeatureError):
                self.logger.warning(f"Falling back to standard generation due to capability error: {str(e)}")
                return await self._process_prompt_stream(prompt, run_manager, **kwargs)
            
            # Create error generation
            error_text = f"Error: {str(e)}"
            return Generation(text=error_text, generation_info={"error": str(e)})
    
    async def _process_prompt_stream(
        self,
        prompt: str,
        run_manager: Optional[AsyncCallbackManagerForLLMRun],
        **kwargs
    ) -> Generation:
        """
        [Method intent]
        Process a prompt with standard streaming.
        
        [Design principles]
        - Standard streaming fallback
        - Consistent with base adapter implementation
        - Complete callback integration
        
        [Implementation details]
        - Uses standard stream_chat or stream_generate
        - Handles callbacks with streaming chunks
        - Creates standard Generation result
        
        Args:
            prompt: Text prompt to process
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
            
            # Use appropriate streaming method based on input format
            if isinstance(prompt, list):
                # Assume it's a messages list for chat
                async for chunk in self.model_client.stream_chat(prompt, **kwargs):
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
            else:
                # Standard prompt case
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
            self.logger.error(f"Error in stream processing: {str(e)}")
            
            # Handle callback for error
            if run_manager:
                await run_manager.on_llm_error(str(e))
            
            # Create error generation
            error_text = f"Error: {str(e)}"
            return Generation(text=error_text, generation_info={"error": str(e)})
    
    # Convenience methods for common capabilities
    
    async def generate_with_reasoning(
        self, 
        prompt: str, 
        **kwargs
    ) -> Generation:
        """
        [Method intent]
        Generate a response with reasoning capability.
        
        [Design principles]
        - Simple interface for reasoning capability
        - Direct access to reasoning features
        - Error handling for unsupported models
        
        [Implementation details]
        - Uses _process_with_capabilities with reasoning enhancement
        - Verifies model supports reasoning
        - Returns structured generation with reasoning
        
        Args:
            prompt: Text prompt to process
            **kwargs: Additional parameters for the model
            
        Returns:
            Generation: LangChain Generation object
        """
        # Initialize capabilities if needed
        await self._initialize_capabilities()
        
        # Check for reasoning capability
        if "reasoning" not in self._capabilities:
            raise UnsupportedFeatureError("Model does not support reasoning capability")
        
        # Process with reasoning capability
        return await self._process_with_capabilities(
            prompt,
            run_manager=None,
            enhancement_type="reasoning",
            **kwargs
        )
    
    async def generate_structured_output(
        self, 
        prompt: str, 
        format_instructions: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Generate structured output from a prompt.
        
        [Design principles]
        - Simple interface for structured output capability
        - Direct access to structure features
        - Support for format instructions
        
        [Implementation details]
        - Uses _process_with_capabilities with structured_output processing
        - Verifies model supports structured output
        - Returns extracted structured data
        
        Args:
            prompt: Text prompt to process
            format_instructions: Instructions for output format
            **kwargs: Additional parameters for the model
            
        Returns:
            Dict[str, Any]: Structured output data
        """
        # Initialize capabilities if needed
        await self._initialize_capabilities()
        
        # Check for structured output capability
        if "structured_output" not in self._capabilities:
            raise UnsupportedFeatureError("Model does not support structured output capability")
        
        # Process with structured output capability
        options = {}
        if format_instructions:
            options["format_instructions"] = format_instructions
            
        generation = await self._process_with_capabilities(
            prompt,
            run_manager=None,
            processing_type="structured_output",
            enhancement_options=options,
            **kwargs
        )
        
        # Extract structured output from generation info
        if "structured_output" in generation.generation_info:
            return generation.generation_info["structured_output"]
        
        # Fallback if no structured data
        raise LLMError("Failed to generate structured output")
    
    async def extract_keywords(
        self, 
        text: str, 
        max_results: int = 10,
        **kwargs
    ) -> List[str]:
        """
        [Method intent]
        Extract keywords from a text using model's capabilities.
        
        [Design principles]
        - Simple interface for keyword extraction
        - Direct access to extraction features
        - Consistent return format
        
        [Implementation details]
        - Uses process_content with keyword_extraction processing type
        - Verifies model supports keyword extraction
        - Returns list of extracted keywords
        
        Args:
            text: Text to extract keywords from
            max_results: Maximum number of keywords to return
            **kwargs: Additional parameters
            
        Returns:
            List[str]: Extracted keywords
        """
        # Initialize capabilities if needed
        await self._initialize_capabilities()
        
        # Check for keyword extraction capability
        if "keyword_extraction" not in self._capabilities:
            raise UnsupportedFeatureError("Model does not support keyword extraction capability")
        
        # Process with keyword extraction capability
        result = await self.model_client.process_content(
            content=text,
            processing_type="keyword_extraction",
            options={"max_results": max_results},
            **kwargs
        )
        
        # Return keywords list
        if isinstance(result, list):
            return result
        
        # Fallback if unexpected result type
        raise LLMError(f"Unexpected result type from keyword extraction: {type(result)}")
    
    async def summarize_text(
        self, 
        text: str, 
        max_length: int = 200,
        focus_on: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        [Method intent]
        Summarize text using model's capabilities.
        
        [Design principles]
        - Simple interface for summarization
        - Direct access to summarization features
        - Support for summarization parameters
        
        [Implementation details]
        - Uses process_content with summarization processing type
        - Verifies model supports summarization
        - Returns summarized text
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            focus_on: Optional aspect to focus on
            **kwargs: Additional parameters
            
        Returns:
            str: Summarized text
        """
        # Initialize capabilities if needed
        await self._initialize_capabilities()
        
        # Check for summarization capability
        if "summarization" not in self._capabilities:
            raise UnsupportedFeatureError("Model does not support summarization capability")
        
        # Process with summarization capability
        options = {
            "max_length": max_length
        }
        if focus_on:
            options["focus_on"] = focus_on
            
        result = await self.model_client.process_content(
            content=text,
            processing_type="summarization",
            options=options,
            **kwargs
        )
        
        # Return summarized text
        if isinstance(result, str):
            return result
        
        # Fallback if unexpected result type
        raise LLMError(f"Unexpected result type from summarization: {type(result)}")
