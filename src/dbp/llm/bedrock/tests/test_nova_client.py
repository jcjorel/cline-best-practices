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
# Tests for the NovaEnhancedChatBedrockConverse class in models/nova.py.
# Validates the behavior of the Nova-specific text extraction logic.
###############################################################################
# [Source file design principles]
# - Clean test separation by functionality
# - Coverage for Nova-specific extraction methods
# - Test Nova-specific response formats
# - Verify correct inheritance patterns
###############################################################################
# [Source file constraints]
# - Must not depend on actual AWS services
# - Tests must be isolated and not affect each other
# - Must validate overridden _extract_text_from_chunk class method
# - Must verify behavior with Nova-specific response formats
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/models/nova.py
# codebase:src/dbp/llm/bedrock/tests/conftest.py
# system:pytest
# system:unittest.mock
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:29:38Z : Created initial tests for NovaEnhancedChatBedrockConverse by CodeAssistant
# * Added tests for the Nova-specific _extract_text_from_chunk method
# * Added tests for Nova-specific response formats
# * Added tests for inheritance behavior from EnhancedChatBedrockConverse
# * Added tests for JSON parsing in chunk bytes format
###############################################################################

"""
Tests for the Nova-specific LangChain implementation.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from ..models.nova import NovaEnhancedChatBedrockConverse
from ..langchain_wrapper import EnhancedChatBedrockConverse


class TestNovaEnhancedChatBedrockConverse:
    """Test suite for NovaEnhancedChatBedrockConverse."""

    def test_nova_extract_text_output_format(self, nova_output_chunk):
        """Test Nova-specific extraction with output format."""
        result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(nova_output_chunk)
        assert result == "Hello from Nova"

    def test_nova_extract_text_chunk_json_format(self, nova_json_chunk):
        """Test Nova-specific extraction with chunk JSON bytes format."""
        result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(nova_json_chunk)
        assert result == "Nova JSON chunk"

    def test_nova_extract_text_chunk_text_format(self, nova_text_chunk):
        """Test Nova-specific extraction with chunk plain text bytes format."""
        result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(nova_text_chunk)
        assert result == "Plain text chunk from Nova"

    def test_nova_extract_text_json_parsing_error(self):
        """Test Nova-specific extraction with invalid JSON in chunk bytes."""
        invalid_json_chunk = {"chunk": {"bytes": "{invalid_json"}}
        # Should not raise exception and return the raw bytes
        result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(invalid_json_chunk)
        assert result == "{invalid_json"

    def test_nova_extract_text_empty_content(self):
        """Test Nova-specific extraction with empty content."""
        assert NovaEnhancedChatBedrockConverse._extract_text_from_chunk(None) == ""
        assert NovaEnhancedChatBedrockConverse._extract_text_from_chunk("") == ""
        assert NovaEnhancedChatBedrockConverse._extract_text_from_chunk({}) == ""

    def test_nova_extract_text_fallback(self, claude_text_chunk):
        """Test Nova-specific extraction falls back to parent for non-Nova formats."""
        # Test with Claude format which Nova doesn't handle specifically
        # Should delegate to parent class implementation
        nova_class_result = NovaEnhancedChatBedrockConverse._extract_text_from_chunk(claude_text_chunk)
        parent_result = EnhancedChatBedrockConverse.extract_text_from_chunk(claude_text_chunk)
        assert nova_class_result == parent_result
        assert nova_class_result == "Hello from Claude 3.5"

    def test_supported_models_constant(self):
        """Test that SUPPORTED_MODELS contains the expected Nova models."""
        # Verify we have the expected Nova models defined
        supported_models = NovaEnhancedChatBedrockConverse.SUPPORTED_MODELS
        
        # Check that we have at least one model
        assert len(supported_models) > 0
        
        # Check that all models are Nova models
        for model in supported_models:
            assert "nova" in model.lower(), f"Model {model} is not a Nova model"

    def test_nova_instance_creation(self, mock_bedrock_runtime):
        """Test instance creation with Nova model ID."""
        # Verify we can create an instance with the first supported Nova model
        model_id = NovaEnhancedChatBedrockConverse._NOVA_MODELS[0]
        instance = NovaEnhancedChatBedrockConverse(
            model=model_id,
            client=mock_bedrock_runtime
        )
        
        # Verify the instance was created successfully
        assert isinstance(instance, NovaEnhancedChatBedrockConverse)
        assert isinstance(instance, EnhancedChatBedrockConverse)
