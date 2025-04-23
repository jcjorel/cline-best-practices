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
# Implements a central manager for all Bedrock model clients. This manager
# serves as the main entry point for all Bedrock LLM operations, providing
# a unified interface for accessing various model clients and handling their
# lifecycle.
###############################################################################
# [Source file design principles]
# - Centralize Bedrock client management across the application
# - Lazily initialize model clients only when needed
# - Cache clients for reuse to optimize resource usage
# - Provide a simple interface for retrieving clients by name
# - Handle configuration loading and default values
# - Support clean shutdown of all active clients
###############################################################################
# [Source file constraints]
# - Must support multiple model types with different parameter requirements
# - Must not hardcode AWS credentials or region information
# - Must handle model unavailability gracefully
# - Must be thread-safe for concurrent access from multiple components
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T13:00:00Z : Initial creation of Bedrock client manager by Cline
# * Implemented client registry and lazy initialization
# * Added support for configuration-based client creation
# * Created interface for retrieving model clients by name
###############################################################################

import logging
import os
import threading
from typing import Dict, Optional, Any, Type, Union, List, Tuple

import boto3
from botocore.config import Config

from .bedrock_base import BedrockModelClientBase, BedrockClientError
from .nova_lite_client import NovaLiteClient
from .claude3_7_client import Claude37SonnetClient
from .prompt_manager import LLMPromptManager

logger = logging.getLogger(__name__)

