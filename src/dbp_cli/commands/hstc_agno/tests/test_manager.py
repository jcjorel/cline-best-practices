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
# This file contains unit tests for the HSTC Manager component of the HSTC
# implementation. It tests the manager's ability to coordinate the file analysis 
# and documentation generation workflow, handle dependencies, and generate
# implementation plans.
###############################################################################
# [Source file design principles]
# - Test end-to-end workflow coordination
# - Verify proper agent collaboration
# - Test plan generation functionality
###############################################################################
# [Source file constraints]
# - Must use pytest fixtures from conftest.py
# - Should use mocked agents where appropriate
###############################################################################
# [Dependencies]
# system:pytest
# codebase:src/dbp_cli/commands/hstc_agno/manager.py
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
# codebase:src/dbp_cli/commands/hstc_agno/tests/conftest.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T08:16:35Z : Initial implementation by CodeAssistant
# * Created unit tests for HSTC Manager
###############################################################################

import pytest
import os
from pathlib import Path
from ..manager import HSTCManager
from unittest.mock import patch, MagicMock


def test_manager_initialization():
    """
    [Function intent]
    Test that the HSTC Manager initializes correctly.
    
    [Design principles]
    Verifies basic object creation and properties are correctly set.
    
    [Implementation details]
    Creates a HSTCManager instance and checks that it has expected attributes.
    """
    manager = HSTCManager()
    assert hasattr(manager, "file_analyzer")
    assert hasattr(manager, "doc_generator")
    assert hasattr(manager, "processed_files")
    assert hasattr(manager, "dependency_cache")
    assert manager.processed_files == {}
    assert manager.dependency_cache == {}


def test_validate_file_path(temp_dir):
    """
    [Function intent]
    Test file path validation.
    
    [Design principles]
    Verifies correct validation of file paths before processing.
    
    [Implementation details]
    Tests validation for existing files, non-existent files, and directories.
    
    Args:
        temp_dir: Pytest fixture providing a temporary directory
    """
    manager = HSTCManager()
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("Test content")
    
    # Test with valid file
    assert manager._validate_file_path(test_file) is True
    
    # Test with non-existent file
    assert manager._validate_file_path(os.path.join(temp_dir, "nonexistent.py")) is False
    
    # Test with directory
    assert manager._validate_file_path(temp_dir) is False


@patch("src.dbp_cli.commands.hstc_agno.agents.FileAnalyzerAgent")
def test_analyze_file(mock_file_analyzer_cls, temp_dir, mock_file_analyzer):
    """
    [Function intent]
    Test file analysis through the manager.
    
    [Design principles]
    Verifies correct delegation to the File Analyzer agent and result handling.
    
    [Implementation details]
    Uses a mock File Analyzer to simulate file analysis and checks caching behavior.
    
    Args:
        mock_file_analyzer_cls: Mocked FileAnalyzerAgent class
        temp_dir: Pytest fixture providing a temporary directory
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
    """
    mock_file_analyzer_cls.return_value = mock_file_analyzer
    
    manager = HSTCManager()
    manager.file_analyzer = mock_file_analyzer
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("Test content")
    
    result = manager.analyze_file(test_file)
    
    # Verify analyzer was called with the right parameters
    mock_file_analyzer.analyze_file.assert_called_once_with(test_file)
    
    # Verify result is correctly returned
    assert result["file_type"] == "source_code"
    assert result["language"] == "python"
    
    # Verify file was added to processed_files cache
    assert test_file in manager.processed_files
    
    # Test cache behavior - analyze again
    mock_file_analyzer.analyze_file.reset_mock()
    result2 = manager.analyze_file(test_file)
    
    # Verify analyzer was not called again
    mock_file_analyzer.analyze_file.assert_not_called()
    
    # Verify cached result was returned
    assert result2 == result


