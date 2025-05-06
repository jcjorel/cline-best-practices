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
# Provides a factory for creating appropriate Bedrock client instances based on 
# model IDs. This factory abstracts client instantiation details, dynamically
# selects the appropriate client class for each model type, verifies model support,
# and handles inference profiles transparently.
###############################################################################
# [Source file design principles]
# - Hide implementation details from client code
# - Dynamic client class detection without hardcoding
# - Transparent inference profile handling
# - Single interface for all Bedrock model types
# - Centralized client creation logic
# - Project model support verification
# - Fail-fast error handling
###############################################################################
# [Source file constraints]
# - Must support all current and future Bedrock model types
# - Must handle inference profiles appropriately for each model type
# - Must integrate with BedrockModelDiscovery for region and profile selection
# - Must not require factory updates when new model clients are added
# - Must verify models against project-supported models
# - Must raise clear exceptions on all error conditions
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/models/claude3.py
# codebase:src/dbp/llm/bedrock/models/nova.py
# codebase:src/dbp/llm/bedrock/discovery/models.py
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/common/exceptions.py
# codebase:doc/design/LLM_COORDINATION.md
# system:logging
# system:importlib
# system:pkgutil
# system:typing
# system:inspect
# system:langchain_aws.chat_models.bedrock_converse
###############################################################################
# [GenAI tool change history]
# 2025-05-06T10:45:00Z : Fixed model parameter handling for LangChain compatibility by CodeAssistant
# * Modified create_langchain_chatbedrock to properly handle model parameters
# * Added property initialization after model creation to set parameters
# * Fixed validation error with direct parameter passing
# * Added more detailed error logging for parameter issues
# 2025-05-05T22:19:07Z : Updated client factory to use model-specific LangChain wrappers by CodeAssistant
# * Removed legacy EnhancedBedrockBase imports
# * Added imports for model-specific LangChain wrappers
# * Updated create_langchain_chatbedrock to use model-specific implementations
# * Improved model detection logic based on SUPPORTED_MODELS lists
# 2025-05-05T11:24:00Z : Added LangChain ChatBedrockConverse factory method by CodeAssistant
# * Added create_langchain_chatbedrock method using langchain_aws.ChatBedrockConverse
# * Implemented model discovery integration for LangChain ChatBedrockConverse
# * Added automatic region selection and inference profile handling
# * Ensured proper error handling and validation for LangChain integration
###############################################################################

"""
Factory class for creating Bedrock clients with dynamic client class detection.
"""

import logging
import importlib
import pkgutil
import inspect
from typing import Dict, Any, List, Optional, Type, Set, Union

from .langchain_wrapper import EnhancedChatBedrockConverse
from .models.claude3 import ClaudeEnhancedChatBedrockConverse
from .models.nova import NovaEnhancedChatBedrockConverse
from .discovery.models import BedrockModelDiscovery
from ..common.exceptions import LLMError, UnsupportedModelError, ConfigurationError


