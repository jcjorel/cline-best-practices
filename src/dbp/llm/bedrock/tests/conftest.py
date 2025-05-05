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
# Provides pytest fixtures and utilities for testing Bedrock LangChain integration.
# This file centralizes all common testing resources needed for testing various
# components of the LangChain-based AWS Bedrock integration.
###############################################################################
# [Source file design principles]
# - DRY test fixture definitions
# - Clear test data organization
# - Isolation from actual AWS services
# - Support both sync and async testing
# - No side effects during tests
###############################################################################
# [Source file constraints]
# - Must not contain actual AWS credentials
# - Must mock all external services
# - Must provide fixtures for all supported model types
# - Must support both sync and async test methods
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/bedrock/models/claude3.py
# codebase:src/dbp/llm/bedrock/models/nova.py
# codebase:src/dbp/llm/bedrock/client_factory.py
# system:pytest
# system:unittest.mock
# system:json
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:25:57Z : Created initial test fixtures by CodeAssistant
# * Added mock data fixtures for Claude and Nova responses
# * Added mock AWS client fixtures
# * Added fixtures for LangChain model instances
# * Added helper utilities for testing
###############################################################################

"""
Test fixtures and utilities for Bedrock LangChain integration testing.
"""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from ..langchain_wrapper import EnhancedChatBedrockConverse
from ..models.claude3 import ClaudeEnhancedChatBedrockConverse
from ..models.nova import NovaEnhancedChatBedrockConverse


# --- Mock Data Fixtures ---

@pytest.fixture
def claude_text_chunk():
    """
    [Method intent]
    Provide a mock Claude text chunk in delta format.
    
    [Design principles]
    - Realistic Claude response format
    - Simple test data for predictable results
    
    [Implementation details]
    - Uses Claude 3.5 delta streaming format
    """
    return {"delta": {"text": "Hello from Claude 3.5"}}


@pytest.fixture
def claude_completion_chunk():
    """
    [Method intent]
    Provide a mock Claude completion chunk.
    
    [Design principles]
    - Realistic Claude response format
    - Alternative format for testing extraction
    
    [Implementation details]
    - Uses Claude completion format
    """
    return {"completion": "Complete response from Claude"}


@pytest.fixture
def nova_output_chunk():
    """
    [Method intent]
    Provide a mock Nova output chunk.
    
    [Design principles]
    - Realistic Nova response format
    - Simple test data for predictable results
    
    [Implementation details]
    - Uses Nova output format with text field
    """
    return {"output": {"text": "Hello from Nova"}}


@pytest.fixture
def nova_json_chunk():
    """
    [Method intent]
    Provide a mock Nova chunk with JSON bytes.
    
    [Design principles]
    - Test JSON parsing in Nova responses
    - Realistic byte format
    
    [Implementation details]
    - Simulates Nova chunk format with JSON encoded bytes
    """
    json_bytes = json.dumps({"text": "Nova JSON chunk"})
    return {"chunk": {"bytes": json_bytes}}


@pytest.fixture
def nova_text_chunk():
    """
    [Method intent]
    Provide a mock Nova chunk with plain text bytes.
    
    [Design principles]
    - Test plain text bytes handling
    - Alternative format for testing extraction
    
    [Implementation details]
    - Simulates Nova chunk format with plain text bytes
    """
    return {"chunk": {"bytes": "Plain text chunk from Nova"}}


# --- Mock Client Fixtures ---

@pytest.fixture
def mock_boto3_client():
    """
    [Method intent]
    Create a mock boto3 client for testing.
    
    [Design principles]
    - Isolate tests from actual AWS services
    - Provide controlled response behavior
    
    [Implementation details]
    - Returns MagicMock with basic methods needed for testing
    """
    mock_client = MagicMock()
    
    # Mock methods for both sync and async operations
    mock_client.converse.return_value = {"output": {"text": "Mock response"}}
    mock_client.converse_stream.return_value = [
        {"chunk": {"bytes": "Chunk 1"}},
        {"chunk": {"bytes": "Chunk 2"}},
    ]
    
    # For async methods
    async_mock = MagicMock()
    async_mock.__aiter__.return_value = [
        {"delta": {"text": "Async chunk 1"}},
        {"delta": {"text": "Async chunk 2"}},
    ]
    mock_client.converse_stream_async = MagicMock(return_value=async_mock)
    
    return mock_client


@pytest.fixture
def mock_bedrock_runtime():
    """
    [Method intent]
    Patch boto3 bedrock-runtime client creation.
    
    [Design principles]
    - Prevent actual AWS service connections during tests
    - Allow controlled testing of AWS client behavior
    
    [Implementation details]
    - Context manager that patches boto3.client
    """
    with patch('boto3.client') as mock_boto3:
        mock_client = mock_boto3_client()
        mock_boto3.return_value = mock_client
        yield mock_client


# --- Model Instance Fixtures ---

@pytest.fixture
def enhanced_chatbedrock_instance(mock_bedrock_runtime):
    """
    [Method intent]
    Create a test instance of EnhancedChatBedrockConverse.
    
    [Design principles]
    - Base instance for generic tests
    - Pre-configured with mock client
    - Ready to use in test cases
    
    [Implementation details]
    - Uses the mocked bedrock runtime client
    - Configured with common test parameters
    """
    return EnhancedChatBedrockConverse(
        model="test-model",
        client=mock_bedrock_runtime,
        logger=logging.getLogger("test_logger")
    )


@pytest.fixture
def claude_chatbedrock_instance(mock_bedrock_runtime):
    """
    [Method intent]
    Create a test instance of ClaudeEnhancedChatBedrockConverse.
    
    [Design principles]
    - Claude-specific instance for targeted tests
    - Pre-configured with mock client
    - Ready to use in test cases
    
    [Implementation details]
    - Uses the mocked bedrock runtime client
    - Configured with Claude-specific model ID
    """
    return ClaudeEnhancedChatBedrockConverse(
        model=ClaudeEnhancedChatBedrockConverse._CLAUDE_MODELS[0],
        client=mock_bedrock_runtime,
        logger=logging.getLogger("test_logger")
    )


@pytest.fixture
def nova_chatbedrock_instance(mock_bedrock_runtime):
    """
    [Method intent]
    Create a test instance of NovaEnhancedChatBedrockConverse.
    
    [Design principles]
    - Nova-specific instance for targeted tests
    - Pre-configured with mock client
    - Ready to use in test cases
    
    [Implementation details]
    - Uses the mocked bedrock runtime client
    - Configured with Nova-specific model ID
    """
    return NovaEnhancedChatBedrockConverse(
        model=NovaEnhancedChatBedrockConverse._NOVA_MODELS[0],
        client=mock_bedrock_runtime,
        logger=logging.getLogger("test_logger")
    )
