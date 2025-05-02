# Phase 10: LangChain Integration

This phase implements the integration between our custom Bedrock clients and the LangChain ecosystem. It focuses on creating adapters, wrappers, and utilities to enable seamless use of our LLM implementations within LangChain's chains, agents, and tools.

## Objectives

1. Create LangChain adapters for our LLM clients
2. Implement LLM wrappers compatible with LangChain's interface
3. Build streaming integration for LangChain
4. Create chain factories for common LangChain patterns

## LangChainAdapter Implementation

Create the LangChain adapter in `src/dbp/llm/langchain/adapters.py`:

```python
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable, Type, Mapping

from langchain_core.language_models import BaseLLM, BaseLanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import LLMResult, ChatResult, ChatGenerationChunk, Generation
from langchain_core.messages import (
    BaseMessage, AIMessage, HumanMessage, SystemMessage, ChatMessage
)
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from src.dbp.llm.common.base import ModelClientBase
from src.dbp.llm.common.exceptions import LLMError

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
    
    def __init__(
        self,
        model_client: ModelClientBase,
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
            **kwargs: Additional arguments for LangChain
        """
        self.model_client = model_client
        self.client_kwargs = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set standard LangChain fields
        self.model_client_class = model_client.__class__.__name__
        self.model_id = model_client.model_id
        
        # Initialize parent
        super().__init__(**kwargs)
    
    @property
    def _llm_type(self) -> str:
        """Return type name for LangChain registry."""
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
        full_text = ""
        
        try:
            # Stream generate from our client
            async for chunk in self.model_client.stream_generate(prompt, **kwargs):
                # Extract text chunk
                if "delta" in chunk and "text" in chunk["delta"]:
                    chunk_text = chunk["delta"]["text"]
                    full_text += chunk_text
                    
                    # Send chunk to callback if available
                    if run_manager:
                        await run_manager.on_llm_new_token(chunk_text)
            
            # Create Generation
            generation = Generation(text=full_text)
            return generation
        
        except Exception as e:
            # Log error
            self.logger.error(f"Error in LLM generation: {str(e)}")
            
            # Create error generation
            return Generation(text=f"Error: {str(e)}")
```

## LangChainChatAdapter Implementation

Create the LangChain chat model adapter in `src/dbp/llm/langchain/chat_adapters.py`:

