# LLM Prompt Templates

This directory contains standardized prompt templates for the Internal LLM Tools used in the Documentation-Based Programming system.

## Template Structure

Each template follows a standardized format:

```markdown
# {Tool Name} Prompt Template

## System Instruction

{System instruction text with placeholders}

## User Query Format

{Expected user query format with placeholders}

## Example Usage

{Example of how this template would be used}

## Response Format

{Expected JSON response format with schema}
```

## Template Guidelines

1. **Placeholders**: Use double curly braces for placeholders (e.g., `{{file_path}}`)
2. **Formatting**: Maintain consistent markdown formatting across all templates
3. **Response Schema**: Always include a clear JSON schema for expected responses
4. **Comments**: Include explanatory comments using HTML comment syntax <!-- comment -->

## Available Templates

- `coordinator_get_codebase_context.md`: Template for extracting file header information
- `coordinator_get_codebase_changelog_context.md`: Template for analyzing code changes
- `coordinator_get_documentation_context.md`: Template for querying project documentation
- `coordinator_get_documentation_changelog_context.md`: Template for analyzing documentation changes
- `coordinator_get_expert_architect_advice.md`: Template for architectural guidance

## Integration Guidelines

These templates are designed to be used by the LLM coordination architecture. The templates should be:

1. Loaded as markdown text without pre-processing
2. Provided directly to the LLM with placeholders replaced by actual values
3. Preserved in their original format without helper formatting functions

## Placeholder Convention

- `{{query}}`: The user's original query
- `{{file_path}}`: Path to a specific file
- `{{file_content}}`: Content of a specific file
- `{{file_list}}`: List of file paths
- `{{context_type}}`: Type of context being requested
- `{{timestamp}}`: Current timestamp
- `{{output_format}}`: Desired output format
- `{{max_tokens}}`: Maximum response tokens
