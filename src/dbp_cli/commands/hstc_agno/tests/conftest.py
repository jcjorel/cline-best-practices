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
# This file provides test fixtures for the HSTC Agno implementation tests.
# It includes fixtures for creating temporary directories, sample files, and mock objects.
###############################################################################
# [Source file design principles]
# - Centralize test fixtures to avoid duplication
# - Provide realistic test data that matches production patterns
# - Support both unit and integration testing
###############################################################################
# [Source file constraints]
# - Must clean up temporary resources after tests complete
# - Should not depend on external services
###############################################################################
# [Dependencies]
# system:pytest
# system:tempfile
# system:shutil
# system:os
# system:pathlib
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
###############################################################################
# [GenAI tool change history]
# 2025-05-13T12:20:00Z : Added AWS client factory mocking by CodeAssistant
# * Implemented mock_aws_client_factory fixture for Bedrock client mocking
# * Added proper AWS credentials support for Agno tests
# 2025-05-12T08:11:30Z : Initial implementation by CodeAssistant
# * Created test fixtures for HSTC Agno implementation
###############################################################################

import os
import pytest
import boto3
from pathlib import Path
import tempfile
import shutil
from unittest.mock import MagicMock, patch

from dbp.api_providers.aws.client_factory import AWSClientFactory


@pytest.fixture
def temp_dir():
    """
    [Function intent]
    Create a temporary directory for tests that's automatically cleaned up.
    
    [Design principles]
    Ensures test isolation by providing a clean directory for each test.
    Uses Python's context management for proper resource cleanup.
    
    [Implementation details]
    Uses tempfile.mkdtemp() to create a directory and shutil.rmtree() for cleanup.
    
    Returns:
        Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_files_dir():
    """
    [Function intent]
    Create a directory with test files within the tests directory.
    
    [Design principles]
    Provides a persistent location for test files.
    Organizes test files separately from test code.
    
    [Implementation details]
    Creates a 'test_files' directory within the current test directory.
    
    Returns:
        Path to test files directory
    """
    # Get the tests directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_files_dir = os.path.join(current_dir, "test_files")
    
    # Create directory if it doesn't exist
    if not os.path.exists(test_files_dir):
        os.makedirs(test_files_dir)
    
    return test_files_dir


@pytest.fixture
def sample_python_file(test_files_dir):
    """
    [Function intent]
    Create a sample Python file with proper HSTC documentation for testing.
    
    [Design principles]
    Provides realistic test data that follows HSTC documentation standards.
    Includes various code constructs to test documentation extraction.
    
    [Implementation details]
    Creates a Python file with header comments, function definitions, and class definitions.
    
    Args:
        test_files_dir: Directory to create the file in
        
    Returns:
        Path to sample Python file
    """
    file_content = '''"""