class BedrockClientFactory:
    """
    [Class intent]
    Provides a centralized factory for creating appropriate Bedrock client 
    instances based on model IDs, with automatic handling of model-specific
    implementation details and inference profiles.
    
    [Design principles]
    - Dynamic client detection with no hardcoding
    - Hide client implementation details
    - Inference profile management
    - Region selection through model discovery
    - Project model support verification
    - Fail-fast error handling
    
    [Implementation details]
    - Dynamically discovers client classes and their supported models
    - Integrates with BedrockModelDiscovery
    - Transparently handles inference profiles
    - Raises exceptions on all error conditions
    - Verifies model support against project-supported models
    """
    
    @classmethod
    def create_langchain_chatbedrock(
        cls,
        model_id: str,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        timeout: int = 30,
        logger: Optional[logging.Logger] = None,
        use_model_discovery: bool = True,
        preferred_regions: Optional[List[str]] = None,
        inference_profile_arn: Optional[str] = None,
        streaming: bool = True,
        model_kwargs: Optional[Dict[str, Any]] = None,
        **langchain_kwargs
    ) -> Any:
        """
        [Method intent]
        Create a native LangChain ChatBedrockConverse instance using our model discovery
        and AWS client factory infrastructure for optimal configuration.
        
        [Design principles]
        - Follow LangChain API patterns
        - Leverage existing model discovery capabilities
        - Use AWSClientFactory for boto3 client creation
        - Maintain consistent error handling and validation
        
        [Implementation details]
        - Creates a boto3 client using our AWSClientFactory
        - Passes client directly to LangChain's ChatBedrockConverse
        - Handles region extraction from inference profile ARNs
        - Returns native LangChain object for seamless integration
        
        Args:
            model_id: The Bedrock model ID
            region_name: Optional AWS region name
            profile_name: Optional AWS profile name for credentials
            credentials: Optional explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            use_model_discovery: Whether to discover model availability
            preferred_regions: Optional list of preferred regions
            inference_profile_arn: Optional inference profile ARN
            streaming: Whether to enable streaming by default
            model_kwargs: Optional model parameters
            **langchain_kwargs: Additional parameters for LangChain
            
        Returns:
            Any: LangChain's ChatBedrockConverse instance
            
        Raises:
            UnsupportedModelError: If model ID is not supported by the project
            ConfigurationError: If required configuration is missing or invalid
            LLMError: If client creation fails for other reasons
            ImportError: If LangChain AWS is not installed
        """
        # Initialize logger
        logger = logger or logging.getLogger("BedrockClientFactory")
        
        try:
            # Check if LangChain is installed first before trying to use it
            try:
                import langchain_aws
                from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
            except ImportError as e:
                error_msg = "LangChain AWS is not installed. Please install langchain-aws package."
                logger.error(error_msg)
                raise ConfigurationError(error_msg, e)
                
            # Get model discovery instance
            discovery = BedrockModelDiscovery.get_instance()
            
            # Verify this model is supported by the project
            project_models = discovery._get_project_supported_models()
            if model_id not in project_models:
                # Check if the model has a supported base prefix
                model_base = model_id.split(":")[0]
                supported_prefixes = {m.split(":")[0] for m in project_models}
                
                if not any(model_base == prefix for prefix in supported_prefixes):
                    error_msg = f"Model ID {model_id} is not supported by this project. " + \
                               f"Supported model prefixes: {', '.join(sorted(supported_prefixes))}"
                    logger.error(error_msg)
                    raise UnsupportedModelError(error_msg)
            
            # Process inference profile ARN and extract region if available
            if inference_profile_arn:
                # Extract region from ARN format: arn:aws:bedrock:REGION:account-id:...
                arn_parts = inference_profile_arn.split(':')
                if len(arn_parts) >= 4 and arn_parts[3]:
                    # Override region_name with the region from the ARN
                    extracted_region = arn_parts[3]
                    if region_name and region_name != extracted_region:
                        # Log that we're overriding the provided region
                        logger.info(f"Overriding provided region {region_name} with region {extracted_region} from inference profile ARN")
                    region_name = extracted_region
            
            # Find the best region if not specified and using model discovery
            if not region_name and use_model_discovery:
                best_regions = discovery.get_best_regions_for_model(model_id, preferred_regions)
                if not best_regions:
                    error_msg = f"No available regions found for model {model_id}"
                    logger.error(error_msg)
                    raise ConfigurationError(error_msg)
                
                region_name = best_regions[0]
                logger.info(f"Selected best region for {model_id}: {region_name}")
            
            # Default region as fallback only if not using model discovery
            elif not region_name:
                region_name = "us-west-2"  # Default region
                logger.info(f"No region specified and model discovery disabled, using default: {region_name}")
                    
            # Check for automatic inference profile selection if not explicitly provided
            # We want to check for inference profiles regardless of use_model_discovery
            # if we have a region_name and no explicit inference_profile_arn
            if not inference_profile_arn and region_name:
                model_info = discovery.get_model(model_id, region_name)
                if model_info:
                    # Get available inference profiles
                    profiles = model_info.get("referencedByInstanceProfiles", [])
                    
                    # First try to find SYSTEM_DEFINED profiles
                    system_defined_profiles = []
                    other_profiles = []
                    
                    for profile in profiles:
                        if "inferenceProfileArn" in profile:
                            if profile.get("inferenceProfileType") == "SYSTEM_DEFINED":
                                system_defined_profiles.append(profile)
                            else:
                                other_profiles.append(profile)
                    
                    # Select profile based on priority: SYSTEM_DEFINED first, then others
                    selected_profile = None
                    profile_source = None
                    
                    if system_defined_profiles:
                        selected_profile = system_defined_profiles[0]
                        profile_source = "SYSTEM_DEFINED"
                    elif other_profiles:
                        selected_profile = other_profiles[0]
                        profile_source = "default"
                    
                    # Use the selected profile if available
                    if selected_profile and "inferenceProfileArn" in selected_profile:
                        inference_profile_arn = selected_profile["inferenceProfileArn"]
                        logger.info(f"Auto-selected {profile_source} inference profile ARN for {model_id}: {inference_profile_arn}")
                    
                    # If the model requires an inference profile and none was found, raise error
                    elif model_info.get("requiresInferenceProfile", False):
                        error_msg = f"Model {model_id} requires an inference profile, but none was found"
                        logger.error(error_msg)
                        raise ConfigurationError(error_msg)
            
            try:
                # Import AWS client factory
                from dbp.api_providers.aws.client_factory import AWSClientFactory
                
                # Get the AWS client factory instance
                aws_client_factory = AWSClientFactory.get_instance()
                
                # Define configuration for bedrock client
                import botocore.config
                bedrock_config = botocore.config.Config(
                    retries={"max_attempts": max_retries},
                    connect_timeout=timeout,
                    read_timeout=120  # Higher read timeout for AI services
                )
                
                # Get the boto3 client for bedrock using our factory
                bedrock_client = aws_client_factory.get_client(
                    service_name="bedrock-runtime",  # Use bedrock-runtime for model invocation
                    region_name=region_name,
                    profile_name=profile_name,
                    credentials=credentials,
                    config=bedrock_config
                )
                
                # The inference profile ARN itself is used as the modelId parameter
                # for AWS Bedrock's ConverseStream API, not as a separate parameter
                model_param = inference_profile_arn if inference_profile_arn else model_id
                
                # Setup parameters for LangChain ChatBedrockConverse
                # Keep only the essential parameters that the LangChain model constructor expects
                chat_model_params = {
                    "model": model_param,  
                    "client": bedrock_client,
                }
                
                # Determine the appropriate class based on model ID
                model_class = EnhancedChatBedrockConverse  # Default fallback
                
                # Check for Claude models
                if any(model_id.startswith(m.split(':')[0]) for m in ClaudeEnhancedChatBedrockConverse.SUPPORTED_MODELS):
                    model_class = ClaudeEnhancedChatBedrockConverse
                    logger.info(f"Using Claude-specific implementation for model {model_id}")
                
                # Check for Nova models
                elif any(model_id.startswith(m.split(':')[0]) for m in NovaEnhancedChatBedrockConverse.SUPPORTED_MODELS):
                    model_class = NovaEnhancedChatBedrockConverse
                    logger.info(f"Using Nova-specific implementation for model {model_id}")
                
                # Create the model-specific instance with ONLY the required parameters
                # Many LangChain chat models have strict validation and don't accept extra kwargs
                try:
                    chat_bedrock = model_class(
                        **chat_model_params,
                        logger=logger
                    )
                    
                    # Now that the model is created, we can set the model parameters 
                    # as attributes directly if needed
                    if model_kwargs:
                        # Store model kwargs outside of the model for future use if needed
                        object.__setattr__(chat_bedrock, "_cached_model_kwargs", model_kwargs)
                
                except Exception as e:
                    # Detailed error logging to help debug parameter issues
                    logger.error(f"Failed to create model with parameters: {chat_model_params}")
                    logger.error(f"Model class: {model_class.__name__}")
                    if model_kwargs:
                        logger.error(f"Model kwargs: {model_kwargs}")
                    raise e
                
                logger.info(f"Created LangChain ChatBedrockConverse for model {model_id} in region {region_name}")
                return chat_bedrock
                
            except ImportError as e:
                error_msg = "AWSClientFactory not found. Cannot create client."
                logger.error(error_msg)
                raise ConfigurationError(error_msg, e)
                
        except (UnsupportedModelError, ConfigurationError, ImportError) as e:
            # Re-raise specific exceptions
            raise e
        except Exception as e:
            # Wrap other exceptions
            error_msg = f"Failed to create LangChain ChatBedrockConverse for model {model_id}: {str(e)}"
            logger.error(error_msg)
            raise LLMError(error_msg, e)