@patch("src.dbp_cli.commands.hstc_agno.agents.FileAnalyzerAgent")
def test_process_dependencies(mock_file_analyzer_cls, temp_dir, mock_file_analyzer):
    """
    [Function intent]
    Test dependency processing.
    
    [Design principles]
    Verifies correct recursive processing of file dependencies.
    
    [Implementation details]
    Creates test files with dependencies and checks that they're processed correctly.
    
    Args:
        mock_file_analyzer_cls: Mocked FileAnalyzerAgent class
        temp_dir: Pytest fixture providing a temporary directory
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
    """
    mock_file_analyzer_cls.return_value = mock_file_analyzer
    
    # Set up analyzer to return different results for different files
    def analyze_side_effect(file_path):
        if "main.py" in file_path:
            return {
                "path": file_path,
                "file_type": "source_code",
                "language": "python",
                "dependencies": [
                    {"kind": "codebase", "path_or_package": "utils.py"},
                    {"kind": "system", "path_or_package": "os"}
                ]
            }
        else:
            return {
                "path": file_path,
                "file_type": "source_code",
                "language": "python",
                "dependencies": []
            }
    
    mock_file_analyzer.analyze_file.side_effect = analyze_side_effect
    
    manager = HSTCManager()
    manager.file_analyzer = mock_file_analyzer
    
    # Create test files
    main_file = os.path.join(temp_dir, "main.py")
    utils_file = os.path.join(temp_dir, "utils.py")
    
    with open(main_file, "w") as f:
        f.write("import utils\n")
    
    with open(utils_file, "w") as f:
        f.write("# Utils\n")
    
    # Analyze main file with dependencies
    result = manager.analyze_file(main_file, recursive=True)
    
    # Verify both files are in processed_files cache
    assert main_file in manager.processed_files
    
    # Check the dependency was processed
    mock_file_analyzer.analyze_file.assert_any_call(os.path.join(os.path.dirname(main_file), "utils.py"))


@patch("src.dbp_cli.commands.hstc_agno.agents.FileAnalyzerAgent")
@patch("src.dbp_cli.commands.hstc_agno.agents.DocumentationGeneratorAgent")
def test_generate_documentation(mock_doc_generator_cls, mock_file_analyzer_cls, 
                               mock_doc_generator, mock_file_analyzer, temp_dir):
    """
    [Function intent]
    Test documentation generation through the manager.
    
    [Design principles]
    Verifies correct delegation to the Documentation Generator agent.
    
    [Implementation details]
    Uses mock agents to simulate the documentation generation workflow.
    
    Args:
        mock_doc_generator_cls: Mocked DocumentationGeneratorAgent class
        mock_file_analyzer_cls: Mocked FileAnalyzerAgent class
        mock_doc_generator: Pytest fixture providing a mock Documentation Generator
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
        temp_dir: Pytest fixture providing a temporary directory
    """
    mock_file_analyzer_cls.return_value = mock_file_analyzer
    mock_doc_generator_cls.return_value = mock_doc_generator
    
    manager = HSTCManager()
    manager.file_analyzer = mock_file_analyzer
    manager.doc_generator = mock_doc_generator
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("def test_function():\n    pass")
    
    # Add file to processed_files cache
    manager.processed_files[test_file] = {
        "path": test_file,
        "file_type": "source_code",
        "language": "python",
        "definitions": [{"name": "test_function", "type": "function"}]
    }
    
    # Generate documentation
    result = manager.generate_documentation(test_file)
    
    # Verify generator was called with the right parameters
    mock_doc_generator.process_file_documentation.assert_called_once()
    args, kwargs = mock_doc_generator.process_file_documentation.call_args
    assert args[0] == test_file
    assert args[1] == manager.processed_files[test_file]
    assert isinstance(args[2], dict)
    
    # Verify result is correctly returned
    assert result["documentation_updated"] is True


@patch("src.dbp_cli.commands.hstc_agno.agents.DocumentationGeneratorAgent")
def test_validate_documentation(mock_doc_generator_cls, mock_doc_generator, temp_dir):
    """
    [Function intent]
    Test documentation validation through the manager.
    
    [Design principles]
    Verifies correct delegation to the Documentation Generator agent for validation.
    
    [Implementation details]
    Uses a mock Documentation Generator to simulate validation.
    
    Args:
        mock_doc_generator_cls: Mocked DocumentationGeneratorAgent class
        mock_doc_generator: Pytest fixture providing a mock Documentation Generator
        temp_dir: Pytest fixture providing a temporary directory
    """
    mock_doc_generator_cls.return_value = mock_doc_generator
    
    manager = HSTCManager()
    manager.doc_generator = mock_doc_generator
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("def test_function():\n    pass")
    
    # Set up mock validation result
    mock_doc_generator.validate_documentation.return_value = {
        "valid": True,
        "issues": []
    }
    
    # Validate documentation
    result = manager.validate_documentation(test_file)
    
    # Verify validator was called with the right parameters
    mock_doc_generator.validate_documentation.assert_called_once_with(test_file)
    
    # Verify result is correctly returned
    assert result["valid"] is True
    assert result["issues"] == []


def test_output_dir(temp_dir):
    """
    [Function intent]
    Test output directory creation.
    
    [Design principles]
    Verifies correct creation and naming of output directories.
    
    [Implementation details]
    Tests both explicit and default output directories.
    
    Args:
        temp_dir: Pytest fixture providing a temporary directory
    """
    manager = HSTCManager(base_dir=Path(temp_dir))
    
    # Test with explicit output path
    output_path = os.path.join(temp_dir, "explicit_output")
    result = manager._output_dir("test_file.py", output_path)
    
    assert result == output_path
    assert os.path.exists(output_path)
    
    # Test with default output path
    result = manager._output_dir("test_file.py")
    
    assert "hstc_update_test_file" in result
    assert os.path.exists(result)


