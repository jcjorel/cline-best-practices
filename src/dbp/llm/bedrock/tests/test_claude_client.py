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
# Tests for the ClaudeEnhancedChatBedrockConverse class in models/claude3.py.
# Validates the behavior of the Claude-specific text extraction logic.
###############################################################################
# [Source file design principles]
# - Clean test separation by functionality
# - Coverage for Claude-specific extraction methods
# - Test Claude-specific response formats
# - Verify correct inheritance patterns
###############################################################################
# [Source file constraints]
# - Must not depend on actual AWS services
# - Tests must be isolated and not affect each other
# - Must validate overridden _extract_text_from_chunk class method
# - Must verify behavior with Claude-specific response formats
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/models/claude3.py
# codebase:src/dbp/llm/bedrock/tests/conftest.py
# system:pytest
# system:unittest.mock
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:28:41Z : Created initial tests for ClaudeEnhancedChatBedrockConverse by CodeAssistant
# * Added tests for the Claude-specific _extract_text_from_chunk method
# * Added tests for Claude-specific response formats
# * Added tests for inheritance behavior from EnhancedChatBedrockConverse
# * Added tests for edge cases in Claude responses
###############################################################################

"""
Tests for the Claude-specific LangChain implementation.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from ..models.claude3 import ClaudeEnhancedChatBedrockConverse
from ..langchain_wrapper import EnhancedChatBedrockConverse


class TestClaudeEnhancedChatBedrockConverse:
    """Test suite for ClaudeEnhancedChatBedrockConverse."""

    def test_claude_extract_text_delta_format(self, claude_text_chunk):
        """Test Claude-specific extraction with delta format."""
        result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(claude_text_chunk)
        assert result == "Hello from Claude 3.5"

    def test_claude_extract_text_completion_format(self, claude_completion_chunk):
        """Test Claude-specific extraction with completion format."""
        result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(claude_completion_chunk)
        assert result == "Complete response from Claude"

    def test_claude_extract_text_delta_content_format(self):
        """Test Claude-specific extraction with delta.content format."""
        chunk = {"delta": {"content": "Content from delta"}}
        result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(chunk)
        assert result == "Content from delta"

    def test_claude_extract_text_empty_content(self):
        """Test Claude-specific extraction with empty content."""
        assert ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(None) == ""
        assert ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk("") == ""
        assert ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk({}) == ""

    def test_claude_extract_text_fallback(self, nova_output_chunk):
        """Test Claude-specific extraction falls back to parent for non-Claude formats."""
        # Test with Nova format which Claude doesn't handle specifically
        # Should delegate to parent class implementation
        claude_class_result = ClaudeEnhancedChatBedrockConverse._extract_text_from_chunk(nova_output_chunk)
        parent_result = EnhancedChatBedrockConverse.extract_text_from_chunk(nova_output_chunk)
        assert claude_class_result == parent_result
        assert claude_class_result == "Hello from Nova"

    def test_supported_models_constant(self):
        """Test that SUPPORTED_MODELS contains the expected Claude models."""
        # Verify we have the expected Claude models defined
        supported_models = ClaudeEnhancedChatBedrockConverse.SUPPORTED_MODELS
        
        # Check that we have at least one model
        assert len(supported_models) > 0
        
        # Check that all models are Claude models
        for model in supported_models:
            assert "claude" in model.lower(), f"Model {model} is not a Claude model"

    def test_claude_instance_creation(self, mock_bedrock_runtime):
        """Test instance creation with Claude model ID."""
        # Verify we can create an instance with the first supported Claude model
        model_id = ClaudeEnhancedChatBedrockConverse._CLAUDE_MODELS[0]
        instance = ClaudeEnhancedChatBedrockConverse(
            model=model_id,
            client=mock_bedrock_runtime
        )
        
        # Verify the instance was created successfully
        assert isinstance(instance, ClaudeEnhancedChatBedrockConverse)
        assert isinstance(instance, EnhancedChatBedrockConverse)
