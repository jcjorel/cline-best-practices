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
# 2025-05-07T10:40:52Z : Fixed _select_best_region error handling by CodeAssistant
# * Implemented proper error handling when model discovery is disabled and no region is specified
# * Replaced fallback to default region with explicit ConfigurationError
# * Improved fail-fast behavior to prevent silent defaults in critical configurations
# 2025-05-06T13:43:42Z : Implemented dynamic model discovery by CodeAssistant
# * Added _discover_client_classes for auto-discovery of model implementations
# * Added _build_model_mappings for mapping models to client and parameter classes
# * Added _ensure_caches_initialized for lazy initialization with caching
# * Added helper functions for accessing model metadata
# * Updated create_langchain_chatbedrock to use new discovery system
# 2025-05-06T12:57:00Z : Applied DRY principle to client factory by CodeAssistant
# * Extracted common code into reusable helper methods
# * Created _verify_model_support for model validation logic
# * Created _extract_region_from_profile_arn for ARN parsing
# * Created _select_best_region for region selection logic
# * Created _select_inference_profile for profile handling
# * Created _get_model_specific_class for model class determination
###############################################################################

"""
Factory class for creating Bedrock clients with dynamic client class detection.
"""

import logging
import importlib
import pkgutil
import inspect
import os
import sys
from typing import Dict, Any, List, Optional, Type, Set, Union, Tuple

from .langchain_wrapper import EnhancedChatBedrockConverse
from .discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
from ..common.exceptions import LLMError, UnsupportedModelError, ConfigurationError

# Cache for discovered classes to avoid repeated scans
_client_classes_cache = None
_model_to_client_class_cache = None
_model_to_parameter_class_cache = None

def _discover_client_classes() -> List[Type[EnhancedChatBedrockConverse]]:
    """
    [Function intent]
    Discovers all EnhancedChatBedrockConverse subclasses in the models directory.
    
    [Design principles]
    - Dynamic discovery without hardcoding
    - Import all modules in models directory
    - Inspect classes to find EnhancedChatBedrockConverse subclasses
    
    [Implementation details]
    - Uses pkgutil to find modules
    - Uses inspect to identify subclasses
    - Returns list of discovered classes
    
    Returns:
        List[Type[EnhancedChatBedrockConverse]]: List of discovered client classes
    """
    client_classes = []
    logger = logging.getLogger("BedrockClientFactory")
    
    # Define the package containing model implementations
    models_package = 'dbp.llm.bedrock.models'
    
    # Import models package
    try:
        package = importlib.import_module(models_package)
        package_path = os.path.dirname(package.__file__)
        
        # Find all modules in the package
        for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
            if not is_pkg:  # Skip subpackages, only load modules
                try:
                    # Import the module
                    module = importlib.import_module(f"{models_package}.{module_name}")
                    
                    # Find all EnhancedChatBedrockConverse subclasses
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, EnhancedChatBedrockConverse) and 
                            obj != EnhancedChatBedrockConverse):
                            client_classes.append(obj)
                except ImportError as e:
                    # Log warning but continue with other modules
                    logger.warning(f"Could not import module {module_name}: {str(e)}")
    except ImportError as e:
        # Log error if models package cannot be imported
        logger.error(f"Could not import models package: {str(e)}")
        
    return client_classes

def _build_model_mappings(client_classes: List[Type[EnhancedChatBedrockConverse]]) -> Tuple[Dict, Dict]:
    """
    [Function intent]
    Builds mappings between model IDs, client classes, and parameter classes.
    
    [Design principles]
    - Create efficient lookup structures
    - Map from model ID to client class
    - Map from model ID to parameter class
    
    [Implementation details]
    - Extracts supported models from parameter classes
    - Creates dictionary mappings for fast lookup
    - Validates no duplicate model IDs across client classes
    
    Args:
        client_classes: List of discovered EnhancedChatBedrockConverse subclasses
        
    Returns:
        Tuple[Dict, Dict]: Mappings from model ID to client class and parameter class
    """
    model_to_client_class = {}
    model_to_parameter_class = {}
    logger = logging.getLogger("BedrockClientFactory")
    
    for client_class in client_classes:
        if not hasattr(client_class, 'PARAMETER_CLASSES') or not client_class.PARAMETER_CLASSES:
            logger.warning(f"Client class {client_class.__name__} has no PARAMETER_CLASSES")
            continue
            
        for param_class in client_class.PARAMETER_CLASSES:
            if hasattr(param_class, 'Config') and hasattr(param_class.Config, 'supported_models'):
                for model_id in param_class.Config.supported_models:
                    # Check for duplicate model ID mappings
                    if model_id in model_to_client_class:
                        logger.warning(
                            f"Model ID {model_id} already mapped to {model_to_client_class[model_id].__name__}, "
                            f"now also found in {client_class.__name__}"
                        )
                    
                    # Map model ID to client class and parameter class
                    model_to_client_class[model_id] = client_class
                    model_to_parameter_class[model_id] = param_class
    
    return model_to_client_class, model_to_parameter_class