@patch("src.dbp_cli.commands.hstc_agno.manager.HSTCManager._generate_overview_markdown")
@patch("src.dbp_cli.commands.hstc_agno.manager.HSTCManager._generate_implementation_markdown")
@patch("src.dbp_cli.commands.hstc_agno.manager.HSTCManager._generate_progress_markdown")
def test_generate_implementation_plan(mock_progress, mock_impl, mock_overview, temp_dir):
    """
    [Function intent]
    Test implementation plan generation.
    
    [Design principles]
    Verifies creation of all required plan files.
    
    [Implementation details]
    Mocks the markdown generation methods and checks that files are created.
    
    Args:
        mock_progress: Mocked progress markdown generator
        mock_impl: Mocked implementation markdown generator
        mock_overview: Mocked overview markdown generator
        temp_dir: Pytest fixture providing a temporary directory
    """
    # Set up mock return values
    mock_overview.return_value = "Test overview content"
    mock_impl.return_value = "Test implementation content"
    mock_progress.return_value = "Test progress content"
    
    manager = HSTCManager()
    
    # Create test documentation data
    documentation = {
        "path": "test_file.py",
        "language": "python",
        "file_header": {"intent": "Test intent"},
        "definitions": []
    }
    
    # Generate implementation plan
    result = manager.generate_implementation_plan("test_file.py", documentation, temp_dir)
    
    # Verify markdown generation methods were called
    mock_overview.assert_called_once()
    mock_impl.assert_called_once()
    mock_progress.assert_called_once()
    
    # Verify files were created
    assert len(result) == 3
    assert all(os.path.exists(path) for path in result)
    assert any("plan_overview.md" in path for path in result)
    assert any("plan_implementation.md" in path for path in result)
    assert any("plan_progress.md" in path for path in result)
    
    # Check file contents
    with open([path for path in result if "plan_overview.md" in path][0], "r") as f:
        assert f.read() == "Test overview content"
    
    with open([path for path in result if "plan_implementation.md" in path][0], "r") as f:
        assert f.read() == "Test implementation content"
    
    with open([path for path in result if "plan_progress.md" in path][0], "r") as f:
        assert f.read() == "Test progress content"


@patch("src.dbp_cli.commands.hstc_agno.agents.FileAnalyzerAgent")
@patch("src.dbp_cli.commands.hstc_agno.agents.DocumentationGeneratorAgent")
@patch("src.dbp_cli.commands.hstc_agno.manager.HSTCManager._generate_overview_markdown")
@patch("src.dbp_cli.commands.hstc_agno.manager.HSTCManager._generate_implementation_markdown")
@patch("src.dbp_cli.commands.hstc_agno.manager.HSTCManager._generate_progress_markdown")
def test_process_file(mock_progress, mock_impl, mock_overview, 
                     mock_doc_generator_cls, mock_file_analyzer_cls,
                     mock_doc_generator, mock_file_analyzer, temp_dir):
    """
    [Function intent]
    Test the complete file processing workflow.
    
    [Design principles]
    Verifies end-to-end integration of analysis, documentation, and plan generation.
    
    [Implementation details]
    Sets up mocks for all components and tests the full process_file method.
    
    Args:
        mock_progress: Mocked progress markdown generator
        mock_impl: Mocked implementation markdown generator
        mock_overview: Mocked overview markdown generator
        mock_doc_generator_cls: Mocked DocumentationGeneratorAgent class
        mock_file_analyzer_cls: Mocked FileAnalyzerAgent class
        mock_doc_generator: Pytest fixture providing a mock Documentation Generator
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
        temp_dir: Pytest fixture providing a temporary directory
    """
    # Set up mock return values
    mock_file_analyzer_cls.return_value = mock_file_analyzer
    mock_doc_generator_cls.return_value = mock_doc_generator
    
    mock_overview.return_value = "Test overview content"
    mock_impl.return_value = "Test implementation content"
    mock_progress.return_value = "Test progress content"
    
    # Set up metadata return value
    mock_file_analyzer.analyze_file.return_value = {
        "path": "test_file.py",
        "file_type": "source_code",
        "language": "python",
        "definitions": []
    }
    
    # Set up documentation return value
    mock_doc_generator.process_file_documentation.return_value = {
        "path": "test_file.py",
        "file_type": "source_code",
        "language": "python",
        "file_header": {"intent": "Test intent"},
        "definitions": [],
        "documentation_updated": True
    }
    
    # Set up validation return value
    mock_doc_generator.validate_documentation.return_value = {
        "valid": True,
        "issues": []
    }
    
    manager = HSTCManager()
    manager.file_analyzer = mock_file_analyzer
    manager.doc_generator = mock_doc_generator
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("def test_function():\n    pass")
    
    # Process the file
    options = {"output": os.path.join(temp_dir, "output")}
    result = manager.process_file(test_file, options)
    
    # Verify all steps were performed
    mock_file_analyzer.analyze_file.assert_called_once_with(test_file)
    mock_doc_generator.process_file_documentation.assert_called_once()
    mock_doc_generator.validate_documentation.assert_called_once_with(test_file)
    
    # Verify result structure
    assert "file_path" in result
    assert "file_metadata" in result
    assert "documentation" in result
    assert "validation" in result
    assert "plan_path" in result
    assert "plan_files" in result
    
    # Verify content
    assert result["file_path"] == test_file
    assert result["documentation"]["documentation_updated"] is True
    assert result["validation"]["valid"] is True
    assert os.path.exists(result["plan_path"])
    assert len(result["plan_files"]) == 3


