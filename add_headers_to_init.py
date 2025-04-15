#!/usr/bin/env python3

"""
Add GenAI headers to all __init__.py files that are missing them.
"""

import os
import sys
import datetime

# List of directories with __init__.py files that need headers
directories = [
    "src/dbp/consistency_analysis",
    "src/dbp/core",
    "src/dbp/doc_relationships", 
    "src/dbp/fs_monitor",
    "src/dbp/internal_tools",
    "src/dbp/llm_coordinator",
    "src/dbp/memory_cache",
    "src/dbp/metadata_extraction",
    "src/dbp/recommendation_generator",
    "src/dbp/scheduler",
    "src/dbp/database"
]

# Template for the GenAI header
def generate_header_template(package_name, description):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return f'''###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# {package_name} package for the Documentation-Based Programming system.
# {description}
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# {timestamp} : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################
'''

# Package descriptions
descriptions = {
    "consistency_analysis": "Provides functionality to analyze consistency between documentation and code.",
    "core": "Implements the core component framework and lifecycle management.",
    "doc_relationships": "Defines and analyzes relationships between documentation files.",
    "fs_monitor": "Implements file system monitoring for detecting changes to documentation and code.",
    "internal_tools": "Provides internal tools for LLM-based processing and analysis.",
    "llm_coordinator": "Coordinates multiple LLM instances for efficient processing of queries.",
    "memory_cache": "Implements in-memory caching for metadata and analysis results.",
    "metadata_extraction": "Provides functionality to extract metadata from code and documentation files.",
    "recommendation_generator": "Generates recommendations for maintaining documentation consistency.",
    "scheduler": "Implements background task scheduling and management.",
    "database": "Database models and repository implementations."
}

# Process each directory
for directory in directories:
    init_path = os.path.join(directory, "__init__.py")
    
    # Skip if file doesn't exist
    if not os.path.exists(init_path):
        print(f"Warning: {init_path} does not exist, skipping.")
        continue
    
    # Check if file already has a GenAI header
    with open(init_path, 'r') as f:
        content = f.read()
        if "GenAI coding tool directive" in content:
            print(f"Note: {init_path} already has a GenAI header, skipping.")
            continue
    
    # Extract the package name from directory path
    package_name = os.path.basename(directory)
    
    # Generate header with package-specific description
    description = descriptions.get(package_name, "Provides package functionality and defines the public API.")
    header = generate_header_template(package_name.replace('_', ' ').title(), description)
    
    # Read the file content
    with open(init_path, 'r') as f:
        content = f.read()
    
    # Check if the file starts with a module docstring
    if content.lstrip().startswith('"""') or content.lstrip().startswith("'''"):
        # Find where the docstring ends
        lines = content.split('\n')
        new_lines = []
        in_docstring = False
        docstring_delimiter = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect start of docstring
            if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
                in_docstring = True
                docstring_delimiter = stripped[:3]
                # Add our header before the docstring
                new_lines.append(header)
                new_lines.append('')  # Add an empty line between header and docstring
                new_lines.append(line)
                continue
                
            # Detect end of docstring
            if in_docstring and docstring_delimiter in stripped:
                in_docstring = False
                new_lines.append(line)
                continue
                
            new_lines.append(line)
            
        # If we didn't find a docstring, add header at the top
        if not in_docstring and docstring_delimiter is None:
            new_content = header + '\n\n' + content
        else:
            new_content = '\n'.join(new_lines)
    else:
        # No docstring, add header at the top
        new_content = header + '\n\n' + content
    
    # Write updated content back to the file
    with open(init_path, 'w') as f:
        f.write(new_content)
    
    print(f"Added header to {init_path}")

print("Done adding headers to __init__.py files.")