def _ensure_caches_initialized():
    """
    [Function intent]
    Ensures the discovery caches are initialized.
    
    [Design principles]
    - Lazy initialization
    - One-time discovery
    - Thread-safe initialization
    
    [Implementation details]
    - Checks if caches are already initialized
    - Performs discovery if needed
    - Updates all caches
    """
    global _client_classes_cache, _model_to_client_class_cache, _model_to_parameter_class_cache
    
    # If caches are already initialized, return
    if _client_classes_cache is not None:
        return
        
    # Discover client classes
    _client_classes_cache = _discover_client_classes()
    
    # Build model mappings
    _model_to_client_class_cache, _model_to_parameter_class_cache = _build_model_mappings(_client_classes_cache)

def get_all_supported_model_ids() -> List[str]:
    """
    [Function intent]
    Returns a list of all supported model IDs across all discovered client classes.
    
    [Design principles]
    - Provide complete model discovery
    - Ensure initialization happens
    
    [Implementation details]
    - Initializes discovery caches if needed
    - Returns all keys from model mapping
    
    Returns:
        List[str]: List of all supported model IDs
    """
    _ensure_caches_initialized()
    return list(_model_to_client_class_cache.keys())

def get_client_class_for_model(model_id: str) -> Type[EnhancedChatBedrockConverse]:
    """
    [Function intent]
    Returns the appropriate client class for a given model ID.
    
    [Design principles]
    - Direct mapping lookup
    - Error handling for unknown models
    
    [Implementation details]
    - Initializes discovery caches if needed
    - Looks up client class from mapping
    - Raises exception if model is not supported
    
    Args:
        model_id: The Bedrock model ID
        
    Returns:
        Type[EnhancedChatBedrockConverse]: The client class for the model
        
    Raises:
        UnsupportedModelError: If no client class supports the model ID
    """
    _ensure_caches_initialized()
    
    # Check for exact model ID match
    if model_id in _model_to_client_class_cache:
        return _model_to_client_class_cache[model_id]
    
    # Check for model ID prefix match (for versioned models)
    model_base = model_id.split(':')[0]
    for supported_model_id, client_class in _model_to_client_class_cache.items():
        supported_base = supported_model_id.split(':')[0]
        if model_base == supported_base:
            return client_class
    
    # No match found, raise exception
    raise UnsupportedModelError(f"No client class supports model ID: {model_id}")

def get_parameter_class_for_model(model_id: str):
    """
    [Function intent]
    Returns the appropriate parameter class for a given model ID.
    
    [Design principles]
    - Direct mapping lookup
    - Error handling for unknown models
    
    [Implementation details]
    - Initializes discovery caches if needed
    - Looks up parameter class from mapping
    - Raises exception if model is not supported
    
    Args:
        model_id: The Bedrock model ID
        
    Returns:
        The parameter class for the model
        
    Raises:
        UnsupportedModelError: If no parameter class supports the model ID
    """
    _ensure_caches_initialized()
    
    # Check for exact model ID match
    if model_id in _model_to_parameter_class_cache:
        return _model_to_parameter_class_cache[model_id]
    
    # Check for model ID prefix match (for versioned models)
    model_base = model_id.split(':')[0]
    for supported_model_id, param_class in _model_to_parameter_class_cache.items():
        supported_base = supported_model_id.split(':')[0]
        if model_base == supported_base:
            return param_class
    
    # No match found, raise exception
    raise UnsupportedModelError(f"No parameter class supports model ID: {model_id}")

def get_parameter_instance_for_client(client_instance: EnhancedChatBedrockConverse):
    """
    [Function intent]
    Returns the parameter instance associated with a client instance.
    
    [Design principles]
    - Direct access to client's parameter instance
    - Type verification
    
    [Implementation details]
    - Verifies client is an EnhancedChatBedrockConverse instance
    - Returns the parameters attribute
    
    Args:
        client_instance: The client instance
        
    Returns:
        The parameter instance for the client
        
    Raises:
        TypeError: If client_instance is not an EnhancedChatBedrockConverse instance
        AttributeError: If client_instance has no parameters attribute
    """
    if not isinstance(client_instance, EnhancedChatBedrockConverse):
        raise TypeError(f"Expected EnhancedChatBedrockConverse instance, got {type(client_instance).__name__}")
    
    # The client should have initialized its parameters instance
    if not hasattr(client_instance, 'parameters') or client_instance.parameters is None:
        raise AttributeError(f"Client instance has no initialized parameters")
        
    return client_instance.parameters

