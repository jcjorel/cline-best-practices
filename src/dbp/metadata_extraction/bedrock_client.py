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
# Implements the BedrockClient class, responsible for interacting with the
# AWS Bedrock service to invoke Large Language Models (LLMs), specifically
# targeting Amazon Nova Lite for metadata extraction tasks. Handles API calls,
# request formatting, response parsing, and basic retry logic.
###############################################################################
# [Source file design principles]
# - Encapsulates all AWS Bedrock interaction logic.
# - Uses the `boto3` library for AWS SDK interactions.
# - Relies on the default AWS credential provider chain (environment variables,
#   config files, IAM roles) for authentication, avoiding hardcoded credentials.
# - Configurable model ID, retry attempts, and delay.
# - Handles potential exceptions during API calls and includes retry logic.
# - Formats requests and parses responses according to the Bedrock Runtime API specification.
# - Design Decision: Use Boto3 Default Credential Chain (2025-04-15)
#   * Rationale: Standard and secure way to handle AWS credentials without embedding them in the code, leveraging existing AWS configurations.
#   * Alternatives considered: Explicit credential configuration (less secure, more complex).
###############################################################################
# [Source file constraints]
# - Requires the `boto3` library (`pip install boto3`).
# - Requires valid AWS credentials configured in the environment where the application runs.
# - Assumes network connectivity to the AWS Bedrock service endpoint.
# - Performance depends on AWS Bedrock API latency and model inference time.
# - Specific model parameters (temperature, max_tokens) are passed during invocation.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/SECURITY.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:51:20Z : Initial creation of BedrockClient class by CodeAssistant
# * Implemented client initialization, model invocation with retry logic, and basic error handling.
###############################################################################

import json
import logging
import time
from typing import Any, Optional

# Try to import boto3
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    logging.getLogger(__name__).warning("The 'boto3' library is required for BedrockClient but was not found. Install it using 'pip install boto3'.")
    # Define dummy exceptions if boto3 is not present
    class ClientError(Exception): pass
    class NoCredentialsError(Exception): pass
    class PartialCredentialsError(Exception): pass


logger = logging.getLogger(__name__)

class BedrockClientInitializationError(Exception):
    """Custom exception for errors during Bedrock client initialization."""
    pass

class BedrockInvocationError(Exception):
    """Custom exception for errors during Bedrock model invocation."""
    pass