class BedrockClientManager:
    """
    Singleton manager for Bedrock model clients across the application.
    
    This class provides a unified interface for accessing different Bedrock
    model clients, handling their initialization, configuration, and lifecycle
    management. It uses a singleton pattern to ensure only one instance exists.
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    # Default configuration for models if not specified elsewhere
    DEFAULT_CONFIG = {
        "nova-lite": {
            "enabled": True,
            "model_id": "amazon.nova-lite-v1:0",
            "max_retries": 3,
            "connect_timeout": 10,
            "read_timeout": 30,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000,
            # List of regions where this model is available
            "available_regions": [
                "us-east-1",
                "us-west-2",
                "eu-west-1"
            ]
        },
        "claude-3-7-sonnet": {
            "enabled": True,
            "model_id": "anthropic.claude-3-7-sonnet-20240620-v1:0",
            "max_retries": 3,
            "connect_timeout": 10,
            "read_timeout": 60, # Claude can take longer for complex responses
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 4000,
            # List of regions where this model is available
            "available_regions": [
                "us-east-1",
                "us-west-2",
                "eu-west-1"
            ]
        }
        # Add more model defaults as needed
    }
    
    # Registry of available model client classes
    MODEL_CLIENT_REGISTRY = {
        "nova-lite": NovaLiteClient,
        "claude-3-7-sonnet": Claude37SonnetClient,
        # Add more model client classes here as they're implemented
    }
    
    # Fallback regions in order of preference
    FALLBACK_REGIONS = [
        "us-east-1",  # N. Virginia - primary region for most services
        "us-west-2",  # Oregon - secondary US region
        "eu-west-1",  # Ireland - primary EU region
        "ap-northeast-1"  # Tokyo - primary APAC region
    ]
    
    @classmethod
    def get_instance(
        cls, 
        config: Optional[Dict[str, Any]] = None,
        default_region: Optional[str] = None,
        prompt_manager: Optional[LLMPromptManager] = None,
        logger_override: Optional[logging.Logger] = None
    ) -> 'BedrockClientManager':
        """
        Get the singleton instance of BedrockClientManager.
        
        If the instance doesn't exist, it will be created.
        If it exists, it will be configured with the provided parameters if any.
        
        Args:
            config: Configuration dictionary with model settings
            default_region: Default AWS region for all clients
            prompt_manager: Shared prompt manager for all clients
            logger_override: Optional logger instance
            
        Returns:
            The singleton BedrockClientManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        config=config,
                        default_region=default_region,
                        prompt_manager=prompt_manager,
                        logger_override=logger_override,
                        _is_singleton=True
                    )
        else:
            # Update existing instance with new config if provided
            cls._instance._update_config(
                config=config,
                default_region=default_region,
                prompt_manager=prompt_manager,
                logger_override=logger_override
            )
        
        return cls._instance
    
    def __init__(
        self, 
        config: Optional[Dict[str, Any]] = None,
        default_region: Optional[str] = None,
        prompt_manager: Optional[LLMPromptManager] = None,
        logger_override: Optional[logging.Logger] = None,
        _is_singleton: bool = False
    ):
        """
        Initialize the Bedrock client manager.
        
        Note: This should not be called directly. Use get_instance() instead.
        
        Args:
            config: Configuration dictionary with model settings
            default_region: Default AWS region for all clients
            prompt_manager: Shared prompt manager for all clients
            logger_override: Optional logger instance
            _is_singleton: Internal flag to enforce singleton pattern
        """
        # Enforce singleton pattern
        if not _is_singleton:
            raise RuntimeError(
                "BedrockClientManager is a singleton. "
                "Use BedrockClientManager.get_instance() instead."
            )
        
        self.config = config or {}
        self.default_region = default_region or os.getenv('AWS_REGION', 'us-east-1')
        self.prompt_manager = prompt_manager
        self.logger = logger_override or logger
        
        # Cache for initialized clients, organized by region and model name
        # {region1: {model_name1: client1, model_name2: client2}, region2: {...}}
        self._clients: Dict[str, Dict[str, BedrockModelClientBase]] = {}
        
        # Cache for boto3 clients by region
        self._boto3_clients: Dict[str, Any] = {}
        
        # Cache for region availability status
        self._region_model_availability: Dict[str, Dict[str, bool]] = {}
        
        self.logger.info({
            "message": "Bedrock client manager initialized",
            "default_region": self.default_region,
            "prompt_manager_configured": self.prompt_manager is not None
        })
    
    def _update_config(
        self,
        config: Optional[Dict[str, Any]] = None,
        default_region: Optional[str] = None,
        prompt_manager: Optional[LLMPromptManager] = None,
        logger_override: Optional[logging.Logger] = None
    ) -> None:
        """
        Update the configuration of the manager.
        
        Args:
            config: New configuration dictionary
            default_region: New default region
            prompt_manager: New prompt manager
            logger_override: New logger instance
        """
        if config is not None:
            self.config = config
            self.logger.debug({
                "message": "Updated client manager configuration"
            })
        
        if default_region is not None:
            self.default_region = default_region
            self.logger.debug({
                "message": "Updated default region",
                "default_region": self.default_region
            })
        
        if prompt_manager is not None:
            self.prompt_manager = prompt_manager
            self.logger.debug({
                "message": "Updated prompt manager"
            })
        
        if logger_override is not None:
            self.logger = logger_override

    def _get_boto3_client(self, region: str) -> Any:
        """
        Get a boto3 client for a specific region, initializing it if necessary.
        
        Args:
            region: AWS region for the client
            
        Returns:
            boto3.client: The initialized boto3 client
        """
        if region in self._boto3_clients:
            return self._boto3_clients[region]
            
        # Create boto3 client configuration
        config = Config(
            retries=dict(
                max_attempts=3,
                mode='standard'
            ),
            connect_timeout=10,
            read_timeout=30
        )
        
        self.logger.debug({
            "message": "Creating new boto3 client for region",
            "region": region
        })
        
        # Initialize the client
        boto3_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            config=config
        )
        
        # Cache the client
        self._boto3_clients[region] = boto3_client
        
        self.logger.info({
            "message": "Initialized new boto3 client for region",
            "region": region
        })
        
        return boto3_client
    
    def _check_model_availability(self, model_id: str, region: str) -> bool:
        """
        Check if a model is available in a specific region.
        
        Args:
            model_id: The Bedrock model ID to check
            region: AWS region to check
            
        Returns:
            bool: True if the model is available, False otherwise
        """
        # Check cache first
        if region in self._region_model_availability and model_id in self._region_model_availability[region]:
            return self._region_model_availability[region][model_id]
            
        # Initialize cache if needed
        if region not in self._region_model_availability:
            self._region_model_availability[region] = {}
            
        # Get boto3 client
        try:
            client = self._get_boto3_client(region)
            
            # Check if model is available
            self.logger.debug({
                "message": "Checking model availability",
                "model_id": model_id,
                "region": region
            })
            
            try:
                client.get_model_invocation_logging_configuration(modelId=model_id)
                # Model is available
                self._region_model_availability[region][model_id] = True
                self.logger.info({
                    "message": "Model is available in region",
                    "model_id": model_id,
                    "region": region
                })
                return True
            except client.exceptions.ValidationException:
                # Model is not available
                self._region_model_availability[region][model_id] = False
                self.logger.warning({
                    "message": "Model is not available in region",
                    "model_id": model_id,
                    "region": region
                })
                return False
        except Exception as e:
            self.logger.error({
                "message": "Error checking model availability",
                "model_id": model_id,
                "region": region,
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            # Assume model is not available if we can't check
            self._region_model_availability[region][model_id] = False
            return False
    
    def _find_available_region(self, model_name: str, model_id: str, preferred_region: str = None) -> str:
        """
        Find a region where the model is available.
        
        First checks the preferred region, then falls back to the list
        of known available regions for the model, and finally tries the
        global fallback regions if needed.
        
        Args:
            model_name: Name of the model
            model_id: ID of the model
            preferred_region: Preferred region to check first
            
        Returns:
            str: Region where the model is available
            
        Raises:
            BedrockClientError: If the model is not available in any region
        """
        # Get model configuration for available regions
        model_config = self._get_model_config(model_name)
        available_regions = model_config.get("available_regions", [])
        
        # Regions to check in order
        regions_to_check = []
        
        # Add preferred region first if specified
        if preferred_region:
            regions_to_check.append(preferred_region)
        
        # Add configured default region if different from preferred
        if self.default_region and self.default_region != preferred_region:
            regions_to_check.append(self.default_region)
        
        # Add all available regions not already included
        for region in available_regions:
            if region not in regions_to_check:
                regions_to_check.append(region)
        
        # Add fallback regions not already included
        for region in self.FALLBACK_REGIONS:
            if region not in regions_to_check:
                regions_to_check.append(region)
        
        # Check each region for availability
        for region in regions_to_check:
            if self._check_model_availability(model_id, region):
                return region
        
        # No region found where model is available
        available_regions_str = ", ".join(regions_to_check)
        error_message = f"Model {model_name} (ID: {model_id}) is not available in any checked region: {available_regions_str}"
        self.logger.error({
            "message": "Model not available in any checked region",
            "model_name": model_name,
            "model_id": model_id,
            "checked_regions": regions_to_check
        })
        raise BedrockClientError(error_message)
        
    def get_client(
        self, 
        model_name: str,
        region: Optional[str] = None,
        initialize: bool = True
    ) -> BedrockModelClientBase:
        """
        Get a model client by name, initializing it if necessary.
        
        Args:
            model_name: Name of the model client to retrieve
            region: Optional region override for this client
            initialize: Whether to initialize the client immediately
            
        Returns:
            The requested model client
            
        Raises:
            ValueError: If the model name is unknown or not configured
            BedrockClientError: If client initialization fails
        """
        # Get model client class from registry
        if model_name not in self.MODEL_CLIENT_REGISTRY:
            self.logger.error({
                "message": "Unknown model client requested",
                "model_name": model_name,
                "available_models": list(self.MODEL_CLIENT_REGISTRY.keys())
            })
            raise ValueError(f"Unknown model client: {model_name}")
        
        # Get client class
        client_class = self.MODEL_CLIENT_REGISTRY[model_name]
        
        # Get model configuration
        model_config = self._get_model_config(model_name)
        if not model_config.get("enabled", True):
            self.logger.warning({
                "message": "Requested model is disabled in configuration",
                "model_name": model_name
            })
            raise ValueError(f"Model {model_name} is disabled in configuration")
        
        # Get model ID
        model_id = model_config.get("model_id")
        if not model_id:
            self.logger.error({
                "message": "Model ID not found in configuration",
                "model_name": model_name
            })
            raise ValueError(f"Model ID not found for {model_name}")
        
        # Get the preferred region - either from param, config, or default
        preferred_region = region or model_config.get("region") or self.default_region
        
        # Use existing client if available for the requested region
        if preferred_region in self._clients and model_name in self._clients[preferred_region]:
            self.logger.debug({
                "message": "Using existing model client from cache",
                "model_name": model_name,
                "region": preferred_region
            })
            return self._clients[preferred_region][model_name]
        
        # Find an available region for this model
        try:
            available_region = self._find_available_region(model_name, model_id, preferred_region)
        except BedrockClientError as e:
            self.logger.error({
                "message": "Failed to find available region for model",
                "model_name": model_name,
                "model_id": model_id,
                "error": str(e)
            })
            raise
        
        # Update the model config with the resolved region
        model_config["region"] = available_region
        
        # Create client instance
        client = self._create_client(model_name, client_class, model_config)
        
        # Initialize if requested
        if initialize:
            try:
                client.initialize()
            except BedrockClientError as e:
                self.logger.error({
                    "message": "Failed to initialize model client",
                    "model_name": model_name,
                    "region": available_region,
                    "error": str(e)
                })
                raise
        
        # Initialize region in client cache if needed
        if available_region not in self._clients:
            self._clients[available_region] = {}
            
        # Cache the client for future use
        self._clients[available_region][model_name] = client
        
        self.logger.info({
            "message": "Created new model client",
            "model_name": model_name,
            "model_id": model_id,
            "region": available_region,
            "client_type": client_class.__name__,
            "initialized": initialize
        })
        
        return client

    def _get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model, merging defaults.
        
        Args:
            model_name: Name of the model to get configuration for
            
        Returns:
            Dict with model configuration
        """
        # Start with default configuration
        default_model_config = self.DEFAULT_CONFIG.get(model_name, {})
        
        # Get model-specific configuration from bedrock section
        bedrock_config = self.config.get("bedrock", {})
        models_config = bedrock_config.get("models", {})
        model_config = models_config.get(model_name, {})
        
        # Merge configurations
        merged_config = {**default_model_config, **model_config}
        
        # Add default region if specified
        if self.default_region and "region" not in merged_config:
            merged_config["region"] = self.default_region
        elif not "region" in merged_config and "default_region" in bedrock_config:
            merged_config["region"] = bedrock_config["default_region"]
        
        return merged_config

    def _create_client(
        self, 
        model_name: str, 
        client_class: Type[BedrockModelClientBase],
        model_config: Dict[str, Any]
    ) -> BedrockModelClientBase:
        """
        Create a new model client instance.
        
        Args:
            model_name: Name of the model
            client_class: Model client class to instantiate
            model_config: Configuration for the model
            
        Returns:
            New model client instance
        """
        # Create logger for this client
        client_logger = self.logger.getChild(f"models.{model_name}")
        
        # Create common parameters
        common_params = {
            "region": model_config.get("region", self.default_region),
            "max_retries": model_config.get("max_retries", 3),
            "connect_timeout": model_config.get("connect_timeout", 10),
            "read_timeout": model_config.get("read_timeout", 30),
            "logger_override": client_logger,
        }
        
        # Add model ID if specified
        if "model_id" in model_config:
            common_params["model_id"] = model_config["model_id"]
        
        # Add prompt manager if available
        if self.prompt_manager:
            common_params["prompt_manager"] = self.prompt_manager
        
        # Add model-specific parameters
        # For NovaLiteClient
        if client_class == NovaLiteClient:
            if "temperature" in model_config:
                common_params["temperature"] = model_config["temperature"]
            if "top_p" in model_config:
                common_params["top_p"] = model_config["top_p"]
            if "max_tokens" in model_config:
                common_params["max_tokens"] = model_config["max_tokens"]
        
        # Create and return the client
        return client_class(**common_params)

    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available without raising exceptions.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            bool: True if the model is available, False otherwise
        """
        try:
            client = self.get_client(model_name, initialize=False)
            return client.is_available()
        except (ValueError, BedrockClientError):
            return False

    def shutdown_all(self) -> None:
        """
        Shutdown all active model clients.
        """
        # Count total active clients
        active_clients_count = sum(len(clients) for clients in self._clients.values())
        
        self.logger.info({
            "message": "Shutting down all Bedrock model clients",
            "active_regions": list(self._clients.keys()),
            "active_clients_count": active_clients_count
        })
        
        # Shutdown each client
        for region, clients in self._clients.items():
            for model_name, client in clients.items():
                try:
                    client.shutdown()
                    self.logger.debug({
                        "message": "Model client shutdown successful",
                        "region": region,
                        "model_name": model_name
                    })
                except Exception as e:
                    self.logger.error({
                        "message": "Error during model client shutdown",
                        "region": region,
                        "model_name": model_name,
                        "error_type": type(e).__name__,
                        "error_details": str(e)
                    })
        
        # Clear all caches
        self._clients.clear()
        self._boto3_clients.clear()
        self._region_model_availability.clear()
        
        self.logger.info({
            "message": "Bedrock client manager shutdown complete"
        })