```python
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Callable, Type, Mapping

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGenerationChunk, LLMResult
from langchain_core.messages import (
    BaseMessage, AIMessage, HumanMessage, SystemMessage, ChatMessage
)
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from src.dbp.llm.common.base import ModelClientBase
from src.dbp.llm.common.exceptions import LLMError

class LangChainChatAdapter(BaseChatModel):
    """
    [Class intent]
    Adapts our custom LLM clients to LangChain's Chat Model interface.
    This adapter enables our LLM implementations to work with LangChain's
    chat-oriented components, supporting conversation history and specialized
    chat-based chains and agents.
    
    [Design principles]
    - Specialized for chat interactions
    - Support for conversation history
    - Streaming-first approach for efficiency
    - Clean message format conversion
    
    [Implementation details]
    - Implements BaseChatModel for LangChain compatibility
    - Converts between our message format and LangChain's
    - Handles streaming responses with callback integration
    - Preserves model configuration options
    """
    
    model_client: ModelClientBase
    client_kwargs: Dict[str, Any]
    
    def __init__(
        self,
        model_client: ModelClientBase,
        **kwargs
    ):
        """
        [Method intent]
        Initialize the LangChain Chat adapter with a model client.
        
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
            **kwargs: Additional arguments for LangChain
        """
        self.model_client = model_client
        self.client_kwargs = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set standard LangChain fields
        self.model_client_class = model_client.__class__.__name__
        self.model_id = model_client.model_id
        
        # Initialize parent
        super().__init__(**kwargs)
    
    @property
    def _llm_type(self) -> str:
        """Return type name for LangChain registry."""
        return f"DBP-Chat-{self.model_client_class}"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        [Method intent]
        Generate completions for chat messages using synchronous interface.
        
        [Design principles]
        - Adaptation to LangChain's synchronous interface
        - Proper callback integration
        - Support for stop sequences
        
        [Implementation details]
        - Uses asyncio to run async methods in sync context
        - Delegates to _agenerate for actual implementation
        - Handles LangChain callbacks
        
        Args:
            messages: List of chat messages
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            ChatResult: LangChain result container
        """
        return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        [Method intent]
        Generate completions for chat messages using asynchronous interface.
        
        [Design principles]
        - Streaming as primary interaction pattern
        - Proper error handling and reporting
        - Message format conversion
        
        [Implementation details]
        - Converts LangChain messages to our format
        - Uses streaming and collects results
        - Handles LangChain callbacks for each chunk
        - Converts our format to LangChain's ChatResult
        
        Args:
            messages: List of chat messages
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            ChatResult: LangChain result container
        """
        # Convert LangChain messages to our format
        formatted_messages = self._convert_messages_to_client_format(messages)
        
        # Prepare parameters
        model_kwargs = self.client_kwargs.copy()
        model_kwargs.update(kwargs)
        if stop:
            model_kwargs["stop_sequences"] = stop
        
        # Stream response
        ai_content = await self._process_chat_stream(
            formatted_messages, run_manager, **model_kwargs
        )
        
        # Create AI message
        ai_message = AIMessage(content=ai_content)
        
        # Return chat result
        return ChatResult(generations=[[ai_message]], llm_output={"model_id": self.model_id})
    
    async def _process_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        run_manager: Optional[AsyncCallbackManagerForLLMRun],
        **kwargs
    ) -> str:
        """
        [Method intent]
        Process chat messages with streaming and callbacks.
        
        [Design principles]
        - Streaming focused for efficiency
        - Complete callback integration
        - Proper error handling
        
        [Implementation details]
        - Streams response chunks from model client
        - Sends each chunk to LangChain callbacks
        - Builds complete response for final ChatResult
        - Handles errors with appropriate responses
        
        Args:
            messages: Formatted messages for our client
            run_manager: LangChain callback manager
            **kwargs: Additional parameters for the model
            
        Returns:
            str: Complete AI response text
        """
        full_text = ""
        
        try:
            # Stream chat from our client
            async for chunk in self.model_client.stream_chat(messages, **kwargs):
                # Extract text chunk
                if "delta" in chunk and "text" in chunk["delta"]:
                    chunk_text = chunk["delta"]["text"]
                    full_text += chunk_text
                    
                    # Send chunk to callback if available
                    if run_manager:
                        await run_manager.on_llm_new_token(chunk_text)
            
            return full_text
        
        except Exception as e:
            # Log error
            self.logger.error(f"Error in chat generation: {str(e)}")
            
            # Return error message
            return f"Error: {str(e)}"
    
    def _convert_messages_to_client_format(
        self,
        messages: List[BaseMessage]
    ) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Convert LangChain messages to our client's format.
        
        [Design principles]
        - Clean format conversion
        - Support for all message types
        - Error handling for unsupported types
        
        [Implementation details]
        - Maps LangChain message types to roles
        - Extracts content from messages
        - Handles special message types
        
        Args:
            messages: List of LangChain messages
            
        Returns:
            List[Dict[str, Any]]: Messages in our client format
        """
        result = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            elif isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, ChatMessage):
                # Map custom roles
                role = message.role
            else:
                # Unknown message type
                self.logger.warning(f"Unknown message type: {type(message)}")
                role = "user"
            
            # Create message in our format
            result.append({
                "role": role,
                "content": message.content
            })
        
        return result
```

## LangChain Factory

Create utilities for creating LangChain chains and agents in `src/dbp/llm/langchain/factories.py`:

