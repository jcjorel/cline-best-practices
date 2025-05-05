#!/usr/bin/env python3
"""
Example demonstrating LangChain integration with AWS Bedrock model discovery.

This example shows:
1. Creating a LangChain ChatBedrockConverse instance using BedrockClientFactory
2. Leveraging model discovery for optimal region selection
3. Using proper LangChain message patterns
4. Handling streaming responses
5. Proper error propagation (no silent failures)

Usage:
    python langchain_client_factory_example.py
"""

import asyncio
import logging
import os
import sys
from typing import List, Dict, Any, Optional

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery
    from dbp.llm.bedrock.client_factory import BedrockClientFactory
    from dbp.llm.bedrock.langchain_wrapper import EnhancedChatBedrockConverse
else:
    # Relative imports when used as part of the package
    from ..discovery.models import BedrockModelDiscovery
    from ..client_factory import BedrockClientFactory
    from ..langchain_wrapper import EnhancedChatBedrockConverse

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langchain-bedrock")

# Set boto3 loggers to WARNING level to reduce verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)


async def test_basic_langchain_integration():
    """Demonstrate basic LangChain integration with model discovery."""
    
    print("\n=== Testing Basic LangChain Integration ===")
    
    # Import LangChain components
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Select a suitable model ID - Claude models work well with LangChain
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0" 
    
    print(f"Creating LangChain model for {model_id}...")
    
    # Create LangChain chat model using our factory
    # This handles all region selection, client creation, etc.
    # Errors will be propagated to the caller - no try/except block
    # Create LangChain chat model using our factory with proper parameter structure
    # The model_kwargs parameter structure used by LangChain is different than direct parameters
    chat_model = BedrockClientFactory.create_langchain_chatbedrock(
        model_id=model_id,
        use_model_discovery=True,  # Enable automatic region selection
        logger=logger,
    )
    
    # Note: streaming will be handled at invocation time, not during initialization
    
    # Create standard LangChain message objects
    messages = [
        SystemMessage(content="You are a helpful AI assistant that provides concise responses."),
        HumanMessage(content="What is Amazon Bedrock and what are its key features?")
    ]
    
    print("\nSending request to model...")
    print("Response:")
    print("-" * 50)
    
    # Demonstrate streaming response - this is a common LangChain pattern
    # Any errors during streaming will be propagated to caller
    # Track content for final length reporting
    response_content = ""
    
    # Print initial message to indicate streaming is starting
    sys.stdout.write("\033[1mStreaming response:\033[0m\n")
    sys.stdout.flush()
    
    # Use the text-only streaming method for cleaner output
    # This method already handles text extraction, so no need for try/except
    async for clean_text in chat_model.astream_text(messages):
        # Add to response content and display
        response_content += clean_text
        sys.stdout.write(clean_text)
        sys.stdout.flush()
    
    print("\n" + "-" * 50)
    print(f"Total response length: {len(response_content)} characters")


async def test_conversation_chain():
    """Demonstrate LangChain conversation chain with memory."""
    
    print("\n=== Testing LangChain Conversation Chain ===")
    
    # Import LangChain components - no try/except to ensure errors propagate
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from langchain_core.runnables import RunnablePassthrough
    
    # Select a suitable model ID
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    
    # Create LangChain chat model using our factory
    # No try/except - errors will propagate up to caller
    chat_model = BedrockClientFactory.create_langchain_chatbedrock(
        model_id=model_id,
        use_model_discovery=True,
        logger=logger,
    )
    
    # Note: streaming will be handled at invocation time
    
    # Create a conversation prompt template using LangChain pattern
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant that provides concise responses about AWS services."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    # Create simple chain that combines prompt + chat model 
    chain = prompt | chat_model
    
    # Create the chain without using deprecated RunnableWithMessageHistory 
    # Instead, we'll manually manage the history for more control and streaming capabilities
    
    # Define a series of questions to simulate a conversation
    questions = [
        "What is Amazon S3?",
        "What storage classes does it offer?",
        "Which one is best for infrequently accessed data?",
        "How does that compare to Glacier?"
    ]
    
    # Set up a message store to hold conversation history
    message_history = []
    session_id = "aws-services-conversation"
    
    # Run the conversation, displaying each exchange
    for i, question in enumerate(questions):
        print(f"\nQuestion {i+1}: {question}")
        print("Response:")
        print("-" * 50)
        
        # Initialize streaming message
        sys.stdout.write("\033[1mStreaming response:\033[0m\n")
        sys.stdout.flush()
        
        # Process the question using the chain with history
        # Instead of using conversation_with_history directly, we'll use the chat model
        # with manual history management to enable streaming
        
        # Get the current conversation history
        current_messages = [
            SystemMessage(content="You are a helpful AI assistant that provides concise responses about AWS services.")
        ]
        
        # Add existing history
        current_messages.extend(message_history)
        
        # Add current question
        current_messages.append(HumanMessage(content=question))
        
        # Stream the response using text-only streaming method
        full_response = ""
        async for clean_text in chat_model.astream_text(current_messages):
            # Add to full response and display
            full_response += clean_text
            sys.stdout.write(clean_text)
            sys.stdout.flush()
        
        # After streaming is complete, update the message history
        message_history.append(HumanMessage(content=question))
        message_history.append(AIMessage(content=full_response))
        
        print("\n" + "-" * 50)


