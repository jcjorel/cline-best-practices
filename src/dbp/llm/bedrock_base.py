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
# Defines the abstract base class for all Bedrock model clients within the LLM
# subsystem. This base class standardizes the interface for interacting with
# different Bedrock models while providing common functionality for client
# initialization, error handling, and lifecycle management.
###############################################################################
# [Source file design principles]
# - Provide a common interface for all Bedrock model clients
# - Encapsulate Bedrock client initialization logic
# - Implement robust error handling and logging
# - Support both streaming and non-streaming invocation patterns
# - Enable validation of model availability
# - Follow the abstract base class pattern for client implementation
###############################################################################
# [Source file constraints]
# - Must not contain model-specific parameters or logic
# - Must handle AWS credentials and region configuration properly
# - Must provide structured logging for all operations
# - Must be compatible with all Bedrock foundation models
# - Must not depend on model-specific response formats
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T12:56:00Z : Initial creation of Bedrock base class by Cline
# * Created abstract base class for Bedrock model clients
# * Implemented common initialization and shutdown functionality
# * Added structured logging and error handling
###############################################################################

import abc
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Iterator, Union

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

class BedrockClientError(Exception):
    """Base exception for all Bedrock client errors."""
    pass


class BedrockModelClientBase(abc.ABC):
    """
    Abstract base class defining the interface for all Bedrock model clients.
    
    This class provides common functionality for initializing and managing
    Bedrock client connections, while leaving model-specific invocation
    details to derived classes.
    """
    
    def __init__(
        self, 
        model_id: str,
        region: Optional[str] = None,
        max_retries: int = 3,
        connect_timeout: int = 10,
        read_timeout: int = 30,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initialize a new Bedrock model client.
        
        Args:
            model_id: The Bedrock model ID to use
            region: AWS region for the Bedrock service (if None, uses environment)
            max_retries: Maximum number of retry attempts for AWS API calls
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            logger_override: Optional logger instance
        """
        self.model_id = model_id
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.max_retries = max_retries
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.logger = logger_override or logger.getChild(self.__class__.__name__)
        
        # Will be initialized in initialize()
        self.bedrock_client = None
        self.initialized = False
        
        self.logger.debug({
            "message": "Created Bedrock model client",
            "model_id": self.model_id,
            "region": self.region,
        })

    def initialize(self) -> None:
        """
        Initialize the Bedrock client connection.
        
        This method sets up the boto3 client for Bedrock runtime with the
        configured parameters and validates that the model is available.
        
        Raises:
            BedrockClientError: If client initialization fails or model is unavailable
        """
        if self.initialized:
            self.logger.debug({
                "message": "Bedrock client already initialized",
                "model_id": self.model_id
            })
            return
            
        # Generate a unique initialization ID for correlation
        init_id = str(uuid.uuid4())
        
        self.logger.info({
            "message": "Starting Bedrock client initialization",
            "initialization_id": init_id,
            "service": "bedrock-runtime",
            "region": self.region,
            "model_id": self.model_id
        })

        try:
            # Configure retry strategy and timeout
            config = Config(
                retries = dict(
                    max_attempts = self.max_retries,
                    mode = 'standard'
                ),
                connect_timeout = self.connect_timeout,
                read_timeout = self.read_timeout
            )
            
            self.logger.debug({
                "message": "Client configuration parameters",
                "initialization_id": init_id,
                "config": {
                    "retry_attempts": config.retries['max_attempts'],
                    "retry_mode": config.retries['mode'],
                    "connect_timeout": config.connect_timeout,
                    "read_timeout": config.read_timeout
                }
            })

            # Initialize the Bedrock Runtime client
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region,
                config=config
            )

            self.logger.info({
                "message": "Bedrock client created successfully",
                "initialization_id": init_id,
                "model_id": self.model_id
            })

            # Validate the client by checking if the model is available
            self._validate_model_availability(init_id)
            
            self.initialized = True
            self.logger.info({
                "message": "Bedrock client initialization completed",
                "initialization_id": init_id,
                "status": "success"
            })
            
        except Exception as e:
            self.logger.error({
                "message": "Failed to initialize Bedrock client",
                "initialization_id": init_id,
                "model_id": self.model_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
                "service": "bedrock-runtime"
            })
            raise BedrockClientError(f"Failed to initialize Bedrock client for {self.model_id}: {str(e)}") from e

    def _validate_model_availability(self, init_id: str) -> None:
        """
        Validate that the specified model is available in the current region.
        
        Args:
            init_id: Correlation ID for logging
            
        Raises:
            BedrockClientError: If the model is unavailable
        """
        try:
            self.bedrock_client.get_model_invocation_logging_configuration(
                modelId=self.model_id
            )
            self.logger.info({
                "message": "Model validation successful",
                "initialization_id": init_id,
                "model_id": self.model_id,
                "status": "available"
            })

        except self.bedrock_client.exceptions.ValidationException as e:
            self.logger.error({
                "message": "Model validation failed",
                "initialization_id": init_id,
                "model_id": self.model_id,
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            raise BedrockClientError(f"Model {self.model_id} is not available in region {self.region}") from e

    def is_available(self) -> bool:
        """
        Check if the model is available without raising exceptions.
        
        Returns:
            bool: True if the model is available, False otherwise
        """
        if not self.initialized:
            try:
                self.initialize()
                return True
            except BedrockClientError:
                return False
        return True

    @abc.abstractmethod
    def invoke_model(self, prompt: Union[str, Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Invoke the model with a prompt and return the complete response.
        
        Args:
            prompt: The prompt to send to the model (string or formatted request)
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dict[str, Any]: The model's response
            
        Raises:
            BedrockClientError: On invocation failure
        """
        pass

    @abc.abstractmethod
    def invoke_model_stream(self, prompt: Union[str, Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """
        Invoke the model with a prompt and return a streaming response.
        
        Args:
            prompt: The prompt to send to the model (string or formatted request)
            **kwargs: Additional model-specific parameters
            
        Returns:
            Iterator[Dict[str, Any]]: Iterator over response chunks
            
        Raises:
            BedrockClientError: On invocation failure
        """
        pass

    def shutdown(self) -> None:
        """
        Clean up resources and prepare for shutdown.
        """
        self.logger.info({
            "message": "Shutting down Bedrock client",
            "model_id": self.model_id,
            "region": self.region
        })
        # Close any resources that need to be cleaned up
        # For boto3 clients, there's typically no explicit cleanup needed
        self.initialized = False
        self.bedrock_client = None