```python
import logging
from typing import Dict, Any, List, Optional, Union, Callable

from langchain_core.language_models import BaseLLM, BaseLanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor, initialize_agent, AgentType

from src.dbp.llm.common.base import ModelClientBase
from src.dbp.llm.langchain.adapters import LangChainLLMAdapter
from src.dbp.llm.langchain.chat_adapters import LangChainChatAdapter

class LangChainFactory:
    """
    [Class intent]
    Creates LangChain components using our LLM implementations.
    This factory simplifies the creation of common LangChain patterns
    like chains, agents, and other components, with our model clients.
    
    [Design principles]
    - Simplified LangChain component creation
    - Consistent configuration
    - Reusable patterns
    - Support for common LangChain use cases
    
    [Implementation details]
    - Creates appropriate adapters for our model clients
    - Configures LangChain components with best practices
    - Provides factory methods for common patterns
    - Handles validation and error checking
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Initialize the LangChain factory.
        
        [Design principles]
        - Minimal initialization
        - Support for customization
        
        [Implementation details]
        - Sets up logging
        
        Args:
            logger: Optional custom logger instance
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def create_llm_adapter(
        self, 
        model_client: ModelClientBase,
        **kwargs
    ) -> BaseLLM:
        """
        [Method intent]
        Create a LangChain LLM adapter for a model client.
        
        [Design principles]
        - Simple adapter creation
        - Support for customization
        - Type-safe interface
        
        [Implementation details]
        - Creates LangChainLLMAdapter with model client
        - Passes through additional kwargs
        
        Args:
            model_client: Our model client instance
            **kwargs: Additional LangChain configuration
            
        Returns:
            BaseLLM: LangChain-compatible LLM adapter
        """
        return LangChainLLMAdapter(model_client, **kwargs)
    
    def create_chat_adapter(
        self, 
        model_client: ModelClientBase,
        **kwargs
    ) -> BaseChatModel:
        """
        [Method intent]
        Create a LangChain Chat Model adapter for a model client.
        
        [Design principles]
        - Simple adapter creation
        - Support for customization
        - Type-safe interface
        
        [Implementation details]
        - Creates LangChainChatAdapter with model client
        - Passes through additional kwargs
        
        Args:
            model_client: Our model client instance
            **kwargs: Additional LangChain configuration
            
        Returns:
            BaseChatModel: LangChain-compatible Chat Model adapter
        """
        return LangChainChatAdapter(model_client, **kwargs)
    
    def create_llm_chain(
        self,
        model_client: ModelClientBase,
        prompt: Union[str, PromptTemplate],
        output_key: str = "text",
        **kwargs
    ) -> LLMChain:
        """
        [Method intent]
        Create a LangChain LLMChain with our model client.
        
        [Design principles]
        - Simplified chain creation
        - Support for different prompt formats
        - Customizable configuration
        
        [Implementation details]
        - Creates adapter for model client
        - Handles prompt formatting
        - Configures LLMChain with best practices
        
        Args:
            model_client: Our model client instance
            prompt: String template or PromptTemplate
            output_key: Key to use for chain output
            **kwargs: Additional LLMChain configuration
            
        Returns:
            LLMChain: Configured LangChain LLMChain
        """
        # Create LLM adapter
        llm = self.create_llm_adapter(model_client)
        
        # Handle prompt format
        if isinstance(prompt, str):
            # Create prompt template from string
            prompt = PromptTemplate.from_template(prompt)
        
        # Create LLM chain
        return LLMChain(
            llm=llm,
            prompt=prompt,
            output_key=output_key,
            **kwargs
        )
    
    def create_chat_chain(
        self,
        model_client: ModelClientBase,
        prompt: Union[str, List[Dict[str, Any]], ChatPromptTemplate],
        output_key: str = "text",
        **kwargs
    ) -> LLMChain:
        """
        [Method intent]
        Create a LangChain Chain with our chat model client.
        
        [Design principles]
        - Simplified chain creation for chat models
        - Support for different prompt formats
        - Customizable configuration
        
        [Implementation details]
        - Creates chat adapter for model client
        - Handles chat prompt formatting
        - Configures LLMChain with best practices
        
        Args:
            model_client: Our model client instance
            prompt: String template, message list, or ChatPromptTemplate
            output_key: Key to use for chain output
            **kwargs: Additional LLMChain configuration
            
        Returns:
            LLMChain: Configured LangChain LLMChain with chat model
        """
        # Create Chat adapter
        chat_model = self.create_chat_adapter(model_client)
        
        # Handle prompt format
        if isinstance(prompt, str):
            # Create chat prompt template with system message
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant."),
                ("user", prompt)
            ])
        elif isinstance(prompt, list):
            # Convert list to ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages(prompt)
        
        # Create LLM chain with chat model
        return LLMChain(
            llm=chat_model,
            prompt=prompt,
            output_key=output_key,
            **kwargs
        )
    
    def create_agent(
        self,
        model_client: ModelClientBase,
        tools: List[Any],
        agent_type: AgentType = AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        **kwargs
    ) -> AgentExecutor:
        """
        [Method intent]
        Create a LangChain Agent with our model client.
        
        [Design principles]
        - Simplified agent creation
        - Support for different agent types
        - Tool integration
        
        [Implementation details]
        - Creates adapter for model client
        - Initializes agent with tools
        - Configures agent with best practices
        
        Args:
            model_client: Our model client instance
            tools: List of LangChain tools
            agent_type: Type of agent to create
            **kwargs: Additional agent configuration
            
        Returns:
            AgentExecutor: Configured LangChain Agent
        """
        # Create LLM adapter
        llm = self.create_llm_adapter(model_client)
        
        # Initialize agent
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=agent_type,
            handle_parsing_errors=True,
            **kwargs
        )
        
        return agent
```

