#!/usr/bin/env python3
"""
LangChain-based example demonstrating the AWS Bedrock model discovery mechanism.

This example shows LangChain integration with Bedrock model discovery:
1. Using LangChain's ChatBedrockConverse with model discovery enabled
2. Finding optimal regions for models
3. Automatic region fallback when a model is not available
4. Specifying preferred regions for model selection
5. Working with inference profiles
6. Using the LangChain message format and patterns

Usage:
    python langchain_model_discovery_example.py
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Callable, AsyncIterator

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
    from dbp.llm.bedrock.client_factory import (
        BedrockClientFactory,
        get_all_supported_model_ids,
        get_client_class_for_model,
        get_parameter_class_for_model,
        get_parameter_instance_for_client
    )
else:
    # Relative imports when used as part of the package
    from ..discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
    from ..client_factory import (
        BedrockClientFactory,
        get_all_supported_model_ids,
        get_client_class_for_model,
        get_parameter_class_for_model,
        get_parameter_instance_for_client
    )

# Import LangChain components
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # When running as a script, use absolute imports
    from dbp.llm.bedrock.langchain_wrapper import EnhancedChatBedrockConverse
    from dbp.llm.bedrock.models.claude3 import ClaudeEnhancedChatBedrockConverse
    from dbp.llm.bedrock.models.nova import NovaEnhancedChatBedrockConverse
else:
    # When imported as a module, use relative imports
    from ..langchain_wrapper import EnhancedChatBedrockConverse
    from ..models.claude3 import ClaudeEnhancedChatBedrockConverse
    from ..models.nova import NovaEnhancedChatBedrockConverse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langchain-bedrock-model-discovery")

# Set boto3 and urllib3 loggers to WARNING level to reduce verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Set discovery logger to INFO level
logging.getLogger('dbp.llm.bedrock.discovery.models_capabilities').setLevel(logging.INFO)


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def print_model_availability(model_id: str, shared_state: Dict[str, Any]):
    """Print availability information about a specific Bedrock model."""
    print(f"\n=== Model Availability for {model_id} ===")
    
    # Get model discovery instance from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Find regions where the model is available (uses cache, no API calls)
    available_regions = model_discovery.get_model_regions(model_id)
    print(f"Model is available in {len(available_regions)} regions: {', '.join(available_regions)}")
    
    # Check availability with preferred regions (uses cache, no API calls)
    preferred_regions = ["us-east-1", "eu-west-1", "ap-southeast-2"]
    print(f"\nChecking best regions with preferences: {preferred_regions}")
    best_regions = model_discovery.get_best_regions_for_model(
        model_id,
        preferred_regions=preferred_regions
    )
    print(f"Best regions (in order): {', '.join(best_regions)}")
    
    # Check for inference profiles
    print("\n=== Inference Profiles ===")
    
    # Get the model with profile information (uses cache, no API calls)
    if best_regions:
        model_data = model_discovery.get_model(model_id)
        if model_data:
            profiles = model_data.get("referencedByInstanceProfiles", [])
            
            if profiles:
                profile_ids = [p.get("inferenceProfileId") for p in profiles if "inferenceProfileId" in p]
                print(f"Model has {len(profile_ids)} inference profiles: {', '.join(profile_ids)}")
                
                # Get details for the first profile
                if profiles:
                    first_profile = profiles[0]
                    print(f"\nDetails for profile {first_profile.get('inferenceProfileId')}:")
                    print(json.dumps(first_profile, indent=2, cls=DateTimeJSONEncoder))
            else:
                print(f"Model {model_id} does not have any inference profiles")
        else:
            print(f"Could not retrieve model data for {model_id}")
    else:
        print(f"Model {model_id} is not available in any region")


async def langchain_with_discovery(shared_state: Dict[str, Any]):
    """
    Demonstrate using LangChain ChatBedrockConverse with model discovery for project supported models.
    This function showcases the integration of LangChain with model discovery.
    """
    print("\n=== Testing Project Supported Models with LangChain and System Prompts ===")
    
    # Get model discovery instance from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Get project-supported models from shared state
    project_models = shared_state.get("project_models")
    if not project_models:
        print("No project-supported models found!")
        return
    
    print(f"Found {len(project_models)} project-supported models to test")
    
    # Define conversation prompts for 3-shot conversation
    prompts = [
        "What is Amazon Bedrock?",
        "What are its key features?",
        "How does it compare to other AWS AI services?"
    ]
    
    # Define a system prompt that will make it obvious in the response if it's working
    system_prompt_content = """You are an AWS spokesperson who MUST ALWAYS follow these rules without exception:
