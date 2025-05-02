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
# Provides factory classes and methods for creating LangChain components using
# our LLM implementations. This enables easy construction of chains, agents, and
# other LangChain components with standardized configurations and best practices.
###############################################################################
# [Source file design principles]
# - Simplified component creation with factory pattern
# - Consistent configuration across components
# - Support for common LangChain use cases
# - Encapsulation of adapter creation and configuration
# - Type-safe interface for component creation
###############################################################################
# [Source file constraints]
# - Must support all LangChain component types
# - Must maintain proper error handling and validation
# - Must not introduce circular dependencies
# - Must follow factory pattern best practices
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/base.py
# codebase:src/dbp/llm/langchain/adapters.py
# codebase:src/dbp/llm/langchain/chat_adapters.py
# system:logging
# system:typing
# system:langchain_core
# system:langchain.chains
# system:langchain.agents
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:28:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Implemented LangChainFactory for component creation
# * Added methods for creating chains and agents
# * Added support for prompt templates and customization
###############################################################################

"""
Factory classes for creating LangChain components with our LLM clients.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Callable, Type, cast

from langchain_core.language_models import BaseLLM, BaseLanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.prompts.chat import MessagesPlaceholder
from langchain.chains import LLMChain, ConversationChain, RetrievalQA
from langchain.agents import AgentExecutor, initialize_agent, AgentType

from ..common.base import ModelClientBase
from .adapters import LangChainLLMAdapter
from .chat_adapters import LangChainChatAdapter

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
        streaming: bool = True,
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
            streaming: Whether to use streaming by default
            **kwargs: Additional LangChain configuration
            
        Returns:
            BaseLLM: LangChain-compatible LLM adapter
        """
        return LangChainLLMAdapter(model_client, streaming=streaming, **kwargs)
    
    def create_chat_adapter(
        self, 
        model_client: ModelClientBase,
        streaming: bool = True,
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
            streaming: Whether to use streaming by default
            **kwargs: Additional LangChain configuration
            
        Returns:
            BaseChatModel: LangChain-compatible Chat Model adapter
        """
        return LangChainChatAdapter(model_client, streaming=streaming, **kwargs)
    
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
    
    def create_conversation_chain(
        self,
        model_client: ModelClientBase,
        system_message: str = "You are a helpful assistant.",
        memory_key: str = "chat_history",
        **kwargs
    ) -> ConversationChain:
        """
        [Method intent]
        Create a conversation chain for multi-turn chat interactions.
        
        [Design principles]
        - Easy setup for conversational agents
        - Default configurations with best practices
        - Memory integration for conversation history
        
        [Implementation details]
        - Creates chat adapter for model client
        - Sets up prompt with memory and system message
        - Configures memory for conversation history
        
        Args:
            model_client: Our model client instance
            system_message: System message to guide the conversation
            memory_key: Key used to store conversation history
            **kwargs: Additional ConversationChain configuration
            
        Returns:
            ConversationChain: Configured conversation chain
        """
        try:
            # Import necessary components
            from langchain.chains import ConversationChain
            from langchain.memory import ConversationBufferMemory
            
            # Create chat adapter
            chat_model = self.create_chat_adapter(model_client)
            
            # Create conversation prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                MessagesPlaceholder(variable_name=memory_key),
                ("user", "{input}")
            ])
            
            # Create memory
            memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
            
            # Create conversation chain
            return ConversationChain(
                llm=chat_model,
                prompt=prompt,
                memory=memory,
                verbose=kwargs.get("verbose", False)
            )
            
        except ImportError:
            self.logger.error("Failed to create conversation chain. Required components not available.")
            raise ImportError("Required LangChain components not available. Make sure langchain is installed.")
    
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
        
        # Set defaults for agent
        default_kwargs = {
            "handle_parsing_errors": True,
            "verbose": kwargs.get("verbose", False),
            "early_stopping_method": "generate"
        }
        
        # Merge with user kwargs
        agent_kwargs = {**default_kwargs, **kwargs}
        
        # Initialize agent
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=agent_type,
            **agent_kwargs
        )
        
        return agent
    
    def create_retrieval_qa(
        self,
        model_client: ModelClientBase,
        retriever: Any,
        chain_type: str = "stuff",
        **kwargs
    ) -> RetrievalQA:
        """
        [Method intent]
        Create a RetrievalQA chain for question answering with documents.
        
        [Design principles]
        - Simplified setup for retrieval-based QA
        - Integration with different retrievers
        - Customizable chain types
        
        [Implementation details]
        - Creates adapter for model client
        - Configures RetrievalQA with retriever
        - Sets appropriate chain type and options
        
        Args:
            model_client: Our model client instance
            retriever: Document retriever instance
            chain_type: Chain type for QA processing
            **kwargs: Additional RetrievalQA configuration
            
        Returns:
            RetrievalQA: Configured retrieval QA chain
        """
        try:
            # Import necessary components
            from langchain.chains import RetrievalQA
            
            # Create LLM adapter
            llm = self.create_llm_adapter(model_client)
            
            # Create RetrievalQA chain
            return RetrievalQA.from_chain_type(
                llm=llm,
                chain_type=chain_type,
                retriever=retriever,
                return_source_documents=kwargs.get("return_source_documents", True),
                verbose=kwargs.get("verbose", False)
            )
            
        except ImportError:
            self.logger.error("Failed to create RetrievalQA chain. Required components not available.")
            raise ImportError("Required LangChain components not available. Make sure langchain is installed.")
