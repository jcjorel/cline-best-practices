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
# Tests for the EnhancedChatBedrockConverse class in langchain_wrapper.py.
# Validates the behavior of the generic text extraction and the new
# abstract method pattern for model-specific extraction.
###############################################################################
# [Source file design principles]
# - Clean test separation by functionality
# - Coverage for all extraction methods
# - Test for backward compatibility
# - Verify correct inheritance patterns
# - Test both sync and async methods
###############################################################################
# [Source file constraints]
# - Must not depend on actual AWS services
# - Tests must be isolated and not affect each other
# - Must validate both the static extract_text_from_chunk and
#   the new _extract_text_from_chunk class method
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/bedrock/tests/conftest.py
# system:pytest
# system:unittest.mock
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-05T22:27:03Z : Created initial tests for EnhancedChatBedrockConverse by CodeAssistant
# * Added tests for the static extract_text_from_chunk method
# * Added tests for the new _extract_text_from_chunk class method
# * Added tests for backward compatibility
# * Verified inheritance between static and class methods
###############################################################################

"""
Tests for the EnhancedChatBedrockConverse class.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from ..langchain_wrapper import EnhancedChatBedrockConverse


class TestEnhancedChatBedrockConverse:
    """Test suite for EnhancedChatBedrockConverse."""

    def test_static_extract_text_with_delta(self, claude_text_chunk):
        """Test static extract_text_from_chunk with delta format."""
        # This tests the backward compatibility of the static method
        result = EnhancedChatBedrockConverse.extract_text_from_chunk(claude_text_chunk)
        assert result == "Hello from Claude 3.5"

    def test_static_extract_text_with_completion(self, claude_completion_chunk):
        """Test static extract_text_from_chunk with completion format."""
        # This tests the backward compatibility of the static method
        result = EnhancedChatBedrockConverse.extract_text_from_chunk(claude_completion_chunk)
        assert result == "Complete response from Claude"

    def test_static_extract_text_with_output(self, nova_output_chunk):
        """Test static extract_text_from_chunk with output format."""
        # This tests the backward compatibility of the static method
        result = EnhancedChatBedrockConverse.extract_text_from_chunk(nova_output_chunk)
        assert result == "Hello from Nova"

    def test_static_extract_text_with_empty_content(self):
        """Test static extract_text_from_chunk with empty content."""
        # Check empty inputs
        assert EnhancedChatBedrockConverse.extract_text_from_chunk(None) == ""
        assert EnhancedChatBedrockConverse.extract_text_from_chunk("") == ""
        assert EnhancedChatBedrockConverse.extract_text_from_chunk({}) == ""
        assert EnhancedChatBedrockConverse.extract_text_from_chunk([]) == ""

    def test_static_extract_text_with_nested_content(self):
        """Test static extract_text_from_chunk with nested content."""
        nested = {
            "message": {
                "content": "Nested content"
            }
        }
        result = EnhancedChatBedrockConverse.extract_text_from_chunk(nested)
        assert result == "Nested content"

    def test_class_extract_text_delegation(self, enhanced_chatbedrock_instance, claude_text_chunk):
        """Test _extract_text_from_chunk class method delegates to static method."""
        # This verifies that the class method correctly delegates to the static method
        # The default implementation should just call the static method
        cls_result = enhanced_chatbedrock_instance._extract_text_from_chunk(claude_text_chunk)
        static_result = EnhancedChatBedrockConverse.extract_text_from_chunk(claude_text_chunk)
        assert cls_result == static_result
        assert cls_result == "Hello from Claude 3.5"

    def test_stream_text_uses_extract_method(self, enhanced_chatbedrock_instance):
        """Test stream_text uses _extract_text_from_chunk."""
        # Mock the stream method to return a predictable result
        mock_chunk = MagicMock()
        mock_chunk.content = {"delta": {"text": "Test content"}}
        
        # Patch the stream method
        with patch.object(enhanced_chatbedrock_instance, 'stream', return_value=[mock_chunk]):
            # Patch the _extract_text_from_chunk method to verify it's called
            with patch.object(enhanced_chatbedrock_instance, '_extract_text_from_chunk') as mock_extract:
                mock_extract.return_value = "Extracted content"
                
                # Call stream_text and collect results
                results = list(enhanced_chatbedrock_instance.stream_text([]))
                
                # Verify _extract_text_from_chunk was called with the right arguments
                mock_extract.assert_called_once_with({"delta": {"text": "Test content"}})
                
                # Verify the results
                assert results == ["Extracted content"]

    @pytest.mark.asyncio
    async def test_astream_uses_extract_method(self, enhanced_chatbedrock_instance):
        """Test astream uses _extract_text_from_chunk."""
        # This test requires pytest-asyncio
        
        # Mock AIMessageChunk
        mock_chunk = MagicMock()
        mock_chunk.content = "Test content"
        
        # Create a mock async generator for astream
        async def mock_astream(*args, **kwargs):
            yield mock_chunk
        
        # Patch the _astream method
        with patch.object(enhanced_chatbedrock_instance, '_astream', mock_astream):
            # Patch the _extract_text_from_chunk method
            with patch.object(enhanced_chatbedrock_instance, '_extract_text_from_chunk') as mock_extract:
                mock_extract.return_value = "Extracted content"
                
                # Call astream and collect results
                results = []
                async for chunk in enhanced_chatbedrock_instance.astream([]):
                    results.append(chunk.content)
                
                # Verify _extract_text_from_chunk was called
                mock_extract.assert_called_once()
                
                # Verify results
                assert results == ["Extracted content"]

    @pytest.mark.asyncio
    async def test_astream_text_uses_extract_method(self, enhanced_chatbedrock_instance):
        """Test astream_text uses _extract_text_from_chunk."""
        # Mock chunk with content
        mock_chunk = MagicMock()
        mock_chunk.content = {"delta": {"text": "Test content"}}
        
        # Create a mock async generator for astream
        async def mock_astream(*args, **kwargs):
            yield mock_chunk
        
        # Patch the astream method
        with patch.object(enhanced_chatbedrock_instance, 'astream', mock_astream):
            # Patch the _extract_text_from_chunk method
            with patch.object(enhanced_chatbedrock_instance, '_extract_text_from_chunk') as mock_extract:
                mock_extract.return_value = "Extracted content"
                
                # Call astream_text and collect results
                results = []
                async for text in enhanced_chatbedrock_instance.astream_text([]):
                    results.append(text)
                
                # Verify _extract_text_from_chunk was called with the right arguments
                mock_extract.assert_called_once_with({"delta": {"text": "Test content"}})
                
                # Verify the results
                assert results == ["Extracted content"]
