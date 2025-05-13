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
# A test driver script for the File Analyzer Agent to verify its functionality
# on test files. This allows quick validation of the file analysis capabilities
# without requiring the full HSTC pipeline to be operational.
###############################################################################
# [Source file design principles]
# - Simple standalone script for testing
# - Comprehensive output for debugging
# - Self-contained with minimal dependencies
###############################################################################
# [Source file constraints]
# - Should not modify or create any files
# - Should only be used for testing purposes
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
# codebase:src/dbp_cli/commands/hstc_agno/test_file.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:19:00Z : Initial implementation by CodeAssistant
# * Created test driver for File Analyzer Agent
###############################################################################

import os
import json
import sys
from pathlib import Path

# Add the parent directory to the Python path to allow importing from the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from dbp_cli.commands.hstc_agno.agents import FileAnalyzerAgent


def print_separator(title=None):
    """Print a separator line with an optional title."""
    width = 80
    if title:
        print(f"\n{'-' * 10} {title} {'-' * (width - 12 - len(title))}")
    else:
        print(f"\n{'-' * width}")


def run_test(file_path):
    """Run the File Analyzer Agent on a test file and display results."""
    print(f"Testing File Analyzer Agent on: {file_path}")
    print_separator()
    
    # Create the agent
    agent = FileAnalyzerAgent()
    
    # Analyze the file
    print("Analyzing file...")
    result = agent.analyze_file(file_path)
    
    # Display results
    print_separator("File Metadata")
    print(f"Path: {result.get('path')}")
    print(f"Size: {result.get('size')} bytes")
    print(f"File Type: {result.get('file_type')}")
    print(f"Language: {result.get('language')}")
    print(f"Confidence: {result.get('confidence')}%")
    
    # Display dependencies
    print_separator("Dependencies")
    for dep in result.get('dependencies', []):
        print(f"- {dep.get('name')} ({dep.get('kind')}): {dep.get('path_or_package')}")
        if dep.get('function_names'):
            print(f"  Functions: {', '.join(dep.get('function_names'))}")
    
    # Display definitions
    print_separator("Definitions")
    for defn in result.get('definitions', []):
        print(f"- {defn.get('name')} ({defn.get('type')}) at line {defn.get('line_number')}")
        if defn.get('comments'):
            comment_preview = defn.get('comments').replace('\n', ' ')[:50]
            print(f"  Comment: {comment_preview}...")
    
    # Display header comment if available
    if result.get('header_comment'):
        print_separator("Header Comment")
        print(result.get('header_comment')[:200] + "..." if len(result.get('header_comment', "")) > 200 else result.get('header_comment'))
    
    print_separator()
    print("Analysis complete!")
    
    return result


if __name__ == "__main__":
    # Get the test file path from the command line or use the default
    if len(sys.argv) > 1:
        test_file_path = sys.argv[1]
    else:
        # Use the included test file
        script_dir = Path(__file__).resolve().parent
        test_file_path = os.path.join(script_dir, "test_file.py")
    
    # Run the test
    result = run_test(test_file_path)
    
    # Optionally save the full JSON result to a file
    if "--save-json" in sys.argv:
        output_path = os.path.join(Path(test_file_path).parent, "analyzer_result.json")
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Full result saved to {output_path}")
