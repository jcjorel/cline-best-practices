# AWS Client Factory Implementation Plan

## Overview
The `AWSClientFactory` will be a singleton service that centralizes AWS client creation and management across the entire project. It will provide efficient, thread-safe access to AWS services while optimizing for performance through client reuse.

## File Location
`src/dbp/api_providers/aws/client_factory.py`

## Class Structure

```python
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
    
    # Class variables
    _instance = None
    _lock = threading.Lock()
    
    # Default configurations for different service types
    DEFAULT_CONFIGS = {
        # Standard services like S3, DynamoDB
        "standard": botocore.config.Config(
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30
        ),
        # AI services like Bedrock, need longer timeouts
        "ai": botocore.config.Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=120
        ),
        # Data services that might involve larger payloads
        "data": botocore.config.Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60
        )
    }
    
    # Service type categorization
    SERVICE_TYPES = {
        "bedrock": "ai",
        "s3": "standard",
        "dynamodb": "standard",
        "sagemaker": "ai",
        "athena": "data",
        # Add more service mappings as needed
    }
```

## Singleton Pattern Implementation

```python
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
        Initialize the AWS client factory.
        
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
```

## Core Functionality

```python
    def get_client(self, 
                  service_name: str, 
                  region_name: Optional[str] = None, 
                  profile_name: Optional[str] = None, 
                  credentials: Optional[Dict[str, Any]] = None,
                  config: Optional[botocore.config.Config] = None,
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
        """
        # Implementation details...
        
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
        """
        # Implementation details...
        
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
        # Implementation details...
```

## Helper Methods

```python
    def _generate_client_key(self,
                            service_name: str,
                            region_name: Optional[str],
                            profile_name: Optional[str],
                            credentials: Optional[Dict[str, Any]],
                            config: Optional[botocore.config.Config]) -> str:
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
        
        Returns:
            str: Unique cache key
        """
        # Implementation details...
    
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
        
        Returns:
            str: Unique cache key
        """
        # Implementation details...
```

## Exception Handling

Related exception classes will be implemented in `src/dbp/api_providers/aws/exceptions.py`:

```python
class AWSClientError(Exception):
    """
    [Class intent]
    Base exception for AWS client-related errors.
    
    [Design principles]
    - Clear error hierarchy
    - Consistent error pattern
    
    [Implementation details]
    - Base class for AWS client errors
    - Contains error code and message
    """
    pass

class AWSCredentialError(AWSClientError):
    """
    [Class intent]
    Exception for AWS credential-related errors.
    
    [Design principles]
    - Specific error type for credential issues
    - Actionable error messages
    
    [Implementation details]
    - Used for profile not found or invalid credentials
    - Contains guidance on fixing credential issues
    """
    pass

class AWSRegionError(AWSClientError):
    """
    [Class intent]
    Exception for AWS region-related errors.
    
    [Design principles]
    - Specific error type for region issues
    - Contains region information
    
    [Implementation details]
    - Used for invalid regions or service not available in region
    - Contains specific region in error message
    """
    pass
```

## Usage Examples

```python
# Get singleton instance
client_factory = AWSClientFactory.get_instance()

# Get S3 client for us-east-1
s3_client = client_factory.get_client("s3", region_name="us-east-1")

# Get Bedrock client with custom configuration
bedrock_config = botocore.config.Config(
    retries={"max_attempts": 5},
    connect_timeout=15,
    read_timeout=300
)
bedrock_client = client_factory.get_client(
    "bedrock", 
    region_name="us-west-2",
    config=bedrock_config
)

# Get client with specific credentials
credentials = {
    "aws_access_key_id": "ACCESS_KEY",
    "aws_secret_access_key": "SECRET_KEY"
}
dynamodb_client = client_factory.get_client(
    "dynamodb", 
    region_name="eu-central-1",
    credentials=credentials
)

# Clear cache for a specific service
client_factory.clear_cache(service_name="bedrock")
```

## Testing Strategy

1. **Unit Tests:**
   - Test singleton behavior
   - Test client/session caching with different parameters
   - Test cache clearing functionality
   - Test thread safety with concurrent access

2. **Integration Tests:**
   - Test with actual AWS services using local mock or restricted credentials
   - Verify correct configuration is applied for different services
   - Test credential handling with different authentication methods

## Implementation Steps

1. Create the directory structure
2. Implement the `exceptions.py` file with AWS-specific exceptions
3. Implement the `client_factory.py` file with the singleton pattern
4. Add core methods for client and session creation/caching
5. Add helper methods for key generation and cache management
6. Add clear_cache functionality for maintenance
7. Add unit tests for all functionality