1. You MUST begin EVERY response with the phrase "🚀 AWS SPECIALIST HERE! I'm delighted to inform you that"
2. You MUST keep your responses concise (under 4 sentences)
3. You MUST mention at least one AWS benefit in EVERY response
4. You MUST use an enthusiastic, marketing-oriented tone
5. You MUST add "AWS - Cloud Innovation at Your Fingertips™" at the end of EVERY response"""
    
    # Non-preferred region where models might not be available
    initial_region = "ap-south-1"  # Mumbai
    preferred_regions = ["us-east-1", "us-west-2"]
    
    # For performance optimization, group models by provider/type to potentially reuse clients
    model_clients = {}
    
    # Test each project model with a 3-shot conversation
    # Using a smaller subset to keep the example concise
    test_models = list(sorted(project_models))[:2]  # Only test first 2 models
    
    for model_id in test_models:
        print(f"\n{'='*80}")
        print(f"TESTING MODEL: {model_id}")
        print(f"{'='*80}")
        
        # Get models and profiles from cache (no API calls)
        print(f"Getting models and profiles for {model_id} from cache...")
        
        # Get cached data from shared state
        region_models = shared_state.get("region_data", {})
        
        # Check for inference profiles
        profiles_found = False
        for region, region_model_dict in region_models.get("models", {}).items():
            # Find our model in the returned models
            if model_id in region_model_dict:
                model = region_model_dict[model_id]
                # Check if this model has associated profiles
                profiles = model.get("referencedByInstanceProfiles", [])
                if profiles:
                    profiles_found = True
                    print(f"  Region {region}: Found {len(profiles)} profiles for {model_id}")
                    
                    # Print profile details
                    for p in profiles:
                        print(f"    - {p.get('inferenceProfileId')}: {p.get('inferenceProfileName', 'No name')}")
        
        if not profiles_found:
            print(f"  No profiles found for {model_id} in any region")
        
        # Get specific model data (uses cache, no API calls)
        print(f"Getting complete model data for {model_id} from cache...")
        model_data = model_discovery.get_model(model_id)
        
        # Check if model requires an inference profile
        requires_profile = model_data and model_data.get("requiresInferenceProfile", False)
        
        if requires_profile:
            print(f"Skipping model {model_id} as it requires an inference profile")
            # Skip models that require inference profiles for this example
            continue
            
        # Extract profiles from model data (for informational purposes only)
        inference_profile_arn = None
        if model_data and "referencedByInstanceProfiles" in model_data:
            profiles = model_data["referencedByInstanceProfiles"]
            profile_arns = []
            if profiles:
                for p in profiles:
                    if "inferenceProfileArn" in p:
                        profile_arns.append(p["inferenceProfileArn"])
                
                if profile_arns:
                    print(f"Found profile ARNs: {', '.join(profile_arns)}")
                    inference_profile_arn = profile_arns[0]
                    print(f"Model requires an inference profile, using ARN: {inference_profile_arn}")
        
        # Check if we already have a suitable client we can reuse
        client_key = f"{model_id}:{inference_profile_arn}"
        chat_model = model_clients.get(client_key)
        
        if not chat_model:
            # Create LangChain client with model discovery enabled
            print(f"Creating new LangChain chat model in initial region {initial_region}")
            print(f"Model discovery is enabled with preferred regions: {', '.join(preferred_regions)}")
            
            # Create LangChain chat model using our factory
            chat_model = BedrockClientFactory.create_langchain_chatbedrock(
                model_id=model_id,
                region_name=initial_region,
                logger=logger,
                use_model_discovery=True,
                preferred_regions=preferred_regions,
                inference_profile_arn=inference_profile_arn
            )
            
            # Store client for potential reuse
            model_clients[client_key] = chat_model
            
            # Get best regions information from model discovery
            best_regions = model_discovery.get_best_regions_for_model(model_id)
            print(f"Best regions for {model_id}: {', '.join(best_regions)}")
        else:
            print(f"Reusing existing LangChain chat model for {model_id}")
        
        # Initialize conversation
        conversation = [
            SystemMessage(content=system_prompt_content)
        ]
        
        # Conduct 3-shot conversation
        for turn, prompt in enumerate(prompts):
            print(f"\nTURN {turn+1} - Sending prompt: {prompt}")
            
            # Add user message to conversation
            conversation.append(HumanMessage(content=prompt))
            
            # Send prompt to model with conversation context
            print("\nSTREAMING RESPONSE:")
            print("-------------------------------------------")
            
            response_text = ""
            chunk_count = 0
            
            # Stream text from the model
            async for chunk in chat_model.astream_text(conversation):
                response_text += chunk
                # Print each chunk immediately to show streaming behavior
                print(chunk, end="", flush=True)
                chunk_count += 1
            
            print("\n-------------------------------------------")
            print(f"Received {len(response_text)} characters in approximately {chunk_count} chunks")
            
            # Add assistant response to conversation for next turn
            conversation.append(AIMessage(content=response_text))
    
    # Clean up all clients at the end
    print("\nNo cleanup needed - LangChain clients are managed automatically")


async def display_project_supported_models(shared_state: Dict[str, Any]):
    """Display the availability of all project-supported models across regions."""
    print("\n=== Project-Supported Models Availability (LangChain Compatible) ===")
    
    # Get model discovery from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Get dynamically discovered models using the new discovery system
    print("\nDynamic Model Discovery:")
    dynamic_models = get_all_supported_model_ids()
    print(f"Discovered {len(dynamic_models)} models using dynamic discovery system:")
    for model_id in sorted(dynamic_models):
        client_class = get_client_class_for_model(model_id)
        param_class = get_parameter_class_for_model(model_id)
        print(f"  - {model_id} → {client_class.__name__} with {param_class.__name__}")
    
    # Get project-supported models from shared state
    project_models = shared_state.get("project_models")
    if not project_models:
        print("No project-supported models found!")
        return
    
    print(f"\nFound {len(project_models)} project-supported models:")
    for model_id in sorted(project_models):
        print(f"  - {model_id}")
    
    print("\nChecking availability across regions (using cached data)...")
    
    # Get cached region data from shared state
    region_data = shared_state.get("region_data", {})
    region_models = region_data.get("models", {})
    
    # For each project model, check availability and best regions
    print("\nAvailability Summary:")
    print("-" * 120)
    print(f"{'Model ID':<40} | {'Available Regions':<30} | {'Best Region':<15} | {'LangChain Compatible'}")
    print("-" * 120)
    
    for model_id in sorted(project_models):
        # Get regions where this model is available (from cache)
        available_regions = model_discovery.get_model_regions(model_id)
        
        # Get best region (from cache)
        best_regions = model_discovery.get_best_regions_for_model(model_id)
        best_region = best_regions[0] if best_regions else "N/A"
        
        # Check if model is compatible with LangChain using dynamic discovery
        try:
            # Check if there's a compatible class using the new discovery system
            client_class = get_client_class_for_model(model_id)
            langchain_compatible = "Yes"
        except Exception:
            langchain_compatible = "No"
        
        # Format for display
        short_model_id = model_id.split(":")[0]
        regions_str = ", ".join(available_regions[:3])
        if len(available_regions) > 3:
            regions_str += f" +{len(available_regions)-3} more"
            
        print(f"{short_model_id:<40} | {regions_str:<30} | {best_region:<15} | {langchain_compatible}")
    
    print("-" * 120)


async def test_system_prompt_variants(shared_state: Dict[str, Any]):
    """Test different formats of system prompts with LangChain."""
    print("\n=== Testing Different System Prompt Formats with LangChain ===")
    
    # Get model discovery instance from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Get project-supported models from shared state
    project_models = shared_state.get("project_models")
    if not project_models:
        print("No project-supported models found!")
        return
    
    # Use the first available model for testing
    test_model_id = sorted(project_models)[0]
    print(f"Using model {test_model_id} for system prompt format tests")
    
    # Define system prompt formats to test
    # With LangChain, we'll use proper Message objects instead of raw formats
    system_prompts = [
        SystemMessage(content="You are a helpful assistant that speaks like a pirate."),
        SystemMessage(content="You are a helpful assistant that speaks like a robot."),
        SystemMessage(content="You are a helpful assistant that speaks like a detective.")
    ]
    
    # Define a simple prompt for testing
    test_prompt = "Tell me about Amazon S3 in one sentence."
    
    # We'll create a new client for each test (LangChain's pattern)
    # Test each system prompt
    for i, system_prompt in enumerate(system_prompts):
        print(f"\n--- Testing System Prompt Format #{i+1} ---")
        print(f"System prompt: {system_prompt.content}")
        
        # Create LangChain client
        chat_model = BedrockClientFactory.create_langchain_chatbedrock(
            model_id=test_model_id,
            logger=logger,
            use_model_discovery=True
        )
        
        # Create message list with system prompt
        messages = [
            system_prompt,
            HumanMessage(content=test_prompt)
        ]
        
        # Send prompt to get response
        print(f"\nSending test prompt: {test_prompt}")
        print("Response:")
        print("-------------------------------------------")
        
        # Stream the response
        response_text = ""
        async for chunk in chat_model.astream_text(messages):
            response_text += chunk
            print(chunk, end="", flush=True)
        
        print("\n-------------------------------------------")
        print(f"Response length: {len(response_text)} characters")
    
    print("\nSystem prompt variant testing complete")


async def test_langchain_conversation_memory(shared_state: Dict[str, Any]):
    """Demonstrate LangChain conversation memory with Bedrock."""
    print("\n=== Testing LangChain Conversation Memory ===")
    
    # Get project-supported models from shared state
    project_models = shared_state.get("project_models")
    if not project_models:
        print("No project-supported models found!")
        return
    
    # Select a model from project-supported models
    model_id = sorted(project_models)[0]
    print(f"Using model {model_id} for conversation memory test")
    
    # Create LangChain chat model
    chat_model = BedrockClientFactory.create_langchain_chatbedrock(
        model_id=model_id,
        use_model_discovery=True,
        logger=logger
    )
    
    # Initialize conversation with a system message
    conversation = [
        SystemMessage(content="You are a helpful assistant that provides information about AWS services in a concise manner.")
    ]
    
    # Define a multi-turn conversation
    questions = [
        "What is Amazon S3?",
        "What storage classes does it offer?",
        "Which one is best for infrequently accessed data?",
        "How does that compare to Glacier?"
    ]
    
    # Conduct the conversation
    for i, question in enumerate(questions):
        print(f"\nQuestion {i+1}: {question}")
        
        # Add user message to the conversation
        conversation.append(HumanMessage(content=question))
        
        # Get model response
        print("Response:")
        print("-" * 50)
        
        # Stream the response
        response_text = ""
        async for chunk in chat_model.astream_text(conversation):
            response_text += chunk
            print(chunk, end="", flush=True)
        
        print("\n" + "-" * 50)
        
        # Add AI response to conversation history
        conversation.append(AIMessage(content=response_text))
    
    print("\nConversation memory test complete!")


async def test_dynamic_discovery(shared_state: Dict[str, Any]):
    """Test the new dynamic discovery functions."""
    print("\n=== Testing Dynamic Discovery Functions ===")
    
    # Get all supported models
    supported_models = get_all_supported_model_ids()
    print(f"Discovered {len(supported_models)} supported models:")
    for model_id in sorted(supported_models):
        print(f"  - {model_id}")
    
    # Take the first model as an example
    if supported_models:
        example_model = sorted(supported_models)[0]
        print(f"\nDetails for example model {example_model}:")
        
        # Get client class for this model
        client_class = get_client_class_for_model(example_model)
        print(f"Client class: {client_class.__name__}")
        
        # Get parameter class for this model
        param_class = get_parameter_class_for_model(example_model)
        print(f"Parameter class: {param_class.__name__}")
        
        # Show parameter values
        param_instance = param_class()
        print(f"Default parameter values:")
        for param_name, param_value in param_instance.dict().items():
            print(f"  - {param_name}: {param_value}")
    
    print("\nDynamic discovery testing complete!")


async def main():
    """Run all LangChain model discovery examples."""
    print("===== LangChain with Bedrock Model Discovery Examples =====")
    
    # Create discovery and get project-supported models
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Check if we need to perform an initial scan (clear cache and rescan)
    print("Checking if cache is populated...")
    region_data = model_discovery.scan_all_regions()
    
    if not region_data.get("models", {}):
        print("Cache is empty or invalid. Performing a full region scan...")
        region_data = model_discovery.scan_all_regions(force_refresh=True)
        print(f"Scan complete. Found models in {len(region_data.get('models', {}))} regions")
    else:
        print(f"Using cached data. Found models in {len(region_data.get('models', {}))} regions")
    
    # Get project-supported models
    project_models = model_discovery.project_supported_models
    if not project_models:
        print("No project-supported models found!")
        return
    
    # Create shared state to pass between functions
    shared_state = {
        "model_discovery": model_discovery,
        "region_data": region_data,
        "project_models": project_models
    }
    
    # Test our new dynamic discovery functions first
    await test_dynamic_discovery(shared_state)
    
    # Run other examples as before
    await display_project_supported_models(shared_state)
    await test_system_prompt_variants(shared_state)
    await langchain_with_discovery(shared_state)
    await test_langchain_conversation_memory(shared_state)
    
    # Use the first project model for detailed availability example
    example_model_id = sorted(project_models)[0]
    await print_model_availability(example_model_id, shared_state)
    
    print("\nAll LangChain examples completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