## Integration Utilities

Create LangChain integration utilities in `src/dbp/llm/langchain/utils.py`:

```python
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union

from langchain_core.callbacks import CallbackManager, AsyncCallbackManager
from langchain_core.tools import BaseTool

from src.dbp.llm.common.tool_registry import ToolRegistry
from src.dbp.llm.common.exceptions import ToolError

def convert_registry_tools_to_langchain(
    tool_registry: ToolRegistry,
    tags: Optional[List[str]] = None
) -> List[BaseTool]:
    """
    [Function intent]
    Convert tools from our ToolRegistry to LangChain tools.
    
    [Design principles]
    - Seamless tool conversion
    - Support for filtering by tags
    - Clean interface
    
    [Implementation details]
    - Retrieves tools from registry
    - Converts to LangChain format
    - Handles tool metadata
    
    Args:
        tool_registry: Our tool registry instance
        tags: Optional list of tags to filter tools
        
    Returns:
        List[BaseTool]: List of LangChain tools
    """
    if tags:
        # Get tools with specified tags
        langchain_tools = tool_registry.get_langchain_tools(tags)
    else:
        # Get all tools
        langchain_tools = tool_registry.get_langchain_tools()
        
    return langchain_tools

def create_tracing_callback_manager(
    session_id: str,
    async_mode: bool = False
) -> Union[CallbackManager, AsyncCallbackManager]:
    """
    [Function intent]
    Create a LangChain callback manager with tracing enabled.
    
    [Design principles]
    - Support for LangChain tracing
    - Simple interface
    - Synchronous and asynchronous support
    
    [Implementation details]
    - Creates appropriate callback manager type
    - Configures with session ID for tracing
    - Sets up default handlers
    
    Args:
        session_id: Unique session ID for tracing
        async_mode: Whether to create an async callback manager
        
    Returns:
        Union[CallbackManager, AsyncCallbackManager]: Configured callback manager
    """
    try:
        # Import LangChain tracing
        from langchain_core.tracers import LangChainTracer
        from langchain_core.callbacks import StdOutCallbackHandler
        
        # Create tracer
        tracer = LangChainTracer(session_id=session_id)
        
        # Create callback handler list
        handlers = [tracer, StdOutCallbackHandler()]
        
        # Create manager based on mode
        if async_mode:
            return AsyncCallbackManager(handlers=handlers)
        else:
            return CallbackManager(handlers=handlers)
            
    except ImportError:
        # Tracing not available, return minimal manager
        if async_mode:
            return AsyncCallbackManager()
        else:
            return CallbackManager()
```

## Implementation Steps

1. **Create LangChain LLM Adapter**
   - Implement `LangChainLLMAdapter` in `src/dbp/llm/langchain/adapters.py`
   - Add streaming support with callbacks
   - Create prompt format conversion utilities
   - Implement proper error handling

2. **Implement Chat Model Adapter**
   - Create `LangChainChatAdapter` in `src/dbp/llm/langchain/chat_adapters.py`
   - Add message format conversion utilities
   - Implement streaming with callbacks
   - Handle chat-specific behavior

3. **Create LangChain Factory**
   - Implement `LangChainFactory` in `src/dbp/llm/langchain/factories.py`
   - Add chain creation utilities
   - Implement agent building utilities
   - Create prompt handling utilities

4. **Build Integration Utilities**
   - Create tool conversion utilities in `src/dbp/llm/langchain/utils.py`
   - Implement tracing support
   - Add callback management utilities

## Notes

- All adapters maintain the streaming-first approach established in earlier phases
- Integration focuses on maintaining a clean separation of concerns
- Factory pattern provides a simple interface for creating LangChain components
- Comprehensive error handling ensures robust integration

## Next Steps

After completing this phase:
1. Proceed to Phase 11 (LangGraph Integration)
2. Implement LangGraph state management
3. Create graph builder utilities
