# HSTC Implementation with Agno - Context Files

This directory contains the context files for implementing the Hierarchical Semantic Tree Context (HSTC) feature using the Agno framework. These files provide comprehensive guidance for implementing the HSTC feature with Amazon Bedrock models (Nova Micro and Claude 3.7).

## Overview

The HSTC feature analyzes source code files to generate standardized documentation that follows the requirements specified in the project's documentation standards. This implementation uses the Agno framework to manage the workflow between different LLM models:

- **Nova Micro**: Used for efficient file analysis and classification tasks
- **Claude 3.7**: Used for in-depth documentation generation and reasoning

## Context Files

### Architecture and Design

- [**HSTC Architecture**](agno_hstc_architecture.md) - Overall architecture and component design for the HSTC feature
- [**HSTC Workflow**](agno_hstc_workflow.md) - Data flow and process orchestration between components

### Agent Implementation Details

- [**File Analyzer Agent**](agno_file_analyzer_agent.md) - Nova-based agent for analyzing source code files
- [**Documentation Generator Agent**](agno_documentation_generator_agent.md) - Claude-based agent for generating documentation

### Implementation Details

- [**Implementation Details Part 1**](agno_implementation_details_part1.md) - CLI and HSTC Manager implementation
- [**Implementation Details Part 2A**](agno_implementation_details_part2a.md) - File Analyzer Agent implementation
- [**Implementation Details Part 2B**](agno_implementation_details_part2b.md) - Documentation Generator Agent implementation
- [**Implementation Details Part 2C**](agno_implementation_details_part2c.md) - Utilities, models, and integration

## Key Features

1. **Two-Stage Processing Pipeline**:
   - File analysis stage using Nova Micro for efficient classification and metadata extraction
   - Documentation generation stage using Claude 3.7 for high-quality documentation

2. **Dependency Analysis**:
   - Extracts and processes dependencies between files
   - Uses the dependency information to provide context for documentation generation

3. **Implementation Plan Generation**:
   - Generates detailed implementation plans as markdown files
   - Includes progress tracking and validation

4. **HSTC Standards Compliance**:
   - Ensures documentation follows the required structure and content
   - Validates all generated documentation against HSTC standards

## Next Steps

To implement the HSTC feature using these context files:

1. Create the project structure in `src/dbp_cli/commands/hstc_agno/`
2. Implement the core components as described in the implementation details
3. Integrate the HSTC command into the CLI framework
4. Test the implementation with various file types

The implementation should be done incrementally, starting with:

1. Basic file type detection and language identification
2. Comment extraction and metadata generation
3. Documentation generation for headers and functions
4. Implementation plan generation
5. Integration with the CLI

## Connection to Existing HSTC Feature

This Agno-based implementation is designed to work alongside the existing LangChain-based implementation, focusing specifically on:

1. Using Amazon Bedrock models (Nova and Claude)
2. Processing files individually rather than entire directories
3. Generating implementation plans for agentic editors to execute

By following these context files, you can create a modular and efficient implementation of the HSTC feature that leverages Agno's capabilities for LLM orchestration.
