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
# Defines AWS-specific exceptions for handling errors that occur when interacting
# with AWS services. Provides a structured approach to error handling with specific
# exception types for different categories of AWS-related errors.
###############################################################################
# [Source file design principles]
# - Clear exception hierarchy for AWS-related errors
# - Specific exception types for common error scenarios
# - Consistent error message formatting
# - Actionable error information for faster debugging
# - Interoperability with boto3 and botocore exceptions
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with boto3's exception model
# - Must not leak sensitive AWS credentials in error messages
# - Must provide clear context for errors to aid troubleshooting
###############################################################################
# [Dependencies]
# system:boto3
# system:botocore.exceptions
###############################################################################
# [GenAI tool change history]
# 2025-05-03T11:30:20Z : Initial implementation by CodeAssistant
# * Created base AWSClientError exception
# * Added specialized exception types for credentials, region, and service errors
# * Implemented consistent error message formatting and attributes
###############################################################################

from typing import Optional, Dict, Any


class AWSClientError(Exception):
    """
    [Class intent]
    Base exception for AWS client-related errors. Provides a foundation for all
    AWS service interaction exceptions with consistent error information.
    
    [Design principles]
    - Clear error hierarchy
    - Consistent error attribute pattern
    - Contextual information about service/region
    
    [Implementation details]
    - Base class for AWS client errors
    - Contains error code, message, and service information
    - Formats error messages consistently for all derived exceptions
    """
    
    def __init__(
        self, 
        message: str,
        service_name: Optional[str] = None,
        region_name: Optional[str] = None,
        error_code: Optional[str] = None,
        operation_name: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        [Method intent]
        Initialize the AWS client error with relevant context information.
        
        [Design principles]
        - Comprehensive error context
        - Consistent error pattern across exception types
        
        [Implementation details]
        - Captures service and region information
        - Stores error code for categorization
        - Retains original exception for debugging
        
        Args:
            message: The error message
            service_name: The AWS service name where the error occurred
            region_name: The AWS region where the error occurred
            error_code: The specific AWS error code (e.g., "ResourceNotFoundException")
            operation_name: The operation being performed when the error occurred
            original_error: The original exception that was raised
        """
        self.service_name = service_name
        self.region_name = region_name
        self.error_code = error_code
        self.operation_name = operation_name
        self.original_error = original_error
        
        # Build detailed error message
        detailed_message = message
        if service_name and region_name:
            detailed_message += f" (Service: {service_name}, Region: {region_name}"
            if error_code:
                detailed_message += f", Code: {error_code}"
            if operation_name:
                detailed_message += f", Operation: {operation_name}"
            detailed_message += ")"
        
        super().__init__(detailed_message)


class AWSCredentialError(AWSClientError):
    """
    [Class intent]
    Exception for AWS credential-related errors such as missing or invalid credentials.
    
    [Design principles]
    - Specific error type for credential issues
    - Actionable error messages
    - No exposure of sensitive data
    
    [Implementation details]
    - Used for profile not found or invalid credentials
    - Contains guidance on fixing credential issues
    - Sanitizes any potentially sensitive information
    """
    pass


class AWSRegionError(AWSClientError):
    """
    [Class intent]
    Exception for AWS region-related errors such as invalid regions or region
    unavailability for specific services.
    
    [Design principles]
    - Specific error type for region issues
    - Contains region information
    - Distinguishes between different region-related errors
    
    [Implementation details]
    - Used for invalid regions or service not available in region
    - Contains specific region in error message
    - Provides context on which regions might be valid
    """
    pass


class AWSServiceError(AWSClientError):
    """
    [Class intent]
    Exception for AWS service-specific errors such as API throttling, service
    unavailability, or invalid parameters.
    
    [Design principles]
    - Service-specific error handling
    - Detailed operation context
    - Guidance for resolution
    
    [Implementation details]
    - Captures service name, operation, and error code
    - Includes retry information when appropriate
    - Formats error message with all relevant details
    """
    pass


class AWSResourceNotFoundError(AWSServiceError):
    """
    [Class intent]
    Exception for AWS resource not found errors, which occur when a requested 
    resource does not exist or is not accessible.
    
    [Design principles]
    - Clear indication of missing resource
    - Resource type and identifier information
    
    [Implementation details]
    - Used for "ResourceNotFoundException" and similar errors
    - Contains resource type and identifier when available
    - Helps distinguish between permission issues and missing resources
    """
    pass


class AWSThrottlingError(AWSServiceError):
    """
    [Class intent]
    Exception for AWS throttling-related errors, which occur when request
    rate limits are exceeded.
    
    [Design principles]
    - Specific handling for rate limiting
    - Provides retry guidance
    
    [Implementation details]
    - Used for "ThrottlingException" and similar errors
    - Includes retry guidance in error message
    - Can be caught specifically for implementing backoff strategies
    """
    pass
