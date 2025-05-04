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
# codebase:src/dbp/llm/bedrock/enhanced_base.py
# codebase:src/dbp/llm/common/exceptions.py
# codebase:doc/design/LLM_COORDINATION.md
# system:logging
# system:importlib
# system:pkgutil
# system:typing
# system:inspect
###############################################################################
# [GenAI tool change history]
# 2025-05-04T12:04:45Z : Created Bedrock client factory by CodeAssistant
# * Implemented dynamic client class detection without hardcoding
# * Added strict error handling with appropriate exceptions
# * Added project model support verification
# * Added automatic inference profile detection and selection
# * Integrated with model discovery for region and profile management
###############################################################################

"""
Factory class for creating Bedrock clients with dynamic client class detection.
"""

import logging
import importlib
import pkgutil
import inspect
from typing import Dict, Any, List, Optional, Type, Set

from .enhanced_base import EnhancedBedrockBase
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
    
    # Cache for discovered client classes
    _client_classes = None
    _model_to_client_map = None
    
    @classmethod
    def _discover_client_classes(cls) -> Dict[str, Type[EnhancedBedrockBase]]:
        """
        [Method intent]
        Dynamically discover all available Bedrock client classes and their supported models.
        
        [Design principles]
        - Dynamic class discovery without hardcoding
        - Introspection of class capabilities
        - Caching for performance
        - Fail-fast error handling
        
        [Implementation details]
        - Uses importlib and pkgutil to scan the models package
        - Inspects classes for EnhancedBedrockBase subclass and SUPPORTED_MODELS attribute
        - Maps each model ID to its supporting client class
        - Caches discovery results for performance
        - Raises exceptions on critical errors
        
        Returns:
            Dict[str, Type[EnhancedBedrockBase]]: Dictionary mapping model IDs to client classes
            
        Raises:
            LLMError: If client discovery fails
        """
        if cls._model_to_client_map is not None:
            return cls._model_to_client_map
        
        # Maps model IDs to their supporting client classes
        model_to_client = {}
        client_classes = []
        logger = logging.getLogger("BedrockClientFactory")
        
        # Import models package
        try:
            from . import models
            model_package_path = models.__path__
            model_package_name = models.__name__
            
            # Scan all modules in the models package
            for _, module_name, _ in pkgutil.iter_modules(model_package_path):
                try:
                    # Import module
                    module = importlib.import_module(f"{model_package_name}.{module_name}")
                    
                    # Find all client classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, EnhancedBedrockBase) and 
                            obj != EnhancedBedrockBase and
                            hasattr(obj, 'SUPPORTED_MODELS')):
                            
                            # Add to client classes list
                            client_classes.append(obj)
                            
                            # Register the client class for each supported model
                            for model_id in obj.SUPPORTED_MODELS:
                                model_to_client[model_id] = obj
                                
                except (ImportError, AttributeError) as e:
                    # Log but continue with other modules
                    logger.error(f"Error loading client module {module_name}: {str(e)}")
                    
        except Exception as e:
            # Critical error in discovery process
            error_msg = f"Failed to discover client classes: {str(e)}"
            logger.error(error_msg)
            raise LLMError(error_msg, e)
        
        if not client_classes:
            error_msg = "No Bedrock client classes found"
            logger.error(error_msg)
            raise LLMError(error_msg)
        
        # Cache the discovered classes
        cls._client_classes = client_classes
        cls._model_to_client_map = model_to_client
        
        return model_to_client
    
    @classmethod
    def get_client_for_model(cls, model_id: str) -> Type[EnhancedBedrockBase]:
        """
        [Method intent]
        Get the appropriate client class for a given model ID.
        
        [Design principles]
        - Dynamic detection without hardcoding
        - Clear class selection logic
        - Support for exact and prefix matching
        - Fail-fast error handling
        
        [Implementation details]
        - First attempts exact match with full model ID
        - Falls back to prefix matching if no exact match
        - Raises exception if no supporting client found
        
        Args:
            model_id: The Bedrock model ID
            
        Returns:
            Type[EnhancedBedrockBase]: The appropriate client class
            
        Raises:
            UnsupportedModelError: If no client class supports the model
        """
        # Get the model-to-client map
        model_to_client = cls._discover_client_classes()
        
        # Try exact match first
        if model_id in model_to_client:
            return model_to_client[model_id]
        
        # If no exact match, try prefix matching
        model_prefix = model_id.split(":")[0]
        
        for supported_model, client_class in model_to_client.items():
            supported_prefix = supported_model.split(":")[0]
            if model_prefix == supported_prefix:
                return client_class
        
        # No matching client found
        error_msg = f"No client class found for model ID {model_id}"
        logging.getLogger("BedrockClientFactory").error(error_msg)
        raise UnsupportedModelError(error_msg)
        
    @classmethod
    def create_client(
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
        inference_profile_arn: Optional[str] = None
    ) -> EnhancedBedrockBase:
        """
        [Method intent]
        Create an appropriate Bedrock client based on the model ID, with automatic 
        region and inference profile selection if not explicitly provided.
        
        [Design principles]
        - Simplify client creation with sensible defaults
        - Abstract model-specific details
        - Support automatic and manual configuration
        - Verify model support against project-supported models
        - Fail-fast error handling
        
        [Implementation details]
        - Verifies model ID against project-supported models
        - Determines the client class based on model ID
        - Uses model discovery to find the best region if not specified
        - Automatically selects inference profiles if required
        - Allows manual override of all parameters
        - Raises exceptions on all error conditions
        
        Args:
            model_id: The Bedrock model ID
            region_name: Optional AWS region name
            profile_name: Optional AWS profile name
            credentials: Optional explicit AWS credentials
            max_retries: Maximum number of API retries
            timeout: API timeout in seconds
            logger: Optional custom logger instance
            use_model_discovery: Whether to discover model availability
            preferred_regions: Optional list of preferred regions
            inference_profile_arn: Optional inference profile ARN (overrides automatic selection)
            
        Returns:
            EnhancedBedrockBase: The appropriate client instance for the model
            
        Raises:
            UnsupportedModelError: If model ID is not supported by the project
            ConfigurationError: If required configuration is missing or invalid
            LLMError: If client creation fails for other reasons
        """
        # Initialize logger
        logger = logger or logging.getLogger("BedrockClientFactory")
        
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
        
        # Find the best region if not specified
        if not region_name and use_model_discovery:
            best_regions = discovery.get_best_regions_for_model(model_id)
            if best_regions:
                region_name = best_regions[0]
                logger.info(f"Selected best region for {model_id}: {region_name}")
            else:
                error_msg = f"No available regions found for model {model_id}"
                logger.error(error_msg)
                raise ConfigurationError(error_msg)
            
        # Check for automatic inference profile selection if not explicitly provided
        if not inference_profile_arn and use_model_discovery and region_name:
            model_info = discovery.get_model(model_id, region_name)
            if model_info and model_info.get("requiresInferenceProfile", False):
                # Try to get an inference profile ARN
                profiles = model_info.get("referencedByInstanceProfiles", [])
                if profiles and len(profiles) > 0:
                    # Get the first profile that matches this model
                    profile_found = False
                    for profile in profiles:
                        if "inferenceProfileArn" in profile:
                            inference_profile_arn = profile["inferenceProfileArn"]
                            logger.info(f"Auto-selected inference profile ARN for {model_id}: {inference_profile_arn}")
                            profile_found = True
                            break
                    
                    if not profile_found:
                        error_msg = f"Model {model_id} requires an inference profile, but none was found"
                        logger.error(error_msg)
                        raise ConfigurationError(error_msg)
        
        try:
            # Determine the appropriate client class based on supported models
            client_class = cls.get_client_for_model(model_id)
            logger.info(f"Using {client_class.__name__} for model {model_id}")
            
            # Create and return the client instance
            return client_class(
                model_id=model_id,
                region_name=region_name,
                profile_name=profile_name,
                credentials=credentials,
                max_retries=max_retries,
                timeout=timeout,
                logger=logger,
                use_model_discovery=use_model_discovery,
                preferred_regions=preferred_regions,
                inference_profile_arn=inference_profile_arn
            )
        except (UnsupportedModelError, ConfigurationError) as e:
            # Re-raise specific exceptions
            raise e
        except Exception as e:
            # Wrap other exceptions
            error_msg = f"Failed to create client for model {model_id}: {str(e)}"
            logger.error(error_msg)
            raise LLMError(error_msg, e)
