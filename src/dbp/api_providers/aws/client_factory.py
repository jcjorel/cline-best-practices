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
# Provides a centralized factory for creating, configuring, and caching AWS clients
# across different services and regions. Implements a singleton pattern to ensure
# consistent client configuration and efficient resource utilization throughout
# the application.
###############################################################################
# [Source file design principles]
# - Thread-safe client creation and caching
# - Region and service-specific client management
# - Standardized configuration profiles for different service types
# - Consistent credential handling across the application
# - Memory-efficient through client reuse
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must be memory-efficient through appropriate caching
# - Must handle AWS credential management securely
# - Must be compatible with all AWS services used in the project
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/exceptions.py
# system:boto3
# system:botocore
# system:hashlib
# system:threading
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-03T11:31:12Z : Initial implementation by CodeAssistant
# * Created AWSClientFactory singleton class
# * Added thread-safe client and session caching
# * Implemented service-specific configuration profiles
# * Added methods for getting clients and sessions
###############################################################################

import hashlib
import json
import logging
import threading
from typing import Dict, Any, Optional, List

import boto3
import botocore
from botocore.config import Config
from botocore.exceptions import ClientError as BotocoreClientError

from .exceptions import (
    AWSClientError,
    AWSCredentialError,
    AWSRegionError,
    AWSServiceError
)


