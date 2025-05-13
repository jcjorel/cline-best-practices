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
# This file contains unit tests for the File Analyzer Agent component of the HSTC
# implementation. It tests the agent's ability to analyze source files, extract
# documentation elements, and identify code structures.
###############################################################################
# [Source file design principles]
# - Test each core functionality in isolation
# - Verify correct handling of different languages and file formats
# - Check both success paths and error handling
###############################################################################
# [Source file constraints]
# - Must use pytest fixtures from conftest.py
# - Should not depend on actual LLM API calls
###############################################################################
# [Dependencies]
# system:pytest
# system:unittest.mock
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
# codebase:src/dbp_cli/commands/hstc_agno/tests/conftest.py
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
###############################################################################
# [GenAI tool change history]
# 2025-05-13T11:32:00Z : Added mock for BedrockModelDiscovery by CodeAssistant
# * Added mock_model_discovery fixture
# * Updated tests to use the mock fixture for region selection
# 2025-05-13T10:54:00Z : Added mock for AWS client factory by CodeAssistant
# * Added mock_aws_client_factory fixture
# * Updated tests to use the mock fixture
# 2025-05-12T08:13:00Z : Initial implementation by CodeAssistant
# * Created unit tests for File Analyzer Agent
###############################################################################

import pytest
import os
from unittest.mock import MagicMock, patch
from ..agents import FileAnalyzerAgent
from dbp.api_providers.aws.client_factory import AWSClientFactory
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery


@pytest.fixture
def mock_model_discovery():
    """
    [Function intent]
    Create a mock BedrockModelDiscovery for testing.
    
    [Design principles]
    Isolates tests from actual AWS model discovery.
    Ensures tests can run without AWS connectivity.
    
    [Implementation details]
    Creates a mock BedrockModelDiscovery instance with a mock get_best_regions_for_model method.
    Patches the get_instance method to return the mock instance.
    
    Returns:
        Mock BedrockModelDiscovery
    """
    # Create mock discovery instance
    mock_discovery = MagicMock()
    
    # Configure get_best_regions_for_model to return a test region
    mock_discovery.get_best_regions_for_model.return_value = ["us-east-1"]
    
    # Patch the get_instance method
    with patch.object(BedrockModelDiscovery, 'get_instance', return_value=mock_discovery):
        yield mock_discovery