@patch("src.dbp_cli.commands.hstc_agno.agents.FileAnalyzerAgent")
@patch("src.dbp_cli.commands.hstc_agno.agents.DocumentationGeneratorAgent")
def test_error_handling(mock_doc_generator_cls, mock_file_analyzer_cls,
                       mock_file_analyzer, temp_dir):
    """
    [Function intent]
    Test error handling in the manager.
    
    [Design principles]
    Verifies robust handling of errors during processing.
    
    [Implementation details]
    Sets up a mock to raise an exception and checks error reporting.
    
    Args:
        mock_doc_generator_cls: Mocked DocumentationGeneratorAgent class
        mock_file_analyzer_cls: Mocked FileAnalyzerAgent class
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
        temp_dir: Pytest fixture providing a temporary directory
    """
    # Set up analyzer to raise an exception
    mock_file_analyzer_cls.return_value = mock_file_analyzer
    mock_file_analyzer.analyze_file.side_effect = RuntimeError("Test error")
    
    manager = HSTCManager()
    manager.file_analyzer = mock_file_analyzer
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("def test_function():\n    pass")
    
    # Process the file, which should handle the error
    result = manager.process_file(test_file, {})
    
    # Verify error handling
    assert "error" in result
    assert "Test error" in result["error"]
    assert "traceback" in result
    assert "file_path" in result
    assert result["file_path"] == test_file


@patch("src.dbp_cli.commands.hstc_agno.agents.FileAnalyzerAgent")
def test_safe_process_file(mock_file_analyzer_cls, mock_file_analyzer, temp_dir):
    """
    [Function intent]
    Test the safe file processing method.
    
    [Design principles]
    Verifies handling of exceptions during processing.
    
    [Implementation details]
    Tests both successful processing and error cases.
    
    Args:
        mock_file_analyzer_cls: Mocked FileAnalyzerAgent class
        mock_file_analyzer: Pytest fixture providing a mock File Analyzer
        temp_dir: Pytest fixture providing a temporary directory
    """
    mock_file_analyzer_cls.return_value = mock_file_analyzer
    
    manager = HSTCManager()
    manager.file_analyzer = mock_file_analyzer
    manager.process_file = MagicMock()
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.py")
    with open(test_file, "w") as f:
        f.write("def test_function():\n    pass")
    
    # Test successful processing
    manager.process_file.return_value = {"success": True}
    result = manager.safe_process_file(test_file, {})
    assert "success" in result
    
    # Test error handling
    manager.process_file.side_effect = RuntimeError("Test error")
    result = manager.safe_process_file(test_file, {})
    assert "error" in result
    assert "Test error" in result["error"]


def test_cache_management(sample_python_file):
    """
    [Function intent]
    Test cache management functionality.
    
    [Design principles]
    Verifies saving, loading, and clearing of cache.
    
    [Implementation details]
    Tests all cache management methods.
    
    Args:
        sample_python_file: Pytest fixture providing a sample Python file
    """
    manager = HSTCManager()
    
    # Add data to cache
    manager.processed_files = {
        sample_python_file: {
            "path": sample_python_file,
            "language": "python"
        }
    }
    
    manager.dependency_cache = {
        "test_dependency.py": {
            "path": "test_dependency.py",
            "language": "python"
        }
    }
    
    # Test saving cache
    cache_path = "test_cache.json"
    manager.save_cache(cache_path)
    assert os.path.exists(cache_path)
    
    # Clear cache
    manager.clear_cache()
    assert manager.processed_files == {}
    assert manager.dependency_cache == {}
    
    # Load cache
    success = manager.load_cache(cache_path)
    assert success is True
    assert sample_python_file in manager.processed_files
    assert "test_dependency.py" in manager.dependency_cache
    
    # Clean up
    os.remove(cache_path)