def get_model_info(model_id: str) -> Dict[str, Any]:
    """
    [Function intent]
    Returns comprehensive metadata about a model based on its ID, including references
    to concrete implementation classes.
    
    [Design principles]
    - Single lookup point for model metadata
    - Complete information including class references
    - Consistent return structure
    
    [Implementation details]
    - Uses existing discovery mechanisms to find model classes
    - Extracts metadata from both client and parameter classes
    - Returns a dictionary with all model information
    
    Args:
        model_id: The Bedrock model ID
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - model_id: Original model ID
            - model_provider: Provider name (e.g., "Amazon", "Anthropic")
            - model_family_friendly_name: Model family name (e.g., "Nova", "Claude")
            - model_version: Version string (e.g., "3.5", "1.0")
            - model_variant: Variant name (e.g., "Sonnet", "Lite")
            - minor_version: Text after ':' in model_id
            - client_class: Reference to concrete client class
            - parameter_class: Reference to concrete parameter class
            
    Raises:
        UnsupportedModelError: If model is not supported
    """
    _ensure_caches_initialized()
    
    try:
        # Get concrete classes
        client_class = get_client_class_for_model(model_id)
        param_class = get_parameter_class_for_model(model_id)
        
        # Extract metadata using class methods
        minor_version = client_class.get_minor_version(model_id)
        model_version = param_class.get_model_version(model_id)
        model_variant = param_class.get_model_variant(model_id)
        
        return {
            "model_id": model_id,
            "model_provider": client_class.model_provider,
            "model_family_friendly_name": client_class.model_family_friendly_name,
            "model_version": model_version,
            "model_variant": model_variant,
            "minor_version": minor_version,
            "client_class": client_class,
            "parameter_class": param_class
        }
    except UnsupportedModelError as e:
        raise e
    except Exception as e:
        raise UnsupportedModelError(f"Error retrieving model info for {model_id}: {str(e)}")


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
    def _verify_model_support(cls, model_id: str, discovery: Any, logger: logging.Logger) -> None:
        """
        [Method intent]
        Verify that the model ID is supported by the project, checking both exact matches
        and model family prefix matches.
        
        [Design principles]
        - Fail-fast validation
        - Clear error messages
        - Project model support verification
        
        [Implementation details]
        - Checks if model ID is directly in project supported models
        - Falls back to checking model prefix support
        - Raises exception with descriptive error message when not supported
        
        Args:
            model_id: The Bedrock model ID to verify
            discovery: BedrockModelDiscovery instance
            logger: Logger instance for error messages
            
        Raises:
            UnsupportedModelError: If model ID is not supported
        """
        project_models = discovery.project_supported_models
        if model_id not in project_models:
            # Check if the model has a supported base prefix
            model_base = model_id.split(":")[0]
            supported_prefixes = {m.split(":")[0] for m in project_models}
            
            if not any(model_base == prefix for prefix in supported_prefixes):
                error_msg = f"Model ID {model_id} is not supported by this project. " + \
                          f"Supported model prefixes: {', '.join(sorted(supported_prefixes))}"
                logger.error(error_msg)
                raise UnsupportedModelError(error_msg)
    
    @classmethod
    def _extract_region_from_profile_arn(cls, inference_profile_arn: str, region_name: Optional[str], logger: logging.Logger) -> str:
        """
        [Method intent]
        Extract and validate region information from an inference profile ARN.
        
        [Design principles]
        - Clean ARN parsing
        - Transparent region override logging
        
        [Implementation details]
        - Extracts region from ARN format: arn:aws:bedrock:REGION:account-id:...
        - Logs message when overriding provided region
        - Returns the extracted region
        
        Args:
            inference_profile_arn: The inference profile ARN
            region_name: Optional current region name that might be overridden
            logger: Logger instance for information messages
            
        Returns:
            str: Extracted region from ARN
        """
        # Extract region from ARN format: arn:aws:bedrock:REGION:account-id:...
        arn_parts = inference_profile_arn.split(':')
        if len(arn_parts) >= 4 and arn_parts[3]:
            # Extract region from ARN
            extracted_region = arn_parts[3]
            
            # Override region_name with the region from the ARN
            if region_name and region_name != extracted_region:
                # Log that we're overriding the provided region
                logger.info(f"Overriding provided region {region_name} with region {extracted_region} from inference profile ARN")
            
            return extracted_region
        
        # Return original region if extraction failed
        return region_name
    
    @classmethod
    def _select_best_region(
        cls,
        model_id: str,
        region_name: Optional[str],
        use_model_discovery: bool,
        preferred_regions: Optional[List[str]],
        discovery: Any,
        logger: logging.Logger
    ) -> str:
        """
        [Method intent]
        Select the best region for a model based on discovery, provided region, or default.
        
        [Design principles]
        - Intelligent model region selection
        - Clear region selection priority
        - Fail-fast for unavailable models
        
        [Implementation details]
        - Uses model discovery when available
        - Falls back to provided region
        - Uses default region as last resort
        - Raises clear exceptions when no region is available
        
        Args:
            model_id: The Bedrock model ID
            region_name: Optional provided region name
            use_model_discovery: Whether to use model discovery
            preferred_regions: Optional list of preferred regions
            discovery: BedrockModelDiscovery instance
            logger: Logger instance
            
        Returns:
            str: Selected region name
            
        Raises:
            ConfigurationError: If no available regions found
        """
        # Return existing region if provided
        if region_name:
            return region_name
            
        # Find the best region if not specified and using model discovery
        if use_model_discovery:
            best_regions = discovery.get_best_regions_for_model(model_id, preferred_regions)
            if not best_regions:
                error_msg = f"No available regions found for model {model_id}"
                logger.error(error_msg)
                raise ConfigurationError(error_msg)
            
            selected_region = best_regions[0]
            logger.info(f"Selected best region for {model_id}: {selected_region}")
            return selected_region
        
        # If region isn't specified and model discovery is disabled, throw error
        error_msg = f"Region must be specified when model discovery is disabled"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    @classmethod
    def _select_inference_profile(
        cls, 
        model_id: str,
        region_name: str,
        inference_profile_arn: Optional[str], 
        discovery: Any,
        logger: logging.Logger
    ) -> Optional[str]:
        """
        [Method intent]
        Select the appropriate inference profile for a model if not explicitly provided.
        
        [Design principles]
        - Automatic inference profile selection
        - Priority-based profile selection
        - Clear error handling for required profiles
        
        [Implementation details]
        - Returns existing profile ARN if provided
        - Prioritizes SYSTEM_DEFINED profiles
        - Falls back to other available profiles
        - Raises error if profile required but none available
        
        Args:
            model_id: The Bedrock model ID
            region_name: AWS region name
            inference_profile_arn: Optional explicitly provided inference profile ARN
            discovery: BedrockModelDiscovery instance
            logger: Logger instance
            
        Returns:
            Optional[str]: Selected inference profile ARN or None
            
        Raises:
            ConfigurationError: If profile required but none available
        """
        # Return the provided profile if available
        if inference_profile_arn:
            return inference_profile_arn
            
        # Only proceed if we have a region_name
        if not region_name:
            return None
            
        # Get model information
        model_info = discovery.get_model(model_id, region_name)
        if not model_info:
            return None
            
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
            selected_arn = selected_profile["inferenceProfileArn"]
            logger.info(f"Auto-selected {profile_source} inference profile ARN for {model_id}: {selected_arn}")
            return selected_arn
        
        # If the model requires an inference profile and none was found, raise error
        if model_info.get("requiresInferenceProfile", False):
            error_msg = f"Model {model_id} requires an inference profile, but none was found"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
            
        # No profile needed or found
        return None
    
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
            cls._verify_model_support(model_id, discovery, logger)
            
            # Process inference profile ARN and extract region if available
            if inference_profile_arn:
                region_name = cls._extract_region_from_profile_arn(inference_profile_arn, region_name, logger)
            
            # Find the best region if needed
            region_name = cls._select_best_region(
                model_id, region_name, use_model_discovery, 
                preferred_regions, discovery, logger
            )
                    
            # Select inference profile if needed
            inference_profile_arn = cls._select_inference_profile(
                model_id, region_name, inference_profile_arn, 
                discovery, logger
            )
            
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
                    read_timeout=900  # Much higher read timeout (15 minutes) for large documents
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
                
                # Use our new discovery system to get the appropriate client class
                try:
                    model_class = get_client_class_for_model(model_id)
                    logger.info(f"Using {model_class.__name__} for model {model_id}")
                except UnsupportedModelError:
                    # This shouldn't happen, since we've already verified the model is supported above
                    # But include fallback logic for robustness
                    logger.warning(f"No specific client class found for {model_id}, using base class")
                    raise
                
                # Create the model instance
                try:
                    chat_bedrock = model_class(
                        model=model_param,  
                        client=bedrock_client,
                        logger=logger
                    )
                    
                    # Now that the model is created, we can set the model parameters 
                    # as attributes directly if needed
                    if model_kwargs:
                        # Store model kwargs outside of the model for future use if needed
                        object.__setattr__(chat_bedrock, "_cached_model_kwargs", model_kwargs)
                        
                        # Apply model kwargs directly to the parameters object if it exists
                        if hasattr(chat_bedrock, "parameters") and chat_bedrock.parameters:
                            for key, value in model_kwargs.items():
                                if hasattr(chat_bedrock.parameters, key):
                                    setattr(chat_bedrock.parameters, key, value)
                
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