def test_file_analyzer_initialization(mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test that the File Analyzer Agent initializes correctly.
    
    [Design principles]
    Verifies basic object creation and properties are correctly set.
    
    [Implementation details]
    Creates a FileAnalyzerAgent instance and checks that it has expected attributes.
    
    Args:
        mock_aws_client_factory: Mock AWS client factory for testing
    """
    analyzer = FileAnalyzerAgent()
    assert hasattr(analyzer, "file_metadata")
    assert analyzer.file_metadata == {}


def test_analyze_file_type(sample_python_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test the file type analysis functionality.
    
    [Design principles]
    Verifies correct identification of source code vs binary files.
    
    [Implementation details]
    Opens a sample Python file and passes its content to the analyzer's
    analyze_file_type method, then verifies the results.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
    """
    analyzer = FileAnalyzerAgent()
    
    with open(sample_python_file, "r") as f:
        content = f.read()
    
    result = analyzer.analyze_file_type(content)
    
    assert "file_type" in result
    assert result["file_type"] == "source_code"
    assert "is_binary" in result
    assert result["is_binary"] is False


def test_detect_language(sample_python_file, sample_javascript_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test language detection for different file types.
    
    [Design principles]
    Verifies accurate language identification based on file content and extension.
    
    [Implementation details]
    Tests two different language files to ensure correct detection with high confidence.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
        sample_javascript_file: Pytest fixture providing a sample JavaScript file
    """
    analyzer = FileAnalyzerAgent()
    
    # Test Python detection
    with open(sample_python_file, "r") as f:
        content = f.read()
    
    py_result = analyzer.detect_language(content, sample_python_file)
    
    assert "language" in py_result
    assert py_result["language"] == "python"
    assert "confidence" in py_result
    assert py_result["confidence"] >= 90
    
    # Test JavaScript detection
    with open(sample_javascript_file, "r") as f:
        content = f.read()
    
    js_result = analyzer.detect_language(content, sample_javascript_file)
    
    assert "language" in js_result
    assert js_result["language"] == "javascript"
    assert "confidence" in js_result
    assert js_result["confidence"] >= 90


def test_identify_comment_formats(mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test identification of comment formats for different languages.
    
    [Design principles]
    Verifies correct identification of language-specific comment formats.
    
    [Implementation details]
    Tests comment format identification for Python and JavaScript.
    """
    analyzer = FileAnalyzerAgent()
    
    # Test Python comment formats
    py_result = analyzer.identify_comment_formats("python")
    
    assert "inline_comment" in py_result
    assert py_result["inline_comment"] == "#"
    assert "docstring_format" in py_result
    assert py_result["docstring_format"] is not None
    
    # Test JavaScript comment formats
    js_result = analyzer.identify_comment_formats("javascript")
    
    assert "inline_comment" in js_result
    assert js_result["inline_comment"] == "//"
    assert "block_comment_start" in js_result
    assert js_result["block_comment_start"] == "/*"
    assert "block_comment_end" in js_result
    assert js_result["block_comment_end"] == "*/"


def test_extract_header_comment(sample_python_file, sample_javascript_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test extraction of header comments from different file types.
    
    [Design principles]
    Verifies ability to extract the top-level documentation from files.
    
    [Implementation details]
    Tests header extraction for both Python and JavaScript files.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
        sample_javascript_file: Pytest fixture providing a sample JavaScript file
    """
    analyzer = FileAnalyzerAgent()
    
    # Test Python header extraction
    with open(sample_python_file, "r") as f:
        py_content = f.read()
    
    py_comment_formats = analyzer.identify_comment_formats("python")
    py_result = analyzer.extract_header_comment(py_content, py_comment_formats)
    
    assert py_result is not None
    assert "Sample Python file" in py_result
    
    # Test JavaScript header extraction
    with open(sample_javascript_file, "r") as f:
        js_content = f.read()
    
    js_comment_formats = analyzer.identify_comment_formats("javascript")
    js_result = analyzer.extract_header_comment(js_content, js_comment_formats)
    
    assert js_result is not None
    assert "Sample JavaScript file" in js_result


def test_extract_dependencies(sample_python_file, sample_javascript_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test extraction of dependencies from source files.
    
    [Design principles]
    Verifies accurate identification of imported modules and packages.
    
    [Implementation details]
    Tests dependency extraction for both Python and JavaScript files.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
        sample_javascript_file: Pytest fixture providing a sample JavaScript file
    """
    analyzer = FileAnalyzerAgent()
    
    # Test Python dependencies
    with open(sample_python_file, "r") as f:
        py_content = f.read()
    
    py_result = analyzer.extract_dependencies(py_content, "python")
    
    assert "dependencies" in py_result
    assert len(py_result["dependencies"]) >= 2
    assert any(dep["name"] == "os" for dep in py_result["dependencies"])
    assert any(dep["name"] == "sys" for dep in py_result["dependencies"])
    
    # Test JavaScript dependencies (module exports)
    with open(sample_javascript_file, "r") as f:
        js_content = f.read()
    
    js_result = analyzer.extract_dependencies(js_content, "javascript")
    
    assert "dependencies" in js_result


def test_extract_function_comments(sample_python_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test extraction of function and class documentation.
    
    [Design principles]
    Verifies ability to extract structured documentation from code definitions.
    
    [Implementation details]
    Tests extraction of documentation for functions and classes in Python.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
    """
    analyzer = FileAnalyzerAgent()
    
    with open(sample_python_file, "r") as f:
        content = f.read()
    
    comment_formats = analyzer.identify_comment_formats("python")
    result = analyzer.extract_function_comments(content, "python", comment_formats)
    
    assert "definitions" in result
    assert len(result["definitions"]) >= 2  # sample_function and SampleClass
    assert any(d["name"] == "sample_function" for d in result["definitions"])
    assert any(d["name"] == "SampleClass" for d in result["definitions"])
    
    # Verify function documentation contains required sections
    function_def = next(d for d in result["definitions"] if d["name"] == "sample_function")
    assert "[Function intent]" in function_def["comments"]
    assert "[Design principles]" in function_def["comments"]
    assert "[Implementation details]" in function_def["comments"]


def test_analyze_file(sample_python_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test the complete file analysis process end-to-end.
    
    [Design principles]
    Verifies integration of all analysis components.
    
    [Implementation details]
    Runs the full analyze_file method and checks all expected result components.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
    """
    analyzer = FileAnalyzerAgent()
    
    result = analyzer.analyze_file(sample_python_file)
    
    # Check basic metadata
    assert result["path"] == sample_python_file
    assert result["file_type"] == "source_code"
    assert result["language"] == "python"
    
    # Check definitions
    assert "definitions" in result
    assert len(result["definitions"]) >= 2
    
    # Check dependencies
    assert "dependencies" in result
    assert len(result["dependencies"]) >= 2
    
    # Check header
    assert "header_comment" in result
    assert "Sample Python file" in result["header_comment"]


def test_missing_docs(missing_docs_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test analysis of files with missing documentation.
    
    [Design principles]
    Verifies robust handling of improperly documented files.
    
    [Implementation details]
    Analyzes a file with missing documentation and checks that the analyzer
    correctly identifies the structure but reports missing documentation.
    
    Args:
        missing_docs_file: Pytest fixture providing a file with missing documentation
    """
    analyzer = FileAnalyzerAgent()
    
    result = analyzer.analyze_file(missing_docs_file)
    
    # Check basic metadata
    assert result["path"] == missing_docs_file
    assert result["file_type"] == "source_code"
    assert result["language"] == "python"
    
    # Check definitions are found despite missing docs
    assert "definitions" in result
    assert len(result["definitions"]) >= 2
    
    # Check that function is found but has no or minimal documentation
    function_def = next(d for d in result["definitions"] if d["name"] == "undocumented_function")
    assert function_def is not None
    # Either comments are missing or don't contain required sections
    if "comments" in function_def:
        assert "[Function intent]" not in function_def["comments"]


def test_get_file_metadata(sample_python_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test the retrieval of cached file metadata.
    
    [Design principles]
    Verifies caching functionality to avoid redundant analysis.
    
    [Implementation details]
    Analyzes a file, then retrieves its metadata from cache and verifies
    the data is correct.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
    """
    analyzer = FileAnalyzerAgent()
    
    # First, analyze the file
    analyzer.analyze_file(sample_python_file)
    
    # Then, retrieve metadata
    result = analyzer.get_file_metadata(sample_python_file)
    
    assert result is not None
    assert result["path"] == sample_python_file
    assert result["file_type"] == "source_code"
    assert result["language"] == "python"


def test_clear_metadata(sample_python_file, mock_aws_client_factory, mock_model_discovery):
    """
    [Function intent]
    Test clearing of cached file metadata.
    
    [Design principles]
    Verifies proper cache reset functionality.
    
    [Implementation details]
    Analyzes a file, clears the cache, and verifies the metadata is gone.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
    """
    analyzer = FileAnalyzerAgent()
    
    # First, analyze the file
    analyzer.analyze_file(sample_python_file)
    
    # Clear metadata
    analyzer.clear_metadata()
    
    # Verify metadata is cleared
    assert analyzer.file_metadata == {}
