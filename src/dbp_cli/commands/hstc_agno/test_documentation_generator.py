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
# A test driver script for the Documentation Generator Agent to verify its functionality
# on test files. This allows quick validation of the documentation generation capabilities
# without requiring the full HSTC pipeline to be operational.
###############################################################################
# [Source file design principles]
# - Simple standalone script for testing
# - Comprehensive output for debugging
# - Self-contained with minimal dependencies
###############################################################################
# [Source file constraints]
# - Should not modify or create any files (outputs to console only)
# - Should only be used for testing purposes
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
# codebase:src/dbp_cli/commands/hstc_agno/test_file.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:25:00Z : Initial implementation by CodeAssistant
# * Created test driver for Documentation Generator Agent
###############################################################################

import os
import json
import sys
from pathlib import Path

# Add the parent directory to the Python path to allow importing from the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from dbp_cli.commands.hstc_agno.agents import FileAnalyzerAgent, DocumentationGeneratorAgent


def print_separator(title=None):
    """Print a separator line with an optional title."""
    width = 80
    if title:
        print(f"\n{'-' * 10} {title} {'-' * (width - 12 - len(title))}")
    else:
        print(f"\n{'-' * width}")


def run_test(file_path):
    """Run the Documentation Generator Agent on a test file and display results."""
    print(f"Testing Documentation Generator Agent on: {file_path}")
    print_separator()
    
    # Step 1: First analyze the file with FileAnalyzerAgent
    print("Step 1: Analyzing file with FileAnalyzerAgent...")
    file_analyzer = FileAnalyzerAgent()
    file_metadata = file_analyzer.analyze_file(file_path)
    
    print(f"File type: {file_metadata.get('file_type')}")
    print(f"Language: {file_metadata.get('language')}")
    print(f"Found {len(file_metadata.get('definitions', []))} definitions")
    
    # Step 2: Generate documentation with DocumentationGeneratorAgent
    print_separator("Step 2: Generating Documentation")
    doc_generator = DocumentationGeneratorAgent()
    documentation = doc_generator.process_file_documentation(file_path, file_metadata, {})
    
    # Display results
    print_separator("Documentation Results")
    print(f"Documentation updated: {documentation.get('documentation_updated', False)}")
    
    # Display header documentation
    header = documentation.get("file_header", {})
    print_separator("File Header Documentation")
    print(f"Intent: {header.get('intent', '')[:100]}...")
    print(f"Design Principles: {header.get('design_principles', '')[:100]}...")
    print(f"Constraints: {header.get('constraints', '')[:100]}...")
    
    # Print dependencies
    print_separator("Dependencies")
    for dep in header.get("dependencies", []):
        print(f"- {dep.get('kind', 'unknown')}: {dep.get('dependency', '')}")
    
    # Print function documentation
    print_separator("Function Documentation")
    for defn in documentation.get("definitions", [])[:3]:  # Show only first 3 definitions
        print(f"- {defn.get('name')} ({defn.get('type')})")
        updated_comment = defn.get("updated_comment", "")
        lines = updated_comment.split("\n")
        # Print first few lines of the comment
        for line in lines[:5]:
            print(f"  {line}")
        print("  ...")
    
    # Validate documentation
    print_separator("Validation Results")
    validation = doc_generator.validate_documentation(file_path)
    print(f"Documentation valid: {validation.get('valid', False)}")
    
    if not validation.get("valid", True):
        print("Issues:")
        for issue in validation.get("issues", []):
            print(f"- {issue}")
    
    print_separator()
    print("Documentation generation complete!")
    
    return documentation


if __name__ == "__main__":
    # Get the test file path from the command line or use the default
    if len(sys.argv) > 1:
        test_file_path = sys.argv[1]
    else:
        # Use the included test file
        script_dir = Path(__file__).resolve().parent
        test_file_path = os.path.join(script_dir, "test_file.py")
    
    # Run the test
    documentation = run_test(test_file_path)
    
    # Optionally save the full JSON result to a file
    if "--save-json" in sys.argv:
        output_path = os.path.join(Path(test_file_path).parent, "documentation_result.json")
        with open(output_path, "w") as f:
            # Convert documentation to a serializable format
            serializable_doc = {
                "path": documentation.get("path", ""),
                "file_type": documentation.get("file_type", ""),
                "language": documentation.get("language", ""),
                "documentation_updated": documentation.get("documentation_updated", False),
                "file_header": {
                    "intent": documentation.get("file_header", {}).get("intent", ""),
                    "design_principles": documentation.get("file_header", {}).get("design_principles", ""),
                    "constraints": documentation.get("file_header", {}).get("constraints", ""),
                    "dependencies": [
                        {"kind": d.get("kind", ""), "dependency": d.get("dependency", "")}
                        for d in documentation.get("file_header", {}).get("dependencies", [])
                    ],
                    "change_history": documentation.get("file_header", {}).get("change_history", [])
                },
                "definitions": [
                    {
                        "name": d.get("name", ""),
                        "type": d.get("type", ""),
                        "updated_comment": d.get("updated_comment", "")
                    }
                    for d in documentation.get("definitions", [])
                ]
            }
            json.dump(serializable_doc, f, indent=2)
        print(f"Full result saved to {output_path}")