class BedrockClient:
    """
    A client for interacting with AWS Bedrock Runtime service, specifically
    configured for invoking models like Amazon Nova Lite.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the BedrockClient.

        Args:
            config: Configuration object providing Bedrock settings. Expected keys:
                    'metadata_extraction.model_id', 'metadata_extraction.max_retries',
                    'metadata_extraction.retry_delay', 'metadata_extraction.temperature',
                    'metadata_extraction.max_tokens', 'aws.region' (optional).
                    Can be None to use defaults.
            logger_override: Optional logger instance.

        Raises:
            ImportError: If boto3 is not installed.
            BedrockClientInitializationError: If the boto3 client cannot be initialized.
        """
        self.config = config or {} # Use empty dict if config is None
        self.logger = logger_override or logger

        if not HAS_BOTO3:
            raise ImportError("boto3 library is required for BedrockClient.")

        # --- Configuration Values ---
        # Provide defaults directly here if config object might be missing keys
        self.model_id = self.config.get('metadata_extraction.model_id', "amazon.titan-text-lite-v1") # Default model
        self.max_retries = int(self.config.get('metadata_extraction.max_retries', 3))
        self.retry_delay = float(self.config.get('metadata_extraction.retry_delay', 1.0))
        self.temperature = float(self.config.get('metadata_extraction.temperature', 0.0))
        self.max_tokens = int(self.config.get('metadata_extraction.max_tokens', 4096))
        self.aws_region = self.config.get('aws.region', None) # Optional region from config

        # --- Initialize Boto3 Client ---
        self.client = self._initialize_client()
        self.logger.debug(f"BedrockClient initialized for model '{self.model_id}' in region '{self.client.meta.region_name}'.")

    def _initialize_client(self):
        """Initializes the AWS Bedrock Runtime boto3 client."""
        try:
            self.logger.info(f"Initializing AWS Bedrock Runtime client (Region: {self.aws_region or 'default'})...")
            # Use default credential provider chain (env vars, ~/.aws/credentials, IAM role, etc.)
            # Specify region if provided in config, otherwise let boto3 determine default
            session = boto3.Session(region_name=self.aws_region)
            bedrock_runtime = session.client('bedrock-runtime')
            # Optionally test connection/credentials here if needed (e.g., list_foundation_models)
            # bedrock_runtime.list_foundation_models() # Example check
            self.logger.info("AWS Bedrock Runtime client initialized successfully.")
            return bedrock_runtime
        except (NoCredentialsError, PartialCredentialsError) as e:
            self.logger.error(f"AWS credentials not found or incomplete: {e}. Ensure credentials are configured (environment variables, ~/.aws/credentials, IAM role).")
            raise BedrockClientInitializationError("AWS credentials not configured.") from e
        except ClientError as e:
            # Handle specific boto3 client errors
            error_code = e.response.get('Error', {}).get('Code')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            self.logger.error(f"AWS Bedrock client error during initialization: {error_code} - {error_msg}")
            raise BedrockClientInitializationError(f"AWS error initializing Bedrock client: {error_code}") from e
        except Exception as e:
            # Catch other potential errors (e.g., invalid region)
            self.logger.error(f"Failed to initialize Bedrock client: {e}", exc_info=True)
            raise BedrockClientInitializationError(f"Unexpected error initializing Bedrock client: {e}") from e

    def invoke_model(self, prompt: str) -> str:
        """
        Invokes the configured Bedrock model with the provided prompt.

        Args:
            prompt: The input prompt string for the language model.

        Returns:
            The text response generated by the model.

        Raises:
            BedrockInvocationError: If the invocation fails after all retries.
        """
        retries = 0
        last_exception: Optional[Exception] = None
        request_body = json.dumps({
            "inputText": prompt, # Assuming Titan Lite format, adjust if using Nova/Claude
            "textGenerationConfig": {
                "maxTokenCount": self.max_tokens,
                "temperature": self.temperature,
                "stopSequences": [], # Add stop sequences if needed
                "topP": 1.0 # Default top_p
            }
        })
        # Note: Payload structure varies by model provider (Anthropic, AI21, Cohere, Amazon)
        # Example for Anthropic Claude:
        # request_body = json.dumps({
        #     "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
        #     "max_tokens_to_sample": self.max_tokens,
        #     "temperature": self.temperature,
        #     # ... other Claude parameters
        # })

        self.logger.debug(f"Invoking Bedrock model '{self.model_id}' (attempt {retries + 1}/{self.max_retries + 1})...")

        while retries <= self.max_retries:
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=request_body,
                    contentType='application/json',
                    accept='application/json' # Specify expected response type
                )

                # Parse the response body
                response_body_str = response['body'].read().decode('utf-8')
                response_data = json.loads(response_body_str)

                # Extract the generated text (structure depends on the model)
                # Example for Amazon Titan Lite:
                generated_text = response_data.get('results', [{}])[0].get('outputText')

                # Example for Anthropic Claude:
                # generated_text = response_data.get('completion')

                if generated_text is None:
                     self.logger.error(f"Could not find generated text in Bedrock response. Response data: {response_data}")
                     raise BedrockInvocationError("Malformed response from Bedrock model: Missing generated text.")

                self.logger.info(f"Bedrock model '{self.model_id}' invoked successfully.")
                return generated_text.strip() # Return the extracted text

            except ClientError as e:
                last_exception = e
                error_code = e.response.get('Error', {}).get('Code')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                self.logger.warning(f"Bedrock API call failed (attempt {retries + 1}): {error_code} - {error_msg}")
                # Check for throttling or retryable errors
                if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalServerException'] and retries < self.max_retries:
                    wait_time = self.retry_delay * (2 ** retries) # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    # Non-retryable error or max retries reached
                    self.logger.error(f"Non-retryable Bedrock error or max retries reached: {error_code}")
                    raise BedrockInvocationError(f"Bedrock API error: {error_code} - {error_msg}") from e
            except Exception as e:
                # Catch other unexpected errors (network issues, JSON parsing errors, etc.)
                last_exception = e
                self.logger.warning(f"Unexpected error during Bedrock invocation (attempt {retries + 1}): {e}", exc_info=True)
                if retries < self.max_retries:
                    wait_time = self.retry_delay * (2 ** retries)
                    self.logger.info(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    self.logger.error(f"Bedrock invocation failed after {self.max_retries} retries due to unexpected error.")
                    raise BedrockInvocationError(f"Unexpected error during Bedrock invocation: {e}") from e

        # Should not be reached if loop finishes correctly, but acts as a safeguard
        self.logger.error(f"Bedrock invocation failed definitively after {self.max_retries} retries.")
        raise BedrockInvocationError(f"Bedrock invocation failed after {self.max_retries} retries. Last error: {last_exception}") from last_exception