class AWSClientFactory:
    """
    [Class intent]
    Thread-safe factory for boto3 AWS clients with service and region-based caching.
    Provides a central point for AWS service access across the entire project.
    
    [Design principles]
    - Region and service-specific client caching for performance
    - Thread safety for concurrent access from multiple components
    - Consistent configuration (retries, timeouts) across clients
    - Standardized credential management
    - Singleton pattern for project-wide reuse
    
    [Implementation details]
    - Uses composite key of (service, region, profile, credentials_hash) for cache
    - Applies standardized retry and timeout policies
    - Implements thread-safe caching with minimal locking overhead
    - Provides singleton access pattern
    """
    
    # Class variables for singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    # Default configurations for different service types
    DEFAULT_CONFIGS = {
        # Standard services like S3, DynamoDB
        "standard": Config(
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30
        ),
        # AI services like Bedrock, need longer timeouts
        "ai": Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=120
        ),
        # Data services that might involve larger payloads
        "data": Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60
        )
    }
    
    # Service type categorization
    SERVICE_TYPES = {
        "bedrock": "ai",
        "sagemaker": "ai",
        "comprehend": "ai",
        "textract": "ai",
        "rekognition": "ai",
        "s3": "standard",
        "dynamodb": "standard",
        "lambda": "standard",
        "ec2": "standard",
        "cloudformation": "standard",
        "athena": "data",
        "glue": "data",
        "redshift": "data",
        "redshift-data": "data"
        # Add more service mappings as needed
    }
    
    @classmethod
    def get_instance(cls):
        """
        [Method intent]
        Get the singleton instance of AWSClientFactory, creating it if needed.
        
        [Design principles]
        - Thread-safe singleton access
        - Lazy initialization
        
        [Implementation details]
        - Double-checked locking pattern
        - Creates instance only when first needed
        - Returns same instance for all callers
        
        Returns:
            AWSClientFactory: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        [Method intent]
        Initialize the AWS client factory with caching structures.
        
        [Design principles]
        - Protected constructor for singleton pattern
        - Thread-safe initialization
        
        [Implementation details]
        - Sets up cache structures
        - Initializes locks for thread safety
        - Configures logging
        
        Raises:
            RuntimeError: If attempting to create instance directly instead of using get_instance()
        """
        # Enforce singleton pattern
        if self.__class__._instance is not None:
            raise RuntimeError(f"{self.__class__.__name__} is a singleton and should be accessed via get_instance()")
        
        self._clients_cache = {}
        self._session_cache = {}
        self._cache_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def get_client(self, 
                  service_name: str, 
                  region_name: Optional[str] = None, 
                  profile_name: Optional[str] = None, 
                  credentials: Optional[Dict[str, Any]] = None,
                  config: Optional[Config] = None,
                  **kwargs) -> Any:
        """
        [Method intent]
        Get a cached boto3 client or create a new one with appropriate configuration.
        
        [Design principles]
        - Cache-first approach for performance
        - Consistent configuration based on service type
        - Support for explicit credentials
        - Thread-safe access
        
        [Implementation details]
        - Generates cache key from parameters
        - Checks cache before creating new client
        - Applies service-appropriate configurations
        - Updates cache with new clients
        
        Args:
            service_name: AWS service name (e.g., "bedrock", "s3")
            region_name: AWS region name (e.g., "us-east-1")
            profile_name: AWS profile name for credentials
            credentials: Explicit credentials dict (overrides profile)
            config: Custom boto3 Config object (overrides defaults)
            **kwargs: Additional parameters for boto3 client
            
        Returns:
            boto3.client: AWS service client
            
        Raises:
            AWSCredentialError: For credential-related issues
            AWSRegionError: For region-related issues
            AWSServiceError: For service-specific errors
        """
        # Generate cache key
        cache_key = self._generate_client_key(
            service_name, region_name, profile_name, credentials, config)
        
        # Check cache first
        with self._cache_lock:
            if cache_key in self._clients_cache:
                return self._clients_cache[cache_key]
        
        # If not in cache, create new client
        try:
            # Get appropriate session
            session = self.get_session(region_name, profile_name, credentials)
            
            # Apply service-specific configuration if no custom config provided
            if config is None:
                service_type = self.SERVICE_TYPES.get(service_name, "standard")
                config = self.DEFAULT_CONFIGS[service_type]
            
            # Create client
            client = session.client(
                service_name, 
                region_name=region_name,
                config=config, 
                **kwargs
            )
            
            # Cache client
            with self._cache_lock:
                self._clients_cache[cache_key] = client
            
            return client
            
        except BotocoreClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code in ('InvalidClientTokenId', 'UnrecognizedClientException', 
                             'AccessDenied', 'AuthFailure'):
                raise AWSCredentialError(
                    f"Invalid AWS credentials: {error_message}",
                    service_name=service_name,
                    region_name=region_name,
                    error_code=error_code,
                    original_error=e
                ) from e
                
            elif error_code in ('InvalidRegion', 'EndpointConnectionError'):
                raise AWSRegionError(
                    f"Invalid or unsupported region: {error_message}",
                    service_name=service_name,
                    region_name=region_name,
                    error_code=error_code,
                    original_error=e
                ) from e
                
            else:
                raise AWSServiceError(
                    f"Service error: {error_message}",
                    service_name=service_name,
                    region_name=region_name,
                    error_code=error_code,
                    original_error=e
                ) from e
                
        except Exception as e:
            raise AWSClientError(
                f"Failed to create AWS client: {str(e)}",
                service_name=service_name,
                region_name=region_name,
                original_error=e
            ) from e
    
    def get_session(self,
                   region_name: Optional[str] = None,
                   profile_name: Optional[str] = None,
                   credentials: Optional[Dict[str, Any]] = None) -> boto3.Session:
        """
        [Method intent]
        Get a cached boto3 session or create a new one with appropriate credentials.
        
        [Design principles]
        - Cache-first approach for performance
        - Support for profile-based or explicit credentials
        - Thread-safe access
        
        [Implementation details]
        - Generates cache key from parameters
        - Checks cache before creating new session
        - Applies credentials consistently
        - Updates cache with new sessions
        
        Args:
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit credentials dict (overrides profile)
            
        Returns:
            boto3.Session: AWS session with appropriate credentials
            
        Raises:
            AWSCredentialError: For credential-related issues
        """
        # Generate cache key
        cache_key = self._generate_session_key(region_name, profile_name, credentials)
        
        # Check cache first
        with self._cache_lock:
            if cache_key in self._session_cache:
                return self._session_cache[cache_key]
        
        # If not in cache, create new session
        try:
            session_kwargs = {}
            
            # Apply region if specified
            if region_name:
                session_kwargs['region_name'] = region_name
            
            # Apply credentials (profile or explicit)
            if profile_name:
                session_kwargs['profile_name'] = profile_name
            elif credentials:
                session_kwargs.update({
                    'aws_access_key_id': credentials.get('aws_access_key_id'),
                    'aws_secret_access_key': credentials.get('aws_secret_access_key'),
                    'aws_session_token': credentials.get('aws_session_token')
                })
            
            # Create session
            session = boto3.Session(**session_kwargs)
            
            # Cache session
            with self._cache_lock:
                self._session_cache[cache_key] = session
            
            return session
            
        except Exception as e:
            # Handle credential-specific exceptions
            if 'profile' in str(e).lower() or 'credential' in str(e).lower():
                raise AWSCredentialError(
                    f"AWS credential error: {str(e)}",
                    region_name=region_name,
                    original_error=e
                ) from e
            else:
                raise AWSClientError(
                    f"Failed to create AWS session: {str(e)}",
                    region_name=region_name,
                    original_error=e
                ) from e
    
    def clear_cache(self, 
                   service_name: Optional[str] = None,
                   region_name: Optional[str] = None) -> None:
        """
        [Method intent]
        Clear client and session caches, optionally filtered by service or region.
        
        [Design principles]
        - Targeted cache clearing capabilities
        - Thread-safe operation
        
        [Implementation details]
        - Uses locking for thread safety
        - Supports filtering by service and/or region
        - Cleans up both client and session caches
        
        Args:
            service_name: Filter clearing to this service
            region_name: Filter clearing to this region
        """
        with self._cache_lock:
            # Handle client cache
            if service_name is None and region_name is None:
                # Clear all caches
                self._clients_cache.clear()
                self._session_cache.clear()
            else:
                # Selectively clear caches
                # For clients, we need to check both service and region
                client_keys_to_remove = []
                for key in self._clients_cache.keys():
                    parts = key.split('|')
                    cached_service = parts[0] if len(parts) > 0 else None
                    cached_region = parts[1] if len(parts) > 1 else None
                    
                    # Match based on filters
                    if (service_name is None or cached_service == service_name) and \
                       (region_name is None or cached_region == region_name):
                        client_keys_to_remove.append(key)
                
                # Remove matched clients
                for key in client_keys_to_remove:
                    del self._clients_cache[key]
                
                # For sessions, only region matters
                if region_name is not None:
                    session_keys_to_remove = []
                    for key in self._session_cache.keys():
                        parts = key.split('|')
                        cached_region = parts[0] if len(parts) > 0 else None
                        
                        if cached_region == region_name:
                            session_keys_to_remove.append(key)
                    
                    # Remove matched sessions
                    for key in session_keys_to_remove:
                        del self._session_cache[key]
        
        # Log cache clearing
        cache_type = ""
        if service_name and region_name:
            cache_type = f"for service '{service_name}' in region '{region_name}'"
        elif service_name:
            cache_type = f"for service '{service_name}'"
        elif region_name:
            cache_type = f"for region '{region_name}'"
        else:
            cache_type = "all caches"
        
        self.logger.info(f"Cleared AWS client cache: {cache_type}")
    
    def _generate_client_key(self,
                            service_name: str,
                            region_name: Optional[str],
                            profile_name: Optional[str],
                            credentials: Optional[Dict[str, Any]],
                            config: Optional[Config]) -> str:
        """
        [Method intent]
        Generate a unique key for client caching based on parameters.
        
        [Design principles]
        - Unique key generation
        - Deterministic results for same inputs
        
        [Implementation details]
        - Combines service, region, profile, and credentials
        - Handles None values appropriately
        - Creates hash for credential dictionaries
        
        Args:
            service_name: AWS service name
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit credentials dict
            config: Custom boto3 Config object
            
        Returns:
            str: Unique cache key
        """
        key_parts = [service_name]
        
        # Add region if specified
        key_parts.append(str(region_name) if region_name else "default")
        
        # Add profile or credentials hash
        if profile_name:
            key_parts.append(f"profile:{profile_name}")
        elif credentials:
            # Hash credentials to avoid storing sensitive information in memory
            cred_hash = hashlib.md5(
                json.dumps(credentials, sort_keys=True).encode()
            ).hexdigest()
            key_parts.append(f"cred:{cred_hash}")
        else:
            key_parts.append("default")
        
        # Add config hash if specified
        if config:
            config_str = str(config.__dict__)
            config_hash = hashlib.md5(config_str.encode()).hexdigest()
            key_parts.append(f"config:{config_hash}")
        
        # Join parts with pipe separator (unlikely to appear in any of the parts)
        return "|".join(key_parts)
    
    def _generate_session_key(self,
                             region_name: Optional[str],
                             profile_name: Optional[str],
                             credentials: Optional[Dict[str, Any]]) -> str:
        """
        [Method intent]
        Generate a unique key for session caching based on parameters.
        
        [Design principles]
        - Unique key generation
        - Deterministic results for same inputs
        
        [Implementation details]
        - Combines region and credentials information
        - Creates hash for credential dictionaries
        
        Args:
            region_name: AWS region name
            profile_name: AWS profile name for credentials
            credentials: Explicit credentials dict
            
        Returns:
            str: Unique cache key
        """
        key_parts = []
        
        # Add region if specified
        key_parts.append(str(region_name) if region_name else "default")
        
        # Add profile or credentials hash
        if profile_name:
            key_parts.append(f"profile:{profile_name}")
        elif credentials:
            # Hash credentials to avoid storing sensitive information in memory
            cred_hash = hashlib.md5(
                json.dumps(credentials, sort_keys=True).encode()
            ).hexdigest()
            key_parts.append(f"cred:{cred_hash}")
        else:
            key_parts.append("default")
        
        # Join parts with pipe separator
        return "|".join(key_parts)