async def test_optimized_discovery(model_id: str):
    """
    Demonstrate optimized model discovery with LangChain.
    
    Args:
        model_id: Specific model ID to use
        
    Raises:
        ConfigurationError: If no regions are available for the model
        LLMError: If error occurs during model creation or invocation
        Other exceptions will propagate from underlying libraries
    """
    
    print("\n=== Testing Optimized Model Discovery with LangChain ===")
    
    # Import model discovery
    from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery
    from dbp.llm.common.exceptions import ConfigurationError
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Get model discovery instance
    discovery = BedrockModelDiscovery.get_instance()
    
    # Get best regions for this model
    best_regions = discovery.get_best_regions_for_model(model_id)
    
    if not best_regions:
        # No regions available - raise error instead of silently failing
        raise ConfigurationError(f"No available regions found for model {model_id}")
    
    print(f"Found optimal regions: {', '.join(best_regions)}")
    region_name = best_regions[0]
        
    # Create LangChain model with selected region
    # No try/except - errors will propagate to caller
    chat_model = BedrockClientFactory.create_langchain_chatbedrock(
        model_id=model_id,
        region_name=region_name,  # Use pre-selected region
        use_model_discovery=False,  # Disable discovery since we already found the best region
        streaming=True,
        logger=logger
    )
    
    # Test the model with a simple query
    messages = [
        SystemMessage(content="You are a helpful AI assistant."),
        HumanMessage(content="Hello! Please introduce yourself briefly.")
    ]
    
    print("\nTesting model with greeting...")
    print("Response:")
    print("-" * 50)
    
    # Process the streaming response with immediate display
    # No try/except - errors will propagate to caller
    response_content = ""
    
    # Initialize streaming
    sys.stdout.write("\033[1mStreaming response:\033[0m\n")
    sys.stdout.flush()
    
    # Use the text-only streaming method for cleaner output
    async for clean_text in chat_model.astream_text(messages):
        # Add to response content and display
        response_content += clean_text
        sys.stdout.write(clean_text)
        sys.stdout.flush()
    
    print("\n" + "-" * 50)
    print(f"Successfully tested model {model_id} in region {region_name}")
    
    return chat_model


async def test_multi_turn_conversation(chat_model):
    """
    Demonstrate multi-turn conversation with LangChain and Bedrock.
    
    Args:
        chat_model: LangChain chat model instance to use
    
    Raises:
        Any exceptions from underlying LangChain or Bedrock calls will propagate
    """
    
    print("\n=== Testing Multi-Turn Conversation ===")
    
    # Import LangChain message components
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    
    # Initialize conversation with a system message
    conversation = [
        SystemMessage(content="You are a software engineering advisor. You provide concise, practical advice for software developers.")
    ]
    
    # Define multi-turn conversation
    user_messages = [
        "What are the key principles of clean code?",
        "How can I apply the DRY principle effectively?",
        "Can you give me an example of a code refactoring that demonstrates these principles?"
    ]
    
    # Process each message in the conversation
    # No try/except - errors will propagate to caller
    for i, msg in enumerate(user_messages):
        # Add user message to conversation
        conversation.append(HumanMessage(content=msg))
        
        print(f"\nTurn {i+1}: {msg}")
        print("Response:")
        print("-" * 50)
        
        # Stream the response with immediate display
        response_content = ""
        
        # Initialize streaming
        sys.stdout.write("\033[1mStreaming response:\033[0m\n")
        sys.stdout.flush()
        
        # Use the text-only streaming method for cleaner output
        async for clean_text in chat_model.astream_text(conversation):
            # Add to response content and display
            response_content += clean_text
            sys.stdout.write(clean_text)
            sys.stdout.flush()
        
        print("\n" + "-" * 50)
        
        # Add AI response to conversation history for context
        conversation.append(AIMessage(content=response_content))


async def main():
    """Run all examples."""
    print("===== LangChain Bedrock Model Discovery Examples =====")
    
    # No try/except - all errors will directly propagate to ensure nothing is silently caught
    # Select a suitable model ID
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    
    # Run the basic integration test
    await test_basic_langchain_integration()
    print("\nBasic integration test completed successfully!")
    
    # Run conversation chain test
    await test_conversation_chain()
    print("\nConversation chain test completed successfully!")
    
    # Run optimized discovery test and get model for multi-turn
    chat_model = await test_optimized_discovery(model_id)
    print("\nOptimized model discovery test completed successfully!")
    
    # Run multi-turn conversation test
    await test_multi_turn_conversation(chat_model)
    print("\nMulti-turn conversation test completed successfully!")
    
    print("\nAll tests completed successfully!")

# Standard Python entry point
if __name__ == "__main__":
    asyncio.run(main())
