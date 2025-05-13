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
# A test driver script for the HSTC Manager to verify its end-to-end workflow.
# This allows validation of the complete HSTC process, from file analysis through
# documentation generation and implementation plan creation.
###############################################################################
# [Source file design principles]
# - Simple standalone script for testing
# - Clear workflow demonstration with status reporting
# - Self-contained with comprehensive error handling
###############################################################################
# [Source file constraints]
# - Should not modify actual production files
# - For testing purposes only
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/manager.py
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
# codebase:src/dbp_cli/commands/hstc_agno/test_file.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:31:00Z : Initial implementation by CodeAssistant
# * Created test driver for HSTC Manager
###############################################################################

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the Python path to allow importing from the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from dbp_cli.commands.hstc_agno.manager import HSTCManager


def print_separator(title=None):
    """Print a separator line with an optional title."""
    width = 80
    if title:
        print(f"\n{'-' * 10} {title} {'-' * (width - 12 - len(title))}")
    else:
        print(f"\n{'-' * width}")


def run_basic_test(file_path, options=None):
    """
    Run a basic test of the HSTC Manager on a specific file.
    
    Args:
        file_path: Path to the test file
        options: Optional processing options
    """
    if options is None:
        options = {}
        
    print(f"Testing HSTC Manager on: {file_path}")
    print_separator()
    
    # Initialize the manager
    manager = HSTCManager()
    
    # Process the file
    print("Processing file...")
    result = manager.process_file(file_path, options)
    
    # Check for errors
    if "error" in result:
        print_separator("ERROR")
        print(f"Error processing file: {result['error']}")
        return False
    
    # Print results
    print_separator("File Analysis Results")
    file_metadata = result["file_metadata"]
    print(f"File type: {file_metadata.get('file_type')}")
    print(f"Language: {file_metadata.get('language')}")
    print(f"Definitions found: {len(file_metadata.get('definitions', []))}")
    print(f"Dependencies found: {len(file_metadata.get('dependencies', []))}")
    
    print_separator("Documentation Results")
    documentation = result["documentation"]
    print(f"Documentation updated: {documentation.get('documentation_updated')}")
    
    print_separator("Validation Results")
    validation = result["validation"]
    print(f"Documentation valid: {validation.get('valid')}")
    
    if not validation.get("valid", True):
        print("Issues:")
        for issue in validation.get("issues", []):
            print(f"- {issue}")
    
    print_separator("Implementation Plan")
    print(f"Plan directory: {result['plan_path']}")
    print("Generated files:")
    for plan_file in result["plan_files"]:
        print(f"- {os.path.basename(plan_file)}")
    
    print_separator()
    print("Test completed successfully!")
    
    return result


def run_directory_test(dir_path, options=None):
    """
    Test directory processing with the HSTC Manager.
    
    Args:
        dir_path: Directory path to process
        options: Optional processing options
    """
    if options is None:
        options = {"recursive_dir": True}
    
    print(f"Testing directory processing on: {dir_path}")
    print_separator()
    
    # Initialize the manager
    manager = HSTCManager()
    
    # Process the directory
    print("Processing directory...")
    result = manager.process_directory(dir_path, options)
    
    print_separator("Directory Processing Results")
    print(f"Files processed: {result['files_processed']}")
    
    successful = sum(1 for r in result['results'] if "error" not in r)
    failed = sum(1 for r in result['results'] if "error" in r)
    
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Print details of any failures
    if failed > 0:
        print_separator("Failed Files")
        for r in result['results']:
            if "error" in r:
                print(f"- {r.get('file_path')}: {r.get('error')}")
    
    print_separator()
    print("Directory test completed!")
    
    return result


def run_cache_test(file_path):
    """
    Test cache saving and loading functionality.
    
    Args:
        file_path: Path to the test file
    """
    print("Testing cache functionality...")
    print_separator()
    
    # Initialize the manager
    manager = HSTCManager()
    
    # Process a file
    print("Processing file...")
    result = manager.process_file(file_path, {})
    
    # Save cache
    cache_path = "test_cache.json"
    print(f"Saving cache to {cache_path}...")
    manager.save_cache(cache_path)
    
    # Create a new manager and load cache
    print("Creating new manager and loading cache...")
    new_manager = HSTCManager()
    load_success = new_manager.load_cache(cache_path)
    
    print(f"Cache loaded successfully: {load_success}")
    
    # Verify cache contents
    print("Verifying cache contents...")
    cached_file = new_manager.processed_files.get(file_path)
    if cached_file:
        print(f"Found cached data for {file_path}")
        print(f"File type: {cached_file.get('file_type')}")
        print(f"Language: {cached_file.get('language')}")
        cache_valid = True
    else:
        print(f"No cached data found for {file_path}")
        cache_valid = False
    
    # Clean up
    print("Cleaning up...")
    if os.path.exists(cache_path):
        os.remove(cache_path)
    
    print_separator()
    print(f"Cache test {'completed successfully' if cache_valid and load_success else 'failed'}")
    
    return cache_valid and load_success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="HSTC Manager Test")
    parser.add_argument("--test-type", choices=["basic", "directory", "cache", "all"], 
                      default="basic", help="Type of test to run")
    parser.add_argument("--file", help="File path for basic test")
    parser.add_argument("--dir", help="Directory path for directory test")
    parser.add_argument("--output", help="Output directory for implementation plan")
    
    args = parser.parse_args()
    
    # Determine file path to use
    if args.file:
        test_file_path = args.file
    else:
        # Use the included test file
        script_dir = Path(__file__).resolve().parent
        test_file_path = os.path.join(script_dir, "test_file.py")
    
    # Determine directory path to use
    if args.dir:
        test_dir_path = args.dir
    else:
        # Use the current script directory (contains test files)
        test_dir_path = Path(__file__).resolve().parent
    
    # Set up options
    options = {}
    if args.output:
        options["output"] = args.output
    
    # Run tests based on type
    if args.test_type in ["basic", "all"]:
        print_separator("BASIC TEST")
        basic_result = run_basic_test(test_file_path, options)
        
    if args.test_type in ["directory", "all"]:
        print_separator("DIRECTORY TEST")
        dir_options = options.copy()
        dir_options["recursive_dir"] = True
        directory_result = run_directory_test(test_dir_path, dir_options)
    
    if args.test_type in ["cache", "all"]:
        print_separator("CACHE TEST")
        cache_result = run_cache_test(test_file_path)
    
    print("\nAll tests completed!")