Sample Python file for testing the HSTC functionality.
"""

import os
import sys
from typing import List, Dict, Any

# Global variable
VERSION = "1.0.0"

def sample_function(arg1: str, arg2: int = 0) -> bool:
    """
    [Function intent]
    This is a sample function for testing documentation extraction.
    
    [Design principles]
    Follows single responsibility principle.
    
    [Implementation details]
    Uses simple implementation for demonstration.
    
    Args:
        arg1: First argument description
        arg2: Second argument description, defaults to 0
        
    Returns:
        bool: Always returns True
    """
    return True

class SampleClass:
    """
    [Class intent]
    Example class for testing documentation extraction.
    
    [Design principles]
    Simple class implementation for testing purposes.
    
    [Implementation details]
    Contains basic initialization and processing methods.
    """
    
    def __init__(self, value: str):
        """
        [Class method intent]
        Initialize with a value.
        
        [Design principles]
        Simple initialization pattern.
        
        [Implementation details]
        Stores the value as an instance variable.
        
        Args:
            value: Initial value for the instance
        """
        self.value = value
    
    def process(self) -> Dict[str, Any]:
        """
        [Class method intent]
        Process the value and return a result.
        
        [Design principles]
        Simple processing with clear return value.
        
        [Implementation details]
        Creates a dictionary with the result.
        
        Returns:
            Dictionary containing the result
        """
        return {"result": self.value}
'''
    
    file_path = os.path.join(test_files_dir, "sample_python.py")
    with open(file_path, "w") as f:
        f.write(file_content)
    
    return file_path


@pytest.fixture
def sample_javascript_file(test_files_dir):
    """
    [Function intent]
    Create a sample JavaScript file with proper HSTC documentation for testing.
    
    [Design principles]
    Provides realistic test data for JavaScript documentation format.
    Includes various code constructs to test multi-language support.
    
    [Implementation details]
    Creates a JavaScript file with JSDoc comments, function definitions, and class definitions.
    
    Args:
        test_files_dir: Directory to create the file in
        
    Returns:
        Path to sample JavaScript file
    """
    file_content = '''/**
 * Sample JavaScript file for testing the HSTC functionality.
 */

// Global variable
const VERSION = "1.0.0";

/**
 * [Function intent]
 * This is a sample function for testing documentation extraction.
 *
 * [Design principles]
 * Follows single responsibility principle.
 *
 * [Implementation details]
 * Uses simple implementation for demonstration.
 *
 * @param {string} arg1 - First argument description
 * @param {number} [arg2=0] - Second argument description, defaults to 0
 * @returns {boolean} Always returns true
 */
function sampleFunction(arg1, arg2 = 0) {
    return true;
}

/**
 * [Class intent]
 * Example class for testing documentation extraction.
 *
 * [Design principles]
 * Simple class implementation for testing purposes.
 *
 * [Implementation details]
 * Contains basic initialization and processing methods.
 */
class SampleClass {
    /**
     * [Class method intent]
     * Initialize with a value.
     *
     * [Design principles]
     * Simple initialization pattern.
     *
     * [Implementation details]
     * Stores the value as an instance variable.
     *
     * @param {string} value - Initial value
     */
    constructor(value) {
        this.value = value;
    }
    
    /**
     * [Class method intent]
     * Process the value and return a result.
     *
     * [Design principles]
     * Simple processing with clear return value.
     *
     * [Implementation details]
     * Creates an object with the result.
     *
     * @returns {Object} Result object
     */
    process() {
        return { result: this.value };
    }
}

module.exports = {
    VERSION,
    sampleFunction,
    SampleClass
};
'''
    
    file_path = os.path.join(test_files_dir, "sample_javascript.js")
    with open(file_path, "w") as f:
        f.write(file_content)
    
    return file_path


@pytest.fixture
def missing_docs_file(test_files_dir):
    """
    [Function intent]
    Create a file with missing documentation for testing validation.
    
    [Design principles]
    Provides test data for documentation validation functionality.
    Tests detection of missing documentation sections.
    
    [Implementation details]
    Creates a Python file without proper HSTC documentation.
    
    Args:
        test_files_dir: Directory to create the file in
        
    Returns:
        Path to file with missing documentation
    """
    file_content = '''# File with missing documentation

import os

def undocumented_function(arg1, arg2=0):
    return True

class UndocumentedClass:
    def __init__(self, value):
        self.value = value
    
    def process(self):
        return {"result": self.value}
'''
    
    file_path = os.path.join(test_files_dir, "missing_docs.py")
    with open(file_path, "w") as f:
        f.write(file_content)
    
    return file_path


@pytest.fixture
def mock_file_analyzer():
    """
    [Function intent]
    Create a mock File Analyzer Agent for testing.
    
    [Design principles]
    Supports isolated unit testing without actual file analysis.
    Provides predictable analyzer behavior for testing other components.
    
    [Implementation details]
    Uses unittest.mock.MagicMock to create a mock object.
    Configures return values for key methods.
    
    Returns:
        Mock File Analyzer Agent
    """
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_file.return_value = {
        "path": "test_file.py",
        "file_type": "source_code",
        "language": "python",
        "confidence": 100,
        "definitions": [
            {
                "name": "sample_function",
                "type": "function",
                "line_number": 10,
                "comments": '"""Sample function docstring"""'
            }
        ],
        "dependencies": [
            {
                "name": "os",
                "kind": "system",
                "path_or_package": "os"
            }
        ],
        "header_comment": '"""Sample header comment"""'
    }
    
    # Add clear_metadata method
    mock_analyzer.clear_metadata = MagicMock()
    
    return mock_analyzer


@pytest.fixture
def mock_doc_generator():
    """
    [Function intent]
    Create a mock Documentation Generator Agent for testing.
    
    [Design principles]
    Supports isolated unit testing without actual documentation generation.
    Provides predictable generator behavior for testing other components.
    
    [Implementation details]
    Uses unittest.mock.MagicMock to create a mock object.
    Configures return values for key methods.
    
    Returns:
        Mock Documentation Generator Agent
    """
    mock_generator = MagicMock()
    mock_generator.process_file_documentation.return_value = {
        "path": "test_file.py",
        "file_type": "source_code",
        "language": "python",
        "file_header": {
            "intent": "Test file intent",
            "design_principles": "Test design principles",
            "constraints": "Test constraints",
            "dependencies": [],
            "raw_header": "Test raw header"
        },
        "definitions": [
            {
                "name": "sample_function",
                "type": "function",
                "original_comment": '"""Sample function docstring"""',
                "updated_comment": '"""[Function intent]\nTest function.\n\n[Design principles]\nTest principles.\n\n[Implementation details]\nTest details.\n"""'
            }
        ],
        "documentation_updated": True
    }
    
    mock_generator.validate_documentation.return_value = {
        "valid": True,
        "issues": []
    }
    
    # Add clear_documentation method
    mock_generator.clear_documentation = MagicMock()
    
    return mock_generator


@pytest.fixture
def mock_aws_client_factory():
    """
    [Function intent]
    Provide a mocked AWS client factory for testing.
    
    [Design principles]
    Isolates tests from actual AWS services.
    Provides predictable AWS client behavior for testing.
    
    [Implementation details]
    Creates a mock AWSClientFactory with pre-configured boto3 session and clients.
    Specifically configures Bedrock client for Agno usage.
    
    Returns:
        Mock AWSClientFactory for testing
    """
    mock = MagicMock(spec=AWSClientFactory)
    
    # Create a mock boto3 session
    mock_session = MagicMock(spec=boto3.Session)
    
    # Configure mock session to return mock clients
    def get_mock_client(service_name, **kwargs):
        mock_client = MagicMock()
        # Configure service-specific client behavior
        if service_name == 'bedrock':
            # Mock bedrock client methods
            mock_client.converse = MagicMock(return_value={"result": "success"})
        return mock_client
    
    mock_session.client = MagicMock(side_effect=get_mock_client)
    
    # Configure get_session to return our mock session
    mock.get_session.return_value = mock_session
    
    # Configure get_client to return mock clients directly
    mock.get_client.side_effect = get_mock_client
    
    # Configure the singleton pattern for the mock
    mock.get_instance.return_value = mock
    
    # Mock the actual singleton instance
    with patch.object(AWSClientFactory, 'get_instance', return_value=mock):
        yield mock
